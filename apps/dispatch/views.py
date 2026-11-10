"""
Views para despacho y rutas con confirmación de entrega
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Driver, Route, Dispatch
from apps.orders.models import Order, OrderStatus
from .serializers import (
    DriverSerializer, RouteSerializer, RouteCreateUpdateSerializer,
    DispatchSerializer, DispatchDeliverSerializer
)


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff_member()


class IsDriverOrStaff(permissions.BasePermission):
    """Conductores pueden ver sus rutas y confirmar entregas"""
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            if request.user.role == 'REPARTIDOR':
                # Verificar si es su ruta
                if hasattr(request.user, 'driver_profile'):
                    return obj.route.driver == request.user.driver_profile
            return True
        # Para confirmar entrega, conductor dueño o staff
        if request.user.role == 'REPARTIDOR':
            if hasattr(request.user, 'driver_profile'):
                return obj.route.driver == request.user.driver_profile
        return request.user.is_staff_member()


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.select_related('user').all()
    serializer_class = DriverSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__first_name', 'user__last_name', 'license_number']
    ordering = ['user__first_name']


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related('driver__user', 'created_by').prefetch_related('dispatches__order__client').all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'driver', 'date']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date', 'name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RouteCreateUpdateSerializer
        return RouteSerializer

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Iniciar ruta"""
        route = self.get_object()
        if route.status != 'PROGRAMADA':
            return Response({'detail': 'Solo se pueden iniciar rutas programadas.'}, status=status.HTTP_400_BAD_REQUEST)
        route.status = 'EN_CURSO'
        route.started_at = timezone.now()
        route.save()
        # Actualizar despachos a EN_RUTA
        route.dispatches.filter(status='PENDIENTE').update(status='EN_RUTA')
        return Response(RouteSerializer(route).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Completar ruta"""
        route = self.get_object()
        if route.status != 'EN_CURSO':
            return Response({'detail': 'Solo se pueden completar rutas en curso.'}, status=status.HTTP_400_BAD_REQUEST)
        route.status = 'COMPLETADA'
        route.completed_at = timezone.now()
        route.save()
        return Response(RouteSerializer(route).data)

    @action(detail=True, methods=['get'])
    def dispatches(self, request, pk=None):
        """Obtener despachos de una ruta"""
        route = self.get_object()
        dispatches = route.dispatches.select_related('order__client').order_by('sequence')
        from .serializers import DispatchListSerializer
        serializer = DispatchListSerializer(dispatches, many=True)
        return Response(serializer.data)


class DispatchViewSet(viewsets.ModelViewSet):
    queryset = Dispatch.objects.select_related('route__driver__user', 'order__client').all()
    permission_classes = [IsDriverOrStaff]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['route', 'status']
    ordering_fields = ['route__date', 'sequence', 'delivered_at']
    ordering = ['route', 'sequence']

    def get_queryset(self):
        qs = super().get_queryset()
        date = self.request.query_params.get('route_date') or self.request.query_params.get('date')
        if date:
            qs = qs.filter(route__date=date)
        return qs

    def get_serializer_class(self):
        if self.action == 'deliver':
            return DispatchDeliverSerializer
        elif self.action == 'list':
            from .serializers import DispatchListSerializer
            return DispatchListSerializer
        return DispatchSerializer

    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        """
        Confirmar entrega con firma digital y foto
        POST /api/v1/dispatches/{id}/deliver/
        """
        dispatch = self.get_object()

        if dispatch.status in ['ENTREGADO', 'FALLIDO']:
            return Response(
                {'detail': 'Este despacho ya fue procesado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DispatchDeliverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dispatch.status = 'ENTREGADO'
        dispatch.delivered_at = timezone.now()
        dispatch.signature = serializer.validated_data['signature']
        if serializer.validated_data.get('photo'):
            dispatch.photo = serializer.validated_data['photo']
        if serializer.validated_data.get('gps_lat'):
            dispatch.gps_lat = serializer.validated_data['gps_lat']
        if serializer.validated_data.get('gps_lng'):
            dispatch.gps_lng = serializer.validated_data['gps_lng']
        dispatch.notes = serializer.validated_data.get('notes', '')
        dispatch.save()

        # Actualizar pedido a ENTREGADO si todos sus despachos están entregados
        order = dispatch.order
        if not order.dispatches.exclude(status='ENTREGADO').exists():
            order.status = OrderStatus.ENTREGADO
            order.save()

        return Response(DispatchSerializer(dispatch).data)

    @action(detail=True, methods=['post'])
    def fail(self, request, pk=None):
        """Marcar despacho como fallido"""
        dispatch = self.get_object()
        if dispatch.status in ['ENTREGADO', 'FALLIDO']:
            return Response({'detail': 'Despacho ya procesado.'}, status=status.HTTP_400_BAD_REQUEST)

        dispatch.status = 'FALLIDO'
        dispatch.failure_reason = request.data.get('failure_reason') or request.data.get('reason', '')
        dispatch.save()
        return Response(DispatchSerializer(dispatch).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Iniciar despacho (cambiar a EN_RUTA)"""
        dispatch = self.get_object()
        if dispatch.status != 'PENDIENTE':
            return Response({'detail': 'Solo se pueden iniciar despachos pendientes.'}, status=status.HTTP_400_BAD_REQUEST)

        dispatch.status = 'EN_RUTA'
        dispatch.save()
        return Response(DispatchSerializer(dispatch).data)