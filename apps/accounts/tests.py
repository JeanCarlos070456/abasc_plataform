from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import AvatarForm
from .models import User
from .services import (
    SupabaseAuthError,
    SupabaseSession,
    sync_supabase_user,
)


VALID_CPF = "52998224725"


def make_png(name="avatar.png"):
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type="image/png",
    )


@override_settings(
    ENABLE_LOCAL_AUTH=True,
    SUPABASE_URL="",
    SUPABASE_ANON_KEY="",
    SUPABASE_STORAGE_BUCKET_AVATARS="abasc-avatars",
)
class AccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="assoc@example.com",
            email="assoc@example.com",
            password="StrongPass123",
            association_status=User.AssociationStatus.ACTIVE,
        )

    def test_local_login(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "email": self.user.email,
                "password": "StrongPass123",
            },
        )
        self.assertRedirects(
            response,
            reverse("accounts:post_login"),
            fetch_redirect_response=False,
        )

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            f"{reverse('accounts:login')}?next=https://example.invalid/phishing",
            {
                "email": self.user.email,
                "password": "StrongPass123",
                "next": "https://example.invalid/phishing",
            },
        )
        self.assertRedirects(
            response,
            reverse("accounts:post_login"),
            fetch_redirect_response=False,
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)

    def test_avatar_form_rejects_non_image(self):
        invalid_file = SimpleUploadedFile(
            "avatar.png",
            b"not-an-image",
            content_type="image/png",
        )
        form = AvatarForm(
            files={"avatar": invalid_file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("avatar", form.errors)

    @patch(
        "apps.accounts.views.upload_avatar",
        return_value="usuarios/1/avatar.png",
    )
    def test_active_associate_can_upload_avatar(self, upload_mock):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile"),
            {
                "action": "avatar",
                "avatar-avatar": make_png(),
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        upload_mock.assert_called_once()

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.avatar_path,
            "usuarios/1/avatar.png",
        )

    @patch("apps.accounts.views.upload_avatar")
    def test_pending_associate_cannot_upload_avatar(self, upload_mock):
        self.user.association_status = User.AssociationStatus.PENDING
        self.user.save(update_fields=[
            "association_status",
            "profile_updated_at",
        ])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile"),
            {
                "action": "avatar",
                "avatar-avatar": make_png(),
            },
        )

        self.assertEqual(response.status_code, 200)
        upload_mock.assert_not_called()

        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar_path, "")

    @patch("apps.accounts.views.delete_avatar")
    def test_user_can_remove_avatar(self, delete_mock):
        self.user.avatar_path = "usuarios/1/old-avatar.png"
        self.user.save(update_fields=[
            "avatar_path",
            "profile_updated_at",
        ])
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("accounts:profile"),
                {
                    "action": "avatar",
                    "avatar-remove_avatar": "on",
                },
            )

        self.assertRedirects(response, reverse("accounts:profile"))
        delete_mock.assert_called_once_with(
            "usuarios/1/old-avatar.png"
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar_path, "")

    def test_user_metadata_cannot_elevate_role(self):
        session = SupabaseSession(
            access_token="token",
            refresh_token="refresh",
            user_id=str(uuid4()),
            email="metadata@example.com",
            user_metadata={"role": User.Role.PRESIDENT},
            app_metadata={},
        )
        synced_user = sync_supabase_user(session)
        self.assertEqual(synced_user.role, User.Role.ASSOCIATE)

    def test_app_metadata_can_assign_executive_role(self):
        session = SupabaseSession(
            access_token="token",
            refresh_token="refresh",
            user_id=str(uuid4()),
            email="executive-metadata@example.com",
            user_metadata={},
            app_metadata={"role": User.Role.EXECUTIVE},
        )
        synced_user = sync_supabase_user(session)
        self.assertEqual(synced_user.role, User.Role.EXECUTIVE)


