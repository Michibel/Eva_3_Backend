"""
Views para ingredientes, stock y compras
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, F
from .models import Supplier, Ingredient, StockMovement, PurchaseOrder, PurchaseOrderItem
from .serializers import (
    SupplierSerializer, IngredientSerializer, IngredientCreateUpdateSerializer,
    IngredientListSerializer, StockMovementSerializer, StockMovementCreateSerializer,
    PurchaseOrderSerializer, PurchaseOrderCreateUpdateSerializer,
    PurchaseOrderItemSerializer
)


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff_member()


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.annotate(ingredients_count=Count('ingredients')).all()
    serializer_class = SupplierSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact', 'email']
    ordering = ['name']


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.select_related('supplier').all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['unit', 'is_perishable', 'is_active', 'supplier']
    search_fields = ['name']
    ordering_fields = ['name', 'current_stock', 'unit_cost', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return IngredientCreateUpdateSerializer
        elif self.action == 'list':
            return IngredientListSerializer
        return IngredientSerializer

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Ingredientes con stock bajo o sin stock"""
        ingredients = Ingredient.objects.filter(
            Q(current_stock__lte=F('min_stock'))
        ).select_related('supplier')
        serializer = IngredientListSerializer(ingredients, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        """Agregar stock manualmente"""
        ingredient = self.get_object()
        serializer = StockMovementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ingredient.add_stock(
            quantity=serializer.validated_data['quantity'],
            movement_type=serializer.validated_data.get('type', 'ENTRADA'),
            reference=serializer.validated_data.get('reference', ''),
            notes=serializer.validated_data.get('notes', ''),
            user=request.user,
        )
        return Response(IngredientSerializer(ingredient).data)

    @action(detail=True, methods=['post'])
    def remove_stock(self, request, pk=None):
        """Quitar stock manualmente"""
        ingredient = self.get_object()
        serializer = StockMovementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ingredient.remove_stock(
                quantity=serializer.validated_data['quantity'],
                movement_type=serializer.validated_data.get('type', 'SALIDA'),
                reference=serializer.validated_data.get('reference', ''),
                notes=serializer.validated_data.get('notes', ''),
                user=request.user,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(IngredientSerializer(ingredient).data)

    @action(detail=True, methods=['get'])
    def movements(self, request, pk=None):
        """Movimientos de stock del insumo"""
        ingredient = self.get_object()
        movements = ingredient.stock_movements.select_related('created_by').order_by('-created_at')
        page = self.paginate_queryset(movements)
        if page is not None:
            serializer = StockMovementSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = StockMovementSerializer(movements, many=True)
        return Response(serializer.data)


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related('ingredient', 'created_by').all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['ingredient', 'type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return StockMovementCreateSerializer
        return StockMovementSerializer


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier', 'created_by').prefetch_related('items__ingredient').all()
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['supplier', 'status']
    ordering_fields = ['expected_date', 'created_at', 'total']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PurchaseOrderCreateUpdateSerializer
        return PurchaseOrderSerializer

    @action(detail=True, methods=['post'])
    def receive_item(self, request, pk=None):
        """Recibir item de orden de compra"""
        order = self.get_object()
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')

        if not item_id or not quantity:
            return Response({'detail': 'item_id y quantity son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            item = order.items.get(id=item_id)
        except PurchaseOrderItem.DoesNotExist:
            return Response({'detail': 'Item no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'detail': 'Cantidad inválida.'}, status=status.HTTP_400_BAD_REQUEST)

        item.receive(quantity, user=request.user)
        order.refresh_from_db()
        return Response(PurchaseOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirmar orden de compra"""
        order = self.get_object()
        if order.status != 'BORRADOR':
            return Response({'detail': 'Solo se pueden confirmar órdenes en borrador.'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'ENVIADA'
        order.save()
        return Response(PurchaseOrderSerializer(order).data)