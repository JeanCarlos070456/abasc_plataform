from uuid import uuid4

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import User
from .services import SupabaseSession, sync_supabase_user


@override_settings(
    ENABLE_LOCAL_AUTH=True,
    SUPABASE_URL='',
    SUPABASE_ANON_KEY='',
)
class AccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='assoc@example.com',
            email='assoc@example.com',
            password='StrongPass123',
        )

    def test_local_login(self):
        response = self.client.post(
            reverse('accounts:login'),
            {
                'email': self.user.email,
                'password': 'StrongPass123',
            },
        )
        self.assertRedirects(
            response,
            reverse('accounts:post_login'),
            fetch_redirect_response=False,
        )

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            f"{reverse('accounts:login')}?next=https://example.invalid/phishing",
            {
                'email': self.user.email,
                'password': 'StrongPass123',
                'next': 'https://example.invalid/phishing',
            },
        )
        self.assertRedirects(
            response,
            reverse('accounts:post_login'),
            fetch_redirect_response=False,
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)

    def test_user_metadata_cannot_elevate_role(self):
        session = SupabaseSession(
            access_token='token',
            refresh_token='refresh',
            user_id=str(uuid4()),
            email='metadata@example.com',
            user_metadata={'role': User.Role.PRESIDENT},
            app_metadata={},
        )
        synced_user = sync_supabase_user(session)
        self.assertEqual(synced_user.role, User.Role.ASSOCIATE)

    def test_app_metadata_can_assign_executive_role(self):
        session = SupabaseSession(
            access_token='token',
            refresh_token='refresh',
            user_id=str(uuid4()),
            email='executive-metadata@example.com',
            user_metadata={},
            app_metadata={'role': User.Role.EXECUTIVE},
        )
        synced_user = sync_supabase_user(session)
        self.assertEqual(synced_user.role, User.Role.EXECUTIVE)
