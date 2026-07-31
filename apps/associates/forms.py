import re

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import MembershipApplication, Payment


User = get_user_model()


FORM_CONTROL = {"class": "form-control"}
RADIO_WIDGET = forms.RadioSelect(attrs={"class": "choice-list"})
CHECKBOX_WIDGET = forms.CheckboxInput(attrs={"class": "form-check-input"})


def _only_digits(value):
    return re.sub(r"\D", "", value or "")


def _cpf_is_valid(value):
    digits = _only_digits(value)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    for size in (9, 10):
        total = sum(int(digits[index]) * (size + 1 - index) for index in range(size))
        check = (total * 10) % 11
        if check == 10:
            check = 0
        if check != int(digits[size]):
            return False
    return True


def _format_cpf(value):
    digits = _only_digits(value)
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "associate",
            "reference_month",
            "due_date",
            "paid_at",
            "amount",
            "status",
            "notes",
        ]
        widgets = {
            "associate": forms.Select(attrs=FORM_CONTROL),
            "reference_month": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "due_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "paid_at": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
            }),
            "status": forms.Select(attrs=FORM_CONTROL),
            "notes": forms.TextInput(attrs=FORM_CONTROL),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["associate"].queryset = (
            self.fields["associate"].queryset
            .filter(is_active=True)
            .order_by("first_name", "last_name", "email")
        )

    def clean_reference_month(self):
        reference_month = self.cleaned_data["reference_month"]
        return reference_month.replace(day=1)


class MembershipApplicationForm(forms.ModelForm):
    supporting_document = forms.FileField(
        label="Documentação comprobatória",
        help_text=(
            "Envie um único PDF ou imagem com diploma/declaração de conclusão, "
            "ou declaração de matrícula e histórico acadêmico. Máximo de 100 MB."
        ),
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": ".pdf,image/jpeg,image/png,image/webp",
        }),
    )
    payment_receipt = forms.FileField(
        label="Comprovante do pagamento PIX",
        help_text="Envie PDF, JPG, PNG ou WEBP. Máximo de 10 MB.",
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": ".pdf,image/jpeg,image/png,image/webp",
        }),
    )
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = MembershipApplication
        fields = [
            "consent_statute",
            "consent_research",
            "consent_communications",
            "full_name",
            "email",
            "cpf",
            "birth_date",
            "gender",
            "race_ethnicity",
            "has_disability",
            "disability_description",
            "marital_status",
            "university",
            "health_collective_link",
            "state",
            "city",
            "whatsapp",
            "allow_whatsapp_group",
            "lattes_url",
            "instagram",
            "application_type",
            "category",
            "payment_agreement",
            "truth_declaration",
        ]
        widgets = {
            "consent_statute": CHECKBOX_WIDGET,
            "consent_research": CHECKBOX_WIDGET,
            "consent_communications": CHECKBOX_WIDGET,
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "autocomplete": "name",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "autocomplete": "email",
            }),
            "cpf": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "000.000.000-00",
                "inputmode": "numeric",
                "maxlength": "14",
            }),
            "birth_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "gender": RADIO_WIDGET,
            "race_ethnicity": RADIO_WIDGET,
            "has_disability": RADIO_WIDGET,
            "disability_description": forms.TextInput(attrs=FORM_CONTROL),
            "marital_status": forms.Select(attrs=FORM_CONTROL),
            "university": forms.TextInput(attrs=FORM_CONTROL),
            "health_collective_link": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
            }),
            "state": forms.Select(attrs=FORM_CONTROL),
            "city": forms.TextInput(attrs=FORM_CONTROL),
            "whatsapp": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "(00) 00000-0000",
                "inputmode": "tel",
                "autocomplete": "tel",
            }),
            "allow_whatsapp_group": RADIO_WIDGET,
            "lattes_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://lattes.cnpq.br/...",
            }),
            "instagram": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "@seuperfil",
            }),
            "application_type": RADIO_WIDGET,
            "category": RADIO_WIDGET,
            "payment_agreement": CHECKBOX_WIDGET,
            "truth_declaration": CHECKBOX_WIDGET,
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Não foi possível enviar o formulário.")
        return ""

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_cpf(self):
        cpf = self.cleaned_data["cpf"]
        if not _cpf_is_valid(cpf):
            raise forms.ValidationError("Informe um CPF válido.")
        return _format_cpf(cpf)

    def _clean_upload(self, field_name, max_size):
        uploaded_file = self.cleaned_data[field_name]
        allowed_types = {
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/webp",
        }
        if uploaded_file.content_type not in allowed_types:
            raise forms.ValidationError(
                "Formato inválido. Envie PDF, JPG, PNG ou WEBP."
            )
        if uploaded_file.size > max_size:
            max_mb = max_size // (1024 * 1024)
            raise forms.ValidationError(
                f"O arquivo deve ter no máximo {max_mb} MB."
            )
        uploaded_file.seek(0)
        return uploaded_file

    def clean_supporting_document(self):
        return self._clean_upload("supporting_document", 100 * 1024 * 1024)

    def clean_payment_receipt(self):
        return self._clean_upload("payment_receipt", 10 * 1024 * 1024)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        cpf = cleaned_data.get("cpf")
        application_type = cleaned_data.get("application_type")
        has_disability = cleaned_data.get("has_disability")
        disability_description = cleaned_data.get("disability_description")

        if has_disability == MembershipApplication.YesNo.YES and not disability_description:
            self.add_error(
                "disability_description",
                "Descreva a deficiência informada.",
            )

        if email and cpf:
            pending = MembershipApplication.objects.filter(
                status=MembershipApplication.Status.PENDING,
            ).filter(Q(email__iexact=email) | Q(cpf=cpf))
            if self.instance.pk:
                pending = pending.exclude(pk=self.instance.pk)
            if pending.exists():
                raise forms.ValidationError(
                    "Já existe uma solicitação pendente para este e-mail ou CPF."
                )

            existing_user = User.objects.filter(
                Q(email__iexact=email) | Q(cpf=cpf)
            ).first()
            if application_type == MembershipApplication.ApplicationType.NEW and existing_user:
                self.add_error(
                    "application_type",
                    "Já existe cadastro com este e-mail ou CPF. Selecione renovação.",
                )
            if application_type == MembershipApplication.ApplicationType.RENEWAL and not existing_user:
                self.add_error(
                    "application_type",
                    "Não encontramos cadastro anterior. Selecione nova associação.",
                )

        return cleaned_data


class MembershipReviewForm(forms.Form):
    target_role = forms.ChoiceField(
        label="Função no sistema",
        widget=forms.Select(attrs=FORM_CONTROL),
    )
    decision_notes = forms.CharField(
        label="Observações internas",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
        }),
    )

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [
            ("associate", "Associado"),
            ("executive", "Executivo"),
        ]
        if actor and getattr(actor, "is_president", False):
            choices.append(("president", "Presidente"))
        self.fields["target_role"].choices = choices


class MemberRoleForm(forms.Form):
    role = forms.ChoiceField(
        label="Nova função",
        widget=forms.Select(attrs=FORM_CONTROL),
    )

    def __init__(self, *args, actor=None, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [
            ("associate", "Associado"),
            ("executive", "Executivo"),
        ]
        if actor and getattr(actor, "is_president", False):
            choices.append(("president", "Presidente"))
        self.fields["role"].choices = choices
        if member:
            self.fields["role"].initial = member.role