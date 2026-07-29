from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'associate',
        'reference_month',
        'due_date',
        'paid_at',
        'amount',
        'status',
    )
    list_filter = ('status', 'reference_month', 'due_date')
    search_fields = (
        'associate__email',
        'associate__first_name',
        'associate__last_name',
        'notes',
    )
    autocomplete_fields = ('associate',)
