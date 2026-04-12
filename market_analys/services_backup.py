# market_analysis/services.py - TO'LIQ YANGILANGAN

from typing import List, Dict, Optional
from decimal import Decimal
from django.db.models import Q
from home.models import BuildHouse
from .models import OLXProperty, ComparisonResult


class PropertyMatcher:
    """OLX va CRM obyektlarini taqqoslash servisi"""
    
    WEIGHTS = {
        'address': 0.30,
        'rooms': 0.25,
        'area': 0.20,
        'floor': 0.10,
        'building_type': 0.10,
        'repair': 0.05
    }
    
    MIN_SIMILARITY = 70
    TOP_N = 3
    PRICE_ALERT_PERCENT = -5
    
    def find_matches_for_olx(self, olx_property: OLXProperty) -> List[ComparisonResult]:
        """Bitta OLX obyekt uchun CRM dan eng o'xshashlarini topish"""
        candidates = self._pre_filter(olx_property)
        
        if not candidates.exists():
            print(f"❌ {olx_property.title[:50]} uchun nomzodlar topilmadi")
            return []
        
        print(f"🔍 {candidates.count()} ta nomzod topildi: {olx_property.title[:50]}")
        
        comparisons = []
        for crm_obj in candidates:
            similarity = self.calculate_similarity(olx_property, crm_obj)
            
            if similarity >= self.MIN_SIMILARITY:
                # Narx - PRICE_OWNER ishlatamiz
                price_diff = olx_property.price_usd - crm_obj.price_owner
                price_diff_percent = (price_diff / crm_obj.price_owner) * 100
                
                comparisons.append({
                    'crm_object': crm_obj,
                    'similarity': similarity,
                    'price_diff': price_diff,
                    'price_diff_percent': price_diff_percent,
                    'match_details': self._get_match_details(olx_property, crm_obj, similarity)
                })
        
        if not comparisons:
            print(f"⚠️ {self.MIN_SIMILARITY}%+ o'xshash obyektlar topilmadi")
            return []
        
        comparisons.sort(key=lambda x: (x['similarity'], -x['price_diff']), reverse=True)
        top_matches = comparisons[:self.TOP_N]
        
        results = []
        for match in top_matches:
            result, created = ComparisonResult.objects.update_or_create(
                olx_property=olx_property,
                crm_object=match['crm_object'],
                defaults={
                    'similarity_score': match['similarity'],
                    'price_difference_usd': match['price_diff'],
                    'price_difference_percent': match['price_diff_percent'],
                    'status': self._get_status(match['price_diff_percent']),
                    'match_details': match['match_details']
                }
            )
            results.append(result)
            
            if created and match['price_diff_percent'] < self.PRICE_ALERT_PERCENT:
                print(f"🔴 ARZON! ${olx_property.price_usd} vs ${match['crm_object'].price_owner} "
                      f"({match['similarity']:.1f}% o'xshash)")
        
        return results
    
    def _pre_filter(self, olx: OLXProperty):
        """Tez filter - faqat o'xshash parametrli uylarni qaytarish"""
        if not olx.rooms or not olx.area_total:
            return BuildHouse.objects.none()
        
        area_min = olx.area_total * Decimal('0.80')
        area_max = olx.area_total * Decimal('1.20')
        
        filters = Q(
            team=olx.team,
            address__full_address__icontains=olx.city,
            rooms_numbers=olx.rooms,  # BuildHouse da rooms_numbers
            total_area__gte=area_min,  # BuildHouse da total_area
            total_area__lte=area_max,
            in_site=True,  # is_active o'rniga
            price_owner__gt=0  # price o'rniga price_owner
        )
        
        if olx.floor:
            filters &= Q(
                floor__gte=olx.floor - 2,
                floor__lte=olx.floor + 2
            )
        
        return BuildHouse.objects.filter(filters).select_related(
            'address', 'user', 'type_building', 'state_repair'
        )
    
    def calculate_similarity(self, olx: OLXProperty, crm: BuildHouse) -> float:
        """O'xshashlik foizini hisoblash (0-100%)"""
        scores = {}
        
        scores['address'] = self._match_address(olx, crm)
        scores['rooms'] = 100.0 if olx.rooms == crm.rooms_numbers else 0.0
        scores['area'] = self._match_area(olx, crm)
        scores['floor'] = self._match_floor(olx, crm)
        scores['building_type'] = self._match_building_type(olx, crm)
        scores['repair'] = self._match_repair(olx, crm)
        
        total = sum(scores[key] * self.WEIGHTS[key] for key in scores)
        return round(total, 2)
    
    def _match_address(self, olx: OLXProperty, crm: BuildHouse) -> float:
        """Manzil o'xshashligi"""
        olx_addr = olx.address_text.lower()
        crm_addr = crm.address.full_address.lower() if crm.address else ""
        
        olx_words = set(olx_addr.split())
        crm_words = set(crm_addr.split())
        
        if not olx_words or not crm_words:
            return 50.0
        
        intersection = len(olx_words & crm_words)
        union = len(olx_words | crm_words)
        
        return (intersection / union) * 100 if union > 0 else 0.0
    
    def _match_area(self, olx: OLXProperty, crm: BuildHouse) -> float:
        """Maydon o'xshashligi"""
        if not olx.area_total or not crm.total_area:
            return 50.0
        
        diff = abs(olx.area_total - crm.total_area)
        diff_percent = (diff / crm.total_area) * 100
        
        if diff_percent <= 5:
            return 100.0
        elif diff_percent <= 10:
            return 80.0
        elif diff_percent <= 20:
            return 50.0
        else:
            return 20.0
    
    def _match_floor(self, olx: OLXProperty, crm: BuildHouse) -> float:
        """Qavat o'xshashligi"""
        if not olx.floor or not crm.floor:
            return 50.0
        
        if olx.floor == crm.floor:
            return 100.0
        elif abs(olx.floor - crm.floor) == 1:
            return 70.0
        elif abs(olx.floor - crm.floor) == 2:
            return 40.0
        else:
            return 10.0
    
    def _match_building_type(self, olx: OLXProperty, crm: BuildHouse) -> float:
        """Bino turi o'xshashligi"""
        if not olx.building_type:
            return 50.0
        
        if not crm.type_building:
            return 50.0
        
        olx_type = olx.building_type.lower()
        crm_type = crm.type_building.name.lower()
        
        keywords = {
            'gʻisht': ['кирпич', 'g\'isht', 'ghisht', 'brick', 'gʻisht'],
            'panel': ['панель', 'panel'],
            'monolit': ['монолит', 'monolit', 'monolith'],
        }
        
        for key, variants in keywords.items():
            olx_match = any(v in olx_type for v in variants)
            crm_match = any(v in crm_type for v in variants)
            if olx_match and crm_match:
                return 100.0
        
        return 30.0
    
    def _match_repair(self, olx: OLXProperty, crm: BuildHouse) -> float:
        """Ta'mir o'xshashligi"""
        if not olx.repair_state:
            return 50.0
        
        if not crm.state_repair:
            return 50.0
        
        olx_repair = olx.repair_state.lower()
        crm_repair = crm.state_repair.name.lower()
        
        repair_keywords = ['ta\'mir', 'yaxshi', 'euro', 'dizayn']
        
        olx_has = any(kw in olx_repair for kw in repair_keywords)
        crm_has = any(kw in crm_repair for kw in repair_keywords)
        
        if olx_has and crm_has:
            return 100.0
        elif not olx_has and not crm_has:
            return 80.0
        else:
            return 30.0
    
    def _get_match_details(self, olx: OLXProperty, crm: BuildHouse, similarity: float) -> Dict:
        """Taqqoslash detallari"""
        return {
            'similarity_score': similarity,
            'scores': {
                'address': self._match_address(olx, crm),
                'rooms': 100.0 if olx.rooms == crm.rooms_numbers else 0.0,
                'area': self._match_area(olx, crm),
                'floor': self._match_floor(olx, crm),
                'building_type': self._match_building_type(olx, crm),
                'repair': self._match_repair(olx, crm),
            },
            'olx': {
                'title': olx.title,
                'address': olx.get_short_address(),
                'rooms': olx.rooms,
                'area': float(olx.area_total) if olx.area_total else None,
                'floor': olx.floor,
                'price': float(olx.price_usd),
                'url': olx.url,
            },
            'crm': {
                'id': crm.id,
                'name': crm.name,
                'address': crm.address.full_address if crm.address else None,
                'rooms': crm.rooms_numbers,
                'area': float(crm.total_area) if crm.total_area else None,
                'floor': crm.floor,
                'price': float(crm.price_owner),
                'agent': crm.user.full_name if crm.user else None,
            }
        }
    
    def _get_status(self, price_diff_percent: float) -> str:
        """Status aniqlash"""
        if price_diff_percent < -5:
            return 'cheaper'
        elif -5 <= price_diff_percent <= 5:
            return 'similar'
        else:
            return 'expensive'