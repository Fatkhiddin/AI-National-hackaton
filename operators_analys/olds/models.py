from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from admintion.models import BaseModel
from users.models import CustomUser, Team


# ═══════════════════════════════════════════════════════
# 1. AI CONFIGURATION (Token, Model, Prompt Settings)
# ═══════════════════════════════════════════════════════

class AIConfiguration(BaseModel):
    """
    AI sozlamalari - admin/superuser tomonidan boshqariladi
    """
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="Konfiguratsiya nomi",
        help_text="Masalan: 'OpenAI GPT-4', 'Anthropic Claude', 'Gemini'"
    )
    
    # API Settings
    api_provider = models.CharField(
        max_length=50,
        choices=[
            ('openai', 'OpenAI'),
            ('anthropic', 'Anthropic'),
            ('google', 'Google Gemini'),
            ('custom', 'Custom API'),
        ],
        default='openai',
        verbose_name="API Provider"
    )
    
    api_key = models.CharField(
        max_length=500,
        verbose_name="API Key/Token",
        help_text="AI provayderning API kaliti"
    )
    
    api_endpoint = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="API Endpoint",
        help_text="Custom API uchun endpoint (ixtiyoriy)"
    )
    
    model_name = models.CharField(
        max_length=200,
        default="gpt-4",
        verbose_name="Model nomi",
        help_text="Masalan: gpt-4, gpt-3.5-turbo, claude-3-opus"
    )
    
    # Prompt Template
    system_prompt = models.TextField(
        verbose_name="Tizim Prompt",
        help_text="AI ga berilgan asosiy ko'rsatmalar",
        default="""Siz mijozlar bilan operator suhbatlarini tahlil qiluvchi professional tahlilchisiz.
Sizning vazifangiz:
1. Suhbat mazmunini tahlil qilish
2. Operator xatti-harakatini baholash
3. Mijoz qoniqish darajasini aniqlash
4. Yaxshilash tavsiyalarini berish
5. Muhim nuqtalarni ajratib ko'rsatish"""
    )
    
    analysis_prompt_template = models.TextField(
        verbose_name="Tahlil Prompt Shabloni",
        help_text="{{text}} o'rniga suhbat matni qo'yiladi",
        default="""Quyidagi telefon suhbatining matnini tahlil qil. 
Maqsad – operatorning mijozni ofisga chaqirishdagi natijaviyligini, SPIN texnikasi va Emotional Matching psixologik yondashuvini qay darajada to'g'ri qo'llaganini aniqlash.

Tahlilni quyidagi formatda yoz:

1. UMUMIY BAHO (foizda):
   Operatorning savdo samaradorligi, suhbatni boshqarish va mijozni ofisga olib kelishdagi umumiy natijasi (0–100%).

2. BOSQICHLAR BO'YICHA TAHLIL:
   1. Salomlashish va ishonch o'rnatish:
   - Operator o'zini va kompaniyani qanday tanishtirdi?
   - Mijoz ismini 3–5 marta ishlatdimi?
   - Ohang va hissiyotda iliqlik bormi? (Emotional matching)
   (Baholash: 0–10 + izoh)

   2. Filtrlash (SPIN – Situation):
   - Operator mijozning holatini aniq so'radimi? (lokatsiya, byudjet, xona soni, va h.k.)
   - Savollar qisqa, maqsadga yo'naltirilganmi?
   (Baholash: 0–10 + izoh)

   3. Ehtiyojni aniqlash (SPIN – Problem + Implication):
   - Operator mijoz muammosini yoki og'rig'ini ochib bera oldimi?
   - E'tibor, hamdardlik, emotsional matching qay darajada sezildi?
   - Suhbat davomida mijoz "ha, shunaqa" deb javob bergan momentlar bormi?
   (Baholash: 0–10 + izoh)

   4. Qiymat yaratish (SPIN – Need Payoff):
   - Operator mijozga uyning afzalliklarini, qadriyatini, yechim sifatida taqdim qildimi?
   - Argumentlar hissiyot bilan uyg'unmi? (masalan: "Farzandlar xavfsiz o'ynaydi", "Sokin joyda dam olasiz" kabi)
   (Baholash: 0–10 + izoh)

   5. Programmalashtirish va boshqaruv:
   - Operator suhbatni boshqarayaptimi?
   - "Keling bunaqa qilamiz..." / "Bo'ladimi shunaqa qilsak" kabi kalit iboralardan foydalanganmi?
   (Baholash: 0–10 + izoh)

   6. Taqdimot:
   - Operator mijoz ehtiyojiga mos variantni taqdim etdi mi?
   - Tavsif to'liq va ishonchli bo'ldimi?
   - Mijozni ofisga yoki obyektni ko'rishga undadimi?
   (Baholash: 0–10 + izoh)

   7. E'tirozlar bilan ishlash:
   - Operator e'tirozlarga samimiy va bosiqlik bilan javob berdimi?
   - Mijozning hissiyotini qayta aks ettirib, uni tinchlantira oldimi? (Emotional mirroring)
   - "Boshliq shunaqa degandi" kabi so'zlardan qochdimi?
   (Baholash: 0–10 + izoh)

   8. Yakuniy bosqich (Sotuv yoki Keyingi qadam):
   - Operator mijozni ofisga chaqirdimi yoki uy ko'rishga undadimi?
   - Suhbatni ijobiy energiya bilan yakunladimi?
   - Keyingi aloqa uchun poydevor qoldirdimi?
   (Baholash: 0–10 + izoh)

3. MIJOZ PSIXOLOGIK HOLATI:
   - Kayfiyat: [ijobiy / betaraf / salbiy]
   - Ishonch darajasi: (0–10)
   - Xaridga tayyorlik foizi: (0–100%)

4. EMOTSIONAL MATCHING KO'RSATKICHI (0–10):
   Operator mijozning ohangini, so'z tanlashini va energiya darajasini qay darajada moslashtirdi?

5. OPERATORNING KUCHLI TOMONLARI:
   - [3–4 ta aniq ijobiy ko'rsatkich: muloqot iliqligi, savollar logikasi, his bilan gapirishi, muomala madaniyati.]

6. O'SISH NUQTALARI VA TAVSIYALAR:
   - [Aniq amaliy tavsiyalar ber: savollarni qanday shaklda berish, emotsional matchingni qanday kuchaytirish, mijozni qanday qiziqtirish.]
   - Tavsiyalarni "ko'chmas mulk bo'yicha mentor" ohangida yoz.

7. QISQA XULOSA (2 jumla):
   - [Operatorning umumiy darajasi va asosiy xulosa.]

Qo'ng'iroq matni:
{{text}}"""
    )
    
    # Settings
    max_tokens = models.IntegerField(
        default=2000,
        verbose_name="Max Tokens",
        help_text="Javob uchun maksimal token soni"
    )
    
    temperature = models.FloatField(
        default=0.7,
        verbose_name="Temperature",
        help_text="0.0 (deterministik) dan 2.0 (ijodiy) gacha. Google API uchun [0.0, 2.0] oralig'i qo'llaniladi",
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(2.0)
        ]
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol",
        help_text="Faqat bir dona faol konfiguratsiya bo'lishi kerak"
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name="Default",
        help_text="Standart konfiguratsiya"
    )
    
    class Meta:
        verbose_name = "AI Konfiguratsiya"
        verbose_name_plural = "AI Konfiguratsiyalar"
        ordering = ['-is_default', '-is_active', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({'Faol' if self.is_active else 'Nofaol'})"
    
    def save(self, *args, **kwargs):
        # Agar bu default bo'lsa, boshqalarni default emas qilish
        if self.is_default:
            AIConfiguration.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════
# 2. STT RECORD (Speech-to-Text natijalar)
# ═══════════════════════════════════════════════════════

class STTRecord(BaseModel):
    """
    UzbekVoice.ai STT natijalarini saqlash
    Generic relation - SipuniCallRecord yoki SIPCall bilan bog'lanadi
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
        verbose_name="Transkripsiya qilingan matn",
        help_text="Nutqdan matnga o'girilgan natija"
    )
    
    # UzbekVoice.ai Response
    api_response = models.JSONField(
        null=True,
        blank=True,
        verbose_name="API javob",
        help_text="To'liq API response (offsets, diarization va boshqalar)"
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
    
    with_offsets = models.BooleanField(
        default=True,
        verbose_name="Vaqt offsetlari bor"
    )
    
    with_diarization = models.BooleanField(
        default=False,
        verbose_name="So'zlovchilar bo'lingan"
    )
    
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
    
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Xatolik xabari"
    )
    
    # Metadata
    processed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_stt_records',
        verbose_name="Kim tomonidan"
    )
    
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Qayta ishlangan vaqt"
    )
    
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Davomiyligi (soniya)"
    )
    
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
# 3. AI ANALYSIS (AI Tahlili)
# ═══════════════════════════════════════════════════════

class AIAnalysis(BaseModel):
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
        AIConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ishlatilgan AI config"
    )
    
    # Tahlil natijasi
    analysis_text = models.TextField(
        verbose_name="AI Tahlili",
        help_text="AI tomonidan tahlil qilingan natija"
    )
    
    # Strukturlangan ma'lumotlar (ixtiyoriy)
    overall_score = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Umumiy baho (1-10)",
        help_text="AI tomonidan berilgan umumiy baho"
    )
    
    customer_satisfaction = models.CharField(
        max_length=20,
        choices=[
            ('satisfied', 'Qoniqdi'),
            ('neutral', 'Neytral'),
            ('unsatisfied', 'Qoniqmadi'),
            ('unknown', 'Noma\'lum'),
        ],
        default='unknown',
        verbose_name="Mijoz qoniqishi"
    )
    
    key_points = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Muhim nuqtalar",
        help_text="AI tomonidan ajratib ko'rsatilgan muhim nuqtalar"
    )
    
    recommendations = models.TextField(
        null=True,
        blank=True,
        verbose_name="Tavsiyalar"
    )
    
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
    
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Xatolik xabari"
    )
    
    # Metadata
    analyzed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_analyses',
        verbose_name="Kim tomonidan"
    )
    
    analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tahlil qilingan vaqt"
    )
    
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Ishlatilgan tokenlar"
    )
    
    api_response = models.JSONField(
        null=True,
        blank=True,
        verbose_name="To'liq API javob"
    )
    
    class Meta:
        verbose_name = "AI Tahlil"
        verbose_name_plural = "AI Tahlillar"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Tahlil #{self.id} - {self.get_status_display()}"


# ═══════════════════════════════════════════════════════
# 4. OPERATOR PERFORMANCE (Operator ishlash ko'rsatkichlari)
# ═══════════════════════════════════════════════════════

class OperatorPerformance(BaseModel):
    """
    Operatorning umumiy ishlash ko'rsatkichlari
    Kunlik/Haftalik/Oylik statistika
    """
    operator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'operator'},
        related_name='performance_records',
        verbose_name="Operator"
    )
    
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        verbose_name="Jamoa"
    )
    
    # Davr
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Kunlik'),
            ('weekly', 'Haftalik'),
            ('monthly', 'Oylik'),
        ],
        default='daily',
        verbose_name="Davr turi"
    )
    
    period_start = models.DateField(
        verbose_name="Davr boshlanishi",
        db_index=True
    )
    
    period_end = models.DateField(
        verbose_name="Davr tugashi",
        db_index=True
    )
    
    # Statistika
    total_calls = models.IntegerField(
        default=0,
        verbose_name="Jami qo'ng'iroqlar"
    )
    
    analyzed_calls = models.IntegerField(
        default=0,
        verbose_name="Tahlil qilingan qo'ng'iroqlar"
    )
    
    average_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="O'rtacha baho"
    )
    
    satisfied_customers = models.IntegerField(
        default=0,
        verbose_name="Qoniqqan mijozlar"
    )
    
    unsatisfied_customers = models.IntegerField(
        default=0,
        verbose_name="Qoniqmagan mijozlar"
    )
    
    # JSON data
    detailed_stats = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Batafsil statistika"
    )
    
    class Meta:
        verbose_name = "Operator Ishlashi"
        verbose_name_plural = "Operator Ishlash Ko'rsatkichlari"
        ordering = ['-period_start', 'operator']
        unique_together = ['operator', 'period_type', 'period_start']
    
    def __str__(self):
        return f"{self.operator.full_name} - {self.get_period_type_display()} ({self.period_start})"
