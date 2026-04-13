"""
IP Phone / SIP Qo'ng'iroqlar uchun servislar
CRM API dan qo'ng'iroqlarni fetch qilish va bazaga saqlash
STT (Speech-to-Text) va AI Analysis xizmatlari
"""
import requests
import re
from typing import Dict, Any, Optional
from urllib.parse import urljoin
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from home.models import CRMConfiguration, UzbekVoiceConfiguration
from .models import IPPhoneCall, STTRecord, AIAnalysis, OperatorAIConfiguration
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


# ═══════════════════════════════════════════════════════
# UZBEKVOICE.AI STT SERVICE
# ═══════════════════════════════════════════════════════

def convert_audio_to_text(
    audio_url: str,
    api_key: str,
    language: str = 'uz',
    return_offsets: bool = True,
    run_diarization: bool = False,
    blocking: bool = True,
    call_record_object=None,
    processed_by=None
) -> Dict[str, Any]:
    """
    Audio faylni textga o'girish (UzbekVoice.ai API)
    
    Args:
        audio_url: Audio fayl URL manzili
        api_key: UzbekVoice.ai API kaliti
        language: Til ('uz', 'ru', 'ru-uz')
        return_offsets: Vaqt offsetlarini qaytarish
        run_diarization: So'zlovchilarni bo'lish
        blocking: Sinxron yoki asinxron
        call_record_object: Qo'ng'iroq obyekti (IPPhoneCall)
        processed_by: Kim tomonidan (CustomUser)
    
    Returns:
        Dict natija bilan
    """
    
    # Avval mavjud STTRecord ni tekshirish (duplicate yaratmaslik)
    stt_record = None
    if call_record_object:
        content_type = ContentType.objects.get_for_model(call_record_object)
        
        existing_stt = STTRecord.objects.filter(
            content_type=content_type,
            object_id=call_record_object.id,
            status='completed'
        ).first()
        
        if existing_stt:
            return {
                'success': True,
                'stt_record_id': existing_stt.id,
                'transcribed_text': existing_stt.transcribed_text,
                'message': 'Bu qo\'ng\'iroq allaqachon STT orqali o\'tkazilgan. Mavjud natija qaytarildi.',
                'already_processed': True
            }
        
        # Yangi STTRecord yaratish
        stt_record = STTRecord.objects.create(
            content_type=content_type,
            object_id=call_record_object.id,
            original_audio_url=audio_url,
            language=language,
            with_offsets=return_offsets,
            with_diarization=bool(run_diarization),
            status='processing',
            processed_by=processed_by
        )
    
    url = 'https://uzbekvoice.ai/api/v1/stt'
    headers = {
        "Authorization": api_key
    }
    
    try:
        # Audio faylni yuklab olish
        logger.info(f"Audio yuklab olinmoqda: {audio_url}")
        audio_response = requests.get(audio_url, timeout=30)
        audio_response.raise_for_status()
        
        files = {
            "file": ("audio.mp3", audio_response.content, "audio/mpeg"),
        }
        
        data = {
            "return_offsets": "true" if return_offsets else "false",
            "run_diarization": str(run_diarization).lower() if run_diarization else "false",
            "language": language,
            "blocking": "true" if blocking else "false",
        }
        
        # STT API ga so'rov
        logger.info(f"UzbekVoice.ai STT API ga so'rov yuborilmoqda...")
        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=120  # 2 daqiqa timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # STTRecord yangilash
            transcribed_text = ""
            if stt_record:
                if isinstance(result, dict):
                    if 'text' in result:
                        transcribed_text = result['text']
                    elif 'result' in result and isinstance(result['result'], dict):
                        transcribed_text = result['result'].get('text', '')
                    elif 'data' in result:
                        transcribed_text = result['data'].get('text', '')
                
                stt_record.transcribed_text = transcribed_text or str(result)
                stt_record.api_response = result
                stt_record.status = 'completed'
                stt_record.processed_at = timezone.now()
                stt_record.save()
                
                logger.info(f"✓ STT muvaffaqiyatli: {len(transcribed_text)} belgi")
            
            return {
                'success': True,
                'data': result,
                'stt_record_id': stt_record.id if stt_record else None,
                'transcribed_text': transcribed_text if stt_record else str(result)
            }
        else:
            error_msg = f"API xatolik: {response.status_code} - {response.text}"
            logger.error(f"✗ STT xatolik: {error_msg}")
            
            if stt_record:
                stt_record.status = 'failed'
                stt_record.error_message = error_msg
                stt_record.save()
            
            return {
                'success': False,
                'error': error_msg
            }
    
    except requests.exceptions.Timeout:
        error_msg = "So'rov vaqti tugadi. API javob bermadi."
        logger.error(f"✗ STT Timeout: {error_msg}")
        
        if stt_record:
            stt_record.status = 'failed'
            stt_record.error_message = error_msg
            stt_record.save()
        
        return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Xatolik: {str(e)}"
        logger.error(f"✗ STT Exception: {error_msg}")
        
        if stt_record:
            stt_record.status = 'failed'
            stt_record.error_message = error_msg
            stt_record.save()
        
        return {'success': False, 'error': error_msg}


