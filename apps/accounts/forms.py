from io import BytesIO
import re

from django import forms
from PIL import Image, UnidentifiedImageError

from .models import User


AVATAR_MAX_SIZE = 2 * 1024 * 1024
AVATAR_MAX_DIMENSION = 6000
AVATAR_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def _digits(value):
    return re.sub(r"\D", "", value or "")


def _valid_cpf(value):
    cpf = _digits(value)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    for position in (9, 10):
        total = sum(
            int(cpf[index]) * (position + 1 - index)
            for index in range(position)
        )
        digit = (total * 10) % 11
        if digit == 10:
            digit = 0
        if digit != int(cpf[position]):
            return False

    return True


def _clean_cpf(value):
    cpf = _digits(value)

    if not _valid_cpf(cpf):
        raise forms.ValidationError("Informe um CPF válido.")

    return cpf


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "autocomplete": "email",
            "placeholder": "seuemail@exemplo.com",
        }),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "current-password",
            "placeholder": "Sua senha",
        }),
    )


class FirstAccessForm(forms.Form):
    """
    Localiza um associado migrado da base histórica.

    Este formulário não autentica o usuário. A posse do e-mail é confirmada
    posteriormente pelo link seguro enviado pelo Supabase Auth.
    """

    email = forms.EmailField(
        label="E-mail cadastrado na ABASC",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "autocomplete": "email",
            "placeholder": "seuemail@exemplo.com",
        }),
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "autocomplete": "off",
            "inputmode": "numeric",
            "placeholder": "000.000.000-00",
        }),
        help_text="Informe o CPF vinculado ao seu cadastro histórico.",
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_cpf(self):
        return _clean_cpf(self.cleaned_data.get("cpf"))


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "cpf",
            "birth_date",
            "gender",
            "profession",
            "education_level",
            "university",
            "city",
            "state",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "autocomplete": "tel",
            }),
            "cpf": forms.TextInput(attrs={
                "class": "form-control",
                "inputmode": "numeric",
            }),
            "birth_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "profession": forms.TextInput(attrs={"class": "form-control"}),
            "education_level": forms.TextInput(attrs={"class": "form-control"}),
            "university": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": 2,
            }),
        }

    def clean_cpf(self):
        return _clean_cpf(self.cleaned_data.get("cpf"))

    def clean_state(self):
        return (self.cleaned_data.get("state") or "").strip().upper()


class OnboardingForm(ProfileForm):
    """
    Formulário obrigatório para o primeiro acesso de associados migrados.
    """

    REQUIRED_FIELDS = (
        "first_name",
        "last_name",
        "phone",
        "cpf",
        "birth_date",
        "city",
        "state",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in self.REQUIRED_FIELDS:
            self.fields[field_name].required = True

        self.fields["first_name"].label = "Nome"
        self.fields["last_name"].label = "Sobrenome"
        self.fields["phone"].label = "Telefone / WhatsApp"
        self.fields["birth_date"].label = "Data de nascimento"
        self.fields["education_level"].label = "Escolaridade"
        self.fields["university"].label = "Universidade / instituição"
        self.fields["state"].label = "UF"

        self.fields["gender"].required = False
        self.fields["profession"].required = False
        self.fields["education_level"].required = False
        self.fields["university"].required = False

    def clean_phone(self):
        phone = _digits(self.cleaned_data.get("phone"))
        if len(phone) < 10 or len(phone) > 11:
            raise forms.ValidationError(
                "Informe um telefone com DDD válido."
            )
        return phone

    def clean_state(self):
        state = super().clean_state()
        if len(state) != 2 or not state.isalpha():
            raise forms.ValidationError("Informe a UF com duas letras.")
        return state


class AvatarForm(forms.Form):
    avatar = forms.ImageField(
        label="Nova foto",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/jpeg,image/png,image/webp",
        }),
        help_text="Envie JPG, PNG ou WEBP com no máximo 2 MB.",
    )
    remove_avatar = forms.BooleanField(
        label="Remover minha foto atual",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
        }),
    )

    def clean_avatar(self):
        uploaded_file = self.cleaned_data.get("avatar")
        if not uploaded_file:
            return uploaded_file

        if uploaded_file.size > AVATAR_MAX_SIZE:
            raise forms.ValidationError(
                "A foto deve ter no máximo 2 MB."
            )

        try:
            uploaded_file.seek(0)
            content = uploaded_file.read()
            uploaded_file.seek(0)

            with Image.open(BytesIO(content)) as image:
                image_format = (image.format or "").upper()
                width, height = image.size
                image.verify()

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
        ) as exc:
            raise forms.ValidationError(
                "O arquivo enviado não é uma imagem válida."
            ) from exc

        if image_format not in AVATAR_FORMATS:
            raise forms.ValidationError(
                "Formato inválido. Envie JPG, PNG ou WEBP."
            )

        if (
            width > AVATAR_MAX_DIMENSION
            or height > AVATAR_MAX_DIMENSION
        ):
            raise forms.ValidationError(
                "A imagem deve ter no máximo 6000 × 6000 pixels."
            )

        uploaded_file.content_type = AVATAR_FORMATS[image_format]
        uploaded_file.seek(0)
        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()
        avatar = cleaned_data.get("avatar")
        remove_avatar = cleaned_data.get("remove_avatar")

        if avatar and remove_avatar:
            raise forms.ValidationError(
                "Escolha entre enviar uma nova foto ou remover a atual."
            )

        if not avatar and not remove_avatar:
            raise forms.ValidationError(
                "Selecione uma foto ou marque a opção para remover a atual."
            )

        return cleaned_data


class OnboardingAvatarForm(forms.Form):
    avatar = forms.ImageField(
        label="Foto de perfil",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/jpeg,image/png,image/webp",
        }),
        help_text="Envie JPG, PNG ou WEBP com no máximo 2 MB.",
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        has_avatar = bool(
            getattr(user, "avatar_path", "")
            or getattr(user, "avatar_url", "")
        )
        self.fields["avatar"].required = not has_avatar

    def clean_avatar(self):
        uploaded_file = self.cleaned_data.get("avatar")
        if not uploaded_file:
            return uploaded_file

        validator = AvatarForm(
            files={"avatar": uploaded_file},
            data={"remove_avatar": ""},
        )
        if not validator.is_valid():
            avatar_errors = validator.errors.get("avatar")
            if avatar_errors:
                raise forms.ValidationError(avatar_errors)
            raise forms.ValidationError(
                "Não foi possível validar a foto enviada."
            )

        return validator.cleaned_data["avatar"]

    def clean(self):
        cleaned_data = super().clean()
        has_avatar = bool(
            getattr(self.user, "avatar_path", "")
            or getattr(self.user, "avatar_url", "")
        )
        if not cleaned_data.get("avatar") and not has_avatar:
            self.add_error(
                "avatar",
                "Adicione uma foto de perfil para concluir o primeiro acesso.",
            )
        return cleaned_data


class RoleUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "role",
            "association_status",
            "membership_number",
            "is_active",
        ]
        widgets = {
            "role": forms.Select(attrs={"class": "form-control"}),
            "association_status": forms.Select(
                attrs={"class": "form-control"}
            ),
            "membership_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }