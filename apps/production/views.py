"""
Views para producción Kanban con drag & drop
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from .models import KanbanColumn, ProductionCard, CardMovement
from .serializers import (
    KanbanColumnSerializer, ProductionCardSerializer,
    ProductionCardMoveSerializer, CardMovementSerializer
)
from apps.orders.models import OrderItem


class ProductionCardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff_member()


class KanbanColumnViewSet(viewsets.ModelViewSet):
    queryset = KanbanColumn.objects.annotate(cards_count=Count('cards')).all()
    serializer_class = KanbanColumnSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None
    filter_backends = [filters.OrderingFilter]
    ordering = ['order']


class ProductionCardViewSet(viewsets.ModelViewSet):
    queryset = ProductionCard.objects.select_related(
        'order_item__product', 'order_item__order__client',
        'column', 'assigned_to'
    ).all()
    serializer_class = ProductionCardSerializer
    pagination_class = ProductionCardPagination
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['column', 'assigned_to']
    ordering_fields = ['column__order', 'created_at']
    ordering = ['column__order', 'id']

    def get_serializer_class(self):
        if self.action == 'move':
            return ProductionCardMoveSerializer
        return ProductionCardSerializer

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """
        Mover tarjeta entre columnas (Drag & Drop)
        POST /api/v1/production-cards/{id}/move/
        Body: {"to_column_id": 3, "notes": "..."}
        """
        card = self.get_object()
        serializer = ProductionCardMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_column_id = serializer.validated_data['to_column_id']
        notes = serializer.validated_data.get('notes', '')

        try:
            to_column = KanbanColumn.objects.get(id=to_column_id)
        except KanbanColumn.DoesNotExist:
            return Response({'detail': 'Columna destino no existe.'}, status=status.HTTP_404_NOT_FOUND)

        if card.column == to_column:
            return Response({'detail': 'La tarjeta ya está en esa columna.'}, status=status.HTTP_400_BAD_REQUEST)

        from_column = card.column
        card.column = to_column

        # Actualizar timestamps
        if from_column.name == 'RECIBIDO' and to_column.name != 'RECIBIDO':
            card.started_at = timezone.now()
        if to_column.is_final:
            card.completed_at = timezone.now()

        card.save()

        # Registrar movimiento
        CardMovement.objects.create(
            card=card,
            from_column=from_column,
            to_column=to_column,
            moved_by=request.user,
            notes=notes,
        )

        return Response(ProductionCardSerializer(card).data)

    @action(detail=True, methods=['post'], url_path='waste')
    def register_waste(self, request, pk=None):
        """Registrar merma en tarjeta"""
        card = self.get_object()
        waste_qty = request.data.get('waste_qty')
        waste_reason = request.data.get('waste_reason', '')

        if waste_qty is None:
            return Response({'detail': 'waste_qty es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            waste_qty = float(waste_qty)
            if waste_qty < 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'detail': 'Cantidad de merma inválida.'}, status=status.HTTP_400_BAD_REQUEST)

        card.waste_qty = waste_qty
        card.waste_reason = waste_reason
        card.save()

        # Registrar movimiento de stock como merma
        from apps.ingredients.models import StockMovement, Ingredient
        # Aquí se podría registrar la merma en ingredientes si se desea

        return Response(ProductionCardSerializer(card).data)

    @action(detail=False, methods=['get'])
    def board(self, request):
        """
        Vista completa del tablero Kanban agrupado por columnas
        GET /api/v1/production-cards/board/
        """
        columns = KanbanColumn.objects.prefetch_related(
            'cards__order_item__product', 'cards__assigned_to'
        ).all()

        data = []
        for column in columns:
            cards = ProductionCardSerializer(column.cards.all(), many=True).data
            data.append({
                'column': KanbanColumnSerializer(column).data,
                'cards': cards,
            })

        return Response(data)


class CardMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CardMovement.objects.select_related('card', 'from_column', 'to_column', 'moved_by').all()
    serializer_class = CardMovementSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['card', 'from_column', 'to_column']
    ordering = ['-moved_at']