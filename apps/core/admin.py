from django.contrib import admin
from .models import AuditLog, SiteConfiguration

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'contact_email', 'updated_at')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'actor', 'action', 'description', 'ip_address'
    )
    list_filter = ('action', 'created_at')
    search_fields = (
        'description', 'actor__email',
        'actor__first_name', 'actor__last_name',
    )
    readonly_fields = (
        'actor', 'action', 'description', 'object_type',
        'object_id', 'ip_address', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
