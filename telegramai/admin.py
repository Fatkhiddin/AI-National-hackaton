from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from .models import (
    TelegramAccount, 
    Contact, 
    Chat, 
    Message, 
    AIIntegration, 
    ContactImportHistory,
    MessagingCampaign,
    CampaignMessageLog,
    AutoReplyRule,
    AutoReplyLog,
    AIProvider,
    AIAssistant,
    ConversationSummary,
    CRMProvider,
    PropertySearchLog,
    PropertyInterest
)


# Contact Resource for Import/Export
class ContactResource(resources.ModelResource):
    telegram_account = fields.Field(
        column_name='telegram_account',
        attribute='telegram_account',
        widget=ForeignKeyWidget(TelegramAccount, 'session_name')
    )
    
    class Meta:
        model = Contact
        fields = ('id', 'telegram_account', 'name', 'phone_number', 'username', 
                 'first_name', 'last_name', 'is_premium', 'is_bot', 'added_to_telegram')
        export_order = fields


@admin.register(TelegramAccount)
class TelegramAccountAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'session_name', 'user', 'is_active', 'is_spam_blocked', 'created_at')
    list_filter = ('is_active', 'is_spam_blocked', 'created_at', 'user')
    search_fields = ('phone_number', 'session_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'spam_block_until')
    list_per_page = 25
    list_select_related = ('user',)
    
    fieldsets = (
        ('Account Info', {
            'fields': ('user', 'phone_number', 'session_name', 'is_active')
        }),
        ('API Credentials', {
            'fields': ('api_id', 'api_hash'),
            'classes': ('collapse',)
        }),
        ('Spam Status', {
            'fields': ('is_spam_blocked', 'spam_block_until', 'spam_info'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['activate_accounts', 'deactivate_accounts']
    
    def activate_accounts(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} account faollashtirildi.')
    activate_accounts.short_description = "Tanlangan account larni faollashtirish"
    
    def deactivate_accounts(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} account nofaol qilindi.')
    deactivate_accounts.short_description = "Tanlangan account larni nofaol qilish"


@admin.register(Contact)
class ContactAdmin(ImportExportModelAdmin):
    resource_class = ContactResource
    list_display = ('name', 'phone_number', 'username', 'telegram_account', 'added_to_telegram', 'created_at')
    list_filter = ('telegram_account', 'added_to_telegram', 'is_premium', 'is_bot', 'created_at')
    search_fields = ('name', 'phone_number', 'username', 'first_name', 'last_name')
    list_per_page = 50
    list_max_show_all = 200
    list_select_related = ('telegram_account',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('telegram_account', 'name', 'phone_number')
        }),
        ('Telegram Info', {
            'fields': ('username', 'user_id', 'first_name', 'last_name', 'is_premium', 'is_bot')
        }),
        ('Status', {
            'fields': ('added_to_telegram',)
        })
    )
    
    actions = ['mark_as_added_to_telegram', 'mark_as_not_added_to_telegram']
    
    def mark_as_added_to_telegram(self, request, queryset):
        count = queryset.update(added_to_telegram=True)
        self.message_user(request, f'{count} contacts marked as added to Telegram.')
    mark_as_added_to_telegram.short_description = "Mark selected contacts as added to Telegram"
    
    def mark_as_not_added_to_telegram(self, request, queryset):
        count = queryset.update(added_to_telegram=False)
        self.message_user(request, f'{count} contacts marked as not added to Telegram.')
    mark_as_not_added_to_telegram.short_description = "Mark selected contacts as not added to Telegram"


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('title', 'username', 'chat_type', 'member_count', 'telegram_account', 'created_at')
    list_filter = ('chat_type', 'is_verified', 'is_restricted', 'telegram_account', 'created_at')
    search_fields = ('title', 'username', 'chat_id')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    list_select_related = ('telegram_account',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chat', 'get_short_text', 'message_type', 'is_outgoing', 'contact', 'date')
    list_filter = ('message_type', 'is_outgoing', 'telegram_account', 'chat__chat_type', 'date')
    search_fields = ('text', 'chat__title', 'contact__name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'date'
    list_per_page = 25
    list_select_related = ('chat', 'contact', 'telegram_account')
    
    def get_short_text(self, obj):
        if obj.text:
            return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
        return f"[{obj.message_type}]"
    get_short_text.short_description = "Message"
    
    fieldsets = (
        ('Message Info', {
            'fields': ('telegram_account', 'chat', 'contact', 'message_id', 'text', 'message_type')
        }),
        ('Details', {
            'fields': ('is_outgoing', 'date', 'reply_to_message_id', 'media_path')
        })
    )


@admin.register(AIIntegration)
class AIIntegrationAdmin(admin.ModelAdmin):
    list_display = ('telegram_account', 'provider', 'model_name', 'is_active', 'created_at')
    list_filter = ('provider', 'is_active', 'telegram_account', 'created_at')
    search_fields = ('model_name', 'telegram_account__phone_number')
    
    fieldsets = (
        ('Basic Settings', {
            'fields': ('telegram_account', 'provider', 'model_name', 'is_active')
        }),
        ('API Configuration', {
            'fields': ('api_key',),
            'classes': ('collapse',)
        }),
        ('Model Parameters', {
            'fields': ('max_tokens', 'temperature', 'system_prompt'),
            'classes': ('collapse',)
        })
    )


@admin.register(ContactImportHistory)
class ContactImportHistoryAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'telegram_account', 'total_contacts', 'successful_imports', 'failed_imports', 'import_date')
    list_filter = ('telegram_account', 'import_date')
    search_fields = ('file_name', 'notes')
    readonly_fields = ('import_date',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MessagingCampaign)
class MessagingCampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'use_ai', 'sent_count', 'total_contacts', 'created_at')
    list_filter = ('status', 'use_ai', 'created_at', 'user')
    search_fields = ('title', 'message_template')
    readonly_fields = ('total_contacts', 'sent_count', 'failed_count', 'spam_blocked_count', 'started_at', 'completed_at')
    filter_horizontal = ('accounts', 'contacts')
    list_per_page = 25
    
    fieldsets = (
        ('Campaign Info', {
            'fields': ('user', 'title', 'status')
        }),
        ('Targets', {
            'fields': ('accounts', 'contacts')
        }),
        ('Message Settings', {
            'fields': ('message_template', 'use_ai', 'ai_prompt', 'delay_between_messages')
        }),
        ('Statistics', {
            'fields': ('total_contacts', 'sent_count', 'failed_count', 'spam_blocked_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(CampaignMessageLog)
class CampaignMessageLogAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'account', 'contact', 'status', 'sent_at')
    list_filter = ('status', 'campaign', 'account', 'sent_at')
    search_fields = ('message_text', 'contact__phone_number', 'error_message')
    readonly_fields = ('sent_at', 'created_at')
    list_per_page = 50
    list_select_related = ('campaign', 'account', 'contact')
    
    def has_add_permission(self, request):
        return False


@admin.register(CRMProvider)
class CRMProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'crm_type', 'user', 'is_active', 'created_at')
    list_filter = ('crm_type', 'is_active', 'created_at')
    search_fields = ('name', 'api_url', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    
    fieldsets = (
        ('Asosiy Ma\'lumot', {
            'fields': ('user', 'name', 'crm_type', 'is_active')
        }),
        ('API Sozlamalari', {
            'fields': ('api_url', 'api_key', 'api_secret'),
            'classes': ('collapse',)
        }),
        ('Field Mapping', {
            'fields': ('field_mapping', 'request_template', 'extraction_prompt'),
            'classes': ('collapse',)
        }),
        ('Vaqt', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(PropertySearchLog)
class PropertySearchLogAdmin(admin.ModelAdmin):
    list_display = ('chat_id', 'username', 'crm_provider', 'results_count', 'status', 'created_at')
    list_filter = ('status', 'crm_provider', 'created_at')
    search_fields = ('username', 'chat_id')
    readonly_fields = ('created_at', 'extracted_requirements', 'crm_request', 'crm_response')
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Qidiruv Ma\'lumoti', {
            'fields': ('crm_provider', 'telegram_account', 'chat_id', 'username')
        }),
        ('Talablar', {
            'fields': ('extracted_requirements',)
        }),
        ('CRM Ma\'lumotlari', {
            'fields': ('crm_request', 'crm_response'),
            'classes': ('collapse',)
        }),
        ('Natija', {
            'fields': ('results_count', 'results_sent', 'status', 'error_message')
        }),
        ('Vaqt', {
            'fields': ('created_at',)
        })
    )
    
    def has_add_permission(self, request):
        return False


@admin.register(AutoReplyRule)
class AutoReplyRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_account', 'is_active', 'trigger_type', 'messages_sent_count', 'created_at')
    list_filter = ('is_active', 'trigger_type', 'work_hours_only', 'reply_once_per_user', 'only_private_chats', 'created_at')
    search_fields = ('name', 'reply_message', 'keywords', 'telegram_account__phone_number')
    readonly_fields = ('messages_sent_count', 'created_at', 'updated_at')
    list_editable = ('is_active',)
    list_per_page = 25
    list_select_related = ('telegram_account',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('telegram_account', 'name', 'is_active')
        }),
        ('Trigger Settings', {
            'fields': ('trigger_type', 'keywords', 'reply_message', 'delay_seconds')
        }),
        ('Realistic Behavior', {
            'fields': ('mark_as_read', 'show_typing', 'typing_duration'),
            'description': 'Make auto-replies look more human-like with typing indicators and read receipts'
        }),
        ('Advanced Settings', {
            'fields': ('reply_once_per_user', 'only_private_chats', 'work_hours_only', 'work_hours_start', 'work_hours_end', 'excluded_users'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('messages_sent_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(AutoReplyLog)
class AutoReplyLogAdmin(admin.ModelAdmin):
    list_display = ('rule', 'username', 'user_id', 'reply_sent', 'sent_at')
    list_filter = ('reply_sent', 'rule', 'sent_at')
    search_fields = ('username', 'trigger_message', 'error_message')
    readonly_fields = ('sent_at',)
    list_per_page = 50
    list_select_related = ('rule', 'rule__telegram_account')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'user', 'is_active', 'created_at')
    list_filter = ('provider_type', 'is_active', 'created_at')
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)
    list_per_page = 25
    list_select_related = ('user',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'name', 'provider_type', 'is_active')
        }),
        ('API Configuration', {
            'fields': ('api_key', 'api_endpoint'),
            'description': 'API kalit va endpoint sozlamalari'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(AIAssistant)
class AIAssistantAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_account', 'ai_provider', 'model', 'is_active', 'auto_respond', 'messages_processed')
    list_filter = ('is_active', 'auto_respond', 'only_private_chats', 'ai_provider__provider_type', 'created_at')
    search_fields = ('name', 'system_prompt', 'telegram_account__phone_number')
    readonly_fields = ('messages_processed', 'created_at', 'updated_at')
    list_editable = ('is_active', 'auto_respond')
    list_per_page = 25
    list_select_related = ('telegram_account', 'ai_provider')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('telegram_account', 'ai_provider', 'name', 'is_active')
        }),
        ('AI Configuration', {
            'fields': ('model', 'system_prompt', 'auto_respond'),
            'description': 'AI model va prompt sozlamalari'
        }),
        ('Behavior Settings', {
            'fields': ('only_private_chats', 'response_delay_seconds', 'mark_as_read', 'show_typing', 'typing_duration'),
            'description': 'Javob berish xatti-harakatlari'
        }),
        ('Statistics', {
            'fields': ('messages_processed',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ConversationSummary)
class ConversationSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'username', 
        'mijoz_tipi_display',
        'message_count', 
        'needs_reply_display',
        'telegram_account', 
        'last_interaction_at'
    )
    list_filter = (
        'needs_reply',
        'telegram_account', 
        'ai_assistant', 
        'last_interaction_at'
    )
    search_fields = ('username', 'chat_id', 'user_id')
    readonly_fields = (
        'created_at', 
        'last_message_at',
        'last_interaction_at',
        'last_summary_at',
        'message_count',
        'messages_since_summary',
        'needs_reply',
        'formatted_summary_display'
    )
    list_per_page = 50
    list_select_related = ('telegram_account', 'ai_assistant')
    
    fieldsets = (
        ('💬 Mijoz Ma\'lumoti', {
            'fields': ('telegram_account', 'ai_assistant', 'chat_id', 'user_id', 'username')
        }),
        ('📊 Xulosa (O\'qiladigan format)', {
            'fields': ('formatted_summary_display',),
            'description': 'Mijoz haqida tizim tahlili'
        }),
        ('📈 Statistika', {
            'fields': (
                'message_count', 
                'messages_since_summary', 
                'context_window_size',
                'needs_reply'
            )
        }),
        ('💬 Oxirgi Xabarlar', {
            'fields': ('last_user_message', 'last_ai_message'),
            'classes': ('collapse',)
        }),
        ('📅 Vaqt Ma\'lumotlari', {
            'fields': ('created_at', 'last_message_at', 'last_interaction_at', 'last_summary_at'),
            'classes': ('collapse',)
        }),
        ('🔧 Raw JSON (Dasturchilar uchun)', {
            'fields': ('summary_data',),
            'classes': ('collapse',)
        })
    )
    
    def mijoz_tipi_display(self, obj):
        from django.utils.html import format_html
        if not obj.summary_data:
            return "—"
        mijoz_tipi = obj.summary_data.get('mijoz_tipi', '')
        tipi_map = {
            'shunchaki_sorayapti': ('❓', 'So\'rayapti', '#FFA500'),
            'jiddiy_qiziqyapti': ('🔥', 'Jiddiy', '#FF4444'),
            'tez_olmoqchi': ('⚡', 'Tez', '#FF0000'),
            'kutmoqda': ('⏳', 'Kutmoqda', '#4169E1'),
            'etibor_yoq': ('❄️', 'E\'tibor yo\'q', '#808080')
        }
        if mijoz_tipi in tipi_map:
            emoji, text, color = tipi_map[mijoz_tipi]
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} {}</span>',
                color, emoji, text
            )
        return "—"
    mijoz_tipi_display.short_description = "Mijoz Tipi"
    
    def needs_reply_display(self, obj):
        from django.utils.html import format_html
        if obj.needs_reply:
            return format_html('<span style="color: red; font-size: 16px;">⚠️ Javob kerak</span>')
        return format_html('<span style="color: green;">✅</span>')
    needs_reply_display.short_description = "Status"
    
    def formatted_summary_display(self, obj):
        from django.utils.html import format_html
        if not obj.summary_data:
            return format_html('<p style="color: #999;">Xulosa hali yaratilmagan</p>')
        
        data = obj.summary_data
        html_parts = []
        
        if data.get('mijoz_tipi'):
            tipi_map = {
                'shunchaki_sorayapti': ('❓', 'Shunchaki so\'rayapti', '#FFA500'),
                'jiddiy_qiziqyapti': ('🔥', 'Jiddiy qiziqyapti', '#FF4444'),
                'tez_olmoqchi': ('⚡', 'Tez olmoqchi', '#FF0000'),
                'kutmoqda': ('⏳', 'Kutmoqda', '#4169E1'),
                'etibor_yoq': ('❄️', 'E\'tibor yo\'q', '#808080')
            }
            tip = data['mijoz_tipi']
            if tip in tipi_map:
                emoji, text, color = tipi_map[tip]
                html_parts.append(
                    f'<div style="padding: 10px; background: {color}20; border-left: 3px solid {color}; margin-bottom: 10px;">'
                    f'<strong style="color: {color};">{emoji} {text}</strong></div>'
                )
        
        if data.get('mijoz_holati'):
            html_parts.append(
                f'<div style="padding: 10px; background: #f0f0f0; margin-bottom: 10px;">'
                f'<strong>📊 Holat:</strong><br>{data["mijoz_holati"]}</div>'
            )
        
        if data.get('keyingi_qadam'):
            html_parts.append(
                f'<div style="padding: 10px; background: #e8f5e9; border-left: 3px solid #4CAF50; margin-bottom: 10px;">'
                f'<strong>➡️ Keyingi qadam:</strong><br>{data["keyingi_qadam"]}</div>'
            )
        
        return format_html(''.join(html_parts))
    formatted_summary_display.short_description = "📋 Mijoz Xulosasi"
    
    def has_add_permission(self, request):
        return False


@admin.register(PropertyInterest)
class PropertyInterestAdmin(admin.ModelAdmin):
    list_display = ('property_id', 'username', 'contact_name', 'status', 'created_at', 'view_property_link')
    list_filter = ('status', 'created_at', 'telegram_account')
    search_fields = ('username', 'property_id', 'chat_id')
    readonly_fields = ('created_at', 'updated_at', 'property_data_display', 'view_property_link')
    list_per_page = 50
    date_hierarchy = 'created_at'
    list_select_related = ('telegram_account', 'contact', 'search_log')
    
    fieldsets = (
        ('Mijoz Ma\'lumoti', {
            'fields': ('telegram_account', 'chat_id', 'username', 'contact')
        }),
        ('Uy Ma\'lumoti', {
            'fields': ('property_id', 'property_data_display', 'view_property_link')
        }),
        ('Status', {
            'fields': ('status', 'search_log')
        }),
        ('Vaqt', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def contact_name(self, obj):
        if obj.contact:
            return obj.contact.name or obj.contact.phone_number
        return '-'
    contact_name.short_description = "Kontakt"
    
    def property_data_display(self, obj):
        if not obj.property_data:
            return '-'
        from django.utils.html import format_html
        data = obj.property_data
        html = '<div style="font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 5px;">'
        if data.get('number'):
            html += f'<strong>№:</strong> {data["number"]}<br>'
        if data.get('title'):
            html += f'<strong>Sarlavha:</strong> {data["title"]}<br>'
        if data.get('price'):
            html += f'<strong>Narx:</strong> {data["price"]:,.0f} {data.get("currency", "USD")}<br>'
        if data.get('rooms'):
            html += f'<strong>Xonalar:</strong> {data["rooms"]}<br>'
        if data.get('area'):
            html += f'<strong>Maydon:</strong> {data["area"]} m²<br>'
        if data.get('location'):
            html += f'<strong>Mo\'ljal:</strong> {data["location"]}<br>'
        html += '</div>'
        return format_html(html)
    property_data_display.short_description = "Uy Ma'lumotlari"
    
    def view_property_link(self, obj):
        from django.utils.html import format_html
        if obj.property_id:
            url = f"https://megapolis1.uz/admin/home/object/{obj.property_id}/change/"
            return format_html('<a href="{}" target="_blank">🔗 CRM da ko\'rish</a>', url)
        return '-'
    view_property_link.short_description = "Havola"
    
    def has_add_permission(self, request):
        return False
