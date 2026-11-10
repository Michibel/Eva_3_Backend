from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.clients.models import Client
from apps.orders.models import Order, OrderStatus
from apps.dispatch.models import Driver, Route, Dispatch


class DispatchFlowTest(TestCase):
    def setUp(self):
        self.driver_user = User.objects.create_user(
            username='repartidor_marriet',
            email='delivery@marriet.cl',
            password='Password123!',
            role=User.Role.REPARTIDOR
        )
        self.driver = Driver.objects.create(
            user=self.driver_user,
            license_number='LIC-9988',
            phone='+56955443322',
            vehicle='Mercedes Sprinter Frío'
        )
        self.client_obj = Client.objects.create(
            name='Embajada de Francia',
            email='reception@ambafrance.cl',
            address='Condell 65, Providencia'
        )
        self.order = Order.objects.create(
            client=self.client_obj,
            status=OrderStatus.LISTO,
            delivery_date=timezone.now() + timedelta(days=1),
            delivery_address=self.client_obj.address,
            total=Decimal('65000.00')
        )
        self.route = Route.objects.create(
            name='Ruta Providencia - Vitacura',
            date=timezone.now().date(),
            driver=self.driver,
            status='PROGRAMADA'
        )
        self.dispatch = Dispatch.objects.create(
            route=self.route,
            order=self.order,
            sequence=1,
            status='PENDIENTE'
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.driver_user)

    def test_start_route_and_dispatch(self):
        # Iniciar ruta
        res_r = self.api_client.post(f'/api/v1/routes/{self.route.id}/start/')
        self.assertEqual(res_r.status_code, status.HTTP_200_OK)
        self.route.refresh_from_db()
        self.assertEqual(self.route.status, 'EN_CURSO')

        # Iniciar despacho individual
        self.dispatch.status = 'PENDIENTE'
        self.dispatch.save()
        res_d = self.api_client.post(f'/api/v1/dispatches/{self.dispatch.id}/start/')
        self.assertEqual(res_d.status_code, status.HTTP_200_OK)
        self.dispatch.refresh_from_db()
        self.assertEqual(self.dispatch.status, 'EN_RUTA')

    def test_fail_dispatch(self):
        res = self.api_client.post(f'/api/v1/dispatches/{self.dispatch.id}/fail/', {
            'reason': 'Dirección cerrada por obras viales'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.dispatch.refresh_from_db()
        self.assertEqual(self.dispatch.status, 'FALLIDO')
        self.assertEqual(self.dispatch.failure_reason, 'Dirección cerrada por obras viales')

    def test_deliver_dispatch_with_base64_signature(self):
        png_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        res = self.api_client.post(f'/api/v1/dispatches/{self.dispatch.id}/deliver/', {
            'signature': png_base64,
            'photo_base64': png_base64,
            'notes': 'Entregado en recepción a guardia'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.dispatch.refresh_from_db()
        self.assertEqual(self.dispatch.status, 'ENTREGADO')
        self.assertIsNotNone(self.dispatch.delivered_at)
        self.assertTrue(bool(self.dispatch.signature))
        # Pedido también se actualiza a ENTREGADO
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.ENTREGADO)
