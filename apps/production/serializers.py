"""
Serializers para producción Kanban
"""
from rest_framework import serializers
from .models import KanbanColumn, ProductionCard, CardMovement
from apps.orders.serializers import OrderItemSerializer


class KanbanColumnSerializer(serializers.ModelSerializer):
    cards_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = KanbanColumn
        fields = ['id', 'name', 'order', 'color', 'is_final', 'cards_count', 'created_at']
        read_only_fields = ['created_at']


class CardMovementSerializer(serializers.ModelSerializer):
    from_column_name = serializers.CharField(source='from_column.get_name_display', read_only=True)
    to_column_name = serializers.CharField(source='to_column.get_name_display', read_only=True)
    to_column_color = serializers.CharField(source='to_column.color', read_only=True)
    moved_by_name = serializers.CharField(source='moved_by.get_full_name', read_only=True)
    moved_by_username = serializers.CharField(source='moved_by.username', read_only=True)

    class Meta:
        model = CardMovement
        fields = ['id', 'card', 'from_column', 'from_column_name', 'to_column', 'to_column_name',
                  'to_column_color', 'moved_by', 'moved_by_name', 'moved_by_username', 'moved_at', 'notes']
        read_only_fields = ['moved_at']


class ProductionCardSerializer(serializers.ModelSerializer):
    order_item_detail = OrderItemSerializer(source='order_item', read_only=True)
    column_detail = KanbanColumnSerializer(source='column', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    movements = CardMovementSerializer(many=True, read_only=True)

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        if 'column_id' in data and 'column' not in data:
            data['column'] = data.pop('column_id')
        if data.get('assigned_to') == '':
            data['assigned_to'] = None
        data.pop('priority', None)
        return super().to_internal_value(data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.order_item:
            oi = instance.order_item
            ret['order_item'] = {
                'id': oi.id,
                'order_id': oi.order_id,
                'product_name': oi.product.name if oi.product else 'Producto',
                'servings': oi.servings,
                'delivery_date': str(oi.order.delivery_date) if oi.order and oi.order.delivery_date else None,
                'client_name': oi.order.client.name if oi.order and oi.order.client else 'Cliente',
                'bom_snapshot_scaled': oi.bom_snapshot_scaled,
            }
        if instance.assigned_to:
            ret['assigned_to'] = {
                'id': instance.assigned_to.id,
                'username': instance.assigned_to.username,
                'name': instance.assigned_to.get_full_name() or instance.assigned_to.username,
                'full_name': instance.assigned_to.get_full_name() or instance.assigned_to.username,
            }
        else:
            ret['assigned_to'] = None
        return ret

    class Meta:
        model = ProductionCard
        fields = ['id', 'order_item', 'order_item_detail', 'column', 'column_detail',
                  'assigned_to', 'assigned_to_name', 'movements', 'started_at', 'completed_at',
                  'notes', 'waste_qty', 'waste_reason', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ProductionCardMoveSerializer(serializers.Serializer):
    """Serializer para mover tarjeta entre columnas"""
    to_column_id = serializers.IntegerField(required=False)
    column_id = serializers.IntegerField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if 'to_column_id' not in attrs and 'column_id' not in attrs:
            raise serializers.ValidationError({'to_column_id': 'Se requiere to_column_id o column_id.'})
        if 'to_column_id' not in attrs:
            attrs['to_column_id'] = attrs['column_id']
        return attrs

    to_column_name = serializers.CharField(source='to_column.get_name_display', read_only=True)
    moved_by_name = serializers.CharField(source='moved_by.get_full_name', read_only=True)

    class Meta:
        model = CardMovement
        fields = ['id', 'card', 'from_column', 'from_column_name', 'to_column', 'to_column_name',
                  'moved_by', 'moved_by_name', 'moved_at', 'notes']
        read_only_fields = ['moved_at']
