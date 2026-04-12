# market_analys/services/price_analyzer.py
"""
Narx tahlil servisi — CRM API dan olingan dict bilan ishlaydi.
"""

from typing import Dict, Optional
from decimal import Decimal
from ..models import MarketPriceReference, PropertyPriceAnalysis
from .claude_integration import ClaudeAI


# Qurilish turi mapping
BUILDING_TYPE_MAP = {
    'кирпич': 'gishtli', 'кирпичный': 'gishtli', 'gʻisht': 'gishtli',
    "g'isht": 'gishtli', 'gishtli': 'gishtli', 'brick': 'gishtli',
    'панель': 'panelli', 'панельный': 'panelli', 'panel': 'panelli', 'panelli': 'panelli',
    'монолит': 'monolitli', 'монолитный': 'monolitli', 'monolit': 'monolitli', 'monolitli': 'monolitli',
    'блок': 'blokli', 'блочный': 'blokli', 'blok': 'blokli', 'blokli': 'blokli',
}


class PriceAnalyzerAPI:
    """
    CRM API dan olingan dict data bilan ishlaydigan narx tahlil servisi.

    Usage:
        from market_analys.crm_api import CRMAPIClient

        client = CRMAPIClient()
        api_obj = client.get_object(123)
        property_data = client.extract_property_data(api_obj)

        analyzer = PriceAnalyzerAPI()
        analysis = analyzer.analyze_from_api(property_data)
    """

    def __init__(self):
        self.claude = ClaudeAI()

    def analyze_from_api(self, property_data: dict, use_ai: bool = True) -> Optional[PropertyPriceAnalysis]:
        """
        CRM API dan olingan dict bilan tahlil qilish.

        Args:
            property_data: CRMAPIClient.extract_property_data() natijasi
            use_ai: AI ishlatishmi?
        """
        if not property_data:
            return None

        prepared = self._prepare_data(property_data)
        if not prepared:
            print("❌ Property ma'lumotlari to'liq emas")
            return None

        print(f"\n{'='*60}")
        print(f"🔍 TAHLIL: CRM Obyekt #{property_data['id']}")
        print(f"   Etaj: {prepared['etaj']}, Xonalar: {prepared['xonalar_soni']}")
        print(f"   Maydon: {prepared['maydon']} m², Qurilish: {prepared['qurilish_turi']}")
        print(f"   Narx/m²: ${prepared['narx_m2']:,.0f}")

        # Bozor ma'lumotini topish
        market_ref = self._find_market_reference(prepared)
        if not market_ref:
            print("❌ Mos bozor ma'lumoti topilmadi")
            return None

        market_data = market_ref.get_narx_range()
        print(f"✅ Bozor: arzon=${market_data['min']:,.0f} / bozor=${market_data['avg']:,.0f} / qimmat=${market_data['max']:,.0f}")

        # Maydon farqi
        avg_maydon = (market_ref.maydon_min + (market_ref.maydon_max or market_ref.maydon_min)) / 2
        maydon_diff = abs(prepared['maydon'] - avg_maydon) / avg_maydon * 100

        ai_market_data = {
            'arzon': market_data['min'],
            'bozor': market_data['avg'],
            'qimmat': market_data['max'],
            'maydon_diff_percent': maydon_diff,
        }

        # Tahlil
        if use_ai:
            print("🤖 AI bilan tahlil...")
            result = self.claude.analyze_property_price(prepared, ai_market_data)
        else:
            print("🧮 Matematik tahlil...")
            result = self.claude._simple_analysis(prepared, ai_market_data)

        # Saqlash
        analysis = PropertyPriceAnalysis.objects.create(
            property_id=property_data['id'],
            property_type='buildhouse',
            status=result['status'],
            bozor_narxi=Decimal(str(round(result['bozor_narxi'], 2))),
            joriy_narxi=Decimal(str(round(result['joriy_narxi'], 2))),
            farq_foiz=Decimal(str(round(result['farq_foiz'], 2))),
            farq_summa=Decimal(str(round(result['farq_summa'], 0))),
            ai_tahlil=result.get('tahlil', ''),
            tavsiya=result.get('tavsiya', ''),
            confidence_score=Decimal(str(result.get('confidence', 0))),
            matched_reference=market_ref,
            property_snapshot=property_data,
        )

        print(f"✅ Status: {analysis.get_status_display()}, Farq: {analysis.farq_foiz}%")
        return analysis

    def _prepare_data(self, prop: dict) -> Optional[Dict]:
        """API dan olingan datani tahlil formatiga o'girish"""
        etaj = prop.get('floor')
        xonalar = prop.get('rooms_numbers')
        maydon = int(prop.get('total_area', 0) or 0)
        narx = prop.get('price_starting', 0) or 0

        if not all([etaj, xonalar, maydon, narx]):
            return None

        # Qurilish turi
        building_name = (prop.get('type_building', '') or '').lower()
        qurilish_turi = BUILDING_TYPE_MAP.get(building_name, 'gishtli')

        # Holat
        repair_name = (prop.get('state_repair', '') or '').lower()
        holat = 'remontsiz'
        if any(k in repair_name for k in ["ta'mir", 'yaxshi', 'euro', 'dizayn', 'ремонт', 'evro']):
            holat = 'remontli'

        return {
            'id': prop['id'],
            'etaj': etaj,
            'xonalar_soni': xonalar,
            'qurilish_turi': qurilish_turi,
            'maydon': maydon,
            'holat': holat,
            'narx_m2': narx / maydon,
            'umumiy_narx': narx,
        }

    def _find_market_reference(self, data: Dict) -> Optional[MarketPriceReference]:
        """Mos bozor narxini topish"""
        # 1. To'liq mos
        exact = MarketPriceReference.objects.filter(
            etaj=data['etaj'],
            xonalar_soni=data['xonalar_soni'],
            qurilish_turi=data['qurilish_turi'],
            holat=data['holat'],
            maydon_min__lte=data['maydon'],
            maydon_max__gte=data['maydon']
        ).first()

        if exact:
            return exact

        # 2. Eng yaqin maydon
        candidates = MarketPriceReference.objects.filter(
            etaj=data['etaj'],
            xonalar_soni=data['xonalar_soni'],
            qurilish_turi=data['qurilish_turi'],
            holat=data['holat']
        )

        closest = self._find_closest(candidates, data['maydon'])
        if closest:
            return closest

        # 3. Holatsiz
        candidates = MarketPriceReference.objects.filter(
            etaj=data['etaj'],
            xonalar_soni=data['xonalar_soni'],
            qurilish_turi=data['qurilish_turi']
        )

        return self._find_closest(candidates, data['maydon'])

    def _find_closest(self, candidates, maydon):
        """Eng yaqin maydon bo'yicha topish"""
        if not candidates.exists():
            return None

        closest = None
        min_diff = float('inf')
        for c in candidates:
            avg = (c.maydon_min + (c.maydon_max or c.maydon_min)) / 2
            diff = abs(maydon - avg)
            if diff < min_diff:
                min_diff = diff
                closest = c
        return closest
