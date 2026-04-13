from django.db import models
from django.contrib.auth.models import User

# Telegram Account Model
class TelegramAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telegram_accounts')
    api_id = models.CharField(max_length=100)
    api_hash = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    session_name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    is_spam_blocked = models.BooleanField(default=False)
    spam_block_until = models.DateTimeField(null=True, blank=True)
    spam_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Telegram Account"
        verbose_name_plural = "Telegram Accounts"
    
    def __str__(self):
        return f"{self.phone_number} - {self.session_name}"

# Contact Model
class Contact(models.Model):
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='contacts', null=True, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    username = models.CharField(max_length=100, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    is_premium = models.BooleanField(default=False)
    is_bot = models.BooleanField(default=False)
    added_to_telegram = models.BooleanField(default=False)
    telegram_exists = models.BooleanField(default=True)  # True = Telegram mavjud, False = Telegram mavjud emas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        unique_together = ('phone_number', 'telegram_account')
    
    def __str__(self):
        return f"{self.name or self.first_name or 'Unknown'} - {self.phone_number}"

# Chat Model
class Chat(models.Model):
    CHAT_TYPES = (
        ('private', 'Private'),
        ('group', 'Group'),
        ('supergroup', 'Supergroup'),
        ('channel', 'Channel'),
    )
    
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='chats')
    chat_id = models.BigIntegerField()
    title = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    chat_type = models.CharField(max_length=20, choices=CHAT_TYPES)
    member_count = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_restricted = models.BooleanField(default=False)
    avatar = models.CharField(max_length=500, blank=True, null=True)  # Avatar fayl yo'li
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chats"
        unique_together = ('chat_id', 'telegram_account')
    
    def __str__(self):
        return f"{self.title or self.username or f'Chat {self.chat_id}'}"

# Message Model
class Message(models.Model):
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('voice', 'Voice'),
        ('sticker', 'Sticker'),
        ('location', 'Location'),
        ('contact', 'Contact'),
        ('poll', 'Poll'),
        ('other', 'Other'),
    )
    
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='messages')
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    message_id = models.BigIntegerField()
    sender_id = models.BigIntegerField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    is_outgoing = models.BooleanField(default=False)
    date = models.DateTimeField()
    reply_to_message_id = models.BigIntegerField(blank=True, null=True)
    media_path = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        unique_together = ('message_id', 'chat', 'telegram_account')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.chat} - {self.text[:50] if self.text else self.message_type}"

# AI Integration Model (for future AI features)
class AIIntegration(models.Model):
    AI_PROVIDERS = (
        ('openai', 'OpenAI'),
        ('claude', 'Claude'),
        ('gemini', 'Gemini'),
        ('local', 'Local Model'),
    )
    
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='ai_integrations')
    provider = models.CharField(max_length=20, choices=AI_PROVIDERS)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    model_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    max_tokens = models.IntegerField(default=1000)
    temperature = models.FloatField(default=0.7)
    system_prompt = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "AI Integration"
        verbose_name_plural = "AI Integrations"
    
    def __str__(self):
        return f"{self.provider} - {self.model_name}"

# Contact Import History
class ContactImportHistory(models.Model):
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='import_history')
    file_name = models.CharField(max_length=255)
    total_contacts = models.IntegerField(default=0)
    successful_imports = models.IntegerField(default=0)
    failed_imports = models.IntegerField(default=0)
    import_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Contact Import History"
        verbose_name_plural = "Contact Import Histories"
        ordering = ['-import_date']
    
    def __str__(self):
        return f"{self.file_name} - {self.successful_imports}/{self.total_contacts} contacts"

# Mass Messaging Campaign Model
class MessagingCampaign(models.Model):
    CAMPAIGN_STATUS = (
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('stopped', 'Stopped'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=255)
    accounts = models.ManyToManyField(TelegramAccount, related_name='campaigns')
    contacts = models.ManyToManyField(Contact, related_name='campaigns')
    message_template = models.TextField()
    ai_prompt = models.TextField(blank=True, null=True, help_text="AI ga beriladigan prompt")
    use_ai = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=CAMPAIGN_STATUS, default='draft')
    total_contacts = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    spam_blocked_count = models.IntegerField(default=0)
    delay_between_messages = models.IntegerField(default=5, help_text="Xabarlar orasidagi kutish vaqti (soniya)")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Messaging Campaign"
        verbose_name_plural = "Messaging Campaigns"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.status}"

