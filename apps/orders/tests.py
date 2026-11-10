from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.clients.models import Client
from apps.products.models import Category, Product, BOMItem
from apps.ingredients.models import Supplier, Ingredient
from apps.orders.models import Order, OrderItem, OrderStatus, Quotation, Payment, PaymentMethod, PaymentStatus


class OrderFlowTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='marriet_patron',
            email='patron@marriet.cl',
            password='Password123!',
            role=User.Role.CLIENTE
        )
        self.staff_user = User.objects.create_user(
            username='marriet_ventas',
            email='ventas@marriet.cl',
            password='Password123!',
            role=User.Role.VENTAS
        )
        self.client_profile = Client.objects.create(
            user=self.client_user,
            name='Marriet VIP Client',
            email='patron@marriet.cl',
            phone='+56999887766',
            address='Av. Vitacura 3565, Santiago'
        )
        self.category = Category.objects.create(name='Haute Pastry')
        self.product = Product.objects.create(
            category=self.category,
            name='Mille-Feuille Vanille Bourbon',
            base_servings=12,
            base_price=Decimal('35000.00'),
            sale_price=Decimal('35000.00')
        )
        self.supplier = Supplier.objects.create(name='Vainilla Madagascar')
        self.vanilla = Ingredient.objects.create(
            name='Vaina de Vainilla Bourbon',
            unit='un',
            current_stock=Decimal('100.000'),
            min_stock=Decimal('10.000'),
            unit_cost=Decimal('2500.00'),
            supplier=self.supplier
        )
        BOMItem.objects.create(
            product=self.product,
            ingredient=self.vanilla,
            quantity=Decimal('2.000'),
            unit='un'
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.staff_user)

    def test_quotation_conversion_to_order(self):
        q = Quotation.objects.create(
            client=self.client_profile,
            items=[{
                'product_id': self.product.id,
                'quantity': 2,
                'servings': 12,
                'unit_price': 35000.0,
                'custom_notes': 'Sin azúcar flor arriba'
            }],
            valid_until=timezone.now().date() + timedelta(days=15),
            status='BORRADOR',
            subtotal=Decimal('70000.00'),
            total=Decimal('70000.00'),
            created_by=self.staff_user
        )

        res = self.api_client.post(f'/api/v1/quotations/{q.id}/convert_to_order/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order_id = res.data['id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.client, self.client_profile)
        self.assertEqual(order.status, OrderStatus.COTIZACION)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().servings, 12)

    def test_order_stock_validation_and_confirmation(self):
        order = Order.objects.create(
            client=self.client_profile,
            status=OrderStatus.COTIZACION,
            delivery_date=timezone.now() + timedelta(days=2),
            delivery_address=self.client_profile.address,
            subtotal=Decimal('35000.00'),
            total=Decimal('35000.00')
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            servings=12,
            unit_price=Decimal('35000.00')
        )

        # Validar stock API endpoint
        stock_res = self.api_client.get(f'/api/v1/orders/{order.id}/validate-stock/')
        self.assertEqual(stock_res.status_code, status.HTTP_200_OK)
        self.assertTrue(stock_res.data['has_stock'])

        # Confirmar pedido
        confirm_res = self.api_client.post(f'/api/v1/orders/{order.id}/confirm/')
        self.assertEqual(confirm_res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CONFIRMADO)

        # El stock de vainilla se descuenta 2 unidades
        self.vanilla.refresh_from_db()
        self.assertEqual(self.vanilla.current_stock, Decimal('98.000'))

    def test_payment_and_refund(self):
        order = Order.objects.create(
            client=self.client_profile,
            status=OrderStatus.CONFIRMADO,
            delivery_date=timezone.now() + timedelta(days=2),
            delivery_address=self.client_profile.address,
            total=Decimal('35000.00')
        )
        payment = Payment.objects.create(
            order=order,
            amount=Decimal('35000.00'),
            method=PaymentMethod.WEBPAY,
            status=PaymentStatus.PAGADO_TOTAL
        )
        res = self.api_client.post(f'/api/v1/payments/{payment.id}/refund/', {'reason': 'Cancelado por cliente'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.REEMBOLSADO)
