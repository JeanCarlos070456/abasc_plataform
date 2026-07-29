from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('ABASC', {'fields': (
            'supabase_user_id',
            'role',
            'membership_number',
            'association_status',
            'phone',
            'cpf',
            'profession',
            'city',
            'state',
            'joined_association_at',
            'avatar_url',
        )}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('ABASC', {'fields': (
            'email',
            'role',
            'association_status',
        )}),
    )
    list_display = (
        'email',
        'first_name',
        'last_name',
        'role',
        'association_status',
        'is_active',
    )
    list_filter = (
        'role',
        'association_status',
        'is_active',
        'is_staff',
    )
    search_fields = (
        'email',
        'first_name',
        'last_name',
        'membership_number',
        'cpf',
    )
    ordering = ('email',)
