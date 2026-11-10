from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.clients.models import Client
from apps.products.models import Category, Product
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.production.models import KanbanColumn, ProductionCard, CardMovement


class ProductionFlowTest(TestCase):
    def setUp(self):
        self.baker = User.objects.create_user(
            username='pastry_chef',
            email='chef@marriet.cl',
            password='Password123!',
            role=User.Role.COCINERO
        )
        self.client_obj = Client.objects.create(name='Hotel Ritz', email='concierge@ritz.cl')
        self.category = Category.objects.create(name='Briocherie')
        self.product = Product.objects.create(
            category=self.category,
            name='Croissant Pur Beurre AOP',
            base_servings=12,
            base_price=Decimal('18000.00')
        )
        self.order = Order.objects.create(
            client=self.client_obj,
            status=OrderStatus.CONFIRMADO,
            delivery_date=timezone.now() + timedelta(days=1),
            total=Decimal('18000.00')
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            servings=12,
            unit_price=Decimal('18000.00')
        )
        self.col_recibido = KanbanColumn.objects.create(name='RECIBIDO', order=1, is_final=False)
        self.col_horneado = KanbanColumn.objects.create(name='HORNEADO_DECORADO', order=3, is_final=False)
        self.col_listo = KanbanColumn.objects.create(name='LISTO', order=5, is_final=True)

        self.card = ProductionCard.objects.create(
            order_item=self.order_item,
            column=self.col_recibido,
            assigned_to=self.baker
        )

        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.baker)

    def test_move_card_with_to_column_id_and_column_id(self):
        # Move using to_column_id
        res1 = self.api_client.post(f'/api/v1/production-cards/{self.card.id}/move/', {
            'to_column_id': self.col_horneado.id,
            'notes': 'Entrando al horno'
        })
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.assertEqual(self.card.column, self.col_horneado)
        self.assertIsNotNone(self.card.started_at)

        # Move using column_id (as frontend kanban.html sends)
        res2 = self.api_client.post(f'/api/v1/production-cards/{self.card.id}/move/', {
            'column_id': self.col_listo.id,
            'notes': 'Listo para despacho'
        })
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.assertEqual(self.card.column, self.col_listo)
        self.assertIsNotNone(self.card.completed_at)

    def test_register_waste(self):
        res = self.api_client.post(f'/api/v1/production-cards/{self.card.id}/waste/', {
            'waste_qty': '0.150',
            'waste_reason': 'Masa ligeramente tostada'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.assertEqual(self.card.waste_qty, Decimal('0.150'))
        self.assertEqual(self.card.waste_reason, 'Masa ligeramente tostada')

    def test_board_view(self):
        res = self.api_client.get('/api/v1/production-cards/board/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)
