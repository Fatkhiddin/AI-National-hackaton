# market_analys/admin.py

from django.contrib import admin
from .models import MarketPriceReference, PropertyPriceAnalysis, OLXProperty, ComparisonResult


@admin.register(MarketPriceReference)
class MarketPriceReferenceAdmin(admin.ModelAdmin):
    list_display = ['etaj', 'xonalar_soni', 'qurilish_turi', 'holat', 'maydon_min', 'maydon_max', 'arzon_narx', 'bozor_narx', 'qimmat_narx']
    list_filter = ['qurilish_turi', 'holat', 'xonalar_soni']
    search_fields = ['source_file']
    ordering = ['etaj', 'xonalar_soni']


@admin.register(PropertyPriceAnalysis)
class PropertyPriceAnalysisAdmin(admin.ModelAdmin):
    list_display = ['property_id', 'property_type', 'status', 'bozor_narxi', 'joriy_narxi', 'farq_foiz', 'confidence_score', 'analyzed_at']
    list_filter = ['status', 'property_type']
    search_fields = ['property_id']
    ordering = ['-analyzed_at']
    readonly_fields = ['analyzed_at', 'property_snapshot']


@admin.register(OLXProperty)
class OLXPropertyAdmin(admin.ModelAdmin):
    list_display = ['olx_id', 'title', 'price_usd', 'city', 'rooms', 'area_total', 'floor', 'is_processed']
    list_filter = ['is_processed', 'city', 'rooms']
    search_fields = ['title', 'olx_id', 'address_text']
    ordering = ['-created_at']


@admin.register(ComparisonResult)
class ComparisonResultAdmin(admin.ModelAdmin):
    list_display = ['olx_property', 'crm_object_id', 'similarity_score', 'price_difference_usd', 'status', 'is_notified']
    list_filter = ['status', 'is_notified']
    ordering = ['-priority_score', '-created_at']
