from io import BytesIO

from django import forms
from PIL import Image, UnidentifiedImageError

from .models import User


AVATAR_MAX_SIZE = 2 * 1024 * 1024
AVATAR_MAX_DIMENSION = 6000
AVATAR_FORMATS = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'WEBP': 'image/webp',
}


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'autocomplete': 'email',
            'placeholder': 'seuemail@exemplo.com',
        }),
    )
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'current-password',
            'placeholder': 'Sua senha',
        }),
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'cpf',
            'profession', 'city', 'state',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'profession': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(
                attrs={'class': 'form-control', 'maxlength': 2}
            ),
        }


class AvatarForm(forms.Form):
    avatar = forms.ImageField(
        label='Nova foto',
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/webp',
        }),
        help_text='Envie JPG, PNG ou WEBP com no máximo 2 MB.',
    )
    remove_avatar = forms.BooleanField(
        label='Remover minha foto atual',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
    )

    def clean_avatar(self):
        uploaded_file = self.cleaned_data.get('avatar')
        if not uploaded_file:
            return uploaded_file

        if uploaded_file.size > AVATAR_MAX_SIZE:
            raise forms.ValidationError(
                'A foto deve ter no máximo 2 MB.'
            )

        try:
            uploaded_file.seek(0)
            content = uploaded_file.read()
            uploaded_file.seek(0)

            with Image.open(BytesIO(content)) as image:
                image_format = (image.format or '').upper()
                width, height = image.size
                image.verify()

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
        ) as exc:
            raise forms.ValidationError(
                'O arquivo enviado não é uma imagem válida.'
            ) from exc

        if image_format not in AVATAR_FORMATS:
            raise forms.ValidationError(
                'Formato inválido. Envie JPG, PNG ou WEBP.'
            )

        if (
            width > AVATAR_MAX_DIMENSION
            or height > AVATAR_MAX_DIMENSION
        ):
            raise forms.ValidationError(
                'A imagem deve ter no máximo 6000 × 6000 pixels.'
            )

        # O tipo usado no Storage passa a vir do conteúdo validado,
        # e não apenas do cabeçalho informado pelo navegador.
        uploaded_file.content_type = AVATAR_FORMATS[image_format]
        uploaded_file.seek(0)
        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()
        avatar = cleaned_data.get('avatar')
        remove_avatar = cleaned_data.get('remove_avatar')

        if avatar and remove_avatar:
            raise forms.ValidationError(
                'Escolha entre enviar uma nova foto ou remover a atual.'
            )

        if not avatar and not remove_avatar:
            raise forms.ValidationError(
                'Selecione uma foto ou marque a opção para remover a atual.'
            )

        return cleaned_data


class RoleUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'role', 'association_status',
            'membership_number', 'is_active',
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'association_status': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'membership_number': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'is_active': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }