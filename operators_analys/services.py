"""
IP Phone / SIP Qo'ng'iroqlar uchun servislar
CRM API dan qo'ng'iroqlarni fetch qilish va bazaga saqlash
"""
import requests
from urllib.parse import urljoin
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from home.models import CRMConfiguration
from .models import IPPhoneCall
import logging

logger = logging.getLogger(__name__)


class SIPCallService:
    """
    CRM dan SIP qo'ng'iroqlarini olish va saqlash
    """
    
    def __init__(self):
        self.config = CRMConfiguration.get_config()
        self.base_url = self.config.crm_url if self.config.crm_url else ""
        self.headers = self.config.get_headers()
        self.timeout = 10
    
    def is_connected(self):
        """
        CRM ga ulanganmi tekshirish
        """
        return self.config.is_connected and self.config.access_token
    
    def fetch_calls(self, params=None):
        """
        CRM API dan qo'ng'iroqlarni olish
        
        Args:
            params (dict): So'rov parametrlari (page, page_size, filters)
        
        Returns:
            dict: API javobining parsed JSON yoki xato
        """
        if not self.is_connected():
            return {
                'success': False,
                'error': 'CRM ulangan emas',
                'results': []
            }
        
        try:
            api_url = urljoin(self.base_url, 'ip-phone/')
            default_params = {
                'page': 1,
                'page_size': 100,
                'ordering': '-timestamp',
            }
            
            if params:
                default_params.update(params)
            
            response = requests.get(
                api_url,
                headers=self.headers,
                params=default_params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ CRM dan {len(data.get('results', []))} ta qo'ng'iroq olindi")
                return {
                    'success': True,
                    'data': data,
                    'results': data.get('results', [])
                }
            elif response.status_code == 401:
                # Token expired, yangilash kerak
                success, msg = self.config.refresh_access_token()
                if success:
                    logger.info("✓ Token yangilandi, qayta urinilmoqda...")
                    return self.fetch_calls(params)
                else:
                    logger.error(f"✗ Token yangilash xatosi: {msg}")
                    return {
                        'success': False,
                        'error': f'Token muddati o\'tgan: {msg}',
                        'results': []
                    }
            else:
                error_msg = f"CRM xatosi: {response.status_code} - {response.text[:200]}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'results': []
                }
        
        except requests.exceptions.Timeout:
            error_msg = "Timeout: CRM javob bermadi"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'results': []}
        except requests.exceptions.ConnectionError:
            error_msg = "CRM serveriga ulanib bo'lmadi"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'results': []}
        except Exception as e:
            error_msg = f"Xato: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'results': []}
    
    def save_calls(self, calls_data):
        """
        Qo'ng'iroqlarni bazaga saqlash (yangilash yoki yangi qo'shish)
        
        Args:
            calls_data (list): CRM dan olingan qo'ng'iroqlar ro'yxati
        
        Returns:
            dict: Natija (saqlangan, yangilangan, xatoliklar soni)
        """
        created_count = 0
        updated_count = 0
        error_count = 0
        
        if not calls_data:
            return {
                'created': created_count,
                'updated': updated_count,
                'errors': error_count,
                'message': 'Bazaga saqlash uchun ma\'lumot yo\'q'
            }
        
        try:
            with transaction.atomic():
                for call_data in calls_data:
                    try:
                        call_id = call_data.get('call_id')
                        
                        if not call_id:
                            error_count += 1
                            logger.warning(f"Call ID yo'q: {call_data}")
                            continue
                        
                        # Qo'ng'iroq timestamp
                        timestamp_str = call_data.get('timestamp')
                        if timestamp_str:
                            try:
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                timestamp = timezone.make_aware(datetime.fromisoformat(timestamp_str[:19]))
                            except:
                                timestamp = timezone.now()
                        else:
                            timestamp = timezone.now()
                        
                        call_obj, created = IPPhoneCall.objects.update_or_create(
                            call_id=call_id,
                            defaults={
                                'phone': call_data.get('phone', ''),
                                'operator_name': call_data.get('operator_name', ''),
                                'client_name': call_data.get('client_name', ''),
                                'timestamp': timestamp,
                                'tree_name': call_data.get('treeName', ''),
                                'status': call_data.get('status', 'unknown'),
                                'call_record_link': call_data.get('call_record_link', ''),
                                'src_num': call_data.get('src_num', ''),
                                'dst_num': call_data.get('dst_num', ''),
                                'duration_seconds': call_data.get('duration_seconds', 0),
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Qo'ng'iroq saqlashda xato (ID: {call_data.get('call_id')}): {str(e)}")
                        continue
            
            logger.info(f"✓ Olingan: {created_count}, Yangilangan: {updated_count}, Xatolar: {error_count}")
        
        except Exception as e:
            logger.error(f"Tranzaksiyada xato: {str(e)}")
            return {
                'created': 0,
                'updated': 0,
                'errors': len(calls_data),
                'message': f'Tranzaksiyada xato: {str(e)}'
            }
        
        return {
            'created': created_count,
            'updated': updated_count,
            'errors': error_count,
            'message': f'Olingan: {created_count}, Yangilangan: {updated_count}, Xatolar: {error_count}'
        }
    
    def sync_all_calls(self, page_size=100):
        """
        Barcha qo'ng'iroqlarni CRM dan fetch qilish va bazaga saqlash
        
        Args:
            page_size (int): Bir so'rovda nechta qo'ng'iroq olish
        
        Returns:
            dict: Synchronization natijasi
        """
        if not self.is_connected():
            return {
                'success': False,
                'message': 'CRM ulangan emas',
                'total_saved': 0
            }
        
        total_created = 0
        total_updated = 0
        total_errors = 0
        page = 1
        
        logger.info("=== SIP Qo'ng'iroqlar Synchronizatsiyasi Boshlandi ===")
        
        while True:
            result = self.fetch_calls({
                'page': page,
                'page_size': page_size
            })
            
            if not result['success']:
                logger.warning(f"Sahifa {page} olishda xato: {result['error']}")
                break
            
            calls = result.get('results', [])
            
            if not calls:
                logger.info(f"Sahifa {page}: Qo'ng'iroq yo'q, tugaldi")
                break
            
            logger.info(f"Sahifa {page}: {len(calls)} ta qo'ng'iroq olinmoqda...")
            
            save_result = self.save_calls(calls)
            total_created += save_result['created']
            total_updated += save_result['updated']
            total_errors += save_result['errors']
            
            logger.info(f"Sahifa {page} natijasi: {save_result['message']}")
            
            # Keyingi sahifa bormi
            next_page = result['data'].get('next')
            if not next_page:
                break
            
            page += 1
        
        logger.info(f"=== Synchronizatsiya Tugadi ===")
        logger.info(f"Jami olingan: {total_created}, Yangilangan: {total_updated}, Xatolar: {total_errors}")
        
        return {
            'success': True,
            'total_created': total_created,
            'total_updated': total_updated,
            'total_errors': total_errors,
            'message': f'Jami: +{total_created} yangi, ↻{total_updated} yangilangan'
        }
    
    def get_recent_calls(self, limit=50):
        """
        So'nggi qo'ng'iroqlarni bazadan olish
        
        Args:
            limit (int): Nechta qo'ng'iroq olish
        
        Returns:
            QuerySet: Oxirgi qo'ng'iroqlar
        """
        return IPPhoneCall.objects.all()[:limit]
    
    def get_calls_by_operator(self, operator_name, limit=50):
        """
        Operatorning qo'ng'iroqlarini bazadan olish
        
        Args:
            operator_name (str): Operator nomi
            limit (int): Nechta qo'ng'iroq olish
        
        Returns:
            QuerySet: Operator qo'ng'iroqlari
        """
        return IPPhoneCall.objects.filter(
            operator_name__icontains=operator_name
        )[:limit]
    
    def get_stats(self):
        """
        Qo'ng'iroqlar statistikasi
        
        Returns:
            dict: Statistika ma'lumotlari
        """
        total = IPPhoneCall.objects.count()
        answered = IPPhoneCall.objects.filter(status='answered').count()
        missed = IPPhoneCall.objects.filter(status='missed').count()
        busy = IPPhoneCall.objects.filter(status='busy').count()
        incoming = IPPhoneCall.objects.filter(tree_name__icontains='Kiruvchi').count()
        outgoing = IPPhoneCall.objects.filter(tree_name__icontains='Chiquvchi').count()
        
        return {
            'total': total,
            'answered': answered,
            'missed': missed,
            'busy': busy,
            'incoming': incoming,
            'outgoing': outgoing,
            'answered_percent': round((answered / total * 100) if total > 0 else 0, 1),
        }
