from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Custom User Admin for managing users with roles
    """
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = UserAdmin.list_filter + ('role', 'is_active')
    search_fields = UserAdmin.search_fields + ('role', 'phone_number')
