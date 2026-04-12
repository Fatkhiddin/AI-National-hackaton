# market_analysis/models.py

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from admintion.models import BaseModel
from users.models import Team, CustomUser
import json


# ============================================
# BOZOR NARXLARI (Google Sheets dan import)
# ============================================

class MarketPriceReference(BaseModel):
    """
    Google Sheets dan import qilingan bozor narxlari ma'lumotnomasi.
    TZ bo'yicha to'liq implementatsiya.
    """
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='market_price_references')
    
    # Primary parametrlar
    etaj = models.IntegerField(verbose_name="Qavat raqami", db_index=True)
    xonalar_soni = models.IntegerField(verbose_name="Xonalar soni", db_index=True)
    qurilish_turi = models.CharField(
        max_length=50,
        choices=[
            ('gishtli', 'Gʻishtli'),
            ('panelli', 'Panelli'),
            ('monolitli', 'Monolitli'),
            ('blokli', 'Blokli'),
        ],
        verbose_name="Qurilish turi",
        db_index=True
    )
    holat = models.CharField(
        max_length=20,
        choices=[
            ('remontli', 'Remontli'),
            ('remontsiz', 'Remontsiz'),
        ],
        verbose_name="Holat",
        db_index=True
    )
    
    # Maydon diapazon
    maydon_min = models.IntegerField(verbose_name="Minimal maydon (m²)")
    maydon_max = models.IntegerField(null=True, blank=True, verbose_name="Maksimal maydon (m²)")
    
    # Narxlar (so'm/m²)
    arzon_narx = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Arzon narx (so'm/m²)")
    bozor_narx = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Bozor narxi (so'm/m²)")
    qimmat_narx = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Qimmat narx (so'm/m²)")
    
    # Metadata
    source_file = models.CharField(max_length=200, blank=True, verbose_name="Qaysi fayldan")
    
    class Meta:
        verbose_name = "Bozor Narxi Ma'lumotnomasi"
        verbose_name_plural = "Bozor Narxlari Ma'lumotnomasi"
        ordering = ['etaj', 'xonalar_soni', 'maydon_min']
        unique_together = ['team', 'etaj', 'xonalar_soni', 'qurilish_turi', 'holat', 'maydon_min']
        indexes = [
            models.Index(fields=['team', 'qurilish_turi', 'xonalar_soni']),
            models.Index(fields=['team', 'etaj', 'holat']),
        ]
    
    def __str__(self):
        return f"{self.qurilish_turi} - {self.xonalar_soni} xona - {self.etaj}-etaj - {self.holat}"
    
    def get_narx_range(self):
        """Narx diapazonini dictionary ko'rinishida qaytarish"""
        return {
            'min': float(self.arzon_narx),
            'avg': float(self.bozor_narx),
            'max': float(self.qimmat_narx)
        }


# ============================================
# ESKI MODEL (backward compatibility)
# ============================================

class PriceReference(BaseModel):
    """Excel dan yuklanadigan ma'lumotnoma narxlar - ESKI VERSION"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='price_references_old')
    
    # Asosiy parametrlar
    floor_number = models.IntegerField(verbose_name="Etaj raqami")
    room_count = models.IntegerField(verbose_name="Xonalar soni")
    area_from = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Maydon dan (m²)")
    area_to = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Maydon gacha (m²)")
    is_renovated = models.BooleanField(default=False, verbose_name="Remontli")
    
    # Narxlar (3 xil)
    price_low = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Arzon narx (UZS)")
    price_market = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Bozor narxi (UZS)")
    price_high = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Qimmat narx (UZS)")
    
    # Qo'shimcha ma'lumot
    source_sheet = models.CharField(
        max_length=50, 
        choices=[('renovated', 'Remontli'), ('not_renovated', 'Remontsiz')],
        verbose_name="Manba sheet"
    )
    excel_row = models.IntegerField(null=True, blank=True, verbose_name="Excel qator raqami")
    notes = models.TextField(blank=True, null=True, verbose_name="Izohlar")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    
    class Meta:
        verbose_name = "Narx Ma'lumotnomasi (ESKI)"
        verbose_name_plural = "Narx Ma'lumotnomasi (ESKI)"
        ordering = ['floor_number', 'room_count', 'area_from']
        indexes = [
            models.Index(fields=['team', 'is_active']),
            models.Index(fields=['floor_number', 'room_count']),
        ]
    
    def __str__(self):
        renovation = "Remontli" if self.is_renovated else "Remontsiz"
        return f"{self.floor_number}-qavat, {self.room_count}-xona, {self.area_from}-{self.area_to}m² ({renovation})"


# ============================================
# NARX TAHLILI (AI bilan)
# ============================================

class PropertyPriceAnalysis(BaseModel):
    """
    Mulk obyektlarining narx tahlil natijalarini saqlash.
    HAM BuildHouse (CRM) HAM OLXProperty uchun ishlaydi.
    """
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='price_analyses')
    
    # Generic relation - BuildHouse yoki OLXProperty
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Property reference (BuildHouse ID yoki OLX ID)
    property_id = models.IntegerField(db_index=True, verbose_name="Obyekt ID")
    
    # Tahlil natijalari
    status = models.CharField(
        max_length=20,
        choices=[
            ('juda_arzon', 'Juda Arzon'),
            ('arzon', 'Arzon'),
            ('normal', 'Normal'),
            ('qimmat', 'Qimmat'),
            ('juda_qimmat', 'Juda Qimmat'),
        ],
        verbose_name="Status",
        db_index=True
    )
    
    # Narx taqqoslash
    bozor_narxi = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Bozor narxi (USD/m²)"
    )
    joriy_narxi = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Hozirgi narx (USD/m²)"
    )
    farq_foiz = models.DecimalField(
        max_digits=8, decimal_places=2,
        verbose_name="Farq (foizda)"
    )
    farq_summa = models.DecimalField(
        max_digits=20, decimal_places=2,
        verbose_name="Farq (USD)"
    )
    
    # AI tahlili
    ai_tahlil = models.TextField(blank=True, verbose_name="AI tahlil matni")
    tavsiya = models.TextField(blank=True, verbose_name="AI tavsiyasi")
    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
        verbose_name="Ishonch darajasi (0-100)"
    )
    
    # Reference
    matched_reference = models.ForeignKey(
        MarketPriceReference,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Mos kelgan ma'lumotnoma"
    )
    
    # Metadata
    analyzed_at = models.DateTimeField(auto_now_add=True, verbose_name="Tahlil qilingan vaqt")
    
    class Meta:
        verbose_name = "Narx Tahlili"
        verbose_name_plural = "Narx Tahillari"
        ordering = ['-analyzed_at']
        indexes = [
            models.Index(fields=['property_id', '-analyzed_at']),
            models.Index(fields=['status']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"Property #{self.property_id} - {self.get_status_display()}"
    
    def get_status_color(self):
        """Status uchun rang kodini qaytarish"""
        colors = {
            'juda_arzon': '#00C853',  # Yashil
            'arzon': '#64DD17',       # Och yashil
            'normal': '#FFC107',      # Sariq
            'qimmat': '#FF6F00',      # To'q sariq
            'juda_qimmat': '#D32F2F', # Qizil
        }
        return colors.get(self.status, '#9E9E9E')
    
    def get_recommendation_summary(self):
        """Qisqa tavsiya matni"""
        if self.tavsiya:
            return self.tavsiya[:200] + '...' if len(self.tavsiya) > 200 else self.tavsiya
        return "Tavsiya mavjud emas"


# ============================================
# ESKI PREDICTION MODEL (backward compatibility)
# ============================================

class PricePrediction(BaseModel):
    """Narx bashorati - ML va AI"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='price_predictions')
    
    # Generic relation - BuildHouse yoki OLXListing
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # ──────────────────────────────────────────────────────
    # ASOSIY PARAMETRLAR (hozir)
    # ──────────────────────────────────────────────────────
    floor_number = models.IntegerField(verbose_name="Etaj")
    room_count = models.IntegerField(verbose_name="Xonalar soni")
    area = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Maydon (m²)")
    is_renovated = models.BooleanField(default=False, verbose_name="Remontli")
    
    # ──────────────────────────────────────────────────────
    # QO'SHIMCHA PARAMETRLAR (kelajak - ixtiyoriy)
    # ──────────────────────────────────────────────────────
    
    # Lokatsiya
    location_lat = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True,
        verbose_name="Kenglik", help_text="GPS koordinata"
    )
    location_lon = models.DecimalField(
        max_digits=11, decimal_places=8, null=True, blank=True,
        verbose_name="Uzunlik", help_text="GPS koordinata"
    )
    location_district = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Tuman/Mahalla"
    )
    
    # Bino va uy
    building_year = models.IntegerField(
        null=True, blank=True,
        verbose_name="Bino yili"
    )
    building_floors = models.IntegerField(
        null=True, blank=True,
        verbose_name="Binodagi jami qavatlar"
    )
    ceiling_height = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True,
        verbose_name="Shift balandligi (m)"
    )
    
    # Qulayliklar
    has_elevator = models.BooleanField(
        default=False,
        verbose_name="Lift bor"
    )
    has_parking = models.BooleanField(
        default=False,
        verbose_name="Parking bor"
    )
    has_security = models.BooleanField(
        default=False,
        verbose_name="Qo'riqxona bor"
    )
    
    # Atrofdagi infratuzilma (keyinchalik to'ldiriladi)
    nearby_schools = models.IntegerField(
        null=True, blank=True,
        verbose_name="Yaqin maktablar (1km radiusda)"
    )
    nearby_hospitals = models.IntegerField(
        null=True, blank=True,
        verbose_name="Yaqin shifoxonalar (1km radiusda)"
    )
    nearby_shops = models.IntegerField(
        null=True, blank=True,
        verbose_name="Yaqin do'konlar (500m radiusda)"
    )
    transport_accessibility = models.CharField(
        max_length=20,
        choices=[
            ('excellent', 'A\'lo'),
            ('good', 'Yaxshi'),
            ('average', 'O\'rtacha'),
            ('poor', 'Yomon'),
        ],
        null=True, blank=True,
        verbose_name="Transport qulayligi"
    )
    
    # Atrofdagi narxlar (keyinchalik avtomatik hisoblanadi)
    nearby_average_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="Atrofdagi o'rtacha narx (1km radiusda)"
    )
    nearby_min_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="Atrofdagi eng arzon"
    )
    nearby_max_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="Atrofdagi eng qimmat"
    )
    nearby_count = models.IntegerField(
        null=True, blank=True,
        verbose_name="Atrofdagi uylar soni"
    )
    
    # ──────────────────────────────────────────────────────
    # ML MODEL BASHORATI
    # ──────────────────────────────────────────────────────
    ml_price_low = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="ML: Arzon narx"
    )
    ml_price_market = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="ML: Bozor narxi"
    )
    ml_price_high = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="ML: Qimmat narx"
    )
    ml_confidence = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="ML: Ishonch darajasi (%)"
    )
    ml_execution_time = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True,
        verbose_name="ML: Ishlash vaqti (sekund)"
    )
    ml_model_version = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name="ML: Model versiyasi"
    )
    
    # ──────────────────────────────────────────────────────
    # CLAUDE AI BASHORATI
    # ──────────────────────────────────────────────────────
    ai_price_low = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="AI: Arzon narx"
    )
    ai_price_market = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="AI: Bozor narxi"
    )
    ai_price_high = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="AI: Qimmat narx"
    )
    ai_analysis = models.TextField(
        blank=True, null=True,
        verbose_name="AI: Tahlil va izohlar"
    )
    ai_confidence = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="AI: Ishonch darajasi (%)"
    )
    ai_execution_time = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True,
        verbose_name="AI: Ishlash vaqti (sekund)"
    )
    ai_tokens_used = models.IntegerField(
        null=True, blank=True,
        verbose_name="AI: Ishlatilgan tokenlar"
    )
    ai_cost = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True,
        verbose_name="AI: Xarajat ($)"
    )
    
    # ──────────────────────────────────────────────────────
    # TAQQOSLASH
    # ──────────────────────────────────────────────────────
    price_difference_low = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="Farq: Arzon narx (AI - ML)"
    )
    price_difference_market = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="Farq: Bozor narxi (AI - ML)"
    )
    price_difference_high = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name="Farq: Qimmat narx (AI - ML)"
    )
    difference_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Farq (%)"
    )
    
    # ──────────────────────────────────────────────────────
    # FINAL - Qaysi narxni tanlash
    # ──────────────────────────────────────────────────────
    final_price_low = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="YAKUNIY: Arzon narx"
    )
    final_price_market = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="YAKUNIY: Bozor narxi"
    )
    final_price_high = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="YAKUNIY: Qimmat narx"
    )
    final_source = models.CharField(
        max_length=20,
        choices=[
            ('ml', 'Machine Learning'),
            ('ai', 'Claude AI'),
            ('average', 'O\'rtacha (ML + AI)'),
            ('manual', 'Qo\'lda kiritilgan'),
        ],
        default='ml',
        verbose_name="Tanlov: Qaysi model"
    )
    
    # ──────────────────────────────────────────────────────
    # TASDIQLASH
    # ──────────────────────────────────────────────────────
    is_approved = models.BooleanField(
        default=False,
        verbose_name="Tasdiqlangan"
    )
    approved_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_predictions',
        verbose_name="Kim tasdiqladi"
    )
    approved_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Tasdiqlangan vaqt"
    )
    
    # Qo'shimcha
    notes = models.TextField(
        blank=True, null=True,
        verbose_name="Izohlar"
    )
    
    class Meta:
        verbose_name = "Narx Bashorati"
        verbose_name_plural = "Narx Bashoratlari"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['team', 'created_at']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"Bashorat #{self.id} - {self.final_price_market:,} UZS ({self.get_final_source_display()})"
    
    def calculate_differences(self):
        """ML va AI orasidagi farqni hisoblash"""
        if self.ml_price_market and self.ai_price_market:
            self.price_difference_low = self.ai_price_low - self.ml_price_low
            self.price_difference_market = self.ai_price_market - self.ml_price_market
            self.price_difference_high = self.ai_price_high - self.ml_price_high
            
            # Foiz farqi
            self.difference_percentage = (
                (self.ai_price_market - self.ml_price_market) / self.ml_price_market * 100
            )
    
    def set_final_price(self, source='average'):
        """Yakuniy narxni belgilash"""
        if source == 'ml':
            self.final_price_low = self.ml_price_low
            self.final_price_market = self.ml_price_market
            self.final_price_high = self.ml_price_high
        elif source == 'ai':
            self.final_price_low = self.ai_price_low
            self.final_price_market = self.ai_price_market
            self.final_price_high = self.ai_price_high
        elif source == 'average':
            # O'rtacha
            self.final_price_low = (self.ml_price_low + self.ai_price_low) / 2
            self.final_price_market = (self.ml_price_market + self.ai_price_market) / 2
            self.final_price_high = (self.ml_price_high + self.ai_price_high) / 2
        
        self.final_source = source
        self.save()


