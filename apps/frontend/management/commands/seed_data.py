"""
Comando para poblar la base de datos con datos de prueba
Ejecutar: python manage.py seed_data
"""
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

from apps.accounts.models import User, Profile
from apps.clients.models import Client, ClientPreference
from apps.products.models import Category, Product, BOMItem
from apps.ingredients.models import Ingredient, Supplier, StockMovement, PurchaseOrder, PurchaseOrderItem
from apps.orders.models import Order, OrderItem, Payment, Quotation
from apps.production.models import KanbanColumn, ProductionCard, CardMovement
from apps.dispatch.models import Driver, Route, Dispatch
from apps.payments.models import WebPayTransaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Pobla la base de datos con datos de prueba para Dulce Arte'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar datos existentes antes de poblar',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Limpiando datos existentes...')
            self.clear_data()

        self.stdout.write('Creando datos de prueba...')

        # 1. Usuarios y Roles
        users = self.create_users()

        # 2. Proveedores
        suppliers = self.create_suppliers()

        # 3. Insumos
        ingredients = self.create_ingredients(suppliers)

        # 4. Categorías
        categories = self.create_categories()

        # 5. Productos con BOM
        products = self.create_products(categories, ingredients)

        # 6. Clientes
        clients = self.create_clients(users)

        # 7. Columnas Kanban
        columns = self.create_kanban_columns()

        # 8. Conductores
        drivers = self.create_drivers(users)

        # 9. Pedidos, Cotizaciones, Pagos
        self.create_orders_and_payments(clients, products, users)

        # 10. Producción (Kanban cards)
        self.create_production_cards(columns, users)

        # 11. Despachos y Rutas
        self.create_dispatches(drivers, users)

        self.stdout.write(self.style.SUCCESS('¡Datos de prueba creados exitosamente!'))
        self.print_summary()

    def clear_data(self):
        """Limpiar todos los datos (orden importante por FK)"""
        WebPayTransaction.objects.all().delete()
        CardMovement.objects.all().delete()
        ProductionCard.objects.all().delete()
        Dispatch.objects.all().delete()
        Route.objects.all().delete()
        Driver.objects.all().delete()
        Payment.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        Quotation.objects.all().delete()
        BOMItem.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        StockMovement.objects.all().delete()
        PurchaseOrderItem.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        Ingredient.objects.all().delete()
        Supplier.objects.all().delete()
        ClientPreference.objects.all().delete()
        Client.objects.all().delete()
        Profile.objects.all().delete()
        KanbanColumn.objects.all().delete()
        # Users except superuser
        User.objects.filter(is_superuser=False).delete()

    def create_users(self):
        """Crear usuarios con diferentes roles"""
        roles_data = [
            ('admin', 'admin@dulcearte.cl', 'ADMIN', 'Administrador', 'Sistema'),
            ('ventas1', 'ventas1@dulcearte.cl', 'VENTAS', 'María', 'González'),
            ('ventas2', 'ventas2@dulcearte.cl', 'VENTAS', 'Carlos', 'Ruiz'),
            ('cocinero1', 'cocinero1@dulcearte.cl', 'COCINERO', 'Pedro', 'Soto'),
            ('cocinero2', 'cocinero2@dulcearte.cl', 'COCINERO', 'Ana', 'Morales'),
            ('bodega1', 'bodega1@dulcearte.cl', 'BODEGA', 'Luis', 'Fernández'),
            ('repartidor1', 'repartidor1@dulcearte.cl', 'REPARTIDOR', 'Jorge', 'Muñoz'),
            ('repartidor2', 'repartidor2@dulcearte.cl', 'REPARTIDOR', 'Patricia', 'Vega'),
        ]

        users = {}
        for username, email, role, first, last in roles_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'role': role,
                    'is_staff': role in ['ADMIN', 'VENTAS'],
                    'is_verified': True,
                }
            )
            if created:
                user.set_password('demo123')
                user.phone = f'+569{random.randint(10000000, 99999999)}'
                user.save()
                Profile.objects.create(
                    user=user,
                    address=f'Dirección de {first} {last}',
                )
            users[role] = users.get(role, []) + [user]

        self.stdout.write(f'  Usuarios creados: {User.objects.count()}')
        return users

    def create_suppliers(self):
        """Crear proveedores"""
        suppliers_data = [
            ('Harinas del Sur', 'contacto@harinasdelsur.cl', '+56223456789', 'Av. La Florida 123, Santiago', True),
            ('Lácteos Los Andes', 'ventas@lacteosandes.cl', '+56224567890', 'Camino Lonquén 456, Talagante', True),
            ('Frutas Frescas Chile', 'pedidos@frutasfrescas.cl', '+56225678901', 'Av. Matta 789, Santiago', True),
            ('Chocolates Premium', 'comercial@chocolatespremium.cl', '+56226789012', 'Los Trapenses 321, Lo Barnechea', True),
            ('Envases y Embalajes', 'ventas@envases.cl', '+56227890123', 'Panamericana Norte 555, Huechuraba', True),
            ('Azúcar y Endulzantes', 'contacto@azucarendulza.cl', '+56228901234', 'San Bernardo 222, San Bernardo', True),
        ]

        suppliers = []
        for name, email, phone, address, active in suppliers_data:
            supplier, _ = Supplier.objects.get_or_create(
                name=name,
                defaults={
                    'email': email,
                    'phone': phone,
                    'address': address,
                    'is_active': active,
                }
            )
            suppliers.append(supplier)

        self.stdout.write(f'  Proveedores creados: {len(suppliers)}')
        return suppliers

    def create_ingredients(self, suppliers):
        """Crear insumos con stock variado"""
        ingredients_data = [
            # (nombre, unidad, stock_actual, stock_minimo, costo_unitario, proveedor_idx, perecible, vida_util)
            ('Harina de trigo 000', 'kg', 50, 20, 1200, 0, False, 0),
            ('Harina integral', 'kg', 15, 10, 1500, 0, False, 0),
            ('Azúcar rubia', 'kg', 30, 15, 950, 5, False, 0),
            ('Azúcar flor', 'kg', 8, 10, 1100, 5, False, 0),  # Crítico
            ('Mantequilla sin sal', 'kg', 25, 10, 4500, 1, True, 30),
            ('Mantequilla con sal', 'kg', 12, 8, 4200, 1, True, 30),
            ('Huevos', 'un', 200, 50, 120, 1, True, 21),
            ('Leche entera', 'l', 40, 20, 850, 1, True, 7),
            ('Crema de leche', 'l', 5, 10, 2200, 1, True, 7),  # Crítico
            ('Chocolate cobertura 70%', 'kg', 10, 5, 8500, 3, False, 0),
            ('Chocolate blanco', 'kg', 3, 5, 9200, 3, False, 0),  # Crítico
            ('Cacao en polvo', 'kg', 8, 5, 6500, 3, False, 0),
            ('Frutillas frescas', 'kg', 0, 5, 3500, 2, True, 3),  # Sin stock
            ('Arándanos', 'kg', 2, 3, 8500, 2, True, 5),  # Crítico
            ('Nueces picadas', 'kg', 6, 3, 12000, 2, False, 0),
            ('Almendras laminadas', 'kg', 4, 2, 15000, 2, False, 0),
            ('Polvo de hornear', 'kg', 2, 1, 3500, 0, False, 0),
            ('Esencia de vainilla', 'l', 1, 0.5, 4500, 0, False, 0),
            ('Sal', 'kg', 5, 2, 400, 0, False, 0),
            ('Cajas torta 20cm', 'un', 50, 20, 800, 4, False, 0),
            ('Cajas torta 25cm', 'un', 30, 15, 1000, 4, False, 0),
            ('Bases para torta', 'un', 20, 10, 1200, 4, False, 0),
            ('Papel mantequilla', 'm', 100, 30, 150, 4, False, 0),
            ('Mangas pasteleras', 'un', 30, 10, 350, 4, False, 0),
            ('Boquillas decoración', 'un', 25, 10, 800, 4, False, 0),
        ]

        ingredients = []
        for i, (name, unit, stock, min_stock, cost, sup_idx, perishable, shelf_life) in enumerate(ingredients_data):
            supplier = suppliers[sup_idx] if sup_idx < len(suppliers) else None
            ingredient, _ = Ingredient.objects.get_or_create(
                name=name,
                defaults={
                    'unit': unit,
                    'current_stock': Decimal(str(stock)),
                    'min_stock': Decimal(str(min_stock)),
                    'unit_cost': Decimal(str(cost)),
                    'supplier': supplier,
                    'is_perishable': perishable,
                    'shelf_life_days': shelf_life,
                }
            )
            ingredients.append(ingredient)

        self.stdout.write(f'  Insumos creados: {len(ingredients)}')
        return ingredients

    def create_categories(self):
        """Crear categorías de productos"""
        categories_data = [
            ('Tortas', 'Tortas artesanales para ocasiones especiales', 1),
            ('Postres', 'Postres individuales y porciones', 2),
            ('Galletas', 'Galletas artesanales y decoradas', 3),
            ('Panadería Dulce', 'Panes dulces y viennoiserie', 4),
            ('Chocolatería', 'Bombones, trufas y figuras de chocolate', 5),
            ('Personalizados', 'Productos hechos a medida', 6),
        ]

        categories = []
        for name, desc, order in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults={'description': desc, 'order': order}
            )
            categories.append(cat)

        self.stdout.write(f'  Categorías creadas: {len(categories)}')
        return categories

    def create_products(self, categories, ingredients):
        """Crear productos con BOM (recetas)"""
        # Mapear ingredientes por nombre para fácil acceso
        ing_map = {ing.name: ing for ing in ingredients}

        products_data = [
            # (nombre, categoria_idx, descripcion, precio_base, precio_venta, tiempo_prep, porciones_base, [(ingrediente, cantidad, unidad, notas), ...])
            (
                'Torta Selva Negra Clásica',
                0,
                'Torta de chocolate con cerezas, crema chantilly y virutas de chocolate',
                18000, 35000, 120, 12,
                [
                    ('Harina de trigo 000', 0.5, 'kg', 'Tamizada'),
                    ('Azúcar rubia', 0.4, 'kg', ''),
                    ('Cacao en polvo', 0.08, 'kg', ''),
                    ('Huevos', 6, 'un', 'Temperatura ambiente'),
                    ('Mantequilla sin sal', 0.25, 'kg', 'Ablandada'),
                    ('Leche entera', 0.2, 'l', ''),
                    ('Polvo de hornear', 0.01, 'kg', ''),
                    ('Esencia de vainilla', 0.01, 'l', ''),
                    ('Frutillas frescas', 0.5, 'kg', 'Para decorar'),
                    ('Crema de leche', 0.5, 'l', 'Para chantilly'),
                    ('Chocolate cobertura 70%', 0.2, 'kg', 'Virutas'),
                    ('Cajas torta 25cm', 1, 'un', ''),
                ]
            ),
            (
                'Torta Tres Leches',
                0,
                'Bizcocho empapado en tres leches con merengue suizo',
                15000, 32000, 90, 12,
                [
                    ('Harina de trigo 000', 0.4, 'kg', ''),
                    ('Azúcar flor', 0.35, 'kg', ''),
                    ('Huevos', 5, 'un', ''),
                    ('Leche entera', 0.4, 'l', 'Para la mezcla tres leches'),
                    ('Crema de leche', 0.2, 'l', 'Para la mezcla tres leches'),
                    ('Leche condensada', 0.395, 'kg', '1 lata'),
                    ('Leche evaporada', 0.36, 'l', '1 lata'),
                    ('Esencia de vainilla', 0.015, 'l', ''),
                    ('Canela en polvo', 0.005, 'kg', 'Para espolvorear'),
                    ('Cajas torta 25cm', 1, 'un', ''),
                ]
            ),
            (
                'Cheesecake de Frutos Rojos',
                0,
                'Base de galleta, crema de queso y coulis de frutos rojos',
                22000, 42000, 180, 12,
                [
                    ('Galletas de vainilla', 0.3, 'kg', 'Para base - usar galletas María'),
                    ('Mantequilla sin sal', 0.15, 'kg', 'Derretida para base'),
                    ('Queso crema', 0.6, 'kg', 'Temperatura ambiente'),
                    ('Azúcar flor', 0.2, 'kg', ''),
                    ('Huevos', 3, 'un', ''),
                    ('Crema de leche', 0.2, 'l', ''),
                    ('Esencia de vainilla', 0.01, 'l', ''),
                    ('Frutillas frescas', 0.3, 'kg', 'Para coulis'),
                    ('Arándanos', 0.15, 'kg', 'Para coulis'),
                    ('Azúcar rubia', 0.1, 'kg', 'Para coulis'),
                    ('Cajas torta 25cm', 1, 'un', ''),
                ]
            ),
            (
                'Torta de Chocolate Belga',
                0,
                'Intensa torta de chocolate 70% cacao con ganache',
                25000, 48000, 150, 12,
                [
                    ('Harina de trigo 000', 0.3, 'kg', ''),
                    ('Cacao en polvo', 0.12, 'kg', ''),
                    ('Azúcar rubia', 0.4, 'kg', ''),
                    ('Huevos', 6, 'un', ''),
                    ('Mantequilla sin sal', 0.3, 'kg', ''),
                    ('Chocolate cobertura 70%', 0.5, 'kg', 'Para masa y ganache'),
                    ('Crema de leche', 0.4, 'l', 'Para ganache'),
                    ('Esencia de vainilla', 0.01, 'l', ''),
                    ('Sal', 0.005, 'kg', ''),
                    ('Cajas torta 25cm', 1, 'un', ''),
                ]
            ),
            (
                'Tiramisú Clásico',
                1,
                'Postre italiano con café, mascarpone y cacao',
                8000, 18000, 60, 8,
                [
                    ('Savoiardi (bizcochos)', 0.3, 'kg', ''),
                    ('Café espresso', 0.3, 'l', 'Fuerte y frío'),
                    ('Queso mascarpone', 0.5, 'kg', ''),
                    ('Huevos', 4, 'un', 'Yemas y claras separadas'),
                    ('Azúcar flor', 0.1, 'kg', ''),
                    ('Cacao en polvo', 0.02, 'kg', 'Para espolvorear'),
                    ('Licor Amaretto', 0.05, 'l', 'Opcional'),
                ]
            ),
            (
                'Mousse de Chocolate',
                1,
                'Mousse aireado de chocolate 70% con crema batida',
                6000, 15000, 45, 6,
                [
                    ('Chocolate cobertura 70%', 0.2, 'kg', ''),
                    ('Huevos', 4, 'un', 'Separadas'),
                    ('Azúcar flor', 0.08, 'kg', ''),
                    ('Crema de leche', 0.3, 'l', 'Para batir'),
                    ('Mantequilla sin sal', 0.05, 'kg', ''),
                ]
            ),
            (
                'Galletas Decoradas Navideñas',
                2,
                'Galletas de mantequilla decoradas con glaseado real',
                3000, 8000, 90, 20,
                [
                    ('Harina de trigo 000', 0.5, 'kg', ''),
                    ('Mantequilla sin sal', 0.25, 'kg', ''),
                    ('Azúcar flor', 0.2, 'kg', ''),
                    ('Huevos', 2, 'un', ''),
                    ('Esencia de vainilla', 0.01, 'l', ''),
                    ('Polvo de hornear', 0.005, 'kg', ''),
                    ('Sal', 0.003, 'kg', ''),
                    ('Clara de huevo', 0.1, 'kg', 'Para glaseado'),
                    ('Azúcar flor', 0.3, 'kg', 'Para glaseado'),
                    ('Colorantes alimentarios', 0.01, 'kg', 'Varios colores'),
                ]
            ),
            (
                'Alfajores de Maicena',
                2,
                'Dulces rellenos de manjar y cubiertos de coco rallado',
                2500, 6000, 60, 24,
                [
                    ('Harina de trigo 000', 0.2, 'kg', ''),
                    ('Maicena', 0.3, 'kg', ''),
                    ('Mantequilla sin sal', 0.2, 'kg', ''),
                    ('Azúcar flor', 0.15, 'kg', ''),
                    ('Huevos', 3, 'un', 'Solo yemas'),
                    ('Polvo de hornear', 0.01, 'kg', ''),
                    ('Manjar', 0.5, 'kg', 'Para rellenar'),
                    ('Coco rallado', 0.2, 'kg', 'Para cubrir'),
                ]
            ),
            (
                'Croissants de Mantequilla',
                3,
                'Croissants franceses hojaldrados artesanales',
                4000, 12000, 240, 12,
                [
                    ('Harina de trigo 000', 0.5, 'kg', 'Fuerza alta'),
                    ('Leche entera', 0.12, 'l', 'Tibia'),
                    ('Agua', 0.12, 'l', 'Fría'),
                    ('Azúcar rubia', 0.05, 'kg', ''),
                    ('Sal', 0.01, 'kg', ''),
                    ('Levadura fresca', 0.015, 'kg', ''),
                    ('Mantequilla sin sal', 0.28, 'kg', 'Para laminado, muy fría'),
                ]
            ),
            (
                'Pain au Chocolat',
                3,
                'Croissant relleno de chocolate belga',
                4500, 13000, 240, 12,
                [
                    ('Harina de trigo 000', 0.5, 'kg', 'Fuerza alta'),
                    ('Leche entera', 0.12, 'l', ''),
                    ('Agua', 0.12, 'l', ''),
                    ('Azúcar rubia', 0.05, 'kg', ''),
                    ('Sal', 0.01, 'kg', ''),
                    ('Levadura fresca', 0.015, 'kg', ''),
                    ('Mantequilla sin sal', 0.28, 'kg', 'Para laminado'),
                    ('Chocolate cobertura 70%', 0.12, 'kg', 'Barras para rellenar'),
                ]
            ),
            (
                'Bombones de Chocolate Rellenos',
                4,
                'Bombones artesanales con ganache de sabores variados',
                12000, 28000, 120, 20,
                [
                    ('Chocolate cobertura 70%', 0.4, 'kg', 'Para caparazón'),
                    ('Chocolate blanco', 0.2, 'kg', 'Para decorar'),
                    ('Crema de leche', 0.3, 'l', 'Para ganache'),
                    ('Mantequilla sin sal', 0.05, 'kg', 'Para ganache'),
                    ('Esencia de vainilla', 0.005, 'l', ''),
                    ('Licor de naranja', 0.03, 'l', 'Para ganache naranja'),
                    ('Pasta de pistacho', 0.05, 'kg', 'Para ganache pistacho'),
                    ('Cajas bombones', 1, 'un', ''),
                ]
            ),
            (
                'Torta Personalizada Cumpleaños',
                5,
                'Torta a medida con diseño, sabor y mensaje personalizado',
                30000, 65000, 180, 20,
                [
                    ('Harina de trigo 000', 0.8, 'kg', 'Base vainilla o chocolate'),
                    ('Azúcar rubia', 0.6, 'kg', ''),
                    ('Huevos', 8, 'un', ''),
                    ('Mantequilla sin sal', 0.4, 'kg', ''),
                    ('Leche entera', 0.3, 'l', ''),
                    ('Polvo de hornear', 0.02, 'kg', ''),
                    ('Cacao en polvo', 0.1, 'kg', 'Opcional para chocolate'),
                    ('Crema de leche', 1, 'l', 'Para buttercream'),
                    ('Mantequilla sin sal', 0.5, 'kg', 'Para buttercream'),
                    ('Azúcar flor', 0.8, 'kg', 'Para buttercream'),
                    ('Colorantes alimentarios', 0.02, 'kg', 'Según diseño'),
                    ('Chocolate cobertura 70%', 0.3, 'kg', 'Decoraciones'),
                    ('Cajas torta 25cm', 1, 'un', ''),
                    ('Bases para torta', 2, 'un', ''),
                ]
            ),
        ]

        products = []
        for name, cat_idx, desc, base_price, sale_price, prep_time, base_servings, bom_items in products_data:
            category = categories[cat_idx] if cat_idx < len(categories) else categories[0]

            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'description': desc,
                    'base_price': Decimal(str(base_price)),
                    'sale_price': Decimal(str(sale_price)),
                    'prep_time_minutes': prep_time,
                    'base_servings': base_servings,
                    'is_active': True,
                }
            )

            if created:
                # Combine duplicate ingredients for the same product
                combined_bom = {}
                for ing_name, qty, unit, notes in bom_items:
                    ingredient = ing_map.get(ing_name)
                    if ingredient:
                        key = ingredient.id
                        if key not in combined_bom:
                            combined_bom[key] = {
                                'ingredient': ingredient,
                                'quantity': Decimal('0'),
                                'unit': unit,
                                'notes': notes
                            }
                        combined_bom[key]['quantity'] += Decimal(str(qty))
                        # Append notes if different
                        if notes and notes not in combined_bom[key]['notes']:
                            combined_bom[key]['notes'] += f'; {notes}'

                # Create BOMItems from combined data
                for item_data in combined_bom.values():
                    BOMItem.objects.create(
                        product=product,
                        ingredient=item_data['ingredient'],
                        quantity=item_data['quantity'],
                        unit=item_data['unit'],
                        notes=item_data['notes']
                    )

            products.append(product)

        self.stdout.write(f'  Productos creados: {len(products)}')
        return products

    def create_clients(self, users):
        """Crear clientes"""
        clients_data = [
            ('María Elena Soto', 'maria.soto@email.com', '+56987654321', 'Av. Providencia 1234, Depto 56, Providencia', 'Alergia a nueces'),
            ('Roberto Carlos Méndez', 'roberto.mendez@empresa.cl', '+56912345678', 'Las Condes 5678, Of. 1201, Las Condes', 'Prefiere chocolate negro'),
            ('Carolina Andrea Vega', 'caro.vega@gmail.com', '+56923456789', 'Ñuñoa 2345, Casa 12, Ñuñoa', 'Cumpleaños en marzo'),
            ('Fernando José Ruiz', 'fernando.ruiz@outlook.com', '+56934567890', 'La Reina 3456, Depto 301, La Reina', 'Sin gluten'),
            ('Patricia Isabel Morales', 'paty.morales@yahoo.com', '+56945678901', 'Macul 4567, Casa 45, Macul', 'Vegana'),
            ('Andrés Felipe Cortés', 'andres.cortes@hotmail.com', '+56956789012', 'Peñalolén 5678, Depto 202, Peñalolén', ''),
            ('Gabriela Andrea Silva', 'gaby.silva@email.com', '+56967890123', 'San Joaquín 6789, Casa 78, San Joaquín', 'Prefiere frutas rojas'),
            ('Jorge Luis Herrera', 'jorge.herrera@empresa.cl', '+56978901234', 'Vitacura 7890, Of. 500, Vitacura', 'Empresarial - factura'),
        ]

        sales_users = users.get('VENTAS', [])
        clients = []
        for i, (name, email, phone, address, notes) in enumerate(clients_data):
            created_by = sales_users[i % len(sales_users)] if sales_users else None
            client, _ = Client.objects.get_or_create(
                email=email,
                defaults={
                    'name': name,
                    'phone': phone,
                    'address': address,
                    'notes': notes,
                    'created_by': created_by,
                }
            )
            # Add preferences
            if 'Alergia' in notes:
                ClientPreference.objects.get_or_create(client=client, key='alergias', defaults={'value': notes})
            if 'Prefiere' in notes:
                ClientPreference.objects.get_or_create(client=client, key='preferencias', defaults={'value': notes})
            clients.append(client)

        self.stdout.write(f'  Clientes creados: {len(clients)}')
        return clients

    def create_kanban_columns(self):
        """Crear columnas del Kanban"""
        columns_data = [
            ('RECIBIDO', 1, '#6c757d', False),
            ('EN_PREPARACION', 2, '#0d6efd', False),
            ('HORNEADO_DECORADO', 3, '#fd7e14', False),
            ('CONTROL_CALIDAD', 4, '#ffc107', False),
            ('LISTO', 5, '#198754', True),
        ]

        columns = []
        for name, order, color, is_final in columns_data:
            col, _ = KanbanColumn.objects.get_or_create(
                name=name,
                defaults={'order': order, 'color': color, 'is_final': is_final}
            )
            columns.append(col)

        self.stdout.write(f'  Columnas Kanban creadas: {len(columns)}')
        return columns

    def create_drivers(self, users):
        """Crear conductores"""
        repartidor_users = users.get('REPARTIDOR', [])

        drivers = []
        for i, user in enumerate(repartidor_users):
            driver, _ = Driver.objects.get_or_create(
                user=user,
                defaults={
                    'license_number': f'LIC{random.randint(10000000, 99999999)}',
                    'phone': user.phone if user.phone else f'+569{random.randint(10000000, 99999999)}',
                    'vehicle': f'Van {["Renault Kangoo", "Fiat Fiorino", "Peugeot Partner"][i % 3]} - ABCD{10+i}',
                    'is_active': True,
                }
            )
            drivers.append(driver)

        self.stdout.write(f'  Conductores creados: {len(drivers)}')
        return drivers

    def create_orders_and_payments(self, clients, products, users):
        """Crear pedidos, cotizaciones y pagos"""
        sales_users = users.get('VENTAS', [])
        statuses = ['COTIZACION', 'CONFIRMADO', 'EN_PRODUCCION', 'LISTO', 'DESPACHADO', 'ENTREGADO']
        payment_statuses = ['PENDIENTE', 'PAGADO_PARCIAL', 'PAGADO_TOTAL']

        for i in range(25):
            client = random.choice(clients)
            status = random.choice(statuses)
            payment_status = random.choice(payment_statuses)
            created_by = random.choice(sales_users) if sales_users else None

            delivery_date = date.today() + timedelta(days=random.randint(1, 14))

            # Create order
            order = Order.objects.create(
                client=client,
                status=status,
                delivery_date=delivery_date,
                delivery_address=client.address,
                subtotal=0,
                discount=Decimal('0'),
                total=0,
                notes=f'Pedido de prueba #{i+1}',
                created_by=created_by,
                confirmed_at=timezone.now() if status != 'COTIZACION' else None,
            )

            # Add 1-3 items
            num_items = random.randint(1, 3)
            selected_products = random.sample(products, min(num_items, len(products)))
            total = Decimal('0')

            for j, product in enumerate(selected_products):
                quantity = random.randint(1, 3)
                servings = random.choice([12, 20, 40])
                unit_price = product.sale_price

                # Simulate BOM snapshot
                bom_snapshot = []
                for bom_item in product.bom_items.all():
                    factor = Decimal(str(servings)) / Decimal(str(product.base_servings))
                    scaled_qty = (bom_item.quantity * factor * quantity).quantize(Decimal('0.001'))
                    bom_snapshot.append({
                        'ingredient_id': bom_item.ingredient.id,
                        'ingredient_name': bom_item.ingredient.name,
                        'quantity': float(scaled_qty),
                        'unit': bom_item.unit,
                        'estimated_cost': float(bom_item.ingredient.unit_cost * scaled_qty),
                    })

                item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    servings=servings,
                    unit_price=unit_price,
                    custom_notes=f'Item {j+1} - {servings} porciones',
                    bom_snapshot_scaled=bom_snapshot,
                )
                total += unit_price * quantity

            order.subtotal = total
            order.total = total
            order.save()

            # Create payments
            if payment_status != 'PENDIENTE':
                paid_amount = total if payment_status == 'PAGADO_TOTAL' else total * Decimal('0.5')
                Payment.objects.create(
                    order=order,
                    amount=paid_amount,
                    method=random.choice(['WEBPAY', 'EFECTIVO', 'TRANSFERENCIA']),
                    status='PAGADO' if payment_status == 'PAGADO_TOTAL' else 'PAGADO_PARCIAL',
                    transaction_id=f'TXN{random.randint(100000, 999999)}',
                    paid_at=timezone.now() - timedelta(days=random.randint(0, 5)),
                )

                # WebPay transaction if method is WEBPAY
                if random.choice([True, False]):
                    WebPayTransaction.objects.create(
                        order=order,
                        buy_order=f'BO{order.id}{random.randint(100, 999)}',
                        session_id=f'SID{random.randint(100000, 999999)}',
                        amount=paid_amount,
                        status='PAGADO',
                        token=f'token_{random.randint(1000000, 9999999)}',
                        response_code='0',
                        response_json={'status': 'AUTHORIZED'},
                        confirmed_at=timezone.now(),
                    )

        # Create some quotations
        for i in range(10):
            client = random.choice(clients)
            Quotation.objects.create(
                client=client,
                items=[{
                    'product_id': p.id,
                    'quantity': random.randint(1, 2),
                    'servings': random.choice([12, 20, 40]),
                    'unit_price': float(p.sale_price),
                } for p in random.sample(products, random.randint(1, 3))],
                valid_until=date.today() + timedelta(days=30),
                status=random.choice(['BORRADOR', 'ENVIADA', 'ACEPTADA', 'EXPIRADA']),
                created_by=random.choice(sales_users) if sales_users else None,
            )

        self.stdout.write(f'  Pedidos creados: {Order.objects.count()}')
        self.stdout.write(f'  Cotizaciones creadas: {Quotation.objects.count()}')

    def create_production_cards(self, columns, users):
        """Crear tarjetas de producción en el Kanban"""
        cocinero_users = users.get('COCINERO', [])
        orders_in_production = Order.objects.filter(status__in=['CONFIRMADO', 'EN_PRODUCCION', 'LISTO'])

        for order in orders_in_production:
            for item in order.items.all():
                # Determine column based on order status
                if order.status == 'CONFIRMADO':
                    column = columns[0]  # RECIBIDO
                elif order.status == 'EN_PRODUCCION':
                    column = random.choice(columns[1:3])  # EN_PREPARACION or HORNEADO_DECORADO
                else:  # LISTO
                    column = columns[4]  # LISTO

                card = ProductionCard.objects.create(
                    order_item=item,
                    column=column,
                    assigned_to=random.choice(cocinero_users) if cocinero_users else None,
                    notes=f'Producir {item.quantity} x {item.product.name} ({item.servings} porciones c/u)',
                )

                # Add some movements
                if column.order > 1:
                    CardMovement.objects.create(
                        card=card,
                        from_column=columns[0],
                        to_column=column,
                        moved_by=random.choice(cocinero_users) if cocinero_users else None,
                        notes='Iniciado producción'
                    )

        self.stdout.write(f'  Tarjetas Kanban creadas: {ProductionCard.objects.count()}')

    def create_dispatches(self, drivers, users):
        """Crear despachos y rutas"""
        orders_ready = Order.objects.filter(status='LISTO')

        # Create routes for today and next few days
        for day_offset in range(3):
            route_date = date.today() + timedelta(days=day_offset)
            driver = random.choice(drivers) if drivers else None

            route = Route.objects.create(
                name=f'Ruta {["Norte", "Sur", "Oriente", "Poniente", "Centro"][day_offset % 5]} - {route_date.strftime("%d/%m")}',
                date=route_date,
                driver=driver,
                status='EN_PROGRESO' if day_offset == 0 else 'PENDIENTE',
                notes=f'Ruta del {route_date.strftime("%d/%m/%Y")}',
            )

            # Assign 2-5 orders to this route
            available_orders = list(orders_ready)
            random.shuffle(available_orders)
            for seq, order in enumerate(available_orders[:random.randint(2, 5)], 1):
                dispatch = Dispatch.objects.create(
                    route=route,
                    order=order,
                    sequence=seq,
                    status='PENDIENTE' if day_offset > 0 else random.choice(['PENDIENTE', 'EN_RUTA', 'ENTREGADO']),
                    notes=f'Entregar a {order.client.name}',
                )

                # If delivered, add signature/photo simulation
                if dispatch.status == 'ENTREGADO':
                    dispatch.delivered_at = timezone.now()
                    dispatch.gps_lat = Decimal(str(-33.45 + random.uniform(-0.05, 0.05)))
                    dispatch.gps_lng = Decimal(str(-70.65 + random.uniform(-0.05, 0.05)))
                    # Note: signature and photo are ImageFields, not base64 strings in DB
                    # They would be stored as files in production; for seed data we leave them blank
                    dispatch.save()
                    order.status = 'ENTREGADO'
                    order.save()

        self.stdout.write(f'  Rutas creadas: {Route.objects.count()}')
        self.stdout.write(f'  Despachos creados: {Dispatch.objects.count()}')

    def print_summary(self):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== RESUMEN DE DATOS CREADOS ==='))
        self.stdout.write(f'Usuarios: {User.objects.count()}')
        self.stdout.write(f'Clientes: {Client.objects.count()}')
        self.stdout.write(f'Proveedores: {Supplier.objects.count()}')
        self.stdout.write(f'Insumos: {Ingredient.objects.count()}')
        self.stdout.write(f'Categorías: {Category.objects.count()}')
        self.stdout.write(f'Productos: {Product.objects.count()}')
        self.stdout.write(f'Items BOM: {BOMItem.objects.count()}')
        self.stdout.write(f'Pedidos: {Order.objects.count()}')
        self.stdout.write(f'Cotizaciones: {Quotation.objects.count()}')
        self.stdout.write(f'Pagos: {Payment.objects.count()}')
        self.stdout.write(f'Transacciones WebPay: {WebPayTransaction.objects.count()}')
        self.stdout.write(f'Columnas Kanban: {KanbanColumn.objects.count()}')
        self.stdout.write(f'Tarjetas Producción: {ProductionCard.objects.count()}')
        self.stdout.write(f'Conductores: {Driver.objects.count()}')
        self.stdout.write(f'Rutas: {Route.objects.count()}')
        self.stdout.write(f'Despachos: {Dispatch.objects.count()}')
        self.stdout.write('')
        self.stdout.write('Credenciales de acceso (password: demo123):')
        self.stdout.write('  admin@dulcearte.cl (ADMIN)')
        self.stdout.write('  ventas1@dulcearte.cl (VENTAS)')
        self.stdout.write('  cocinero1@dulcearte.cl (COCINERO)')
        self.stdout.write('  bodega1@dulcearte.cl (BODEGA)')
        self.stdout.write('  repartidor1@dulcearte.cl (REPARTIDOR)')