# employee_analytics/services.py

"""
STT (Speech-to-Text) va AI Analysis xizmatlari
"""

import requests
import os
from typing import Dict, Any, Optional
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from .models import AIConfiguration, STTRecord, AIAnalysis


# ═══════════════════════════════════════════════════════
# 1. UZBEKVOICE.AI STT SERVICE
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
        run_diarization: So'zlovchilarni bo'lish (true, false, phone)
        blocking: Sinxron (true) yoki asinxron (false)
        call_record_object: Qo'ng'iroq obyekti (SipuniCallRecord yoki SIPCall)
        processed_by: Kim tomonidan (CustomUser)
    
    Returns:
        Dict natija bilan
    """
    
    # Avval mavjud STTRecord ni tekshirish (duplicate yaratmaslik)
    stt_record = None
    if call_record_object:
        content_type = ContentType.objects.get_for_model(call_record_object)
        
        # Allaqachon STT yozuv borligini tekshirish
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
            if stt_record:
                # Textni extract qilish
                transcribed_text = ""
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
            
            return {
                'success': True,
                'data': result,
                'stt_record_id': stt_record.id if stt_record else None,
                'transcribed_text': transcribed_text if stt_record else None
            }
        else:
            error_msg = f"API xatolik: {response.status_code} - {response.text}"
            
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
        
        if stt_record:
            stt_record.status = 'failed'
            stt_record.error_message = error_msg
            stt_record.save()
        
        return {
            'success': False,
            'error': error_msg
        }
    
    except Exception as e:
        error_msg = f"Xatolik: {str(e)}"
        
        if stt_record:
            stt_record.status = 'failed'
            stt_record.error_message = error_msg
            stt_record.save()
        
        return {
            'success': False,
            'error': error_msg
        }


# ═══════════════════════════════════════════════════════
# 2. AI ANALYSIS SERVICE
# ═══════════════════════════════════════════════════════

def analyze_text_with_ai(
    stt_record: STTRecord,
    ai_config: Optional[AIConfiguration] = None,
    analyzed_by=None
) -> Dict[str, Any]:
    """
    STT natijasini AI bilan tahlil qilish
    
    Args:
        stt_record: STTRecord obyekti
        ai_config: AIConfiguration (agar berilmasa default ishlatiladi)
        analyzed_by: Kim tomonidan (CustomUser)
    
    Returns:
        Dict natija bilan
    """
    
    # AI config olish
    if not ai_config:
        ai_config = AIConfiguration.objects.filter(
            is_active=True, is_default=True
        ).first()
        
        if not ai_config:
            ai_config = AIConfiguration.objects.filter(is_active=True).first()
    
    if not ai_config:
        return {
            'success': False,
            'error': 'Faol AI konfiguratsiya topilmadi'
        }
    
    # AIAnalysis tekshirish - agar allaqachon tahlil qilingan bo'lsa, qayta tahlil qilmaslik
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
            'message': 'Bu suhbat allaqachon tahlil qilingan. Mavjud tahlil qaytarildi.'
        }
    
    # Yangi AIAnalysis yaratish
    ai_analysis = AIAnalysis.objects.create(
        stt_record=stt_record,
        ai_config=ai_config,
        status='processing',
        analyzed_by=analyzed_by
    )
    
    try:
        # Promptni tayyorlash
        prompt = ai_config.analysis_prompt_template.replace(
            '{{text}}', stt_record.transcribed_text
        )
        
        # API provider ga qarab so'rov yuborish
        if ai_config.api_provider == 'openai':
            result = _call_openai_api(ai_config, prompt)
        elif ai_config.api_provider == 'anthropic':
            result = _call_anthropic_api(ai_config, prompt)
        elif ai_config.api_provider == 'google':
            result = _call_google_api(ai_config, prompt)
        elif ai_config.api_provider == 'custom':
            result = _call_custom_api(ai_config, prompt)
        else:
            return {
                'success': False,
                'error': f'Provider "{ai_config.api_provider}" qo\'llab-quvvatlanmaydi'
            }
        
        if result['success']:
            # Natijani parse qilish va saqlash
            analysis_text = result['data']
            
            # Strukturlangan ma'lumotlarni extract qilish
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
        ai_analysis.status = 'failed'
        ai_analysis.error_message = error_msg
        ai_analysis.save()
        
        return {
            'success': False,
            'error': error_msg
        }


# ═══════════════════════════════════════════════════════
# 3. AI PROVIDER FUNCTIONS
# ═══════════════════════════════════════════════════════

def _call_openai_api(config: AIConfiguration, prompt: str) -> Dict[str, Any]:
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
                {"role": "system", "content": config.system_prompt},
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
        return {
            'success': False,
            'error': f'OpenAI xatolik: {str(e)}'
        }


def _call_anthropic_api(config: AIConfiguration, prompt: str) -> Dict[str, Any]:
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
            system=config.system_prompt,
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
        return {
            'success': False,
            'error': f'Anthropic xatolik: {str(e)}'
        }


def _call_google_api(config: AIConfiguration, prompt: str) -> Dict[str, Any]:
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
        
        full_prompt = f"{config.system_prompt}\n\n{prompt}"
        
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
            'tokens_used': None,  # Gemini token count qaytarmaydi
            'raw_response': {'text': response.text}
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Google xatolik: {str(e)}'
        }


def _call_custom_api(config: AIConfiguration, prompt: str) -> Dict[str, Any]:
    """Custom API chaqirish"""
    if not config.api_endpoint:
        return {
            'success': False,
            'error': 'Custom API uchun endpoint ko\'rsatilmagan'
        }
    
    try:
        response = requests.post(
            config.api_endpoint,
            headers={
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'prompt': prompt,
                'system_prompt': config.system_prompt,
                'max_tokens': config.max_tokens,
                'temperature': config.temperature
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'data': result.get('text', str(result)),
                'tokens_used': result.get('tokens_used'),
                'raw_response': result
            }
        else:
            return {
                'success': False,
                'error': f'Custom API xatolik: {response.status_code} - {response.text}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Custom API xatolik: {str(e)}'
        }


# ═══════════════════════════════════════════════════════
# 4. HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════

def _extract_score(text: str) -> Optional[int]:
    """Textdan bahoni ajratib olish"""
    import re
    
    # Patternlar: "Umumiy baho: 8/10", "Baho: 7", "8 ball" va h.k.
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
# 5. COMBINED FUNCTION (STT + AI)
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
        call_record_object: Qo'ng'iroq obyekti
        user: Foydalanuvchi
        language: Til
        run_diarization: So'zlovchilarni bo'lish
        analyze_with_ai: AI bilan tahlil qilinsinmi
    
    Returns:
        Dict natija bilan
    """
    
    # 1. STT
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
            'transcribed_text': stt_result['transcribed_text'],
            'ai_analysis_id': ai_result.get('ai_analysis_id'),
            'analysis_text': ai_result.get('analysis_text'),
            'overall_score': ai_result.get('overall_score'),
            'ai_error': ai_result.get('error') if not ai_result['success'] else None
        }
    
    return stt_result
