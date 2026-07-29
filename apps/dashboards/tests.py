from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class DashboardPermissionTests(TestCase):
    def test_president_dashboard_blocks_executive(self):
        executive = User.objects.create_user(
            username='exec@example.com',
            email='exec@example.com',
            password='StrongPass123',
            role=User.Role.EXECUTIVE,
        )
        self.client.force_login(executive)
        response = self.client.get(
            reverse('dashboards:president')
        )
        self.assertEqual(response.status_code, 403)

    def test_president_can_access(self):
        president = User.objects.create_user(
            username='pres@example.com',
            email='pres@example.com',
            password='StrongPass123',
            role=User.Role.PRESIDENT,
        )
        self.client.force_login(president)
        response = self.client.get(
            reverse('dashboards:president')
        )
        self.assertEqual(response.status_code, 200)

    def test_president_cannot_demote_self(self):
        president = User.objects.create_user(
            username='president@example.com',
            email='president@example.com',
            password='StrongPass123',
            role=User.Role.PRESIDENT,
            association_status=User.AssociationStatus.ACTIVE,
        )
        self.client.force_login(president)
        response = self.client.post(
            reverse('dashboards:update_user', kwargs={'pk': president.pk}),
            {
                'role': User.Role.ASSOCIATE,
                'association_status': User.AssociationStatus.ACTIVE,
                'membership_number': '',
                'is_active': 'on',
            },
        )
        self.assertEqual(response.status_code, 200)
        president.refresh_from_db()
        self.assertEqual(president.role, User.Role.PRESIDENT)
        self.assertTrue(president.is_active)