# Campaign Message Log
class CampaignMessageLog(models.Model):
    MESSAGE_STATUS = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('spam_blocked', 'Spam Blocked'),
    )
    
    campaign = models.ForeignKey(MessagingCampaign, on_delete=models.CASCADE, related_name='message_logs')
    account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    message_text = models.TextField()
    status = models.CharField(max_length=20, choices=MESSAGE_STATUS, default='pending')
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Campaign Message Log"
        verbose_name_plural = "Campaign Message Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.campaign.title} - {self.contact.phone_number} - {self.status}"

# Auto Reply Rule Model
class AutoReplyRule(models.Model):
    TRIGGER_TYPES = (
        ('keyword', 'Kalit so\'zlar'),
        ('all_messages', 'Barcha xabarlar'),
        ('first_message', 'Birinchi xabar'),
        ('command', 'Bot komandalar'),
    )
    
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='auto_reply_rules')
    name = models.CharField(max_length=200, help_text="Qoida nomi")
    is_active = models.BooleanField(default=True)
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES, default='keyword')
    keywords = models.TextField(blank=True, help_text="Kalit so'zlar (har birini yangi qatorda)")
    reply_message = models.TextField(help_text="Javob xabari matni")
    delay_seconds = models.IntegerField(default=0, help_text="Javob berishdan oldin kutish (soniya)")
    reply_once_per_user = models.BooleanField(default=False, help_text="Har bir userga faqat 1 marta javob")
    work_hours_only = models.BooleanField(default=False, help_text="Faqat ish vaqtida ishlash")
    work_hours_start = models.TimeField(null=True, blank=True, help_text="Ish boshlanish vaqti")
    work_hours_end = models.TimeField(null=True, blank=True, help_text="Ish tugash vaqti")
    excluded_users = models.TextField(blank=True, help_text="Javob bermaslik kerak userlar (username yoki user_id, har birini yangi qatorda)")
    only_private_chats = models.BooleanField(default=True, help_text="Faqat shaxsiy chatlarda ishlash")
    
    # Real-time behavior settings
    mark_as_read = models.BooleanField(default=True, help_text="Xabarni o'qilgan deb belgilash (double tick)")
    show_typing = models.BooleanField(default=True, help_text="Typing indicator ko'rsatish")
    typing_duration = models.IntegerField(default=2, help_text="Typing ko'rsatish davomiyligi (soniya)")
    
    messages_sent_count = models.IntegerField(default=0, help_text="Yuborilgan javoblar soni")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Auto Reply Rule"
        verbose_name_plural = "Auto Reply Rules"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.telegram_account.phone_number}"
    
    def get_keywords_list(self):
        """Return keywords as list"""
        if self.keywords:
            return [k.strip().lower() for k in self.keywords.split('\n') if k.strip()]
        return []
    
    def get_excluded_users_list(self):
        """Return excluded users as list"""
        if self.excluded_users:
            return [u.strip() for u in self.excluded_users.split('\n') if u.strip()]
        return []

# Auto Reply Log Model
class AutoReplyLog(models.Model):
    rule = models.ForeignKey(AutoReplyRule, on_delete=models.CASCADE, related_name='logs')
    chat_id = models.BigIntegerField()
    user_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    trigger_message = models.TextField(help_text="Javob trigger qilgan xabar")
    reply_sent = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Auto Reply Log"
        verbose_name_plural = "Auto Reply Logs"
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.rule.name} - Chat {self.chat_id}"


