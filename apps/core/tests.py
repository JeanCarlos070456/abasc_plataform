from django.test import TestCase
from django.urls import reverse

class CoreViewsTests(TestCase):
    def test_home_is_public(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_health_endpoint(self):
        response = self.client.get(reverse('core:health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
