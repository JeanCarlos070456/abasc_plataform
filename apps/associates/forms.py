from django import forms
from .models import Payment

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'associate',
            'reference_month',
            'due_date',
            'paid_at',
            'amount',
            'status',
            'notes',
        ]
        widgets = {
            'associate': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'reference_month': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'paid_at': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'status': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'notes': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['associate'].queryset = (
            self.fields['associate'].queryset
            .filter(is_active=True)
            .order_by('first_name', 'last_name', 'email')
        )


    def clean_reference_month(self):
        reference_month = self.cleaned_data['reference_month']
        return reference_month.replace(day=1)