# ═══════════════════════════════════════════════════════
# AI ANALYSIS SERVICE
# ═══════════════════════════════════════════════════════


def analyze_text_with_ai(
    stt_record: STTRecord,
    analyzed_by=None
) -> Dict[str, Any]:
    """
    STT natijasini AI bilan tahlil qilish
    Admin paneldan kiritilgan AIConfiguration ishlatiladi
    
    Args:
        stt_record: STTRecord obyekti
        analyzed_by: Kim tomonidan (CustomUser)
    
    Returns:
        Dict natija bilan
    """
    
    # AI config olish (operators_analys.OperatorAIConfiguration dan)
    ai_config = OperatorAIConfiguration.get_config()
    
    if not ai_config or not ai_config.api_key:
        return {
            'success': False,
            'error': 'AI konfiguratsiya topilmadi yoki API key kiritilmagan. Admin paneldan sozlang.'
        }
    
    # AIAnalysis tekshirish - allaqachon tahlil qilingan bo'lsa
    existing_analysis = AIAnalysis.objects.filter(
        stt_record=stt_record,
        status='completed'
    ).first()
    
    if existing_analysis:
        return {
            'success': True,
            'ai_analysis_id': existing_analysis.id,
            'analysis_text': existing_analysis.analysis_text,
            'overall_score': existing_analysis.overall_score,
            'customer_satisfaction': existing_analysis.customer_satisfaction,
            'message': 'Bu suhbat allaqachon tahlil qilingan. Mavjud tahlil qaytarildi.',
            'already_analyzed': True
        }
    
    # Yangi AIAnalysis yaratish
    ai_analysis = AIAnalysis.objects.create(
        stt_record=stt_record,
        ai_config=ai_config,
        status='processing',
        analyzed_by=analyzed_by
    )
    
    try:
        # Promptni tayyorlash (modeldan olish)
        prompt = ai_config.get_prompt(stt_record.transcribed_text)
        system_prompt = ai_config.system_prompt
        
        # Provider ga qarab so'rov yuborish
        if ai_config.api_provider == 'anthropic':
            result = _call_anthropic_api(ai_config, prompt, system_prompt)
        elif ai_config.api_provider == 'openai':
            result = _call_openai_api(ai_config, prompt, system_prompt)
        elif ai_config.api_provider == 'google':
            result = _call_google_api(ai_config, prompt, system_prompt)
        else:
            # Custom API
            result = _call_custom_api(ai_config, prompt, system_prompt)
        
        if result['success']:
            analysis_text = result['data']
            overall_score = _extract_score(analysis_text)
            customer_satisfaction = _extract_satisfaction(analysis_text)
            
            ai_analysis.analysis_text = analysis_text
            ai_analysis.overall_score = overall_score
            ai_analysis.customer_satisfaction = customer_satisfaction
            ai_analysis.api_response = result.get('raw_response')
            ai_analysis.tokens_used = result.get('tokens_used')
            ai_analysis.status = 'completed'
            ai_analysis.analyzed_at = timezone.now()
            ai_analysis.save()
            
            logger.info(f"✓ AI tahlil muvaffaqiyatli: score={overall_score}")
            
            return {
                'success': True,
                'ai_analysis_id': ai_analysis.id,
                'analysis_text': analysis_text,
                'overall_score': overall_score,
                'customer_satisfaction': customer_satisfaction
            }
        else:
            ai_analysis.status = 'failed'
            ai_analysis.error_message = result['error']
            ai_analysis.save()
            return result
    
    except Exception as e:
        error_msg = f"Tahlil xatosi: {str(e)}"
        logger.error(f"✗ AI Analysis Exception: {error_msg}")
        ai_analysis.status = 'failed'
        ai_analysis.error_message = error_msg
        ai_analysis.save()
        return {'success': False, 'error': error_msg}