# AI Provider Model - API kalitlarni saqlash
class AIProvider(models.Model):
    """AI API Provider (OpenAI, Claude, etc.)"""
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI (GPT)'),
        ('anthropic', 'Anthropic (Claude)'),
        ('google', 'Google (Gemini)'),
        ('custom', 'Custom API'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_providers')
    name = models.CharField(max_length=100, help_text="Provider nomi (masalan: 'My OpenAI Key')")
    provider_type = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='openai')
    api_key = models.CharField(max_length=500, help_text="API kalit")
    api_endpoint = models.URLField(blank=True, null=True, help_text="Custom API endpoint (agar kerak bo'lsa)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Provider"
        verbose_name_plural = "AI Providers"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"


# AI Assistant Model - Har bir account uchun AI sozlamalari
class AIAssistant(models.Model):
    """AI Assistant configuration for Telegram account"""
    MODEL_CHOICES = [
        # OpenAI
        ('gpt-4o', 'GPT-4o'),
        ('gpt-4o-mini', 'GPT-4o Mini'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        # Anthropic
        ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet'),
        ('claude-3-5-haiku-20241022', 'Claude 3.5 Haiku'),
        ('claude-3-opus-20240229', 'Claude 3 Opus'),
        # Google
        ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash'),
        ('gemini-1.5-pro', 'Gemini 1.5 Pro'),
        # Custom
        ('custom', 'Custom Model'),
    ]
    
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='ai_assistants')
    ai_provider = models.ForeignKey(AIProvider, on_delete=models.CASCADE, related_name='assistants')
    name = models.CharField(max_length=100, help_text="Assistant nomi")
    model = models.CharField(max_length=100, choices=MODEL_CHOICES, default='gpt-4o-mini')
    system_prompt = models.TextField(
        help_text="AI assistant uchun system prompt",
        default="""Siz Telegram orqali mijozlar bilan suhbatlashadigan professional AI yordamchisiz.

MUHIM QOIDALAR:
- Har doim o'zbek tilida javob bering (agar mijoz o'zbekcha yozgan bo'lsa)
- Tabiiy va samimiy yozing, xuddi oddiy odam kabi
- Mijozning barcha so'rovlarini kontekstda eslab qoling
- Agar bir nechta savol bo'lsa, barchasiga bitta javobda javob bering
- Qisqa va aniq javob bering, ortiqcha gapirmang
- Do'stona va hurmatli munosabatda bo'ling
- Agar biror narsa tushunmagan bo'lsangiz, aniq so'rang

Sizning vazifangiz - mijozlarga yordam berish va ularning savollariga javob berish."""
    )
    
    # Settings
    is_active = models.BooleanField(default=True, help_text="AI assistant faolmi?")
    auto_respond = models.BooleanField(default=True, help_text="Avtomatik javob beradimi?")
    only_private_chats = models.BooleanField(default=True, help_text="Faqat shaxsiy chatlarda ishlasin")
    response_delay_seconds = models.IntegerField(default=2, help_text="Javob berishdan oldin kutish vaqti")
    
    # Realistic behavior
    mark_as_read = models.BooleanField(default=True, help_text="Xabarni o'qilgan deb belgilash")
    show_typing = models.BooleanField(default=True, help_text="Typing indicator ko'rsatish")
    typing_duration = models.IntegerField(default=3, help_text="Typing davomiyligi (soniya)")
    
    # Statistics
    messages_processed = models.IntegerField(default=0, help_text="Qayta ishlangan xabarlar soni")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Assistant"
        verbose_name_plural = "AI Assistants"
        ordering = ['-created_at']
        unique_together = ['telegram_account', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.telegram_account.phone_number}"


# Conversation Summary Model - Har bir mijoz bilan suhbat xulosasi
class ConversationSummary(models.Model):
    """Store conversation summaries for each user"""
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='conversation_summaries')
    ai_assistant = models.ForeignKey(AIAssistant, on_delete=models.CASCADE, related_name='summaries')
    chat_id = models.BigIntegerField(help_text="Telegram chat ID")
    user_id = models.BigIntegerField(null=True, blank=True, help_text="Telegram user ID")
    username = models.CharField(max_length=100, blank=True, null=True)
    
    # Summary data (JSON format)
    summary_data = models.JSONField(
        default=dict,
        help_text="Suhbat xulosasi JSON formatda",
        blank=True
    )
    # Example structure:
    # {
    #   "user_info": {"name": "John", "interests": ["tech", "sports"]},
    #   "conversation_topics": ["product inquiry", "pricing"],
    #   "user_intent": "potential customer",
    #   "last_context": "Asked about pricing for premium plan",
    #   "action_items": ["Send pricing sheet", "Schedule demo"],
    #   "sentiment": "positive",
    #   "key_facts": ["Budget: $1000", "Timeline: Next month"]
    # }
    
    # Smart tracking fields
    message_count = models.IntegerField(default=0, help_text="Jami xabarlar soni")
    messages_since_summary = models.IntegerField(default=0, help_text="Summary yaratilganidan keyingi xabarlar")
    context_window_size = models.IntegerField(default=20, help_text="Context window size (o'zgartirish mumkin)")
    
    # Pending response tracking
    needs_reply = models.BooleanField(default=False, help_text="Javob kerakmi?")
    last_user_message = models.TextField(blank=True, null=True, help_text="Oxirgi user xabari")
    last_ai_message = models.TextField(blank=True, null=True, help_text="Oxirgi AI xabari")
    
    # Timestamps
    last_message_at = models.DateTimeField(auto_now=True, help_text="Oxirgi xabar vaqti")
    last_interaction_at = models.DateTimeField(auto_now=True, help_text="Oxirgi o'zaro ta'sir")
    last_summary_at = models.DateTimeField(null=True, blank=True, help_text="Oxirgi summary yangilangan vaqt")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Conversation Summary"
        verbose_name_plural = "Conversation Summaries"
        ordering = ['-last_message_at']
        unique_together = ['telegram_account', 'ai_assistant', 'chat_id']
    
    def __str__(self):
        return f"Summary: {self.username or self.chat_id} - {self.ai_assistant.name} ({self.message_count} msgs)"
    
    def update_summary(self, new_data):
        """Update summary with new information"""
        from django.utils import timezone
        if not self.summary_data:
            self.summary_data = {}
        self.summary_data.update(new_data)
        self.last_summary_at = timezone.now()
        self.messages_since_summary = 0
        self.save()
    
    def should_update_summary(self):
        """Check if summary needs update based on message count"""
        return self.messages_since_summary >= self.context_window_size
    
    def mark_needs_reply(self, user_message):
        """Mark that conversation needs AI reply"""
        self.needs_reply = True
        self.last_user_message = user_message
        self.save(update_fields=['needs_reply', 'last_user_message', 'last_interaction_at'])
    
    def mark_replied(self, ai_message):
        """Mark that AI has replied"""
        self.needs_reply = False
        self.last_ai_message = ai_message
        self.save(update_fields=['needs_reply', 'last_ai_message', 'last_interaction_at'])
    
    def increment_message_count(self):
        """Increment message counters"""
        self.message_count += 1
        self.messages_since_summary += 1
        self.save(update_fields=['message_count', 'messages_since_summary'])


