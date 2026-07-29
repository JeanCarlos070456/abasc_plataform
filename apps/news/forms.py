from django import forms
from django.db.models import Q
from .models import Category, Post

class PostForm(forms.ModelForm):
    image_file = forms.ImageField(
        label='Enviar nova imagem',
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/png,image/jpeg,image/webp',
        }),
    )

    class Meta:
        model = Post
        fields = [
            'title',
            'summary',
            'body',
            'category',
            'external_url',
            'image_url',
            'status',
            'visibility',
            'featured',
            'is_opportunity',
            'published_at',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título da publicação',
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Resumo curto para o card',
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 12,
                'placeholder': 'Conteúdo completo',
            }),
            'category': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'external_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...',
            }),
            'image_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Opcional: URL de imagem existente',
            }),
            'status': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'visibility': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'published_at': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                },
                format='%Y-%m-%dT%H:%M',
            ),
            'featured': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'is_opportunity': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category_queryset = Category.objects.filter(active=True)
        if self.instance and self.instance.category_id:
            category_queryset = Category.objects.filter(
                Q(active=True) | Q(pk=self.instance.category_id)
            )
        self.fields['category'].queryset = category_queryset
        if self.instance and self.instance.published_at:
            self.initial['published_at'] = (
                self.instance.published_at.strftime('%Y-%m-%dT%H:%M')
            )

    def clean_image_file(self):
        image = self.cleaned_data.get('image_file')
        if not image:
            return image
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                'A imagem deve ter no máximo 5 MB.'
            )
        image_format = getattr(
            getattr(image, 'image', None),
            'format',
            '',
        ).upper()
        if image_format not in {'JPEG', 'PNG', 'WEBP'}:
            raise forms.ValidationError(
                'Formato inválido. Use JPEG, PNG ou WEBP.'
            )
        image.seek(0)
        return image

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'active': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }
