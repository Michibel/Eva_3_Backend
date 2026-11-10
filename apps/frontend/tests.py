from django.test import TestCase, Client as TestClient
from django.template import Template, Context
from apps.accounts.models import User
from apps.clients.models import Client as ClientModel


class FrontendTemplateTagsTest(TestCase):
    def test_class_name_filter(self):
        t = Template("{% load frontend_tags %}{{ obj|class_name }}")
        rendered = t.render(Context({'obj': "a string"}))
        self.assertEqual(rendered, 'str')

    def test_split_filter(self):
        t = Template("{% load frontend_tags %}{% for item in 'alpha,beta,gamma'|split:',' %}[{{ item }}]{% endfor %}")
        rendered = t.render(Context({}))
        self.assertEqual(rendered, '[alpha][beta][gamma]')


class FrontendViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.admin = User.objects.create_user(
            username='admin_marriet',
            email='admin@marriet.cl',
            password='Password123!',
            role=User.Role.ADMIN
        )
        self.customer = User.objects.create_user(
            username='client_marriet',
            email='client@marriet.cl',
            password='Password123!',
            role=User.Role.CLIENTE
        )
        ClientModel.objects.create(user=self.customer, name='Cliente Test', email='client@marriet.cl')

    def test_public_pages(self):
        login_res = self.client.get('/login/')
        self.assertEqual(login_res.status_code, 200)
        self.assertContains(login_res, 'Marriet')

        register_res = self.client.get('/register/')
        self.assertEqual(register_res.status_code, 200)
        self.assertContains(register_res, 'Marriet')

    def test_staff_pages(self):
        self.client.force_login(self.admin)

        for url in ['/', '/productos/', '/insumos/', '/pedidos/', '/produccion/', '/despachos/', '/reportes/', '/pagos/', '/clientes/']:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Error cargando {url}")
            self.assertContains(res, 'Marriet')

    def test_client_portal(self):
        self.client.force_login(self.customer)
        portal_res = self.client.get('/portal/')
        self.assertEqual(portal_res.status_code, 200)
        self.assertContains(portal_res, 'Marriet')