# CRM Integration Models
class CRMProvider(models.Model):
    """
    CRM provider ma'lumotlari - turli CRM tizimlar bilan ishlash uchun
    """
    CRM_TYPES = (
        ('custom_api', 'Custom API'),
        ('amocrm', 'AmoCRM'),
        ('bitrix24', 'Bitrix24'),
        ('hubspot', 'HubSpot'),
        ('salesforce', 'Salesforce'),
        ('zoho', 'Zoho CRM'),
        ('pipedrive', 'Pipedrive'),
        ('simple_json', 'Simple JSON File'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crm_providers')
    name = models.CharField(max_length=200, help_text="CRM nomi (masalan: 'Uy-joy CRM')")
    crm_type = models.CharField(max_length=50, choices=CRM_TYPES, default='custom_api')
    
    # API Connection
    api_url = models.URLField(max_length=500, blank=True, null=True, help_text="CRM API endpoint")
    api_key = models.CharField(max_length=500, blank=True, null=True, help_text="API Key/Token")
    api_secret = models.CharField(max_length=500, blank=True, null=True, help_text="API Secret (agar kerak bo'lsa)")
    
    # Field Mapping - Bu eng muhim qism!
    field_mapping = models.JSONField(
        default=dict,
        blank=True,
        help_text="CRM field mapping - Telegram summary -> CRM fields"
    )
    # Example field_mapping structure:
    # {
    #   "property_fields": {
    #     "price_min": "price.min",
    #     "price_max": "price.max",
    #     "rooms": "rooms",
    #     "area": "area",
    #     "location": "district",
    #     "floor": "floor",
    #     "property_type": "type"
    #   },
    #   "search_params": {
    #     "available": "status",
    #     "verified": "is_verified"
    #   },
    #   "response_format": {
    #     "id": "id",
    #     "title": "title",
    #     "price": "price",
    #     "description": "description",
    #     "images": "images",
    #     "link": "url"
    #   }
    # }
    
    # Request/Response Templates
    request_template = models.JSONField(
        default=dict,
        blank=True,
        help_text="API so'rov template"
    )
    # Example:
    # {
    #   "method": "POST",
    #   "endpoint": "/api/properties/search",
    #   "headers": {
    #     "Authorization": "Bearer {api_key}",
    #     "Content-Type": "application/json"
    #   },
    #   "body_template": {
    #     "filters": "{search_criteria}",
    #     "limit": 10
    #   }
    # }
    
    # AI Prompt for extracting property requirements
    extraction_prompt = models.TextField(
        blank=True,
        help_text="AI ga beriluvchi prompt - suhbatdan uy talablarini JSON formatda chiqarish uchun"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "CRM Provider"
        verbose_name_plural = "CRM Providers"
    
    def __str__(self):
        return f"{self.name} ({self.get_crm_type_display()})"


class PropertySearchLog(models.Model):
    """
    CRM qidiruv log - har bir qidiruv natijasini saqlash
    """
    crm_provider = models.ForeignKey(CRMProvider, on_delete=models.CASCADE, related_name='search_logs')
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='property_searches')
    chat_id = models.BigIntegerField(help_text="Telegram chat ID")
    username = models.CharField(max_length=200, blank=True, null=True)
    
    # Extracted requirements from conversation
    extracted_requirements = models.JSONField(
        default=dict,
        help_text="Suhbatdan olingan talablar"
    )
    # Example:
    # {
    #   "price_min": 50000,
    #   "price_max": 100000,
    #   "rooms": 3,
    #   "location": "Tashkent",
    #   "property_type": "apartment",
    #   "area_min": 70,
    #   "floor_min": 2
    # }
    
    # CRM request/response
    crm_request = models.JSONField(default=dict, help_text="CRM ga yuborilgan so'rov")
    crm_response = models.JSONField(default=dict, help_text="CRM dan kelgan javob")
    
    # Results
    results_count = models.IntegerField(default=0, help_text="Topilgan uylar soni")
    results_sent = models.BooleanField(default=False, help_text="Natijalar yuborilganmi?")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('no_results', 'No Results'),
        ),
        default='pending'
    )
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Property Search Log"
        verbose_name_plural = "Property Search Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Search by {self.username or self.chat_id} - {self.results_count} results"


