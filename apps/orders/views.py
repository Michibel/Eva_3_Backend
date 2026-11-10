"""
Views para pedidos con confirmación y escalado BOM
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from .models import Order, OrderItem, Payment, Quotation, PaymentStatus, OrderStatus, PaymentMethod
from .filters import OrderFilter
from apps.clients.models import Client
from .serializers import (
    OrderSerializer, OrderCreateUpdateSerializer, OrderListSerializer,
    OrderItemSerializer, PaymentSerializer, PaymentCreateSerializer,
    QuotationSerializer, QuotationCreateUpdateSerializer
)


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            if request.user.role == 'CLIENTE':
                return obj.client.user == request.user
            return True
        return request.user.is_staff_member()


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('client', 'created_by', 'confirmed_by').prefetch_related('items__product', 'payments').all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ['client__name', 'client__email', 'id']
    ordering_fields = ['delivery_date', 'total', 'created_at', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return OrderCreateUpdateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENTE':
            return Order.objects.filter(client__user=user).select_related('client').prefetch_related('items__product', 'payments')
        return Order.objects.select_related('client', 'created_by', 'confirmed_by').prefetch_related('items__product', 'payments').all()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirmar pedido: valida stock, descuenta BOM escalado, cambia estado a CONFIRMADO
        POST /api/v1/orders/{id}/confirm/
        """
        order = self.get_object()

        if order.status != Order.OrderStatus.COTIZACION:
            return Response(
                {'detail': 'Solo se pueden confirmar pedidos en estado Cotización.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order.confirm(user=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='validate-stock')
    def validate_stock(self, request, pk=None):
        """Valida stock de todos los items del pedido antes de confirmar"""
        order = self.get_object()
        missing = []
        items_summary = []

        for item in order.items.select_related('product').all():
            has_stock, shortages = item.product.check_stock_for_servings(item.servings, item.quantity)
            items_summary.append({
                'product_name': item.product.name,
                'servings': item.servings,
                'quantity': item.quantity,
                'bom_summary': f"{len(item.scaled_bom)} insumos requeridos",
            })
            if not has_stock:
                for s in shortages:
                    missing.append({
                        'ingredient_name': s['ingredient'],
                        'missing_quantity': s['shortage'],
                        'unit': s['unit']
                    })

        return Response({
            'ok': len(missing) == 0,
            'has_stock': len(missing) == 0,
            'items': items_summary,
            'missing': missing
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancelar pedido"""
        order = self.get_object()
        if order.status in [Order.OrderStatus.ENTREGADO, Order.OrderStatus.CANCELADO]:
            return Response(
                {'detail': 'No se puede cancelar un pedido entregado o ya cancelado.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = Order.OrderStatus.CANCELADO
        order.save()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Agregar pago al pedido"""
        order = self.get_object()
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(order=order)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-orders')
    def my_orders(self, request):
        """
        Obtener pedidos del cliente autenticado
        GET /api/v1/orders/my-orders/
        """
        user = request.user
        if user.role != 'CLIENTE':
            return Response({'detail': 'Solo disponible para clientes.'}, status=status.HTTP_403_FORBIDDEN)

        client = getattr(user, 'client_profile', None)
        if not client:
            return Response({'detail': 'Perfil de cliente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        orders = Order.objects.filter(client=client).select_related('client').prefetch_related('items__product', 'payments').order_by('-created_at')

        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = OrderListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.select_related('order', 'product').all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order', 'product', 'servings']
    ordering = ['order', 'id']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            from .serializers import OrderItemCreateSerializer
            return OrderItemCreateSerializer
        return OrderItemSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('order').all()
    serializer_class = PaymentSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order', 'method', 'status']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENTE':
            client = getattr(user, 'client_profile', None)
            if client:
                return Payment.objects.filter(order__client=client).select_related('order')
            return Payment.objects.none()
        return Payment.objects.select_related('order').all()

    @action(detail=False, methods=['get'], url_path='my-pending')
    def my_pending(self, request):
        """
        Obtener pagos pendientes del cliente autenticado
        GET /api/v1/payments/my-pending/
        """
        user = request.user
        if user.role != 'CLIENTE':
            return Response({'detail': 'Solo disponible para clientes.'}, status=status.HTTP_403_FORBIDDEN)

        client = getattr(user, 'client_profile', None)
        if not client:
            return Response({'detail': 'Perfil de cliente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        payments = Payment.objects.filter(
            order__client=client,
            status=PaymentStatus.PENDIENTE
        ).select_related('order').order_by('-created_at')

        page = self.paginate_queryset(payments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-history')
    def my_history(self, request):
        """
        Obtener historial de pagos del cliente autenticado
        GET /api/v1/payments/my-history/
        """
        user = request.user
        if user.role != 'CLIENTE':
            return Response({'detail': 'Solo disponible para clientes.'}, status=status.HTTP_403_FORBIDDEN)

        client = getattr(user, 'client_profile', None)
        if not client:
            return Response({'detail': 'Perfil de cliente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        payments = Payment.objects.filter(
            order__client=client
        ).select_related('order').order_by('-created_at')

        page = self.paginate_queryset(payments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        Estadísticas de pagos para dashboard
        GET /api/v1/payments/stats/
        """
        user = request.user
        if user.role == 'CLIENTE':
            client = getattr(user, 'client_profile', None)
            if not client:
                return Response({'detail': 'Perfil de cliente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            payments = Payment.objects.filter(order__client=client)
        else:
            payments = Payment.objects.all()

        total_payments = payments.count()
        total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
        by_method = payments.values('method').annotate(count=Count('id'), total=Sum('amount'))
        by_status = payments.values('status').annotate(count=Count('id'), total=Sum('amount'))

        return Response({
            'total_payments': total_payments,
            'total_amount': float(total_amount),
            'by_method': list(by_method),
            'by_status': list(by_status),
        })

    @action(detail=False, methods=['get', 'post'], url_path='methods')
    def payment_methods(self, request):
        """Métodos de pago guardados del cliente"""
        user = request.user
        profile = getattr(user, 'profile', None)
        if not profile:
            return Response([])
        if not isinstance(profile.preferences, dict):
            profile.preferences = {}
        methods = profile.preferences.get('saved_payment_methods', [
            {
                'id': 'webpay-default',
                'name': 'WebPay Plus / Transbank',
                'type': 'WEBPAY',
                'card_brand': 'Visa / Mastercard',
                'last4': '4242',
                'is_default': True
            }
        ])

        if request.method == 'POST':
            new_method = {
                'id': f"method-{timezone.now().timestamp()}",
                'name': request.data.get('name', 'Tarjeta'),
                'type': request.data.get('type', 'WEBPAY'),
                'card_brand': request.data.get('card_brand', 'Visa'),
                'last4': request.data.get('last4', '1234'),
                'is_default': False,
            }
            methods.append(new_method)
            profile.preferences['saved_payment_methods'] = methods
            profile.save()
            return Response(new_method, status=status.HTTP_201_CREATED)

        return Response(methods)

    @action(detail=False, methods=['post'], url_path=r'methods/(?P<method_id>[^/.]+)/set_default')
    def set_default_method(self, request, method_id=None):
        """Marcar método como default"""
        profile = getattr(request.user, 'profile', None)
        if profile and isinstance(profile.preferences, dict):
            methods = profile.preferences.get('saved_payment_methods', [])
            for m in methods:
                m['is_default'] = (str(m.get('id')) == str(method_id))
            profile.preferences['saved_payment_methods'] = methods
            profile.save()
        return Response({'status': 'ok'})

    @action(detail=False, methods=['delete'], url_path=r'methods/(?P<method_id>[^/.]+)')
    def delete_method(self, request, method_id=None):
        """Eliminar método guardado"""
        profile = getattr(request.user, 'profile', None)
        if profile and isinstance(profile.preferences, dict):
            methods = profile.preferences.get('saved_payment_methods', [])
            methods = [m for m in methods if str(m.get('id')) != str(method_id)]
            profile.preferences['saved_payment_methods'] = methods
            profile.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='refund')
    def refund(self, request, pk=None):
        """Reembolsar un pago"""
        payment = self.get_object()
        amount = request.data.get('amount', payment.amount)
        reason = request.data.get('reason', '')
        payment.status = PaymentStatus.REEMBOLSADO
        payment.save()
        return Response({'detail': 'Pago reembolsado correctamente.', 'amount': amount, 'reason': reason})


class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.select_related('client', 'created_by').all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client', 'status']
    search_fields = ['client__name', 'client__email', 'id']
    ordering_fields = ['valid_until', 'total', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENTE':
            return Quotation.objects.filter(client__user=user).select_related('client', 'created_by')
        return Quotation.objects.select_related('client', 'created_by').all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return QuotationCreateUpdateSerializer
        return QuotationSerializer

    @action(detail=True, methods=['post'])
    def convert_to_order(self, request, pk=None):
        """Convertir cotización en pedido"""
        quotation = self.get_object()
        if quotation.status in ['RECHAZADA', 'EXPIRADA']:
            return Response(
                {'detail': 'No se puede convertir una cotización rechazada o expirada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order = quotation.convert_to_order(user=request.user)
        return Response(OrderSerializer(order).data)