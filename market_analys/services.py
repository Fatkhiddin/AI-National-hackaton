# market_analys/services.py
"""
PropertyMatcher — OLX va CRM obyektlarini API orqali taqqoslash.
"""

from typing import List, Dict
from decimal import Decimal
from .models import OLXProperty, ComparisonResult
from .crm_api import CRMAPIClient


class PropertyMatcher:
    """OLX va CRM obyektlarini taqqoslash (CRM API orqali)"""

    WEIGHTS = {
        'address': 0.30,
        'rooms': 0.25,
        'area': 0.20,
        'floor': 0.10,
        'building_type': 0.10,
        'repair': 0.05,
    }

    MIN_SIMILARITY = 70
    TOP_N = 3
    PRICE_ALERT_PERCENT = -5

    def find_matches_for_olx(self, olx_property: OLXProperty) -> List[ComparisonResult]:
        """OLX obyekt uchun CRM dan eng o'xshash obyektlarni topish"""
        if not olx_property.rooms or not olx_property.area_total:
            return []

        client = CRMAPIClient()

        # API dan filter bilan obyektlarni olish
        area_min = float(olx_property.area_total) * 0.8
        area_max = float(olx_property.area_total) * 1.2

        crm_objects = client.get_objects_for_comparison(
            rooms=olx_property.rooms,
            min_area=area_min,
            max_area=area_max,
            min_price=1
        )

        if not crm_objects:
            return []

        comparisons = []
        for crm_obj in crm_objects:
            crm_data = client.extract_property_data(crm_obj)
            if not crm_data or not crm_data.get('price_starting'):
                continue

            similarity = self._calculate_similarity(olx_property, crm_data)

            if similarity >= self.MIN_SIMILARITY:
                price_diff = float(olx_property.price_usd) - crm_data['price_starting']
                price_diff_percent = (price_diff / crm_data['price_starting']) * 100

                comparisons.append({
                    'crm_id': crm_data['id'],
                    'crm_data': crm_data,
                    'similarity': similarity,
                    'price_diff': price_diff,
                    'price_diff_percent': price_diff_percent,
                })

        comparisons.sort(key=lambda x: x['similarity'], reverse=True)
        top_matches = comparisons[:self.TOP_N]

        results = []
        for match in top_matches:
            status = 'similar'
            if match['price_diff_percent'] < -5:
                status = 'cheaper'
            elif match['price_diff_percent'] > 5:
                status = 'expensive'

            result, created = ComparisonResult.objects.update_or_create(
                olx_property=olx_property,
                crm_object_id=match['crm_id'],
                defaults={
                    'similarity_score': match['similarity'],
                    'price_difference_usd': match['price_diff'],
                    'price_difference_percent': match['price_diff_percent'],
                    'status': status,
                    'crm_object_snapshot': match['crm_data'],
                    'match_details': {
                        'similarity': match['similarity'],
                        'price_diff': match['price_diff'],
                    },
                }
            )
            results.append(result)

        return results

    def _calculate_similarity(self, olx: OLXProperty, crm: dict) -> float:
        """O'xshashlik foizini hisoblash"""
        scores = {}

        # Rooms
        scores['rooms'] = 100.0 if olx.rooms == crm.get('rooms_numbers') else 0.0

        # Area
        olx_area = float(olx.area_total or 0)
        crm_area = crm.get('total_area', 0)
        if olx_area and crm_area:
            diff_pct = abs(olx_area - crm_area) / crm_area * 100
            if diff_pct <= 5:
                scores['area'] = 100
            elif diff_pct <= 10:
                scores['area'] = 80
            elif diff_pct <= 20:
                scores['area'] = 50
            else:
                scores['area'] = 20
        else:
            scores['area'] = 50

        # Floor
        olx_floor = olx.floor or 0
        crm_floor = crm.get('floor', 0)
        if olx_floor and crm_floor:
            if olx_floor == crm_floor:
                scores['floor'] = 100
            elif abs(olx_floor - crm_floor) <= 1:
                scores['floor'] = 70
            elif abs(olx_floor - crm_floor) <= 2:
                scores['floor'] = 40
            else:
                scores['floor'] = 10
        else:
            scores['floor'] = 50

        # Address
        olx_addr = (olx.address_text or '').lower()
        crm_addr = crm.get('address', '').lower()
        if olx_addr and crm_addr:
            olx_words = set(olx_addr.split())
            crm_words = set(crm_addr.split())
            intersection = len(olx_words & crm_words)
            union = len(olx_words | crm_words)
            scores['address'] = (intersection / union * 100) if union > 0 else 50
        else:
            scores['address'] = 50

        # Building type & repair (simplified)
        scores['building_type'] = 50
        scores['repair'] = 50

        total = sum(scores[k] * self.WEIGHTS[k] for k in scores)
        return round(total, 2)
