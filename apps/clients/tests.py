from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.clients.models import Client, ClientPreference


class ClientTest(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='ventas_marriet',
            email='ventas@marriet.cl',
            password='Password123!',
            role=User.Role.VENTAS
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.staff_user)

    def test_client_crud_and_preferences(self):
        # Create client
        res = self.api_client.post('/api/v1/clients/', {
            'name': 'Isidora Goyenechea',
            'email': 'isidora@marriet.cl',
            'phone': '+56987654321',
            'address': 'Isidora Goyenechea 3000, Las Condes',
            'notes': 'Cliente corporativo',
            'is_active': True
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        client_id = res.data['id']

        # Add preference
        client = Client.objects.get(id=client_id)
        ClientPreference.objects.create(
            client=client,
            key='favorito_categoria',
            value='Pastelería Francesa'
        )
        self.assertEqual(client.preferences.count(), 1)

        # Retrieve client with preferences
        res_get = self.api_client.get(f'/api/v1/clients/{client_id}/')
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data['name'], 'Isidora Goyenechea')
        self.assertEqual(len(res_get.data['preferences']), 1)
