# market_analys/models.py
# TO'LIQ QAYTA YOZILGAN — external dependency yo'q, CRM API orqali ishlaydi

from django.db import models
import json


# ============================================
# BASE MODEL (admintion.models.BaseModel o'rniga)
# ============================================

class BaseModel(models.Model):
    """Abstract base model with timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ============================================
# BOZOR NARXLARI (Google Sheets / Excel dan import)
# ============================================

class MarketPriceReference(BaseModel):
    """
    Google Sheets dan import qilingan bozor narxlari ma'lumotnomasi.
    """
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
        verbose_name = "Bozor Narxi"
        verbose_name_plural = "Bozor Narxlari"
        ordering = ['etaj', 'xonalar_soni', 'maydon_min']
        unique_together = ['etaj', 'xonalar_soni', 'qurilish_turi', 'holat', 'maydon_min']
        indexes = [
            models.Index(fields=['qurilish_turi', 'xonalar_soni']),
            models.Index(fields=['etaj', 'holat']),
        ]

    def __str__(self):
        return f"{self.qurilish_turi} - {self.xonalar_soni} xona - {self.etaj}-etaj - {self.holat}"

    def get_narx_range(self):
        return {
            'min': float(self.arzon_narx),
            'avg': float(self.bozor_narx),
            'max': float(self.qimmat_narx)
        }


# ============================================
# NARX TAHLILI (AI bilan)
# ============================================

class PropertyPriceAnalysis(BaseModel):
    """
    Mulk narx tahlil natijalarini saqlash.
    BuildHouse — CRM API dan olinadi (faqat property_id saqlaymiz)
    OLXProperty — lokal DB da saqlanadi
    """
    property_id = models.IntegerField(db_index=True, verbose_name="Obyekt ID")
    property_type = models.CharField(
        max_length=20,
        choices=[
            ('buildhouse', 'CRM Obyekt'),
            ('olxproperty', 'OLX E\'lon'),
        ],
        default='buildhouse',
        verbose_name="Obyekt turi"
    )

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
    bozor_narxi = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Bozor narxi (USD/m²)")
    joriy_narxi = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Hozirgi narx (USD/m²)")
    farq_foiz = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Farq (foizda)")
    farq_summa = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Farq (USD)")

    # AI tahlili
    ai_tahlil = models.TextField(blank=True, verbose_name="AI tahlil matni")
    tavsiya = models.TextField(blank=True, verbose_name="AI tavsiyasi")
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Ishonch darajasi")

    # Reference
    matched_reference = models.ForeignKey(
        MarketPriceReference,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Mos kelgan ma'lumotnoma"
    )

    # Metadata
    analyzed_at = models.DateTimeField(auto_now_add=True, verbose_name="Tahlil vaqti")

    # CRM dan olingan data snapshot
    property_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Obyekt snapshot")

    class Meta:
        verbose_name = "Narx Tahlili"
        verbose_name_plural = "Narx Tahillari"
        ordering = ['-analyzed_at']
        indexes = [
            models.Index(fields=['property_id', '-analyzed_at']),
            models.Index(fields=['status']),
            models.Index(fields=['property_type', 'property_id']),
        ]

    def __str__(self):
        return f"#{self.property_id} - {self.get_status_display()}"

    def get_status_color(self):
        colors = {
            'juda_arzon': '#00C853',
            'arzon': '#64DD17',
            'normal': '#FFC107',
            'qimmat': '#FF6F00',
            'juda_qimmat': '#D32F2F',
        }
        return colors.get(self.status, '#9E9E9E')


# ============================================
# OLX INTEGRATION
# ============================================

class OLXProperty(BaseModel):
    """OLX.uz dan olingan ko'chmas mulk e'lonlari"""
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
    floor = models.IntegerField(null=True, blank=True, verbose_name="Qavat")
    total_floors = models.IntegerField(null=True, blank=True, verbose_name="Umumiy qavatlar")

    # Bino va holat
    building_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Qurilish turi")
    repair_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ta'mirlash holati")

    # Qo'shimcha
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    image_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="Rasm URL")

    # Processing
    is_processed = models.BooleanField(default=False, verbose_name="Qayta ishlangan", db_index=True)

    # Raw data
    raw_data = models.JSONField(default=dict, blank=True, verbose_name="Xom ma'lumot")

    class Meta:
        verbose_name = "OLX E'lon"
        verbose_name_plural = "OLX E'lonlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"OLX #{self.olx_id} - {self.title[:50]}"

    def mark_as_processed(self):
        from django.utils import timezone
        self.is_processed = True
        self.save(update_fields=['is_processed'])


class ComparisonResult(BaseModel):
    """OLX va CRM obyektlarini taqqoslash natijalari"""
    olx_property = models.ForeignKey(OLXProperty, on_delete=models.CASCADE, related_name='comparisons')

    # CRM obyekti — faqat ID saqlanadi, data API orqali olinadi
    crm_object_id = models.IntegerField(verbose_name="CRM Obyekt ID", db_index=True)
    crm_object_snapshot = models.JSONField(default=dict, blank=True, verbose_name="CRM obyekt snapshot")

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

    match_details = models.JSONField(default=dict, blank=True)
    priority_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_notified = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = "Taqqoslash Natijasi"
        verbose_name_plural = "Taqqoslash Natijalari"
        ordering = ['-priority_score', '-created_at']
        unique_together = ['olx_property', 'crm_object_id']

    def __str__(self):
        return f"OLX #{self.olx_property.olx_id} vs CRM #{self.crm_object_id} ({self.similarity_score}%)"

    def mark_as_notified(self):
        from django.utils import timezone
        self.is_notified = True
        self.save(update_fields=['is_notified'])
