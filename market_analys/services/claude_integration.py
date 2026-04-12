# market_analysis/services/claude_integration.py

"""
Claude AI API bilan integratsiya.
TZ bo'yicha to'liq implementatsiya.
"""

import requests
import json
from typing import Dict
from decimal import Decimal


class ClaudeAI:
    """
    Claude AI API bilan ishlash uchun service.
    
    Usage:
        claude = ClaudeAI()
        result = claude.analyze_property_price(property_data, market_data)
    """
    
    API_URL = "https://api.anthropic.com/v1/messages"
    
    def __init__(self):
        """
        Initialization - API key ni AIConfiguration modeldan olish.
        
        Raises:
            ValueError: Agar API key mavjud bo'lmasa
        """
        from home.models import AIConfiguration
        config = AIConfiguration.get_config()
        
        self.api_key = config.api_key
        self.model = config.model or "claude-sonnet-4-20250514"
        
        if not self.api_key:
            raise ValueError(
                "AI API Key topilmadi! "
                "Admin paneldan AI Configuration da API Key ni kiriting."
            )
    
    def analyze_property_price(self, property_data: Dict, market_data: Dict) -> Dict:
        """
        Property narxini AI bilan tahlil qilish.
        
        Args:
            property_data = {
                'etaj': int,
                'xonalar_soni': int,
                'qurilish_turi': str,
                'maydon': int,
                'holat': str,
                'narx_m2': float,
                'umumiy_narx': float
            }
            
            market_data = {
                'arzon': float,
                'bozor': float,
                'qimmat': float
            }
        
        Returns:
            {
                'status': str,  # 'arzon', 'normal', etc.
                'farq_foiz': float,
                'farq_summa': float,
                'tahlil': str,
                'tavsiya': str,
                'confidence': float,
                'bozor_narxi': float,
                'joriy_narxi': float,
            }
        """
        try:
            # 1. Prompt yaratish
            prompt = self._create_analysis_prompt(property_data, market_data)
            
            # 2. Claude API ga request
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01'
            }
            
            payload = {
                'model': self.model,
                'max_tokens': 2000,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            print(f"🤖 Claude AI ga so'rov yuborilmoqda...")
            
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            
            # 3. Response'ni parse qilish
            response_data = response.json()
            
            if 'content' in response_data and len(response_data['content']) > 0:
                analysis_text = response_data['content'][0]['text']
                print(f"✅ AI javob olindi ({len(analysis_text)} belgi)")
                
                # 4. Natijani extract qilish
                result = self._parse_analysis(analysis_text, property_data, market_data)
                return result
            else:
                print("⚠️ AI javob bo'sh, fallback ishlatilmoqda")
                return self._simple_analysis(property_data, market_data)
        
        except requests.RequestException as e:
            print(f"❌ AI API xatolik: {str(e)}")
            print("   Fallback: oddiy matematik tahlil")
            return self._simple_analysis(property_data, market_data)
        
        except Exception as e:
            print(f"❌ AI tahlil xatolik: {str(e)}")
            print("   Fallback: oddiy matematik tahlil")
            return self._simple_analysis(property_data, market_data)
    
    def _create_analysis_prompt(self, property_data: Dict, market_data: Dict) -> str:
        """
        Claude uchun prompt yaratish.
        
        Args:
            property_data: Property ma'lumotlari
            market_data: Bozor narxlari
        
        Returns:
            str: To'liq prompt matni
        """
        prompt = f"""
Siz ko'chmas mulk narxlarini tahlil qiluvchi professional ekspertsiz.

**PROPERTY MA'LUMOTLARI:**
- Qavat: {property_data['etaj']}
- Xonalar soni: {property_data['xonalar_soni']}
- Qurilish turi: {property_data['qurilish_turi']}
- Maydon: {property_data['maydon']} m²
- Holat: {property_data['holat']}
- Joriy narx (1 m² uchun): ${property_data['narx_m2']:,.2f}/m²
- Umumiy narx (butun uy): ${property_data['umumiy_narx']:,.0f}

**BOZOR NARXLARI (1 m² uchun, USD):**
- Arzon narx: ${market_data['arzon']:,.0f}/m² (karobka holati, bo'sh uy)
- Bozor narxi (o'rtacha): ${market_data['bozor']:,.0f}/m²
- Qimmat narx: ${market_data['qimmat']:,.0f}/m² (mebelli, to'liq ta'mirlangan)

**MUHIM:**
- Bozor narxlari 1 m² uchun USD'da berilgan
- Joriy narx ham 1 m² uchun hisoblab olingan
- "Arzon" = karobka (bo'sh uy), "Qimmat" = mebelli/ta'mirlangan
- Property holati: {property_data['holat']} - buni inobatga oling!

**VAZIFA:**
1. Joriy narx (${property_data['narx_m2']:,.2f}/m²) ni bozor narxlari bilan taqqoslang
2. Agar property REMONTLI bo'lsa, "qimmat" narx bilan taqqoslang
3. Agar property REMONTSIZ bo'lsa, "arzon" yoki "bozor" narx bilan taqqoslang
4. Foiz farqini aniq hisoblang: ((joriy - bozor) / bozor) * 100
5. USD summa farqini hisoblang: (joriy - bozor) * maydon
6. Status aniqlang:
   - "juda_arzon" - agar narx bozordan 20%+ past bo'lsa
   - "arzon" - agar narx bozordan 10-20% past bo'lsa
   - "normal" - agar narx bozorga ±10% oralig'ida bo'lsa
   - "qimmat" - agar narx bozordan 10-20% yuqori bo'lsa
   - "juda_qimmat" - agar narx bozordan 20%+ yuqori bo'lsa
7. Batafsil tahlil yozing (150-250 so'z)
8. Sotuvchi va xaridor uchun amaliy tavsiya bering

**JAVOB FORMATI - FAQAT JSON:**
{{
    "status": "arzon",
    "farq_foiz": -15.5,
    "farq_summa": -350000,
    "tahlil": "Batafsil tahlil matni (holat, maydon, narx taqqoslash)...",
    "tavsiya": "Xaridor va sotuvchi uchun tavsiya...",
    "confidence": 85
}}

MUHIM: Faqat JSON javob bering, boshqa matn yo'q!
"""
        return prompt
    
    def _parse_analysis(self, analysis_text: str, property_data: Dict, market_data: Dict) -> Dict:
        """
        Claude response'ni parse qilish.
        
        Args:
            analysis_text: AI dan kelgan matn
            property_data: Property ma'lumotlari
            market_data: Bozor narxlari
        
        Returns:
            dict: Parse qilingan natija
        """
        try:
            # JSON'ni topish
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                print("⚠️ JSON topilmadi, fallback ishlatilmoqda")
                return self._simple_analysis(property_data, market_data)
            
            json_str = analysis_text[json_start:json_end]
            parsed = json.loads(json_str)
            
            # Result dict yaratish
            result = {
                'status': parsed.get('status', 'normal'),
                'farq_foiz': float(parsed.get('farq_foiz', 0)),
                'farq_summa': float(parsed.get('farq_summa', 0)),
                'tahlil': parsed.get('tahlil', ''),
                'tavsiya': parsed.get('tavsiya', ''),
                'confidence': float(parsed.get('confidence', 75)),
                'bozor_narxi': float(market_data['bozor']),
                'joriy_narxi': float(property_data['narx_m2']),
            }
            
            print(f"✅ AI tahlil: {result['status'].upper()} ({result['farq_foiz']:.1f}%)")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse xatolik: {str(e)}")
            return self._simple_analysis(property_data, market_data)
        
        except Exception as e:
            print(f"⚠️ Parse xatolik: {str(e)}")
            return self._simple_analysis(property_data, market_data)
    
    def _simple_analysis(self, property_data: Dict, market_data: Dict) -> Dict:
        """
        Fallback: Oddiy matematik tahlil (AI ishlamasa).
        
        Args:
            property_data: Property ma'lumotlari
            market_data: Bozor narxlari
        
        Returns:
            dict: Oddiy tahlil natijasi
        """
        joriy_narx = float(property_data['narx_m2'])
        maydon = property_data['maydon']
        holat = property_data['holat']  # 'remontli' yoki 'remontsiz'
        
        # Holatga qarab to'g'ri bozor narxini tanlash
        # remontli bo'lsa -> qimmat narx bilan taqqoslash
        # remontsiz bo'lsa -> arzon yoki o'rtacha narx bilan taqqoslash
        if holat == 'remontli':
            # Remontli uyni qimmat narx bilan taqqoslash kerak
            bozor_narx = float(market_data['qimmat'])  # Mebelli, to'liq ta'mirlangan
            print(f"   📊 Remontli uy - qimmat narx bilan taqqoslanmoqda: ${bozor_narx:,.0f}/m²")
        else:
            # Remontsiz uyni arzon yoki o'rtacha narx bilan taqqoslash
            bozor_narx = float(market_data['bozor'])  # O'rtacha
            print(f"   📊 Remontsiz uy - o'rtacha narx bilan taqqoslanmoqda: ${bozor_narx:,.0f}/m²")
        
        # Foiz farqi
        farq_foiz = ((joriy_narx - bozor_narx) / bozor_narx) * 100
        
        # Summa farqi (USD, butun uy uchun)
        farq_summa = (joriy_narx - bozor_narx) * maydon
        
        # Status aniqlash
        if farq_foiz < -20:
            status = 'juda_arzon'
            status_text = 'juda arzon'
        elif farq_foiz < -10:
            status = 'arzon'
            status_text = 'arzon'
        elif farq_foiz < 10:
            status = 'normal'
            status_text = 'bozor narxida'
        elif farq_foiz < 20:
            status = 'qimmat'
            status_text = 'qimmat'
        else:
            status = 'juda_qimmat'
            status_text = 'juda qimmat'
        
        # Tahlil yaratish
        holat_text = "remontli" if holat == 'remontli' else "karobka (bo'sh)"
        tahlil = f"""
Bu {property_data['xonalar_soni']} xonali, {property_data['maydon']} m² maydonga ega, 
{property_data['qurilish_turi']} binodagi, {property_data['etaj']}-qavatdagi, {holat_text} 
uy {status_text} narxda taklif qilinmoqda.

Joriy narx: ${joriy_narx:,.2f}/m² (umumiy: ${property_data['umumiy_narx']:,.0f})
Bozor narxi: ${bozor_narx:,.0f}/m²
Farq: {farq_foiz:.1f}% ({'+' if farq_foiz > 0 else ''}${farq_summa:,.0f})

Bozor narxlari oralig'i: 
- Arzon (karobka): ${market_data['arzon']:,.0f}/m²
- O'rtacha: ${market_data['bozor']:,.0f}/m²
- Qimmat (remontli): ${market_data['qimmat']:,.0f}/m²
        """.strip()
        
        # Tavsiya
        if status in ['juda_arzon', 'arzon']:
            tavsiya = f"""
✅ XARIDOR UCHUN: Bu juda yaxshi taklifdir! Bozor narxidan {abs(farq_foiz):.1f}% arzon. 
Imkoniyatni qo'ldan boy bermang, tezroq qaror qiling.

⚠️ SOTUVCHI UCHUN: Narx pastroq belgilangan. Agar tez sotish kerak bo'lmasa, 
narxni ${bozor_narx:,.0f}/m² atrofida belgilashni tavsiya qilamiz.
            """.strip()
        elif status == 'normal':
            tavsiya = f"""
✅ XARIDOR UCHUN: Narx bozor narxiga mos. Obyektning boshqa parametrlarini (joylashuv, 
holat, qulayliklar) tahlil qiling.

✅ SOTUVCHI UCHUN: Narx to'g'ri belgilangan. Bozor narxida savdo qilish mumkin.
            """.strip()
        else:
            tavsiya = f"""
⚠️ XARIDOR UCHUN: Narx bozor narxidan {farq_foiz:.1f}% qimmat. Savdo qilishni yoki 
boshqa variantlarni ko'rib chiqishni tavsiya qilamiz.

⚠️ SOTUVCHI UCHUN: Narx yuqori belgilangan. Tezroq sotish uchun narxni 
${bozor_narx:,.0f}/m² atrofida tushirishni ko'rib chiqing.
            """.strip()
        
        # Confidence score - maydon farqiga qarab
        confidence = 85  # Base confidence
        
        # Maydon farqi bo'yicha kamaytirish
        maydon_diff = market_data.get('maydon_diff_percent', 0)
        if maydon_diff > 50:
            confidence = 40  # Juda katta farq
        elif maydon_diff > 30:
            confidence = 55  # Katta farq
        elif maydon_diff > 20:
            confidence = 65  # O'rtacha farq
        elif maydon_diff > 10:
            confidence = 75  # Kichik farq
        # else: confidence = 85 (to'liq mos yoki juda yaqin)
        
        return {
            'status': status,
            'bozor_narxi': bozor_narx,
            'joriy_narxi': joriy_narx,
            'farq_foiz': farq_foiz,
            'farq_summa': farq_summa,
            'tahlil': tahlil,
            'tavsiya': tavsiya,
            'confidence': confidence,
        }