class MLModelMetrics(BaseModel):
    """ML Model metrikalari va versiyalari"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='ml_metrics')
    
    model_version = models.CharField(max_length=50, verbose_name="Versiya")
    model_type = models.CharField(
        max_length=50,
        choices=[
            ('random_forest', 'Random Forest'),
            ('linear_regression', 'Linear Regression'),
            ('xgboost', 'XGBoost'),
            ('neural_network', 'Neural Network'),
        ],
        default='random_forest',
        verbose_name="Model turi"
    )
    
    # O'qitish ma'lumotlari
    training_date = models.DateTimeField(auto_now_add=True)
    training_samples = models.IntegerField(verbose_name="O'quv namunalari")
    test_samples = models.IntegerField(verbose_name="Test namunalari")
    features_used = models.JSONField(
        default=list,
        verbose_name="Ishlatilgan parametrlar"
    )
    
    # Metrikalar
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Aniqlik (%)")
    mae = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="MAE")
    rmse = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="RMSE")
    r2_score = models.DecimalField(max_digits=5, decimal_places=4, verbose_name="R² Score")
    
    # Model fayli
    model_file_path = models.CharField(
        max_length=255,
        verbose_name="Model fayl yo'li"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "ML Model Metrikasi"
        verbose_name_plural = "ML Model Metrikalari"
        ordering = ['-training_date']
    
    def __str__(self):
        return f"v{self.model_version} - {self.accuracy}% ({self.get_model_type_display()})"


class PredictionComparison(BaseModel):
    """ML va AI bashoratlari taqqoslash statistikasi"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    
    period_start = models.DateField(verbose_name="Davr boshlanishi")
    period_end = models.DateField(verbose_name="Davr tugashi")
    
    # Umumiy
    total_predictions = models.IntegerField(verbose_name="Jami bashoratlar")
    
    # ML statistika
    ml_average_accuracy = models.DecimalField(max_digits=5, decimal_places=2)
    ml_average_time = models.DecimalField(max_digits=6, decimal_places=4)
    ml_total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # AI statistika
    ai_average_accuracy = models.DecimalField(max_digits=5, decimal_places=2)
    ai_average_time = models.DecimalField(max_digits=6, decimal_places=4)
    ai_total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    ai_total_tokens = models.IntegerField()
    
    # Taqqoslash
    average_price_difference = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="O'rtacha narx farqi"
    )
    winner = models.CharField(
        max_length=20,
        choices=[('ml', 'ML aniqroq'), ('ai', 'AI aniqroq'), ('equal', 'Teng')],
        verbose_name="G'olib"
    )
    
    class Meta:
        verbose_name = "Taqqoslash Statistikasi"
        verbose_name_plural = "Taqqoslash Statistikalari"
        ordering = ['-period_end']


# ============================================
# OLX INTEGRATION MODELS
# ============================================

class OLXProperty(BaseModel):
    """OLX.uz dan olingan ko'chmas mulk e'lonlari"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='olx_properties')
    
    # OLX identifikatori
    olx_id = models.CharField(max_length=100, unique=True, verbose_name="OLX ID", db_index=True)
    url = models.URLField(max_length=500, verbose_name="E'lon URL")
    title = models.CharField(max_length=500, verbose_name="Sarlavha")
    
    # Narx
    price_usd = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Narx (USD)")
    
    # Joylashuv
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shahar")
    address_text = models.TextField(blank=True, null=True, verbose_name="Manzil")
    
    # Asosiy parametrlar
    rooms = models.IntegerField(null=True, blank=True, verbose_name="Xonalar soni")
    area_total = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Umumiy maydon (m²)")
    area_living = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Yashash maydoni (m²)")
    area_kitchen = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Oshxona maydoni (m²)")
    floor = models.IntegerField(null=True, blank=True, verbose_name="Qavat")
    total_floors = models.IntegerField(null=True, blank=True, verbose_name="Umumiy qavatlar")
    
    # Bino va holat
    building_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Qurilish turi")
    repair_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ta'mirlash holati")
    layout = models.CharField(max_length=100, blank=True, null=True, verbose_name="Reja")
    furniture = models.BooleanField(default=False, verbose_name="Mebelli")
    bathroom = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sanuzel")
    
    # Qo'shimcha
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    image_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="Rasm URL")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    seller_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sotuvchi turi")
    
    # Processing
    is_processed = models.BooleanField(default=False, verbose_name="Qayta ishlangan", db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Qayta ishlangan vaqt")
    
    # Raw data
    raw_data = models.JSONField(default=dict, blank=True, verbose_name="Xom ma'lumot")
    
    class Meta:
        verbose_name = "OLX E'lon"
        verbose_name_plural = "OLX E'lonlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', 'is_processed']),
            models.Index(fields=['city', 'rooms']),
        ]
    
    def __str__(self):
        return f"OLX #{self.olx_id} - {self.title[:50]}"
    
    def mark_as_processed(self):
        """Qayta ishlangan deb belgilash"""
        from django.utils import timezone
        self.is_processed = True
        self.processed_at = timezone.now()
        self.save(update_fields=['is_processed', 'processed_at'])
    
    def get_short_address(self):
        """Qisqa manzil"""
        if self.address_text:
            return self.address_text[:100]
        return self.city or "Manzil yo'q"


class ComparisonResult(BaseModel):
    """OLX va CRM obyektlarini taqqoslash natijalari"""
    olx_property = models.ForeignKey(OLXProperty, on_delete=models.CASCADE, related_name='comparisons')
    
    # CRM obyekti (BuildHouse)
    from home.models import BuildHouse
    crm_object = models.ForeignKey(BuildHouse, on_delete=models.CASCADE, related_name='olx_comparisons')
    
    # Taqqoslash natijalari
    similarity_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="O'xshashlik (%)")
    price_difference_usd = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Narx farqi (USD)")
    price_difference_percent = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Narx farqi (%)")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('cheaper', 'Arzonroq'),
            ('similar', 'O\'xshash'),
            ('expensive', 'Qimmatroq'),
        ],
        verbose_name="Status",
        db_index=True
    )
    
    # Match details
    match_details = models.JSONField(default=dict, blank=True, verbose_name="Taqqoslash tafsilotlari")
    
    # Priority score (qanchalik muhim)
    priority_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
        verbose_name="Muhimlik darajasi"
    )
    
    # Notification
    is_notified = models.BooleanField(default=False, verbose_name="Xabarnoma yuborilgan", db_index=True)
    notified_at = models.DateTimeField(null=True, blank=True, verbose_name="Xabarnoma vaqti")
    
    class Meta:
        verbose_name = "Taqqoslash Natijasi"
        verbose_name_plural = "Taqqoslash Natijalari"
        ordering = ['-priority_score', '-created_at']
        unique_together = ['olx_property', 'crm_object']
        indexes = [
            models.Index(fields=['status', '-priority_score']),
            models.Index(fields=['is_notified', 'status']),
        ]
    
    def __str__(self):
        return f"OLX #{self.olx_property.olx_id} vs CRM #{self.crm_object.id} ({self.similarity_score}%)"