# market_analysis/services/price_analyzer.py

"""
Asosiy narx tahlil logikasi.
PriceAnalyzerAPI — CRM API dan olingan dict data bilan ishlaydi.
"""

from typing import Dict, Optional
from decimal import Decimal
from django.db.models import Q

from ..models import MarketPriceReference, PropertyPriceAnalysis
from .claude_integration import ClaudeAI


# Qurilish turi mapping
BUILDING_TYPE_MAP = {
    'кирпич': 'gishtli', 'кирпичный': 'gishtli', 'gʻisht': 'gishtli',
    "g'isht": 'gishtli', 'gishtli': 'gishtli', 'brick': 'gishtli',
    'панель': 'panelli', 'панельный': 'panelli', 'panel': 'panelli', 'panelli': 'panelli',
    'монолит': 'monolitli', 'монолитный': 'monolitli', 'monolit': 'monolitli', 'monolitli': 'monolitli',
    'блок': 'blokli', 'блочный': 'blokli', 'blok': 'blokli', 'blokli': 'blokli',
}


class PriceAnalyzerAPI:
    """
    CRM API dan olingan dict data bilan ishlaydigan narx tahlil servisi.
    
    Usage:
        from market_analys.crm_api import CRMAPIClient
        
        client = CRMAPIClient()
        api_obj = client.get_object(123)
        property_data = client.extract_property_data(api_obj)
        
        analyzer = PriceAnalyzerAPI()
        analysis = analyzer.analyze_from_api(property_data)
    """

    def __init__(self):
        self.claude = ClaudeAI()

    def analyze_from_api(self, property_data: dict, use_ai: bool = True) -> Optional[PropertyPriceAnalysis]:
        """
        CRM API dan olingan dict bilan tahlil qilish.
        
        Args:
            property_data: CRMAPIClient.extract_property_data() natijasi
            use_ai: AI ishlatishmi?
        """
        if not property_data:
            return None

        prepared = self._prepare_data(property_data)
        if not prepared:
            print("❌ Property ma'lumotlari to'liq emas")
            return None

        print(f"\n{'='*60}")
        print(f"🔍 TAHLIL: CRM Obyekt #{property_data['id']}")
        print(f"   Etaj: {prepared['etaj']}, Xonalar: {prepared['xonalar_soni']}")
        print(f"   Maydon: {prepared['maydon']} m², Qurilish: {prepared['qurilish_turi']}")
        print(f"   Narx/m²: ${prepared['narx_m2']:,.0f}")

        # Bozor ma'lumotini topish
        market_ref = self._find_market_reference(prepared)
        if not market_ref:
            print("❌ Mos bozor ma'lumoti topilmadi")
            return None

        market_data = market_ref.get_narx_range()
        print(f"✅ Bozor: arzon=${market_data['min']:,.0f} / bozor=${market_data['avg']:,.0f} / qimmat=${market_data['max']:,.0f}")

        # Maydon farqi
        avg_maydon = (market_ref.maydon_min + (market_ref.maydon_max or market_ref.maydon_min)) / 2
        maydon_diff = abs(prepared['maydon'] - avg_maydon) / avg_maydon * 100

        ai_market_data = {
            'arzon': market_data['min'],
            'bozor': market_data['avg'],
            'qimmat': market_data['max'],
            'maydon_diff_percent': maydon_diff,
        }

        # Tahlil
        if use_ai:
            print("🤖 AI bilan tahlil...")
            result = self.claude.analyze_property_price(prepared, ai_market_data)
        else:
            print("🧮 Matematik tahlil...")
            result = self.claude._simple_analysis(prepared, ai_market_data)

        # Saqlash
        analysis = PropertyPriceAnalysis.objects.create(
            property_id=property_data['id'],
            property_type='buildhouse',
            status=result['status'],
            bozor_narxi=Decimal(str(round(result['bozor_narxi'], 2))),
            joriy_narxi=Decimal(str(round(result['joriy_narxi'], 2))),
            farq_foiz=Decimal(str(round(result['farq_foiz'], 2))),
            farq_summa=Decimal(str(round(result['farq_summa'], 0))),
            ai_tahlil=result.get('tahlil', ''),
            tavsiya=result.get('tavsiya', ''),
            confidence_score=Decimal(str(result.get('confidence', 0))),
            matched_reference=market_ref,
            property_snapshot=property_data,
        )

        print(f"✅ Status: {analysis.get_status_display()}, Farq: {analysis.farq_foiz}%")
        return analysis

    def _prepare_data(self, prop: dict) -> Optional[Dict]:
        """API dan olingan datani tahlil formatiga o'girish"""
        etaj = prop.get('floor')
        xonalar = prop.get('rooms_numbers')
        maydon = int(prop.get('total_area', 0))
        narx = prop.get('price_starting', 0)

        if not all([etaj, xonalar, maydon, narx]):
            return None

        # Qurilish turi
        building_name = (prop.get('type_building', '') or '').lower()
        qurilish_turi = BUILDING_TYPE_MAP.get(building_name, 'gishtli')

        # Holat
        repair_name = (prop.get('state_repair', '') or '').lower()
        holat = 'remontsiz'
        if any(k in repair_name for k in ["ta'mir", 'yaxshi', 'euro', 'dizayn', 'ремонт', 'evro']):
            holat = 'remontli'

        return {
            'id': prop['id'],
            'etaj': etaj,
            'xonalar_soni': xonalar,
            'qurilish_turi': qurilish_turi,
            'maydon': maydon,
            'holat': holat,
            'narx_m2': narx / maydon,
            'umumiy_narx': narx,
        }

    def _find_market_reference(self, data: Dict) -> Optional[MarketPriceReference]:
        """Mos bozor narxini topish"""
        # 1. To'liq mos
        exact = MarketPriceReference.objects.filter(
            etaj=data['etaj'],
            xonalar_soni=data['xonalar_soni'],
            qurilish_turi=data['qurilish_turi'],
            holat=data['holat'],
            maydon_min__lte=data['maydon'],
            maydon_max__gte=data['maydon']
        ).first()

        if exact:
            return exact

        # 2. Eng yaqin maydon
        candidates = MarketPriceReference.objects.filter(
            etaj=data['etaj'],
            xonalar_soni=data['xonalar_soni'],
            qurilish_turi=data['qurilish_turi'],
            holat=data['holat']
        )

        if candidates.exists():
            closest = None
            min_diff = float('inf')
            for c in candidates:
                avg = (c.maydon_min + (c.maydon_max or c.maydon_min)) / 2
                diff = abs(data['maydon'] - avg)
                if diff < min_diff:
                    min_diff = diff
                    closest = c
            if closest:
                return closest

        # 3. Holatsiz
        candidates = MarketPriceReference.objects.filter(
            etaj=data['etaj'],
            xonalar_soni=data['xonalar_soni'],
            qurilish_turi=data['qurilish_turi']
        )

        if candidates.exists():
            closest = None
            min_diff = float('inf')
            for c in candidates:
                avg = (c.maydon_min + (c.maydon_max or c.maydon_min)) / 2
                diff = abs(data['maydon'] - avg)
                if diff < min_diff:
                    min_diff = diff
                    closest = c
            return closest

        return None
    """
    Narx tahlil servisi - HAM CRM HAM OLX obyektlar uchun.
    
    Usage:
        analyzer = PriceAnalyzer()
        
        # CRM property uchun
        from home.models import BuildHouse
        house = BuildHouse.objects.get(id=123)
        analysis = analyzer.analyze_property(house, use_ai=True)
        
        # OLX property uchun
        from market_analysis.models import OLXProperty
        olx = OLXProperty.objects.get(id=456)
        analysis = analyzer.analyze_property(olx, use_ai=True)
    """
    
    # Qurilish turi mapping - BuildHouse -> MarketPriceReference
    BUILDING_TYPE_MAP = {
        # BuildHouse type_building nomlaridan MarketPriceReference ga
        'кирпич': 'gishtli',
        'кирпичный': 'gishtli',
        'gʻisht': 'gishtli',
        'g\'isht': 'gishtli',
        'gishtli': 'gishtli',
        'brick': 'gishtli',
        
        'панель': 'panelli',
        'панельный': 'panelli',
        'panel': 'panelli',
        'panelli': 'panelli',
        
        'монолит': 'monolitli',
        'монолитный': 'monolitli',
        'monolit': 'monolitli',
        'monolitli': 'monolitli',
        'monolith': 'monolitli',
        
        'блок': 'blokli',
        'блочный': 'blokli',
        'blok': 'blokli',
        'blokli': 'blokli',
        'block': 'blokli',
    }
    
    def __init__(self):
        """Initialize ClaudeAI instance"""
        self.claude = ClaudeAI()
    
    def analyze_property(self, property_obj, use_ai: bool = True) -> Optional[PropertyPriceAnalysis]:
        """
        Bitta property'ni tahlil qilish.
        
        Args:
            property_obj: BuildHouse yoki OLXProperty instance
            use_ai: bool - AI ishlatishmi?
        
        Returns:
            PropertyPriceAnalysis instance yoki None
        """
        model_name = property_obj.__class__.__name__
        print(f"\n{'='*60}")
        print(f"🔍 TAHLIL BOSHLANDI: {model_name} #{property_obj.id}")
        print(f"{'='*60}")
        
        # 1. Property ma'lumotlarini tayyorlash
        property_data = self._prepare_property_data(property_obj)
        
        if not property_data:
            print("❌ Property ma'lumotlari to'liq emas")
            return None
        
        print(f"✅ Property ma'lumotlari tayyorlandi:")
        print(f"   Etaj: {property_data['etaj']}")
        print(f"   Xonalar: {property_data['xonalar_soni']}")
        print(f"   Qurilish: {property_data['qurilish_turi']}")
        print(f"   Maydon: {property_data['maydon']} m²")
        print(f"   Holat: {property_data['holat']}")
        print(f"   Narx/m²: ${property_data['narx_m2']:,.0f}")
        
        # 2. Bozor ma'lumotini topish
        market_ref = self._find_market_reference(property_data)
        
        if not market_ref:
            print("❌ Mos bozor ma'lumoti topilmadi")
            return None
        
        print(f"✅ Bozor ma'lumoti topildi:")
        print(f"   {market_ref}")
        
        # Maydon farqini hisoblash (confidence uchun)
        property_maydon = property_data['maydon']
        if market_ref.maydon_max:
            avg_market_maydon = (market_ref.maydon_min + market_ref.maydon_max) / 2
        else:
            avg_market_maydon = market_ref.maydon_min
        
        maydon_diff_percent = abs(property_maydon - avg_market_maydon) / avg_market_maydon * 100
        print(f"   Maydon farqi: {maydon_diff_percent:.1f}%")
        
        market_data_raw = market_ref.get_narx_range()
        print(f"   Arzon: ${market_data_raw['min']:,.0f}/m²")
        print(f"   Bozor: ${market_data_raw['avg']:,.0f}/m²")
        print(f"   Qimmat: ${market_data_raw['max']:,.0f}/m²")
        
        # Market data ni ClaudeAI formatiga o'tkazish
        market_data = {
            'arzon': market_data_raw['min'],
            'bozor': market_data_raw['avg'],
            'qimmat': market_data_raw['max'],
            'maydon_diff_percent': maydon_diff_percent,  # Confidence uchun
        }
        
        # 3. Tahlil qilish (AI yoki oddiy)
        if use_ai:
            print("\n🤖 AI bilan tahlil qilinmoqda...")
            analysis_result = self.claude.analyze_property_price(property_data, market_data)
        else:
            print("\n🧮 Oddiy matematik tahlil...")
            analysis_result = self._simple_comparison(property_data, market_data)
        
        # 4. Natijani saqlash
        analysis = self._save_analysis(property_obj, analysis_result, market_ref)
        
        print(f"\n✅ TAHLIL TUGADI:")
        print(f"   Status: {analysis.get_status_display()}")
        print(f"   Farq: {analysis.farq_foiz:.1f}%")
        print(f"   Confidence: {analysis.confidence_score}%")
        print(f"{'='*60}\n")
        
        return analysis
    
    def _prepare_property_data(self, property_obj) -> Optional[Dict]:
        """
        Property obyektidan kerakli ma'lumotlarni extract qilish.
        HAM BuildHouse HAM OLXProperty bilan ishlaydi.
        
        Returns:
            {
                'id': int,
                'etaj': int,
                'xonalar_soni': int,
                'qurilish_turi': str,  # normalized
                'maydon': int,
                'holat': str,  # 'remontli' yoki 'remontsiz'
                'narx_m2': float,
                'umumiy_narx': float,
            }
        """
        model_name = property_obj.__class__.__name__
        
        try:
            if model_name == 'BuildHouse':
                return self._prepare_buildhouse_data(property_obj)
            elif model_name == 'OLXProperty':
                return self._prepare_olx_data(property_obj)
            else:
                print(f"❌ Noma'lum model: {model_name}")
                return None
        except Exception as e:
            print(f"❌ Ma'lumot tayyorlashda xatolik: {str(e)}")
            return None
    
    def _prepare_buildhouse_data(self, house) -> Optional[Dict]:
        """BuildHouse obyektidan ma'lumot olish"""
        # Etaj
        etaj = house.floor
        if not etaj:
            return None
        
        # Xonalar
        xonalar_soni = house.rooms_numbers
        if not xonalar_soni:
            return None
        
        # Maydon
        maydon = int(house.total_area) if house.total_area else None
        if not maydon:
            return None
        
        # Qurilish turi
        qurilish_turi = 'gishtli'  # default
        if house.type_building:
            building_name = house.type_building.name.lower()
            qurilish_turi = self.BUILDING_TYPE_MAP.get(building_name, 'gishtli')
        
        # Holat (ta'mir)
        holat = 'remontsiz'  # default
        if house.state_repair:
            repair_name = house.state_repair.name.lower()
            # Agar "ta'mir", "yaxshi", "euro", "dizayn" so'zlari bo'lsa
            if any(keyword in repair_name for keyword in ['ta\'mir', 'yaxshi', 'euro', 'dizayn', 'ремонт']):
                holat = 'remontli'
        
        # Narx
        narx = house.price_owner if house.price_owner else 0
        if narx <= 0:
            return None
        
        # Narx USD'da
        narx_m2 = narx / maydon
        
        return {
            'id': house.id,
            'etaj': etaj,
            'xonalar_soni': xonalar_soni,
            'qurilish_turi': qurilish_turi,
            'maydon': maydon,
            'holat': holat,
            'narx_m2': narx_m2,
            'umumiy_narx': narx,
        }
    
    def _prepare_olx_data(self, olx) -> Optional[Dict]:
        """OLXProperty obyektidan ma'lumot olish"""
        # Etaj
        etaj = olx.floor
        if not etaj:
            return None
        
        # Xonalar
        xonalar_soni = olx.rooms
        if not xonalar_soni:
            return None
        
        # Maydon
        maydon = int(olx.area_total) if olx.area_total else None
        if not maydon:
            return None
        
        # Qurilish turi
        qurilish_turi = 'gishtli'  # default
        if olx.building_type:
            building_name = olx.building_type.lower()
            qurilish_turi = self.BUILDING_TYPE_MAP.get(building_name, 'gishtli')
        
        # Holat
        holat = 'remontsiz'  # default
        if olx.repair_state:
            repair_name = olx.repair_state.lower()
            if any(keyword in repair_name for keyword in ['ta\'mir', 'yaxshi', 'euro', 'dizayn', 'ремонт']):
                holat = 'remontli'
        
        # Narx (USD dan so'mga)
        USD_TO_UZS = 12700  # Update this regularly
        narx_usd = float(olx.price_usd) if olx.price_usd else 0
        if narx_usd <= 0:
            return None
        
        narx_uzs = narx_usd * USD_TO_UZS
        narx_m2 = narx_uzs / maydon
        
        return {
            'id': olx.id,
            'etaj': etaj,
            'xonalar_soni': xonalar_soni,
            'qurilish_turi': qurilish_turi,
            'maydon': maydon,
            'holat': holat,
            'narx_m2': narx_m2,
            'umumiy_narx': narx_uzs,
        }
    
    def _find_market_reference(self, property_data: Dict) -> Optional[MarketPriceReference]:
        """
        Property uchun mos bozor ma'lumotini topish.
        
        Algorithm:
            1. To'liq mos qidiruv
            2. Agar topilmasa, eng yaqinini topish
        """
        team = None  # Team'ni property_obj dan olish kerak (keyingi versiyada)
        
        # 1. To'liq mos qidiruv
        exact_match = MarketPriceReference.objects.filter(
            # team=team,  # TODO: team filter qo'shish
            etaj=property_data['etaj'],
            xonalar_soni=property_data['xonalar_soni'],
            qurilish_turi=property_data['qurilish_turi'],
            holat=property_data['holat'],
            maydon_min__lte=property_data['maydon'],
            maydon_max__gte=property_data['maydon']
        ).first()
        
        if exact_match:
            print(f"   ✅ To'liq mos ma'lumot topildi")
            return exact_match
        
        # 2. Eng yaqinini topish (maydon bo'yicha)
        print(f"   🔍 Eng yaqin maydon qidirilmoqda...")
        
        # Barcha mos keluvchilarni olish
        candidates = MarketPriceReference.objects.filter(
            # team=team,
            etaj=property_data['etaj'],
            xonalar_soni=property_data['xonalar_soni'],
            qurilish_turi=property_data['qurilish_turi'],
            holat=property_data['holat']
        )
        
        if candidates.exists():
            # Maydon bo'yicha eng yaqinni topish
            property_maydon = property_data['maydon']
            closest = None
            min_diff = float('inf')
            
            for candidate in candidates:
                # O'rtacha maydon
                if candidate.maydon_max:
                    avg_maydon = (candidate.maydon_min + candidate.maydon_max) / 2
                else:
                    avg_maydon = candidate.maydon_min
                
                # Farq
                diff = abs(property_maydon - avg_maydon)
                
                if diff < min_diff:
                    min_diff = diff
                    closest = candidate
            
            if closest:
                print(f"   ✅ Eng yaqin maydon topildi: {closest.maydon_min}-{closest.maydon_max}m² (farq: {min_diff:.0f}m²)")
                return closest
        
        # 3. Holatsiz qidiruv (remontli/remontsiz farqsiz)
        print(f"   🔍 Holatsiz qidirilmoqda...")
        
        candidates = MarketPriceReference.objects.filter(
            # team=team,
            etaj=property_data['etaj'],
            xonalar_soni=property_data['xonalar_soni'],
            qurilish_turi=property_data['qurilish_turi']
        )
        
        if candidates.exists():
            # Maydon bo'yicha eng yaqinni topish
            property_maydon = property_data['maydon']
            closest = None
            min_diff = float('inf')
            
            for candidate in candidates:
                # O'rtacha maydon
                if candidate.maydon_max:
                    avg_maydon = (candidate.maydon_min + candidate.maydon_max) / 2
                else:
                    avg_maydon = candidate.maydon_min
                
                # Farq
                diff = abs(property_maydon - avg_maydon)
                
                if diff < min_diff:
                    min_diff = diff
                    closest = candidate
            
            if closest:
                print(f"   ⚠️ Holat farqi bilan topildi: {closest.maydon_min}-{closest.maydon_max}m² (farq: {min_diff:.0f}m²)")
                return closest
        
        return None
    
    def _simple_comparison(self, property_data: Dict, market_data: Dict) -> Dict:
        """
        Oddiy matematik taqqoslash (AI'siz).
        Claude AI'ning _simple_analysis() metodi bilan bir xil.
        """
        return self.claude._simple_analysis(property_data, market_data)
    
    def _save_analysis(
        self, 
        property_obj, 
        analysis_result: Dict, 
        market_ref: MarketPriceReference
    ) -> PropertyPriceAnalysis:
        """
        Tahlil natijasini database'ga saqlash.
        
        Args:
            property_obj: BuildHouse yoki OLXProperty instance
            analysis_result: Tahlil natijasi
            market_ref: Mos kelgan MarketPriceReference
        
        Returns:
            PropertyPriceAnalysis instance
        """
        content_type = ContentType.objects.get_for_model(property_obj)
        team = property_obj.team if hasattr(property_obj, 'team') else None
        
        analysis = PropertyPriceAnalysis.objects.create(
            team=team,
            content_type=content_type,
            object_id=property_obj.id,
            property_id=property_obj.id,
            status=analysis_result['status'],
            bozor_narxi=Decimal(str(round(analysis_result['bozor_narxi'], 2))),
            joriy_narxi=Decimal(str(round(analysis_result['joriy_narxi'], 2))),
            farq_foiz=Decimal(str(round(analysis_result['farq_foiz'], 2))),
            farq_summa=Decimal(str(round(analysis_result['farq_summa'], 0))),  # Desimal qismni olib tashlash
            ai_tahlil=analysis_result.get('tahlil', ''),
            tavsiya=analysis_result.get('tavsiya', ''),
            confidence_score=Decimal(str(analysis_result['confidence'])),
            matched_reference=market_ref,
        )
        
        print(f"💾 Tahlil saqlandi: ID {analysis.id}")
        
        return analysis
    
    def bulk_analyze(self, property_queryset, use_ai: bool = True) -> Dict:
        """
        Ko'p propertylarni bir vaqtda tahlil qilish.
        
        Args:
            property_queryset: Django QuerySet (BuildHouse yoki OLXProperty)
            use_ai: bool - AI ishlatishmi?
        
        Returns:
            {
                'total': int,
                'analyzed': int,
                'failed': int,
                'statuses': {
                    'juda_arzon': int,
                    'arzon': int,
                    'normal': int,
                    'qimmat': int,
                    'juda_qimmat': int,
                }
            }
        """
        total = property_queryset.count()
        analyzed = 0
        failed = 0
        statuses = {
            'juda_arzon': 0,
            'arzon': 0,
            'normal': 0,
            'qimmat': 0,
            'juda_qimmat': 0,
        }
        
        print(f"\n🚀 BULK TAHLIL BOSHLANDI: {total} ta obyekt")
        print("="*60)
        
        for i, property_obj in enumerate(property_queryset, 1):
            print(f"\n[{i}/{total}] ", end='')
            
            try:
                analysis = self.analyze_property(property_obj, use_ai=use_ai)
                
                if analysis:
                    analyzed += 1
                    statuses[analysis.status] += 1
                else:
                    failed += 1
                    
            except Exception as e:
                print(f"❌ Xatolik: {str(e)}")
                failed += 1
        
        print("\n" + "="*60)
        print(f"✅ BULK TAHLIL TUGADI")
        print(f"   Jami: {total}")
        print(f"   Muvaffaqiyatli: {analyzed}")
        print(f"   Xatolik: {failed}")
        print(f"\n   STATUS STATISTIKASI:")
        for status, count in statuses.items():
            if count > 0:
                print(f"   {status.upper()}: {count}")
        print("="*60 + "\n")
        
        return {
            'total': total,
            'analyzed': analyzed,
            'failed': failed,
            'statuses': statuses
        }
