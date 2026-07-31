from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from .forms import MembershipReviewForm
from .models import MembershipApplication


class AssociateDashboardTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("associates:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_associate_access(self):
        user = User.objects.create_user(
            username="assoc@example.com",
            email="assoc@example.com",
            password="StrongPass123",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("associates:dashboard"))
        self.assertEqual(response.status_code, 200)


class MembershipApplicationTests(TestCase):
    def test_join_page_is_public(self):
        response = self.client.get(reverse("associates:join"))
        self.assertEqual(response.status_code, 200)

    def test_executive_cannot_assign_president(self):
        executive = User.objects.create_user(
            username="exec@example.com",
            email="exec@example.com",
            password="StrongPass123",
            role="executive",
        )
        form = MembershipReviewForm(
            {"target_role": "president"},
            actor=executive,
        )
        self.assertFalse(form.is_valid())

    def test_president_can_assign_president(self):
        president = User.objects.create_user(
            username="president@example.com",
            email="president@example.com",
            password="StrongPass123",
            role="president",
        )
        form = MembershipReviewForm(
            {"target_role": "president"},
            actor=president,
        )
        self.assertTrue(form.is_valid())

    @patch("apps.associates.views.upload_application_file")
    def test_invalid_cpf_does_not_upload(self, upload_mock):
        response = self.client.post(
            reverse("associates:join"),
            data={
                "consent_statute": "on",
                "consent_research": "on",
                "consent_communications": "on",
                "full_name": "Pessoa Teste",
                "email": "pessoa@example.com",
                "cpf": "111.111.111-11",
                "birth_date": "1990-01-01",
                "gender": MembershipApplication.Gender.NON_BINARY,
                "race_ethnicity": MembershipApplication.RaceEthnicity.BROWN,
                "has_disability": MembershipApplication.YesNo.NO,
                "marital_status": MembershipApplication.MaritalStatus.SINGLE,
                "university": "Universidade Teste",
                "health_collective_link": "Bacharel em Saúde Coletiva",
                "state": "DF",
                "city": "Brasília",
                "whatsapp": "(61) 99999-9999",
                "application_type": MembershipApplication.ApplicationType.NEW,
                "category": MembershipApplication.Category.FULL,
                "payment_agreement": "on",
                "truth_declaration": "on",
                "supporting_document": SimpleUploadedFile(
                    "documento.pdf",
                    b"%PDF-1.4 teste",
                    content_type="application/pdf",
                ),
                "payment_receipt": SimpleUploadedFile(
                    "comprovante.pdf",
                    b"%PDF-1.4 teste",
                    content_type="application/pdf",
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(upload_mock.called)
        self.assertEqual(MembershipApplication.objects.count(), 0)


@override_settings(ABASC_SITE_URL='http://127.0.0.1:8000')
class PasswordSetupUrlTests(TestCase):
    def test_password_setup_url_uses_abasc_site_url(self):
        from .services import password_setup_url

        self.assertEqual(
            password_setup_url(),
            'http://127.0.0.1:8000/conta/criar-senha/',
        )