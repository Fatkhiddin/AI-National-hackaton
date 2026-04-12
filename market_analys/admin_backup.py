# market_analysis/admin.py

"""
Admin panel konfiguratsiyasi - TZ bo'yicha to'liq implementatsiya.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    MarketPriceReference,
    PropertyPriceAnalysis,
    PriceReference,
    PricePrediction,
    MLModelMetrics,
    PredictionComparison
)


# ============================================
# YANGI MODELLAR (TZ bo'yicha)
# ============================================

@admin.register(MarketPriceReference)
class MarketPriceReferenceAdmin(admin.ModelAdmin):
    """Bozor narxlari ma'lumotnomasi - TZ bo'yicha"""
    
    list_display = [
        'id',
        'qurilish_turi_badge',
        'xonalar_soni',
        'etaj',
        'holat_badge',
        'maydon_range_display',
        'narx_display',
        'source_file',
        'created_at',
    ]
    
    list_filter = [
        'qurilish_turi',
        'holat',
        'xonalar_soni',
        'etaj',
        'created_at',
    ]
    
    search_fields = [
        'source_file',
        'team__name',
    ]
    
    ordering = ['etaj', 'xonalar_soni', 'maydon_min']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Asosiy Parametrlar', {
            'fields': ('team', 'etaj', 'xonalar_soni', 'qurilish_turi', 'holat')
        }),
        ('Maydon', {
            'fields': ('maydon_min', 'maydon_max')
        }),
        ('Narxlar (so\'m/m²)', {
            'fields': ('arzon_narx', 'bozor_narx', 'qimmat_narx'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('source_file', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_to_csv']
    
    def qurilish_turi_badge(self, obj):
        """Qurilish turi - color-coded badge"""
        colors = {
            'gishtli': '#F44336',
            'panelli': '#2196F3',
            'monolitli': '#4CAF50',
            'blokli': '#FF9800',
        }
        color = colors.get(obj.qurilish_turi, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_qurilish_turi_display()
        )
    qurilish_turi_badge.short_description = 'Qurilish'
    
    def holat_badge(self, obj):
        """Holat - color-coded badge"""
        color = '#4CAF50' if obj.holat == 'remontli' else '#FF9800'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_holat_display()
        )
    holat_badge.short_description = 'Holat'
    
    def maydon_range_display(self, obj):
        """Maydon oralig'i"""
        if obj.maydon_max:
            return f"{obj.maydon_min} - {obj.maydon_max} m²"
        return f"{obj.maydon_min} m²"
    maydon_range_display.short_description = 'Maydon'
    
    def narx_display(self, obj):
        """Narxlar - HTML formatted"""
        return format_html(
            '<div>'
            '<span style="color: #4CAF50; font-weight: bold;">${}</span> '
            '<span style="color: #999; font-size: 11px;">(karobka)</span><br>'
            '<span style="font-weight: bold;">${}</span> '
            '<span style="color: #999; font-size: 11px;">(o\'rtacha)</span><br>'
            '<span style="color: #F44336; font-weight: bold;">${}</span> '
            '<span style="color: #999; font-size: 11px;">(remontli)</span>'
            '</div>',
            f'{float(obj.arzon_narx):,.0f}',
            f'{float(obj.bozor_narx):,.0f}',
            f'{float(obj.qimmat_narx):,.0f}'
        )
    narx_display.short_description = 'Narxlar (1 m² uchun, USD)'
    
    def export_to_csv(self, request, queryset):
        """CSV ga export qilish"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="market_prices.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Etaj', 'Xonalar', 'Qurilish', 'Holat',
            'Maydon (min)', 'Maydon (max)',
            'Arzon', 'Bozor', 'Qimmat', 'Manba'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.id,
                obj.etaj,
                obj.xonalar_soni,
                obj.get_qurilish_turi_display(),
                obj.get_holat_display(),
                obj.maydon_min,
                obj.maydon_max,
                obj.arzon_narx,
                obj.bozor_narx,
                obj.qimmat_narx,
                obj.source_file,
            ])
        
        return response
    export_to_csv.short_description = '📥 CSV ga export qilish'


@admin.register(PropertyPriceAnalysis)
class PropertyPriceAnalysisAdmin(admin.ModelAdmin):
    """Narx tahlili - TZ bo'yicha"""
    
    list_display = [
        'id',
        'property_link',
        'content_type',
        'status_badge',
        'joriy_narxi_display',
        'bozor_narxi_display',
        'farq_display',
        'confidence_badge',
        'analyzed_at',
    ]
    
    list_filter = [
        'status',
        'content_type',
        'analyzed_at',
    ]
    
    search_fields = [
        'property_id',
        'ai_tahlil',
        'tavsiya',
    ]
    
    date_hierarchy = 'analyzed_at'
    
    ordering = ['-analyzed_at']
    
    readonly_fields = [
        'analyzed_at',
        'content_type',
        'object_id',
        'property_id',
        'ai_tahlil_formatted',
        'tavsiya_formatted',
    ]
    
    fieldsets = (
        ('Obyekt Ma\'lumotlari', {
            'fields': ('team', 'content_type', 'object_id', 'property_id')
        }),
        ('Tahlil Natijalari', {
            'fields': (
                'status',
                'bozor_narxi',
                'joriy_narxi',
                'farq_foiz',
                'farq_summa',
                'confidence_score',
            ),
            'classes': ('wide',)
        }),
        ('AI Tahlil', {
            'fields': ('ai_tahlil_formatted', 'tavsiya_formatted'),
            'classes': ('collapse',)
        }),
        ('Reference', {
            'fields': ('matched_reference', 'analyzed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['re_analyze', 'export_to_csv']
    
    def property_link(self, obj):
        """Property ga link"""
        if obj.content_type.model == 'buildhouse':
            url = reverse('admin:home_buildhouse_change', args=[obj.object_id])
            return format_html('<a href="{}">{} #{}</a>', url, 'BuildHouse', obj.property_id)
        elif obj.content_type.model == 'olxproperty':
            url = reverse('admin:market_analysis_olxproperty_change', args=[obj.object_id])
            return format_html('<a href="{}">{} #{}</a>', url, 'OLX', obj.property_id)
        return f'Property #{obj.property_id}'
    property_link.short_description = 'Obyekt'
    
    def status_badge(self, obj):
        """Status - color-coded badge"""
        color = obj.get_status_color()
        
        icons = {
            'juda_arzon': '💚',
            'arzon': '✅',
            'normal': '⚖️',
            'qimmat': '⚠️',
            'juda_qimmat': '🔴',
        }
        icon = icons.get(obj.status, '❓')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; '
            'border-radius: 4px; font-weight: bold; display: inline-block;">'
            '{} {}</span>',
            color,
            icon,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def joriy_narxi_display(self, obj):
        """Joriy narx - formatted"""
        return format_html(
            '<span style="font-weight: bold;">${}</span>/m²',
            f'{float(obj.joriy_narxi):,.0f}'
        )
    joriy_narxi_display.short_description = 'Joriy Narx'
    
    def bozor_narxi_display(self, obj):
        """Bozor narxi - formatted"""
        return format_html(
            '<span style="color: #2196F3; font-weight: bold;">${}</span>/m²',
            f'{float(obj.bozor_narxi):,.0f}'
        )
    bozor_narxi_display.short_description = 'Bozor Narxi'
    
    def farq_display(self, obj):
        """Farq - color-coded with icon"""
        if obj.farq_foiz < 0:
            color = '#4CAF50'
            icon = '▼'
        else:
            color = '#F44336'
            icon = '▲'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}%</span><br>'
            '<span style="color: #666; font-size: 11px;">(${} )</span>',
            color,
            icon,
            f'{float(obj.farq_foiz):.1f}',
            f'{float(obj.farq_summa):,.0f}'
        )
    farq_display.short_description = 'Farq'
    
    def confidence_badge(self, obj):
        """Ishonch darajasi - color-coded"""
        score = float(obj.confidence_score)
        
        if score >= 80:
            color = '#4CAF50'
        elif score >= 60:
            color = '#FF9800'
        else:
            color = '#F44336'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}%</span>',
            color,
            f'{score:.0f}'
        )
    confidence_badge.short_description = 'Confidence'
    
    def ai_tahlil_formatted(self, obj):
        """AI tahlil - formatted"""
        if obj.ai_tahlil:
            return format_html(
                '<div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #2196F3; '
                'white-space: pre-wrap;">{}</div>',
                obj.ai_tahlil
            )
        return '-'
    ai_tahlil_formatted.short_description = 'AI Tahlil'
    
    def tavsiya_formatted(self, obj):
        """Tavsiya - formatted"""
        if obj.tavsiya:
            return format_html(
                '<div style="background: #fff3e0; padding: 15px; border-left: 4px solid #FF9800; '
                'white-space: pre-wrap;">{}</div>',
                obj.tavsiya
            )
        return '-'
    tavsiya_formatted.short_description = 'Tavsiya'
    
    def re_analyze(self, request, queryset):
        """Qayta tahlil qilish"""
        from .services import PriceAnalyzer
        
        analyzer = PriceAnalyzer()
        success = 0
        failed = 0
        
        for analysis in queryset:
            try:
                property_obj = analysis.content_object
                if property_obj:
                    analyzer.analyze_property(property_obj, use_ai=True)
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
        
        self.message_user(
            request,
            f'✅ {success} ta qayta tahlil qilindi, ❌ {failed} ta xato'
        )
    re_analyze.short_description = '🔄 Qayta tahlil qilish (AI bilan)'
    
    def export_to_csv(self, request, queryset):
        """CSV ga export"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="price_analysis.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Property ID', 'Model', 'Status',
            'Joriy Narx', 'Bozor Narxi', 'Farq (%)', 'Farq (so\'m)',
            'Confidence', 'Tahlil Vaqti'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.id,
                obj.property_id,
                obj.content_type.model,
                obj.get_status_display(),
                obj.joriy_narxi,
                obj.bozor_narxi,
                obj.farq_foiz,
                obj.farq_summa,
                obj.confidence_score,
                obj.analyzed_at.strftime('%Y-%m-%d %H:%M'),
            ])
        
        return response
    export_to_csv.short_description = '📥 CSV ga export qilish'


# ============================================
# ESKI MODELLAR (backward compatibility)
# ============================================

@admin.register(PriceReference)
class PriceReferenceAdmin(admin.ModelAdmin):
    list_display = ['id', 'floor_number', 'room_count', 'area_from', 'area_to', 
                    'is_renovated', 'price_market', 'is_active']
    list_filter = ['is_renovated', 'is_active', 'floor_number', 'room_count']
    search_fields = ['notes']
    ordering = ['floor_number', 'room_count', 'area_from']
    
    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('team', 'floor_number', 'room_count', 'area_from', 'area_to', 'is_renovated')
        }),
        ('Narxlar', {
            'fields': ('price_low', 'price_market', 'price_high')
        }),
        ('Qo\'shimcha', {
            'fields': ('source_sheet', 'excel_row', 'notes', 'is_active'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PricePrediction)
class PricePredictionAdmin(admin.ModelAdmin):
    list_display = ['id', 'content_type', 'object_id', 'final_price_market', 
                    'final_source', 'is_approved', 'created_at']
    list_filter = ['final_source', 'is_approved', 'is_renovated', 'created_at']
    search_fields = ['notes', 'ai_analysis']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Asosiy', {
            'fields': ('team', 'content_type', 'object_id', 
                      'floor_number', 'room_count', 'area', 'is_renovated')
        }),
        ('ML Bashorati', {
            'fields': ('ml_price_low', 'ml_price_market', 'ml_price_high',
                      'ml_confidence', 'ml_execution_time', 'ml_model_version'),
            'classes': ('collapse',)
        }),
        ('AI Bashorati', {
            'fields': ('ai_price_low', 'ai_price_market', 'ai_price_high',
                      'ai_confidence', 'ai_analysis', 'ai_execution_time',
                      'ai_tokens_used', 'ai_cost'),
            'classes': ('collapse',)
        }),
        ('Taqqoslash', {
            'fields': ('price_difference_low', 'price_difference_market', 
                      'price_difference_high', 'difference_percentage'),
            'classes': ('collapse',)
        }),
        ('Yakuniy', {
            'fields': ('final_price_low', 'final_price_market', 'final_price_high',
                      'final_source', 'is_approved', 'approved_by', 'approved_at', 'notes')
        }),
    )


@admin.register(MLModelMetrics)
class MLModelMetricsAdmin(admin.ModelAdmin):
    list_display = ['id', 'model_version', 'model_type', 'accuracy', 
                    'training_date', 'is_active']
    list_filter = ['model_type', 'is_active', 'training_date']
    readonly_fields = ['training_date']


@admin.register(PredictionComparison)
class PredictionComparisonAdmin(admin.ModelAdmin):
    list_display = ['id', 'period_start', 'period_end', 'total_predictions',
                    'winner', 'ml_total_cost', 'ai_total_cost']
    list_filter = ['winner', 'period_start']
    readonly_fields = ['created_at']