class PropertyInterest(models.Model):
    """
    Mijoz qiziqish bildirgan uylar - takliflar ro'yxati
    """
    STATUS_CHOICES = (
        ('interested', 'Qiziqdi'),
        ('rejected', 'Rad etdi'),
        ('viewed', 'Ko\'rdi'),
    )
    
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE, related_name='property_interests')
    search_log = models.ForeignKey(PropertySearchLog, on_delete=models.CASCADE, related_name='interests', null=True, blank=True)
    
    chat_id = models.BigIntegerField(help_text="Telegram chat ID")
    username = models.CharField(max_length=200, blank=True, null=True)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Property details
    property_id = models.CharField(max_length=100, help_text="CRM da uy ID si")
    property_data = models.JSONField(default=dict, help_text="Uy to'liq ma'lumotlari")
    # Example:
    # {
    #   "number": "1355",
    #   "title": "ПРОДАЁТСЯ УЧАСТОК",
    #   "price": 130000,
    #   "rooms": 5,
    #   "area": 300,
    #   "location": "29 мактаб ОБЛ больница",
    #   "category": "Turar",
    #   "images": ["url1", "url2"]
    # }
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='viewed')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Property Interest"
        verbose_name_plural = "Property Interests"
        ordering = ['-created_at']
        unique_together = ('chat_id', 'property_id')
    
    def __str__(self):
        return f"{self.username or self.chat_id} - Property #{self.property_id} - {self.status}"