# ═══════════════════════════════════════════════════════
# AI PROVIDER FUNCTIONS
# ═══════════════════════════════════════════════════════

def _call_openai_api(config, prompt: str, system_prompt: str = '') -> Dict[str, Any]:
    """OpenAI API chaqirish"""
    try:
        try:
            import openai
        except ImportError:
            return {
                'success': False,
                'error': 'OpenAI kutubxonasi o\'rnatilmagan. O\'rnatish: pip install openai'
            }
        
        client = openai.OpenAI(api_key=config.api_key)
        
        response = client.chat.completions.create(
            model=config.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        
        return {
            'success': True,
            'data': response.choices[0].message.content,
            'tokens_used': response.usage.total_tokens,
            'raw_response': response.model_dump()
        }
    except Exception as e:
        return {'success': False, 'error': f'OpenAI xatolik: {str(e)}'}


def _call_anthropic_api(config, prompt: str, system_prompt: str = '') -> Dict[str, Any]:
    """Anthropic API chaqirish"""
    try:
        try:
            import anthropic
        except ImportError:
            return {
                'success': False,
                'error': 'Anthropic kutubxonasi o\'rnatilmagan. O\'rnatish: pip install anthropic'
            }
        
        client = anthropic.Anthropic(api_key=config.api_key)
        
        response = client.messages.create(
            model=config.model_name,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            'success': True,
            'data': response.content[0].text,
            'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            'raw_response': response.model_dump()
        }
    except Exception as e:
        return {'success': False, 'error': f'Anthropic xatolik: {str(e)}'}


def _call_google_api(config, prompt: str, system_prompt: str = '') -> Dict[str, Any]:
    """Google Gemini API chaqirish"""
    try:
        try:
            import google.generativeai as genai
        except ImportError:
            return {
                'success': False,
                'error': 'Google Generative AI kutubxonasi o\'rnatilmagan. O\'rnatish: pip install google-generativeai'
            }
        
        genai.configure(api_key=config.api_key)
        model = genai.GenerativeModel(config.model_name)
        
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = model.generate_content(
            full_prompt,
            generation_config={
                'temperature': config.temperature,
                'max_output_tokens': config.max_tokens,
            }
        )
        
        return {
            'success': True,
            'data': response.text,
            'tokens_used': None,
            'raw_response': {'text': response.text}
        }
    except Exception as e:
        return {'success': False, 'error': f'Google xatolik: {str(e)}'}


def _call_custom_api(config, prompt: str, system_prompt: str = '') -> Dict[str, Any]:
    """Custom API chaqirish (OpenAI-compatible endpoint)"""
    try:
        if not config.api_endpoint:
            return {
                'success': False,
                'error': 'Custom API endpoint kiritilmagan. Admin paneldan sozlang.'
            }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config.api_key}'
        }
        
        payload = {
            'model': config.model_name,
            'messages': [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            'max_tokens': config.max_tokens,
            'temperature': config.temperature
        }
        
        response = requests.post(
            config.api_endpoint,
            json=payload,
            headers=headers,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        
        # OpenAI-compatible response format
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        tokens = data.get('usage', {}).get('total_tokens')
        
        if not content:
            return {'success': False, 'error': 'Custom API bo\'sh javob qaytardi'}
        
        return {
            'success': True,
            'data': content,
            'tokens_used': tokens,
            'raw_response': data
        }
    except Exception as e:
        return {'success': False, 'error': f'Custom API xatolik: {str(e)}'}


# ═══════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════

def _extract_score(text: str) -> Optional[int]:
    """Textdan bahoni ajratib olish"""
    patterns = [
        r'(?:umumiy\s+baho|baho)[\s:]*(\d+)(?:\s*/\s*10)?',
        r'(\d+)\s*/\s*10',
        r'(\d+)\s+ball',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 1 <= score <= 10:
                return score
    return None


def _extract_satisfaction(text: str) -> str:
    """Textdan mijoz qoniqishini ajratib olish"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['qoniqdi', 'mamnun', 'baxtli', 'yaxshi']):
        return 'satisfied'
    elif any(word in text_lower for word in ['qoniqmadi', 'norozi', 'xafa', 'yomon']):
        return 'unsatisfied'
    elif 'neytral' in text_lower:
        return 'neutral'
    return 'unknown'


# ═══════════════════════════════════════════════════════
# COMBINED FUNCTION (STT + AI) 
# ═══════════════════════════════════════════════════════

def process_call_recording(
    audio_url: str,
    uzbekvoice_api_key: str,
    call_record_object=None,
    user=None,
    language: str = 'uz',
    run_diarization: bool = False,
    analyze_with_ai: bool = True
) -> Dict[str, Any]:
    """
    Qo'ng'iroqni to'liq qayta ishlash: STT + AI tahlil
    
    Args:
        audio_url: Audio fayl URL
        uzbekvoice_api_key: UzbekVoice.ai API key
        call_record_object: IPPhoneCall obyekti
        user: Foydalanuvchi
        language: Til
        run_diarization: So'zlovchilarni bo'lish
        analyze_with_ai: AI bilan tahlil qilinsinmi
    
    Returns:
        Dict natija bilan
    """
    
    # 1. STT - Audio ni textga o'girish
    logger.info(f"=== STT + AI Tahlil boshlandi: {audio_url} ===")
    
    stt_result = convert_audio_to_text(
        audio_url=audio_url,
        api_key=uzbekvoice_api_key,
        language=language,
        run_diarization=run_diarization,
        call_record_object=call_record_object,
        processed_by=user
    )
    
    if not stt_result['success']:
        return stt_result
    
    # 2. AI Analysis (agar kerak bo'lsa)
    if analyze_with_ai and stt_result.get('stt_record_id'):
        stt_record = STTRecord.objects.get(id=stt_result['stt_record_id'])
        
        ai_result = analyze_text_with_ai(
            stt_record=stt_record,
            analyzed_by=user
        )
        
        return {
            'success': True,
            'stt_record_id': stt_result['stt_record_id'],
            'transcribed_text': stt_result.get('transcribed_text', ''),
            'ai_analysis_id': ai_result.get('ai_analysis_id'),
            'analysis_text': ai_result.get('analysis_text'),
            'overall_score': ai_result.get('overall_score'),
            'customer_satisfaction': ai_result.get('customer_satisfaction'),
            'ai_error': ai_result.get('error') if not ai_result.get('success') else None,
            'already_processed': stt_result.get('already_processed', False),
            'already_analyzed': ai_result.get('already_analyzed', False),
        }
    
    return stt_result
