# market_analys/crm_api.py
"""
CRM API Client — BuildHouse va boshqa datalarni API orqali olish.
CRM dagi apiga ulanib, /api/all-objects/ endpoint orqali BuildHouse datalarini oladi.
"""

import requests
from urllib.parse import urljoin, urlencode
from home.models import CRMConfiguration


class CRMAPIClient:
    """
    Megapolis CRM API Client.
    
    Usage:
        client = CRMAPIClient()
        
        # Barcha obyektlar
        data = client.get_objects(page=1, page_size=20)
        
        # Bitta obyekt
        obj = client.get_object(42)
        
        # Filter bilan
        objects = client.get_objects(rooms_numbers=3, min_price=50000)
        
        # Lookup data
        categories = client.get_lookup('Categorys')
    """

    def __init__(self):
        self.config = CRMConfiguration.get_config()
        if not self.config.crm_url:
            raise ValueError("CRM URL sozlanmagan. Admin paneldan CRM konfiguratsiyasini kiriting.")

    def _get_headers(self):
        """JWT tokenli headers"""
        return self.config.get_headers()

    def _make_request(self, endpoint, params=None, method='GET'):
        """
        CRM API ga so'rov yuborish (token refresh bilan).
        """
        url = urljoin(self.config.crm_url, endpoint)

        try:
            response = requests.request(
                method,
                url,
                headers=self._get_headers(),
                params=params,
                timeout=15
            )

            # Token expired → refresh va qayta urinish
            if response.status_code == 401:
                success, msg = self.config.refresh_access_token()
                if success:
                    response = requests.request(
                        method,
                        url,
                        headers=self._get_headers(),
                        params=params,
                        timeout=15
                    )
                else:
                    # Qayta login qilish
                    success, msg = self.config.test_connection()
                    if success:
                        response = requests.request(
                            method,
                            url,
                            headers=self._get_headers(),
                            params=params,
                            timeout=15
                        )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ CRM API xato: {response.status_code} - {url}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ CRM API ulanish xatosi: {e}")
            return None

    # ==========================================
    # BuildHouse (Ko'chmas mulk obyektlari)
    # ==========================================

    def get_objects(self, **kwargs):
        """
        /api/all-objects/ — BuildHouse ro'yxatini olish (CRM ichki, JWT majburiy).
        
        Params:
            page, page_size, search, rooms_numbers, floor, floor_build,
            min_area, max_area, min_price, max_price, category,
            state_repair, type_building, ordering, ...
        
        Returns:
            {
                'count': 150,
                'next': '...?page=2',
                'previous': None,
                'total_pages': 8,
                'current_page': 1,
                'results': [...]
            }
        """
        # Bo'sh qiymatlarni olib tashlash
        params = {k: v for k, v in kwargs.items() if v is not None and v != ''}
        return self._make_request('all-objects/', params=params)

    def get_object(self, object_id):
        """
        /api/all-objects/<id>/ — Bitta BuildHouse obyektini olish (in_site=False ham ishlaydi).
        
        Returns:
            {
                'id': 42,
                'name': '3 xonali kvartira',
                'price_starting': 85000,
                'total_area': 70.5,
                'rooms_numbers': 3,
                'floor': 5,
                'state_repair': 'Evro ta\'mir',
                'type_building': {...},
                'address': {...},
                ...
            }
        """
        return self._make_request(f'all-objects/{object_id}/')

    def search_objects(self, query, **kwargs):
        """Matn bo'yicha qidiruv"""
        kwargs['search'] = query
        return self.get_objects(**kwargs)

    def get_objects_for_comparison(self, rooms=None, min_area=None, max_area=None, min_price=None):
        """
        OLX taqqoslash uchun CRM obyektlarini olish.
        Barcha sahifalarni yuklaydi.
        """
        all_objects = []
        page = 1
        
        while True:
            data = self.get_objects(
                page=page,
                page_size=100,
                rooms_numbers=rooms,
                min_area=min_area,
                max_area=max_area,
                min_price=min_price,
                ordering='-created_at'
            )
            
            if not data or not data.get('results'):
                break
            
            all_objects.extend(data['results'])
            
            if not data.get('next'):
                break
            
            page += 1
        
        return all_objects

    # ==========================================
    # Bozor Narxlari (Market Prices)
    # ==========================================

    def get_market_prices(self, **kwargs):
        """
        /api/market-prices/ — Bozor narxlari ro'yxati.
        
        Params:
            qurilish_turi: gishtli, panelli, monolitli, blokli
            holat: remontli, remontsiz
            xonalar_soni: int
            etaj: int
            search: str
            ordering: str (etaj, -bozor_narx, etc.)
            page: int
            page_size: int (1-100, default 20)
        
        Returns:
            {
                'count': 120,
                'next': '...?page=2',
                'previous': None,
                'total_pages': 6,
                'current_page': 1,
                'results': [
                    {
                        'id': 1,
                        'etaj': 5,
                        'xonalar_soni': 3,
                        'qurilish_turi': 'gishtli',
                        'qurilish_turi_display': "Gʻishtli",
                        'holat': 'remontli',
                        'holat_display': 'Remontli',
                        'maydon_min': 60,
                        'maydon_max': 80,
                        'maydon_display': '60–80 m²',
                        'arzon_narx': '850.00',
                        'bozor_narx': '1000.00',
                        'qimmat_narx': '1200.00',
                        'narx_range': {'min': 850.0, 'avg': 1000.0, 'max': 1200.0},
                        'source_file': 'google_sheets_2024',
                        'updated_at': '2024-11-10T08:30:00Z'
                    }, ...
                ]
            }
        """
        params = {k: v for k, v in kwargs.items() if v is not None and v != ''}
        return self._make_request('market-prices/', params=params)

    def get_market_price(self, price_id):
        """
        /api/market-prices/<id>/ — Bitta bozor narxi.
        """
        return self._make_request(f'market-prices/{price_id}/')

    def get_all_market_prices(self, **kwargs):
        """
        Barcha bozor narxlarini sahifalab olish.
        """
        all_prices = []
        page = 1
        while True:
            kwargs['page'] = page
            kwargs['page_size'] = 100
            data = self.get_market_prices(**kwargs)
            if not data or not data.get('results'):
                break
            all_prices.extend(data['results'])
            if not data.get('next'):
                break
            page += 1
        return all_prices

    def sync_market_prices_to_db(self):
        """
        CRM API dan barcha bozor narxlarini olib, lokal DB ga saqlash.
        PriceAnalyzer uni local DB dan ishlatadi.
        
        Returns: (created, updated, errors)
        """
        from .models import MarketPriceReference
        from decimal import Decimal

        all_prices = self.get_all_market_prices()
        created = 0
        updated = 0
        errors = 0

        for item in all_prices:
            try:
                obj, is_new = MarketPriceReference.objects.update_or_create(
                    etaj=item['etaj'],
                    xonalar_soni=item['xonalar_soni'],
                    qurilish_turi=item['qurilish_turi'],
                    holat=item['holat'],
                    maydon_min=item['maydon_min'],
                    defaults={
                        'maydon_max': item.get('maydon_max'),
                        'arzon_narx': Decimal(str(item['arzon_narx'])),
                        'bozor_narx': Decimal(str(item['bozor_narx'])),
                        'qimmat_narx': Decimal(str(item['qimmat_narx'])),
                        'source_file': item.get('source_file', 'crm_api'),
                    }
                )
                if is_new:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                print(f"❌ Market price sync xato: {e}")
                errors += 1

        return created, updated, errors

    # ==========================================
    # Lookup (Spravochnik) endpointlar
    # ==========================================

    def get_lookup(self, endpoint_name):
        """
        Lookup endpointlardan data olish.
        Masalan: get_lookup('Categorys'), get_lookup('StateRepairs')
        
        Returns: [{'id': 1, 'name': '...'}, ...]
        """
        return self._make_request(f'{endpoint_name}/')

    def get_categories(self):
        return self.get_lookup('Categorys')

    def get_state_repairs(self):
        return self.get_lookup('StateRepairs')

    def get_type_buildings(self):
        return self.get_lookup('TypeBuildings')

    def get_addresses(self):
        return self.get_lookup('addresses')

    # ==========================================
    # Statistika
    # ==========================================

    def get_objects_count(self):
        """Jami obyektlar sonini olish"""
        data = self.get_objects(page=1, page_size=1)
        if data:
            return data.get('count', 0)
        return 0

    def get_objects_stats(self):
        """
        CRM obyektlari bo'yicha statistika.
        """
        stats = {
            'total': 0,
            'by_rooms': {},
        }

        data = self.get_objects(page=1, page_size=1)
        if data:
            stats['total'] = data.get('count', 0)

        # Xonalar bo'yicha
        for rooms in [1, 2, 3, 4, 5]:
            room_data = self.get_objects(page=1, page_size=1, rooms_numbers=rooms)
            if room_data:
                stats['by_rooms'][rooms] = room_data.get('count', 0)

        return stats

    # ==========================================
    # Utility
    # ==========================================

    def is_connected(self):
        """CRM ulanganligini tekshirish"""
        return self.config.is_connected

    def extract_property_data(self, api_obj):
        """
        API javobidagi obyektdan kerakli ma'lumotlarni extract qilish.
        BuildHouse ORM o'rniga dict bilan ishlaydi.
        
        Returns dict with normalized property data.
        """
        if not api_obj:
            return None

        # Address
        address = api_obj.get('address', {})
        if isinstance(address, dict):
            full_address = address.get('full_address', '') or address.get('name', '')
        elif isinstance(address, str):
            full_address = address
        else:
            full_address = ''

        # State repair
        state_repair = api_obj.get('state_repair', '')
        if isinstance(state_repair, dict):
            state_repair = state_repair.get('name', '')

        # Type building
        type_building = api_obj.get('type_building', '')
        if isinstance(type_building, dict):
            type_building = type_building.get('name', '')

        return {
            'id': api_obj.get('id'),
            'name': api_obj.get('name', ''),
            'price_starting': api_obj.get('price_starting', 0),
            'price_meter': api_obj.get('price_meter', 0),
            'total_area': float(api_obj.get('total_area', 0) or 0),
            'living_area': float(api_obj.get('living_area', 0) or 0),
            'rooms_numbers': api_obj.get('rooms_numbers', 0),
            'floor': api_obj.get('floor', 0),
            'floor_build': api_obj.get('floor_build', 0),
            'year_construction': api_obj.get('year_construction'),
            'address': full_address,
            'state_repair': state_repair,
            'type_building': type_building,
            'category': api_obj.get('category', {}).get('name', '') if isinstance(api_obj.get('category'), dict) else '',
            'images': [img.get('image', '') for img in api_obj.get('build_house_images', [])],
            'created_at': api_obj.get('created_at', ''),
        }
