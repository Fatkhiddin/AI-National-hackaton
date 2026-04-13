from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings


# ═══════════════════════════════════════════════════════
# OPERATOR AI CONFIGURATION
# ═══════════════════════════════════════════════════════

class OperatorAIConfiguration(models.Model):
    """
    Operator suhbatlarini AI bilan tahlil qilish konfiguratsiyasi.
    Admin paneldan sozlanadi — prompt, model, temperature, max_tokens
    """
    
    API_PROVIDER_CHOICES = [
        ('openai', 'OpenAI (GPT)'),
        ('anthropic', 'Anthropic (Claude)'),
        ('google', 'Google (Gemini)'),
        ('custom', 'Custom API'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name="Nomi",
        help_text="Konfiguratsiya nomi (masalan: Asosiy tahlil, SPIN tahlil)"
    )
    
    # API sozlamalari
    api_provider = models.CharField(
        max_length=20,
        choices=API_PROVIDER_CHOICES,
        default='openai',
        verbose_name="AI Provider"
    )
    
    api_key = models.CharField(
        max_length=500,
        verbose_name="API Key",
        help_text="AI provider API kaliti"
    )
    
    api_endpoint = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="API Endpoint (Custom)",
        help_text="Faqat Custom API uchun. Masalan: https://api.example.com/v1/chat"
    )
    
    model_name = models.CharField(
        max_length=100,
        default='gpt-4o-mini',
        verbose_name="Model nomi",
        help_text="Masalan: gpt-4o-mini, claude-3-5-sonnet-20241022, gemini-1.5-flash"
    )
    
    # Prompt sozlamalari
    system_prompt = models.TextField(
        default="""Siz mijozlar bilan operator suhbatlarini tahlil qiluvchi professional tahlilchisiz.
Sizning vazifangiz:
1. Suhbat mazmunini tahlil qilish
2. Operator xatti-harakatini baholash
3. Mijoz qoniqish darajasini aniqlash
4. Yaxshilash tavsiyalarini berish
5. Muhim nuqtalarni ajratib ko'rsatish""",
        verbose_name="System Prompt",
        help_text="AI ga beriladigan system (tizim) ko'rsatmasi"
    )
    
    analysis_prompt_template = models.TextField(
        default="""Quyidagi telefon suhbatining matnini tahlil qil. 
Maqsad – operatorning mijozni ofisga chaqirishdagi natijaviyligini, SPIN texnikasi va Emotional Matching psixologik yondashuvini qay darajada to'g'ri qo'llaganini aniqlash.

Tahlilni quyidagi formatda yoz:

1. UMUMIY BAHO (foizda):
   Operatorning savdo samaradorligi, suhbatni boshqarish va mijozni ofisga olib kelishdagi umumiy natijasi (0–100%).

2. BOSQICHLAR BO'YICHA TAHLIL:
   1. Salomlashish va ishonch o'rnatish (0–10 + izoh)
   2. Filtrlash - SPIN Situation (0–10 + izoh)
   3. Ehtiyojni aniqlash - SPIN Problem + Implication (0–10 + izoh)
   4. Qiymat yaratish - SPIN Need Payoff (0–10 + izoh)
   5. Programmalashtirish va boshqaruv (0–10 + izoh)
   6. Taqdimot (0–10 + izoh)
   7. E'tirozlar bilan ishlash (0–10 + izoh)
   8. Yakuniy bosqich - Sotuv yoki Keyingi qadam (0–10 + izoh)

3. MIJOZ PSIXOLOGIK HOLATI:
   - Kayfiyat: [ijobiy / betaraf / salbiy]
   - Ishonch darajasi: (0–10)
   - Xaridga tayyorlik foizi: (0–100%)

4. EMOTSIONAL MATCHING KO'RSATKICHI (0–10)

5. OPERATORNING KUCHLI TOMONLARI (3-4 ta)

6. O'SISH NUQTALARI VA TAVSIYALAR

7. QISQA XULOSA (2 jumla)

8. UMUMIY BAHO: X/10

Qo'ng'iroq matni:
{{text}}""",
        verbose_name="Tahlil Prompt Shabloni",
        help_text="{{text}} o'rniga suhbat matni qo'yiladi"
    )
    
    # Model parametrlari
    max_tokens = models.IntegerField(
        default=4000,
        validators=[MinValueValidator(100), MaxValueValidator(32000)],
        verbose_name="Max Tokens",
        help_text="AI javobidagi maksimal tokenlar soni"
    )
    
    temperature = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        verbose_name="Temperature",
        help_text="0.0 = aniq javob, 2.0 = ijodiy javob. Tavsiya: 0.5-0.8"
    )
    
    # Holat
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faolmi",
        help_text="Faqat faol konfiguratsiyalar ishlatiladi"
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name="Standart",
        help_text="Standart konfiguratsiya sifatida ishlatilsinmi"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Operator AI Konfiguratsiya"
        verbose_name_plural = "Operator AI Konfiguratsiyalar"
        ordering = ['-is_default', '-is_active', '-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_api_provider_display()}) {'✓' if self.is_active else '✗'}"
    
    def save(self, *args, **kwargs):
        """Faqat bitta default bo'lishini ta'minlash"""
        if self.is_default:
            OperatorAIConfiguration.objects.filter(
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Faol va standart konfiguratsiyani olish"""
        config = cls.objects.filter(is_active=True, is_default=True).first()
        if not config:
            config = cls.objects.filter(is_active=True).first()
        return config
    
    def get_prompt(self, text: str) -> str:
        """Tahlil promptini matn bilan to'ldirish"""
        return self.analysis_prompt_template.replace('{{text}}', text)


# ═══════════════════════════════════════════════════════
# IP PHONE CALLS
# ═══════════════════════════════════════════════════════

class IPPhoneCall(models.Model):
    """
    CRM dan olingan IP telefon qo'ng'iroqlari
    Hozircha temp model - ma'lumot CRM dan fetch qilinadi
    """
    call_id = models.CharField(max_length=255, unique=True)
    phone = models.CharField(max_length=50)
    operator_name = models.CharField(max_length=255, blank=True)
    client_name = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField()
    tree_name = models.CharField(max_length=100)  # Kiruvchi, Chiquvchi
    status = models.CharField(max_length=50)  # answered, missed, busy
    call_record_link = models.URLField(blank=True)
    duration_seconds = models.IntegerField(default=0)
    src_num = models.CharField(max_length=50, blank=True)
    dst_num = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = "IP Phone Call"
        verbose_name_plural = "IP Phone Calls"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.phone} - {self.tree_name} - {self.timestamp}"


# ═══════════════════════════════════════════════════════
# STT RECORD (Speech-to-Text natijalar)
# ═══════════════════════════════════════════════════════

class STTRecord(models.Model):
    """
    UzbekVoice.ai STT natijalarini saqlash
    Generic relation - IPPhoneCall yoki boshqa model bilan bog'lanadi
    """
    # Generic Foreign Key - qaysi qo'ng'iroq uchun
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Model turi"
    )
    object_id = models.PositiveIntegerField(verbose_name="Object ID")
    call_record = GenericForeignKey('content_type', 'object_id')
    
    # STT ma'lumotlari
    original_audio_url = models.URLField(
        max_length=1000,
        verbose_name="Audio URL",
        help_text="Asl audio fayl URL manzili"
    )
    
    transcribed_text = models.TextField(
        blank=True,
        default='',
        verbose_name="Transkripsiya qilingan matn",
        help_text="Nutqdan matnga o'girilgan natija"
    )
    
    # UzbekVoice.ai Response
    api_response = models.JSONField(
        null=True,
        blank=True,
        verbose_name="API javob",
        help_text="To'liq API response"
    )
    
    # Settings
    language = models.CharField(
        max_length=10,
        default='uz',
        choices=[
            ('uz', "O'zbek"),
            ('ru', 'Rus'),
            ('ru-uz', "O'zbek-Rus (Aralash)"),
        ],
        verbose_name="Til"
    )
    
    with_offsets = models.BooleanField(default=True, verbose_name="Vaqt offsetlari bor")
    with_diarization = models.BooleanField(default=False, verbose_name="So'zlovchilar bo'lingan")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Kutilmoqda'),
            ('processing', 'Jarayonda'),
            ('completed', 'Bajarildi'),
            ('failed', 'Xatolik'),
        ],
        default='pending',
        db_index=True,
        verbose_name="Status"
    )
    
    error_message = models.TextField(null=True, blank=True, verbose_name="Xatolik xabari")
    
    # Metadata
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_stt_records',
        verbose_name="Kim tomonidan"
    )
    
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Qayta ishlangan vaqt")
    duration_seconds = models.IntegerField(null=True, blank=True, verbose_name="Davomiyligi (soniya)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "STT Yozuv"
        verbose_name_plural = "STT Yozuvlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"STT #{self.id} - {self.get_status_display()}"


# ═══════════════════════════════════════════════════════
# AI ANALYSIS (AI Tahlili)
# ═══════════════════════════════════════════════════════

class AIAnalysis(models.Model):
    """
    STT natijasi asosida AI tahlili
    """
    stt_record = models.OneToOneField(
        STTRecord,
        on_delete=models.CASCADE,
        related_name='ai_analysis',
        verbose_name="STT yozuv"
    )
    
    ai_config = models.ForeignKey(
        OperatorAIConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ishlatilgan AI config"
    )
    
    # Tahlil natijasi
    analysis_text = models.TextField(
        blank=True,
        default='',
        verbose_name="AI Tahlili",
        help_text="AI tomonidan tahlil qilingan natija"
    )
    
    # Strukturlangan ma'lumotlar
    overall_score = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Umumiy baho (1-10)",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    customer_satisfaction = models.CharField(
        max_length=20,
        choices=[
            ('satisfied', 'Qoniqdi'),
            ('neutral', 'Neytral'),
            ('unsatisfied', 'Qoniqmadi'),
            ('unknown', "Noma'lum"),
        ],
        default='unknown',
        verbose_name="Mijoz qoniqishi"
    )
    
    key_points = models.JSONField(null=True, blank=True, verbose_name="Muhim nuqtalar")
    recommendations = models.TextField(null=True, blank=True, verbose_name="Tavsiyalar")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Kutilmoqda'),
            ('processing', 'Jarayonda'),
            ('completed', 'Bajarildi'),
            ('failed', 'Xatolik'),
        ],
        default='pending',
        db_index=True,
        verbose_name="Status"
    )
    
    error_message = models.TextField(null=True, blank=True, verbose_name="Xatolik xabari")
    
    # Metadata
    analyzed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_analyses',
        verbose_name="Kim tomonidan"
    )
    
    analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tahlil qilingan vaqt")
    tokens_used = models.IntegerField(null=True, blank=True, verbose_name="Ishlatilgan tokenlar")
    api_response = models.JSONField(null=True, blank=True, verbose_name="To'liq API javob")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Tahlil"
        verbose_name_plural = "AI Tahlillar"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Tahlil #{self.id} - {self.get_status_display()}"
