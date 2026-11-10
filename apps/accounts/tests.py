from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, Profile
from apps.accounts.forms import CustomUserCreationForm
from apps.clients.models import Client
from apps.dispatch.models import Driver


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='marriet_chef',
            email='chef@marriet.cl',
            password='Password123!',
            first_name='Marriet',
            last_name='Chef',
            role=User.Role.COCINERO
        )

    def test_user_properties(self):
        self.assertEqual(self.user.get_full_name(), 'Marriet Chef')
        self.assertTrue(self.user.is_staff_member())
        self.assertFalse(self.user.is_client)

    def test_client_and_driver_relations(self):
        client_user = User.objects.create_user(
            username='client1',
            email='client@marriet.cl',
            password='Password123!',
            role=User.Role.CLIENTE
        )
        client_profile = Client.objects.create(
            user=client_user,
            name='Cliente Marriet',
            email='client@marriet.cl'
        )
        self.assertEqual(client_user.client, client_profile)

        driver_user = User.objects.create_user(
            username='driver1',
            email='driver@marriet.cl',
            password='Password123!',
            role=User.Role.REPARTIDOR
        )
        driver_profile = Driver.objects.create(
            user=driver_user,
            license_number='LIC-1234',
            phone='+5699999999',
            vehicle='Camioneta Marriet'
        )
        self.assertEqual(driver_user.driver, driver_profile)


class UserFormTest(TestCase):
    def test_custom_user_creation_form_valid(self):
        form_data = {
            'username': 'nuevousuario',
            'email': 'nuevo@marriet.cl',
            'first_name': 'Dulce',
            'last_name': 'Pastry',
            'phone': '+56912345678',
            'password1': 'Password123!',
            'password2': 'Password123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, 'nuevo@marriet.cl')
        self.assertEqual(user.role, User.Role.CLIENTE)


class AccountsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='admin_marriet',
            email='admin@marriet.cl',
            password='Password123!',
            role=User.Role.ADMIN
        )
        self.client.force_authenticate(user=self.user)

    def test_me_and_update_me(self):
        res = self.client.get('/api/v1/users/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], 'admin@marriet.cl')

        update_res = self.client.patch('/api/v1/users/update_me/', {
            'first_name': 'Haute',
            'last_name': 'Patisserie'
        })
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Haute')
