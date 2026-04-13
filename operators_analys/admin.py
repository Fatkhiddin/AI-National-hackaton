from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import IPPhoneCall, STTRecord, AIAnalysis, OperatorAIConfiguration


@admin.register(OperatorAIConfiguration)
class OperatorAIConfigurationAdmin(admin.ModelAdmin):
    """
    Operator AI Konfiguratsiya admin panel
    """
    list_display = ('name', 'api_provider', 'model_name', 'temperature', 'max_tokens', 'is_active_badge', 'is_default_badge', 'updated_at')
    list_filter = ('api_provider', 'is_active', 'is_default')
    search_fields = ('name', 'model_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Asosiy', {
            'fields': ('name', 'is_active', 'is_default')
        }),
        ('API Sozlamalari', {
            'fields': ('api_provider', 'api_key', 'api_endpoint', 'model_name')
        }),
        ('Promptlar', {
            'fields': ('system_prompt', 'analysis_prompt_template'),
            'description': 'Tahlil promptlarini sozlang. {{text}} o\'rniga suhbat matni qo\'yiladi.'
        }),
        ('Model Parametrlari', {
            'fields': ('temperature', 'max_tokens'),
            'description': 'AI model parametrlari. Temperature: 0=aniq, 2=ijodiy. Max tokens: javob uzunligi.'
        }),
        ('Vaqtlar', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span style="color: #10b981; font-weight: bold;">✓ Faol</span>')
        return mark_safe('<span style="color: #ef4444;">✗ Nofaol</span>')
    is_active_badge.short_description = "Holat"
    
    def is_default_badge(self, obj):
        if obj.is_default:
            return mark_safe('<span style="color: #3b82f6; font-weight: bold;">⭐ Standart</span>')
        return '—'
    is_default_badge.short_description = "Standart"


@admin.register(IPPhoneCall)
class IPPhoneCallAdmin(admin.ModelAdmin):
    """
    IP Phone Calls admin panel
    """
    list_display = ('phone', 'operator_name', 'tree_name', 'status', 'timestamp')
    list_filter = ('tree_name', 'status', 'timestamp')
    search_fields = ('phone', 'operator_name', 'client_name', 'call_id')
    readonly_fields = (
        'call_id', 'timestamp', 'src_num', 'dst_num',
        'duration_seconds', 'call_record_link'
    )
    fieldsets = (
        ('Qo\'ng\'iroq Ma\'lumotlari', {
            'fields': (
                'call_id', 'phone', 'timestamp',
                'src_num', 'dst_num', 'duration_seconds'
            )
        }),
        ('Shaxslar', {
            'fields': ('operator_name', 'client_name')
        }),
        ('Holat', {
            'fields': ('tree_name', 'status', 'call_record_link')
        })
    )
    ordering = ['-timestamp']


@admin.register(STTRecord)
class STTRecordAdmin(admin.ModelAdmin):
    """
    STT (Speech-to-Text) yozuvlar admin panel
    """
    list_display = ('id', 'status_badge', 'language', 'short_text', 'processed_by', 'created_at')
    list_filter = ('status', 'language', 'created_at')
    search_fields = ('transcribed_text', 'original_audio_url')
    readonly_fields = (
        'content_type', 'object_id', 'api_response',
        'processed_at', 'created_at', 'updated_at'
    )
    fieldsets = (
        ('Qo\'ng\'iroq', {
            'fields': ('content_type', 'object_id', 'original_audio_url')
        }),
        ('STT Natija', {
            'fields': ('transcribed_text', 'status', 'error_message')
        }),
        ('Sozlamalar', {
            'fields': ('language', 'with_offsets', 'with_diarization')
        }),
        ('Ma\'lumotlar', {
            'fields': ('processed_by', 'processed_at', 'duration_seconds', 'api_response'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'processing': '#3b82f6',
            'completed': '#10b981',
            'failed': '#ef4444',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def short_text(self, obj):
        if obj.transcribed_text:
            return obj.transcribed_text[:80] + '...' if len(obj.transcribed_text) > 80 else obj.transcribed_text
        return '—'
    short_text.short_description = "Matn"


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    """
    AI Tahlil admin panel
    """
    list_display = ('id', 'status_badge', 'overall_score_badge', 'satisfaction_badge', 'analyzed_by', 'analyzed_at')
    list_filter = ('status', 'customer_satisfaction', 'analyzed_at')
    search_fields = ('analysis_text',)
    readonly_fields = (
        'stt_record', 'ai_config', 'api_response', 'tokens_used',
        'analyzed_at', 'created_at', 'updated_at'
    )
    fieldsets = (
        ('Bog\'lanish', {
            'fields': ('stt_record', 'ai_config')
        }),
        ('AI Tahlil Natijasi', {
            'fields': ('analysis_text', 'overall_score', 'customer_satisfaction', 'status', 'error_message')
        }),
        ('Qo\'shimcha', {
            'fields': ('key_points', 'recommendations')
        }),
        ('Ma\'lumotlar', {
            'fields': ('analyzed_by', 'analyzed_at', 'tokens_used', 'api_response'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'processing': '#3b82f6',
            'completed': '#10b981',
            'failed': '#ef4444',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def overall_score_badge(self, obj):
        if obj.overall_score is None:
            return '—'
        if obj.overall_score >= 7:
            color = '#10b981'
        elif obj.overall_score >= 4:
            color = '#f59e0b'
        else:
            color = '#ef4444'
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 1.2em;">{}/10</span>',
            color, obj.overall_score
        )
    overall_score_badge.short_description = "Baho"
    
    def satisfaction_badge(self, obj):
        icons = {
            'satisfied': '😊 Qoniqdi',
            'neutral': '😐 Neytral',
            'unsatisfied': '😞 Qoniqmadi',
            'unknown': '❓ Noma\'lum',
        }
        return icons.get(obj.customer_satisfaction, obj.customer_satisfaction)
    satisfaction_badge.short_description = "Mijoz"
