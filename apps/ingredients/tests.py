from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.ingredients.models import Supplier, Ingredient, StockMovement, PurchaseOrder, PurchaseOrderItem


class IngredientModelTest(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Harinas del Sur',
            contact='Juan Molinero',
            phone='+56911223344',
            email='ventas@harinasdelsur.cl'
        )
        self.harina = Ingredient.objects.create(
            name='Harina de Trigo T55',
            unit='kg',
            current_stock=Decimal('50.000'),
            min_stock=Decimal('20.000'),
            unit_cost=Decimal('1200.00'),
            supplier=self.supplier
        )

    def test_add_and_remove_stock(self):
        self.harina.add_stock(Decimal('30.000'), movement_type='ENTRADA', reference='Compra 101')
        self.assertEqual(self.harina.current_stock, Decimal('80.000'))
        self.assertEqual(StockMovement.objects.filter(ingredient=self.harina, type='ENTRADA').count(), 1)

        self.harina.remove_stock(Decimal('70.000'), movement_type='SALIDA', reference='Horneado 201')
        self.assertEqual(self.harina.current_stock, Decimal('10.000'))
        self.assertTrue(self.harina.is_low_stock)

        # Retirar mas del disponible lanza ValueError
        with self.assertRaises(ValueError):
            self.harina.remove_stock(Decimal('50.000'))


class IngredientAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='bodeguero',
            email='bodega@marriet.cl',
            password='Password123!',
            role=User.Role.BODEGA
        )
        self.client.force_authenticate(user=self.user)
        self.supplier = Supplier.objects.create(name='Mantequilla Premium')
        self.mantequilla = Ingredient.objects.create(
            name='Mantequilla Francesa Elle & Vire',
            unit='kg',
            current_stock=Decimal('5.000'),
            min_stock=Decimal('10.000'),  # Bajo stock
            unit_cost=Decimal('8500.00'),
            supplier=self.supplier
        )

    def test_low_stock_action(self):
        res = self.client.get('/api/v1/ingredients/low_stock/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], 'Mantequilla Francesa Elle & Vire')

    def test_ingredient_movements_action(self):
        # Registrar un movimiento
        self.mantequilla.add_stock(Decimal('15.000'), user=self.user)
        res = self.client.get(f'/api/v1/ingredients/{self.mantequilla.id}/movements/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movements = res.data.get('results', res.data)
        self.assertEqual(len(movements), 1)

    def test_purchase_order_flow(self):
        from django.utils import timezone
        from datetime import timedelta
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            created_by=self.user,
            expected_date=timezone.now().date() + timedelta(days=5),
            total=Decimal('85000.00')
        )
        item = PurchaseOrderItem.objects.create(
            order=po,
            ingredient=self.mantequilla,
            quantity=Decimal('10.000'),
            unit_cost=Decimal('8500.00')
        )
        # Confirmar orden
        conf_res = self.client.post(f'/api/v1/purchase-orders/{po.id}/confirm/')
        self.assertEqual(conf_res.status_code, status.HTTP_200_OK)
        po.refresh_from_db()
        self.assertEqual(po.status, 'ENVIADA')

        # Recibir item
        rec_res = self.client.post(f'/api/v1/purchase-orders/{po.id}/receive_item/', {
            'item_id': item.id,
            'quantity': 10
        })
        self.assertEqual(rec_res.status_code, status.HTTP_200_OK)
        self.mantequilla.refresh_from_db()
        self.assertEqual(self.mantequilla.current_stock, Decimal('15.000'))
