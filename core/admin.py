from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import CRMConfiguration


@admin.register(CRMConfiguration)
class CRMConfigurationAdmin(admin.ModelAdmin):
    """
    CRM Configuration admin panel
    """
    list_display = ('crm_url', 'status_badge', 'test_button', 'last_connection_attempt')
    readonly_fields = (
        'access_token', 'refresh_token', 'token_expires_at',
        'is_connected', 'last_connection_attempt',
        'connection_error_message', 'created_at', 'updated_at',
        'test_connection_button'
    )
    fieldsets = (
        ('CRM Sozlamalari', {
            'fields': ('crm_url', 'username', 'password')
        }),
        ('Token Ma\'lumotlari', {
            'fields': (
                'access_token', 'refresh_token', 'token_expires_at',
                'test_connection_button'
            ),
            'classes': ('collapse',)
        }),
        ('Holati', {
            'fields': (
                'is_connected', 'connection_error_message',
                'last_connection_attempt', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    def status_badge(self, obj):
        """
        Holat badge ko'rsatish
        """
        if obj.is_connected:
            return format_html(
                '<span style="color: green; font-weight: bold;">● Ulangan</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">● Ulanmagan</span>'
            )
    status_badge.short_description = "Holat"

    def test_button(self, obj):
        """
        CRM test tugmasi
        """
        return format_html(
            '<a class="button" href="#" onclick="alert(\'Test xususiyati tez orada!\');">Test ulanish</a>'
        )
    test_button.short_description = "Harakat"

    def test_connection_button(self, obj):
        """
        Test ulanish na'muna
        """
        if not obj.id:
            return "Avval saqlang"
        
        status = "✓ Ulangan" if obj.is_connected else "✗ Ulanmagan"
        error = f"\n\nXato: {obj.connection_error_message}" if obj.connection_error_message else ""
        
        return format_html(
            f'<div style="padding: 10px; background: #f0f0f0; border-radius: 4px;">'
            f'<strong>Holat:</strong> {status}'
            f'<br><small style="color: #666;">{obj.last_connection_attempt}{error}</small>'
            f'</div>'
        )
    test_connection_button.short_description = "Ulanish holatini tekshirish"

    def has_add_permission(self, request):
        """
        Faqat bitta konfiguratsiya yaratish
        """
        return not CRMConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """
        O'chirishni blokirovka qilish
        """
        return False

    actions = ['test_crm_connection']

    def test_crm_connection(self, request, queryset):
        """
        CRM ulanishini tekshirish action
        """
        for config in queryset:
            success, message = config.test_connection()
            self.message_user(
                request,
                f"{config.crm_url}: {message}",
                level='success' if success else 'error'
            )
    test_crm_connection.short_description = "CRM ulanishini tekshirish"
