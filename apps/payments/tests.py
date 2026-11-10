from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.clients.models import Client
from apps.orders.models import Order, OrderStatus
from apps.payments.models import WebPayTransaction


class WebPayTransactionTest(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='cajero_marriet',
            email='caja@marriet.cl',
            password='Password123!',
            role=User.Role.VENTAS
        )
        self.client_obj = Client.objects.create(name='Cliente Gourmet', email='gourmet@cliente.cl')
        self.order = Order.objects.create(
            client=self.client_obj,
            status=OrderStatus.COTIZACION,
            delivery_date=timezone.now() + timedelta(days=3),
            total=Decimal('42000.00')
        )
        self.token_sample = '01ab5678cd90ef1234567890abcdef1234567890abcdef1234567890abcdef'
        self.tx = WebPayTransaction.objects.create(
            order=self.order,
            buy_order='DA-1001-TEST',
            session_id='sess-test-123',
            amount=Decimal('42000.00'),
            status='INICIADA',
            token=self.token_sample
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.staff_user)

    def test_lookup_by_id_and_by_token(self):
        # Lookup by integer ID
        res_id = self.api_client.get(f'/api/v1/webpay-transactions/{self.tx.id}/')
        self.assertEqual(res_id.status_code, status.HTTP_200_OK)
        self.assertEqual(res_id.data['token'], self.token_sample)

        # Lookup by string Token (as frontend does)
        res_token = self.api_client.get(f'/api/v1/webpay-transactions/{self.token_sample}/')
        self.assertEqual(res_token.status_code, status.HTTP_200_OK)
        self.assertEqual(res_token.data['id'], self.tx.id)

    def test_cancel_transaction_by_token(self):
        res = self.api_client.post(f'/api/v1/webpay-transactions/{self.token_sample}/cancel/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, 'CANCELADA')

    def test_conciliation_endpoint(self):
        today_str = timezone.now().date().strftime('%Y-%m-%d')
        res = self.api_client.post('/api/v1/webpay-transactions/conciliation/', {'date': today_str})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('total_transactions', res.data)
        self.assertGreaterEqual(res.data['total_transactions'], 1)
