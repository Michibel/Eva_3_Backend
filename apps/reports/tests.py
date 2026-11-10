from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.clients.models import Client
from apps.orders.models import Order, OrderStatus


class ReportsTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_director',
            email='director@marriet.cl',
            password='Password123!',
            role=User.Role.ADMIN
        )
        self.client_obj = Client.objects.create(name='Palacio Cousiño', email='eventos@cousino.cl')
        self.order = Order.objects.create(
            client=self.client_obj,
            status=OrderStatus.CONFIRMADO,
            delivery_date=timezone.now() + timedelta(days=2),
            total=Decimal('150000.00')
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.admin)

    def test_dashboard_endpoint(self):
        res = self.api_client.get('/api/v1/reports/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('kpis', res.data)
        self.assertIn('recent_orders', res.data)

    def test_by_type_sales(self):
        res = self.api_client.get('/api/v1/reports/sales/?period=month')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('summary', res.data)
        self.assertIn('chart_data', res.data)

    def test_export_endpoints(self):
        # CSV Export
        csv_res = self.api_client.get('/api/v1/reports/sales/export/?format=csv&period=month')
        self.assertEqual(csv_res.status_code, status.HTTP_200_OK)
        self.assertTrue(csv_res.has_header('Content-Disposition'))
        self.assertIn('text/csv', csv_res['Content-Type'])

        # Excel Export
        excel_res = self.api_client.get('/api/v1/reports/sales/export/?format=excel&period=month')
        self.assertEqual(excel_res.status_code, status.HTTP_200_OK)
        self.assertTrue(excel_res.has_header('Content-Disposition'))

        # PDF Export
        pdf_res = self.api_client.get('/api/v1/reports/sales/export/?format=pdf&period=month')
        self.assertEqual(pdf_res.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_res['Content-Type'], 'application/pdf')
