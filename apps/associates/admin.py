from django.contrib import admin

from .models import MembershipApplication, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "associate",
        "reference_month",
        "due_date",
        "paid_at",
        "amount",
        "status",
    )
    list_filter = ("status", "reference_month", "due_date")
    search_fields = (
        "associate__email",
        "associate__first_name",
        "associate__last_name",
        "notes",
    )
    autocomplete_fields = ("associate",)


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "cpf",
        "application_type",
        "category",
        "status",
        "requested_at",
        "reviewed_by",
    )
    list_filter = (
        "status",
        "application_type",
        "category",
        "state",
        "requested_at",
    )
    search_fields = (
        "full_name",
        "email",
        "cpf",
        "city",
        "university",
    )
    readonly_fields = (
        "requested_at",
        "reviewed_at",
        "supporting_document_path",
        "payment_receipt_path",
    )
    autocomplete_fields = ("reviewed_by", "approved_user")