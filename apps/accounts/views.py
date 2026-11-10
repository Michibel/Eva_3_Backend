"""
Views para cuentas y usuarios
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User, Profile, AuditLog
from .serializers import UserSerializer, UserCreateSerializer, UserListSerializer, ProfileSerializer, AuditLogSerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    """Solo admins pueden crear/modificar/eliminar usuarios"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role == 'ADMIN'


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('profile').all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_verified', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['username', 'email', 'date_joined', 'role']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'list':
            return UserListSerializer
        return UserSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return User.objects.select_related('profile').all()
        elif user.role == 'CLIENTE':
            # Clientes solo se ven a sí mismos
            return User.objects.filter(id=user.id).select_related('profile')
        else:
            # Staff ve usuarios activos
            return User.objects.filter(is_active=True).select_related('profile')

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener perfil del usuario autenticado"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_me(self, request):
        """Actualizar propio perfil"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """Cambiar contraseña del usuario autenticado"""
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'detail': 'Contraseña actual y nueva son requeridas.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(old_password):
            return Response({'detail': 'Contraseña actual incorrecta.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'detail': 'La nueva contraseña debe tener al menos 8 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({'detail': 'Contraseña cambiada correctamente.'})

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar usuario (solo admin)"""
        if request.user.role != 'ADMIN':
            return Response({'detail': 'No tiene permisos.'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({'is_active': user.is_active})


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user').all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return Profile.objects.select_related('user').all()
        return Profile.objects.filter(user=self.request.user)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['action', 'model_name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return AuditLog.objects.select_related('user').all()
        return AuditLog.objects.none()


@method_decorator(csrf_exempt, name='dispatch')
class GetJWTTokensView(LoginRequiredMixin, View):
    """
    Obtener tokens JWT usando autenticación de sesión.
    Se usa después de login exitoso para obtener access/refresh tokens para API calls.
    POST /api/v1/accounts/jwt-tokens/
    """
    def post(self, request, *args, **kwargs):
        refresh = RefreshToken.for_user(request.user)
        return JsonResponse({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })