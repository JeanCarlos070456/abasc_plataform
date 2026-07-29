from django import forms
from .models import User

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
