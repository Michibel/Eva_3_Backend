from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.products.models import Category, Product, BOMItem
from apps.ingredients.models import Supplier, Ingredient


class ProductBOMTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Tortas Especiales')
        self.product = Product.objects.create(
            category=self.category,
            name='Torta Ópera Marriet',
            base_servings=12,
            base_price=Decimal('28000.00'),
            prep_time_minutes=120
        )
        self.supplier = Supplier.objects.create(name='Valrhona Chocolate')
        self.chocolate = Ingredient.objects.create(
            name='Chocolate Guanaja 70%',
            unit='kg',
            current_stock=Decimal('10.000'),
            min_stock=Decimal('2.000'),
            unit_cost=Decimal('15000.00'),
            supplier=self.supplier
        )
        self.cafe = Ingredient.objects.create(
            name='Extracto de Café',
            unit='kg',
            current_stock=Decimal('5.000'),
            min_stock=Decimal('1.000'),
            unit_cost=Decimal('8000.00'),
            supplier=self.supplier
        )
        # 12 porciones usa 0.600 kg de chocolate y 0.200 kg de café
        BOMItem.objects.create(product=self.product, ingredient=self.chocolate, quantity=Decimal('0.600'), unit='kg')
        BOMItem.objects.create(product=self.product, ingredient=self.cafe, quantity=Decimal('0.200'), unit='kg')

    def test_scaled_bom_calculations(self):
        # 20 porciones = 20/12 * 0.600 = 1.000 kg chocolate
        scaled_20 = self.product.get_scaled_bom(target_servings=20)
        choc_item = next(i for i in scaled_20 if i['ingredient_id'] == self.chocolate.id)
        self.assertEqual(choc_item['scaled_quantity'], Decimal('1.000'))

        # 40 porciones = 40/12 * 0.600 = 2.000 kg chocolate
        scaled_40 = self.product.get_scaled_bom(target_servings=40)
        choc_item_40 = next(i for i in scaled_40 if i['ingredient_id'] == self.chocolate.id)
        self.assertEqual(choc_item_40['scaled_quantity'], Decimal('2.000'))

    def test_stock_check_and_consumption(self):
        has_stock, shortages = self.product.check_stock_for_servings(target_servings=20, quantity=2)
        self.assertTrue(has_stock)
        self.assertEqual(len(shortages), 0)

        # Consume stock para 20 porciones x 2 unidades = 2.000 kg de chocolate
        self.product.consume_stock_for_servings(target_servings=20, quantity=2)
        self.chocolate.refresh_from_db()
        self.assertEqual(self.chocolate.current_stock, Decimal('8.000'))

    def test_insufficient_stock(self):
        # Requiere 10 * 2.000 = 20 kg chocolate (tenemos 10) y 6.67 kg café (tenemos 5)
        has_stock, shortages = self.product.check_stock_for_servings(target_servings=40, quantity=10)
        self.assertFalse(has_stock)
        self.assertEqual(len(shortages), 2)
        ingredient_names = [s['ingredient'] for s in shortages]
        self.assertIn('Chocolate Guanaja 70%', ingredient_names)
        self.assertIn('Extracto de Café', ingredient_names)


class ProductAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='client_taster',
            email='taster@marriet.cl',
            password='Password123!',
            role=User.Role.CLIENTE
        )
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name='Tartaletas')
        self.product = Product.objects.create(
            category=self.category,
            name='Tartaleta Bourdaloue',
            base_servings=12,
            base_price=Decimal('22000.00')
        )

    def test_product_favorites_toggle(self):
        res = self.client.post(f'/api/v1/products/{self.product.id}/toggle_favorite/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['is_favorite'])

        # List favorites
        fav_res = self.client.get('/api/v1/products/favorites/')
        self.assertEqual(fav_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(fav_res.data), 1)

        # Toggle off
        res2 = self.client.post(f'/api/v1/products/{self.product.id}/toggle_favorite/')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertFalse(res2.data['is_favorite'])
