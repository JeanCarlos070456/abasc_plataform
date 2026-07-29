from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import User

class AssociateDashboardTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(
            reverse('associates:dashboard')
        )
        self.assertEqual(response.status_code, 302)

    def test_associate_access(self):
        user = User.objects.create_user(
            username='assoc@example.com',
            email='assoc@example.com',
            password='StrongPass123',
        )
        self.client.force_login(user)
        response = self.client.get(
            reverse('associates:dashboard')
        )
        self.assertEqual(response.status_code, 200)
