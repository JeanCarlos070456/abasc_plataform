from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import AvatarForm
from .models import User
from .services import SupabaseSession, sync_supabase_user


def make_png(name='avatar.png'):
    buffer = BytesIO()
    Image.new('RGB', (32, 32), 'white').save(buffer, format='PNG')
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type='image/png',
    )


@override_settings(
    ENABLE_LOCAL_AUTH=True,
    SUPABASE_URL='',
    SUPABASE_ANON_KEY='',
    SUPABASE_STORAGE_BUCKET_AVATARS='abasc-avatars',
)
class AccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='assoc@example.com',
            email='assoc@example.com',
            password='StrongPass123',
            association_status=User.AssociationStatus.ACTIVE,
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

    def test_avatar_form_rejects_non_image(self):
        invalid_file = SimpleUploadedFile(
            'avatar.png',
            b'not-an-image',
            content_type='image/png',
        )
        form = AvatarForm(
            files={'avatar': invalid_file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    @patch(
        'apps.accounts.views.upload_avatar',
        return_value='usuarios/1/avatar.png',
    )
    def test_active_associate_can_upload_avatar(self, upload_mock):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('accounts:profile'),
            {
                'action': 'avatar',
                'avatar-avatar': make_png(),
            },
        )

        self.assertRedirects(response, reverse('accounts:profile'))
        upload_mock.assert_called_once()

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.avatar_path,
            'usuarios/1/avatar.png',
        )

    @patch('apps.accounts.views.upload_avatar')
    def test_pending_associate_cannot_upload_avatar(self, upload_mock):
        self.user.association_status = User.AssociationStatus.PENDING
        self.user.save(update_fields=[
            'association_status',
            'profile_updated_at',
        ])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('accounts:profile'),
            {
                'action': 'avatar',
                'avatar-avatar': make_png(),
            },
        )

        self.assertEqual(response.status_code, 200)
        upload_mock.assert_not_called()

        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar_path, '')

    @patch('apps.accounts.views.delete_avatar')
    def test_user_can_remove_avatar(self, delete_mock):
        self.user.avatar_path = 'usuarios/1/old-avatar.png'
        self.user.save(update_fields=[
            'avatar_path',
            'profile_updated_at',
        ])
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('accounts:profile'),
                {
                    'action': 'avatar',
                    'avatar-remove_avatar': 'on',
                },
            )

        self.assertRedirects(response, reverse('accounts:profile'))
        delete_mock.assert_called_once_with(
            'usuarios/1/old-avatar.png'
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar_path, '')

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

@override_settings(
    SUPABASE_URL='https://project.example.supabase.co',
    SUPABASE_ANON_KEY='sb_publishable_test',
)
class PasswordSetupPageTests(TestCase):
    def test_create_password_page_is_public(self):
        response = self.client.get(
            reverse('accounts:create_password')
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Crie sua senha de acesso')

    def test_create_password_context_uses_publishable_key(self):
        response = self.client.get(
            reverse('accounts:create_password')
        )
        config = response.context['supabase_config']
        self.assertEqual(
            config['publishableKey'],
            'sb_publishable_test',
        )
        self.assertNotIn('service', config)
        self.assertNotIn('secret', config)