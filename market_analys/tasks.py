# market_analysis/tasks.py

from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging

from .models import OLXProperty, ComparisonResult, PropertyPriceAnalysis
from .services import PriceAnalyzer
from home.models import Notification, BuildHouse

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_olx_comparisons(self):
    """
    Barcha yangi OLX obyektlarni CRM bilan taqqoslash
    Celery Beat orqali 1 marta/kun ishga tushadi
    """
    try:
        # Yangi obyektlarni olish
        new_olx_properties = OLXProperty.objects.filter(
            is_processed=False
        ).select_related('team')
        
        total = new_olx_properties.count()
        
        if total == 0:
            logger.info("✅ Yangi OLX obyektlar yo'q")
            return {'success': True, 'message': 'No new properties'}
        
        logger.info(f"🔄 {total} ta yangi OLX obyektni tahlil qilish boshlandi")
        
        analyzer = PriceAnalyzer()
        processed_count = 0
        cheap_found = 0
        
        for olx_prop in new_olx_properties:
            try:
                # Yangi PriceAnalyzer bilan tahlil qilish
                analysis = analyzer.analyze_property(olx_prop, use_ai=False)
                
                if analysis:
                    # Processed belgilash
                    olx_prop.is_processed = True
                    olx_prop.save()
                    processed_count += 1
                    
                    # Arzon takliflarni topish
                    if analysis.status in ['juda_arzon', 'arzon']:
                        cheap_found += 1
                        # Notification task
                        notify_cheap_findings.delay(
                            olx_property_id=olx_prop.id,
                            analysis_id=analysis.id
                        )
                
            except Exception as e:
                logger.error(f"❌ OLX {olx_prop.id} tahlilida xato: {e}")
                continue
                
            except Exception as e:
                logger.error(f"❌ OLX {olx_prop.id} taqqoslashda xato: {e}")
                continue
        
        logger.info(f"✅ {processed_count}/{total} qayta ishlandi. {cheap_found} ta arzon taklif topildi")
        
        return {
            'success': True,
            'total': total,
            'processed': processed_count,
            'cheap_found': cheap_found
        }
        
    except Exception as exc:
        logger.error(f"❌ Task xatolik: {exc}")
        raise self.retry(exc=exc, countdown=300)  # 5 daqiqa kutib retry


@shared_task
def compare_single_olx(olx_property_id: int):
    """
    Bitta OLX obyektni tahlil qilish (manual yoki test uchun)
    """
    try:
        olx_prop = OLXProperty.objects.get(id=olx_property_id)
        analyzer = PriceAnalyzer()
        
        # Tahlil qilish
        analysis = analyzer.analyze_property(olx_prop, use_ai=True)
        
        if analysis:
            olx_prop.is_processed = True
            olx_prop.save()
            
            # Arzon takliflar
            if analysis.status in ['juda_arzon', 'arzon']:
                notify_cheap_findings.delay(
                    olx_property_id=olx_prop.id,
                    analysis_id=analysis.id
                )
            
            return {
                'success': True,
                'status': analysis.status,
                'farq_foiz': float(analysis.farq_foiz)
            }
        else:
            return {'success': False, 'error': 'Analysis failed'}
        
    except OLXProperty.DoesNotExist:
        logger.error(f"❌ OLX {olx_property_id} topilmadi")
        return {'success': False, 'error': 'Not found'}
    except Exception as e:
        logger.error(f"❌ Xatolik: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def notify_cheap_findings(olx_property_id: int, analysis_id: int):
    """
    Arzon takliflar haqida Telegram ga xabar yuborish
    """
    try:
        olx_prop = OLXProperty.objects.get(id=olx_property_id)
        analysis = PropertyPriceAnalysis.objects.get(id=analysis_id)
        
        # Xabar tayyorlash
        message = f"""
🔴 ARZON TAKLIF TOPILDI!

📍 OLX ID: {olx_prop.olx_id}
🏠 {olx_prop.title}
💰 Narx: ${olx_prop.price_usd:,.0f}
📊 Status: {analysis.get_status_display()}
📉 Farq: {analysis.farq_foiz}% ({analysis.farq_summa:,.0f} so'm)

🔗 {olx_prop.url}
"""
        
        # Database notification yaratish
        # Boss va team adminlarga
        from users.models import CustomUser
        admins = CustomUser.objects.filter(
            team=olx_prop.team,
            role__in=['boss', 'admin']
        )
        
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title='🔴 Arzon OLX taklif!',
                message=message,
                is_read=False
            )
        
        logger.info(f"✅ Notification yuborildi: OLX {olx_property_id}")
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"❌ Notification task xatolik: {e}")
        return {'success': False, 'error': str(e)}


# Eski ComparisonResult uchun helper (backward compatibility)
def format_comparison_message(comparison: ComparisonResult) -> str:
    """
    ESKI: Telegram uchun xabar formatlash (deprecated, faqat eski kod uchun)
    """
    olx = comparison.olx_property
    crm = comparison.crm_object if hasattr(comparison, 'crm_object') else None
    
    if not crm:
        return f"OLX ID: {olx.olx_id} - {olx.title}"
    
    message = f"""🔔 ARZON TAKLIF!

📍 {olx.city}
🏠 {olx.rooms} xona, {olx.area_total} m²
🏢 {olx.floor}/{olx.total_floors or '?'} qavat

💰 OLX: ${olx.price_usd:,.0f}
💰 CRM: ${crm.price:,.0f}

🔗 {olx.url}
"""
    return message


@shared_task
def cleanup_old_olx_data(days: int = 30):
    """
    Eski OLX ma'lumotlarni tozalash (30+ kun)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Eski va processed obyektlar
    old_properties = OLXProperty.objects.filter(
        created_at__lt=cutoff_date,
        is_processed=True
    )
    
    deleted_count = old_properties.count()
    old_properties.delete()
    
    logger.info(f"🧹 {deleted_count} ta eski OLX obyekt o'chirildi")
    
    return {
        'success': True,
        'deleted': deleted_count
    }