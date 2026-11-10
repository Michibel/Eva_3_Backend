"""
Views para clientes
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Client, ClientPreference
from .serializers import ClientSerializer, ClientCreateSerializer, ClientListSerializer, ClientPreferenceSerializer


class IsStaffOrReadOnly(permissions.BasePermission):
    """Staff puede escribir, clientes solo leen sus propios datos"""
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Cliente puede ver su propio perfil
            if request.user.role == 'CLIENTE':
                return hasattr(request.user, 'client_profile') and request.user.client_profile == obj
            return request.user.is_staff_member()
        return request.user.is_staff_member()


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.prefetch_related('preferences').all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'email', 'created_at', 'total_orders']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'create':
            return ClientCreateSerializer
        elif self.action == 'list':
            return ClientListSerializer
        return ClientSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENTE':
            return Client.objects.filter(user=user).prefetch_related('preferences')
        return Client.objects.prefetch_related('preferences').all()

    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        """Obtener pedidos del cliente"""
        client = self.get_object()
        from apps.orders.serializers import OrderListSerializer
        orders = client.orders.all()
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)


class ClientPreferenceViewSet(viewsets.ModelViewSet):
    queryset = ClientPreference.objects.select_related('client').all()
    serializer_class = ClientPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['client', 'key']
    ordering = ['client', 'key']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return ClientPreference.objects.select_related('client').all()
        elif user.role == 'CLIENTE':
            return ClientPreference.objects.filter(client__user=user).select_related('client')
        return ClientPreference.objects.none()