@override_settings(
    ENABLE_LOCAL_AUTH=True,
    SUPABASE_URL="",
    SUPABASE_ANON_KEY="",
    SUPABASE_STORAGE_BUCKET_AVATARS="abasc-avatars",
)
class LegacyFirstAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="migrado@example.com",
            email="migrado@example.com",
            password="TemporaryLocalPassword123",
            first_name="Maria",
            last_name="Silva",
            cpf=VALID_CPF,
            phone="61999999999",
            birth_date="1990-05-10",
            city="Brasília",
            state="DF",
            association_status=User.AssociationStatus.ACTIVE,
            member_category=User.MemberCategory.FULL,
            legacy_imported=True,
            onboarding_completed=False,
            migration_status=User.MigrationStatus.READY,
            is_active=True,
        )

    def test_first_access_page_is_public(self):
        response = self.client.get(reverse("accounts:first_access"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Primeiro acesso")

    @patch("apps.accounts.views.resend_member_access")
    def test_first_access_sends_supabase_link_for_matching_member(
        self,
        resend_mock,
    ):
        resend_mock.return_value = "invite"

        response = self.client.post(
            reverse("accounts:first_access"),
            {
                "email": self.user.email,
                "cpf": VALID_CPF,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        resend_mock.assert_called_once()

        called_user = resend_mock.call_args.args[0]
        self.assertEqual(called_user.pk, self.user.pk)

        self.assertContains(
            response,
            "Se os dados informados corresponderem a um cadastro habilitado",
        )

    @patch("apps.accounts.views.resend_member_access")
    def test_first_access_does_not_reveal_unknown_registration(
        self,
        resend_mock,
    ):
        response = self.client.post(
            reverse("accounts:first_access"),
            {
                "email": "desconhecido@example.com",
                "cpf": VALID_CPF,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        resend_mock.assert_not_called()
        self.assertContains(
            response,
            "Se os dados informados corresponderem a um cadastro habilitado",
        )

    def test_post_login_forces_onboarding_for_migrated_member(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("accounts:post_login"))

        self.assertRedirects(
            response,
            reverse("accounts:onboarding"),
            fetch_redirect_response=False,
        )

    def test_profile_cannot_bypass_pending_onboarding(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("accounts:profile"))

        self.assertRedirects(
            response,
            reverse("accounts:onboarding"),
            fetch_redirect_response=False,
        )

    def test_onboarding_requires_login(self):
        response = self.client.get(reverse("accounts:onboarding"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    @patch(
        "apps.accounts.views.upload_avatar",
        return_value="usuarios/99/onboarding.png",
    )
    def test_onboarding_completes_profile_and_avatar(self, upload_mock):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:onboarding"),
            {
                "profile-first_name": "Maria",
                "profile-last_name": "Silva",
                "profile-phone": "61988887777",
                "profile-cpf": VALID_CPF,
                "profile-birth_date": "1990-05-10",
                "profile-gender": User.Gender.FEMALE,
                "profile-profession": "Sanitarista",
                "profile-education_level": "Graduação",
                "profile-university": "Universidade de Brasília",
                "profile-city": "Brasília",
                "profile-state": "DF",
                "avatar-avatar": make_png(),
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:post_login"),
            fetch_redirect_response=False,
        )
        upload_mock.assert_called_once()

        self.user.refresh_from_db()
        self.assertTrue(self.user.onboarding_completed)
        self.assertEqual(
            self.user.migration_status,
            User.MigrationStatus.READY,
        )
        self.assertEqual(
            self.user.avatar_path,
            "usuarios/99/onboarding.png",
        )
        self.assertEqual(self.user.phone, "61988887777")

    def test_completed_onboarding_returns_to_normal_dashboard_flow(self):
        self.user.onboarding_completed = True
        self.user.save(update_fields=[
            "onboarding_completed",
            "profile_updated_at",
        ])
        self.client.force_login(self.user)

        response = self.client.get(reverse("accounts:onboarding"))

        self.assertRedirects(
            response,
            reverse("accounts:post_login"),
            fetch_redirect_response=False,
        )


class SupabaseMigrationSyncTests(TestCase):
    def test_existing_legacy_user_is_linked_without_losing_imported_data(self):
        user = User.objects.create_user(
            username="legado@example.com",
            email="legado@example.com",
            password="LocalPassword123",
            first_name="Nome Histórico",
            last_name="Preservado",
            cpf=VALID_CPF,
            city="Brasília",
            state="DF",
            role=User.Role.ASSOCIATE,
            association_status=User.AssociationStatus.OVERDUE,
            member_category=User.MemberCategory.FULL,
            legacy_imported=True,
            onboarding_completed=False,
        )

        supabase_id = uuid4()
        session = SupabaseSession(
            access_token="token",
            refresh_token="refresh",
            user_id=str(supabase_id),
            email=user.email,
            user_metadata={
                "first_name": "Nome do Auth",
                "last_name": "Não deve sobrescrever",
            },
            app_metadata={"role": User.Role.PRESIDENT},
        )

        synced_user = sync_supabase_user(session)
        synced_user.refresh_from_db()

        self.assertEqual(synced_user.pk, user.pk)
        self.assertEqual(synced_user.supabase_user_id, supabase_id)
        self.assertEqual(synced_user.first_name, "Nome Histórico")
        self.assertEqual(synced_user.last_name, "Preservado")
        self.assertEqual(
            synced_user.association_status,
            User.AssociationStatus.OVERDUE,
        )
        self.assertEqual(
            synced_user.member_category,
            User.MemberCategory.FULL,
        )
        self.assertEqual(synced_user.role, User.Role.ASSOCIATE)
        self.assertFalse(synced_user.onboarding_completed)
        self.assertFalse(synced_user.has_usable_password())

    def test_sync_rejects_different_auth_for_already_linked_email(self):
        original_auth_id = uuid4()
        User.objects.create_user(
            username="vinculado@example.com",
            email="vinculado@example.com",
            password="LocalPassword123",
            supabase_user_id=original_auth_id,
        )

        session = SupabaseSession(
            access_token="token",
            refresh_token="refresh",
            user_id=str(uuid4()),
            email="vinculado@example.com",
            user_metadata={},
            app_metadata={},
        )

        with self.assertRaises(SupabaseAuthError):
            sync_supabase_user(session)


@override_settings(
    SUPABASE_URL="https://project.example.supabase.co",
    SUPABASE_ANON_KEY="sb_publishable_test",
)
class PasswordSetupPageTests(TestCase):
    def test_create_password_page_is_public(self):
        response = self.client.get(
            reverse("accounts:create_password")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crie sua senha de acesso")

    def test_create_password_context_uses_publishable_key(self):
        response = self.client.get(
            reverse("accounts:create_password")
        )
        config = response.context["supabase_config"]
        self.assertEqual(
            config["publishableKey"],
            "sb_publishable_test",
        )
        self.assertNotIn("service", config)
        self.assertNotIn("secret", config)