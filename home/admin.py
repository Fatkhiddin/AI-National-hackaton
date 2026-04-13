from django.contrib import admin
from django.utils.html import mark_safe
from .models import CRMConfiguration, AIConfiguration, UzbekVoiceConfiguration


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
            return mark_safe(
                '<span style="color: green; font-weight: bold;">● Ulangan</span>'
            )
        else:
            return mark_safe(
                '<span style="color: red; font-weight: bold;">● Ulanmagan</span>'
            )
    status_badge.short_description = "Holat"

    def test_button(self, obj):
        """
        CRM test tugmasi
        """
        return mark_safe(
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
        
        html = f'<div style="padding: 10px; background: #f0f0f0; border-radius: 4px;">' \
               f'<strong>Holat:</strong> {status}' \
               f'<br><small style="color: #666;">{obj.last_connection_attempt}{error}</small>' \
               f'</div>'
        return mark_safe(html)
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


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = ('provider', 'model', 'status_badge', 'updated_at')
    fieldsets = (
        ('AI Sozlamalari', {
            'fields': ('provider', 'api_key', 'model')
        }),
    )

    def status_badge(self, obj):
        if obj.api_key:
            return mark_safe('<span style="color: green; font-weight: bold;">● Sozlangan</span>')
        return mark_safe('<span style="color: red; font-weight: bold;">● Sozlanmagan</span>')
    status_badge.short_description = "Holat"

    def has_add_permission(self, request):
        return not AIConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UzbekVoiceConfiguration)
class UzbekVoiceConfigurationAdmin(admin.ModelAdmin):
    """
    UzbekVoice.ai STT Configuration admin panel
    """
    list_display = ('__str__', 'default_language', 'status_badge', 'is_active', 'updated_at')
    fieldsets = (
        ('UzbekVoice.ai STT Sozlamalari', {
            'fields': ('api_key', 'api_url', 'default_language', 'is_active'),
            'description': 'UzbekVoice.ai dan olingan API kalitni shu yerga kiriting. '
                           'API key olish: https://uzbekvoice.ai da ro\'yxatdan o\'ting.'
        }),
    )

    def status_badge(self, obj):
        if obj.api_key:
            return mark_safe('<span style="color: green; font-weight: bold;">● Sozlangan</span>')
        return mark_safe('<span style="color: red; font-weight: bold;">● Sozlanmagan</span>')
    status_badge.short_description = "Holat"

    def has_add_permission(self, request):
        return not UzbekVoiceConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False