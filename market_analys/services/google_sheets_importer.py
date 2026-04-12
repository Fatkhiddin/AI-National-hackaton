# market_analysis/services/google_sheets_importer.py

"""
Google Sheets dan bozor narxlarini import qilish servisi.
TZ bo'yicha to'liq implementatsiya.
"""

import requests
import pandas as pd
from decimal import Decimal
from typing import Dict, List
from django.db import transaction
from ..models import MarketPriceReference


class GoogleSheetsImporter:
    """
    Google Sheets'dan ma'lumotlarni import qilish.
    
    Usage:
        importer = GoogleSheetsImporter(team=team_instance)
        result = importer.import_all()
    """
    
    # Google Sheets URLs (TZ dan)
    SHEETS_URLS = {
        'sheet1': 'https://docs.google.com/spreadsheets/d/1hVwC09Wlz4HPcQCnZpkGsznFHEfZ0Z9B575Sgq8aaRk/edit?usp=sharing',
        'sheet2': 'https://docs.google.com/spreadsheets/d/1OCjZjtwIV4rzKRDoGsudOus3rSIzN6zzT8nFsysLcRw/edit?usp=drivesdk',
        'sheet3': 'https://docs.google.com/spreadsheets/d/11hg22AxGAv2yKkZbRbIUreXnjGASyrvIIZIkk-eVMUk/edit?usp=drivesdk',
    }
    
    # Qurilish turi mapping (Uzbek -> database value)
    QURILISH_MAP = {
        'Gʻishtli': 'gishtli',
        'g\'ishtli': 'gishtli',
        'gishtli': 'gishtli',
        'Panelli': 'panelli',
        'panelli': 'panelli',
        'Monolitli': 'monolitli',
        'monolitli': 'monolitli',
        'Blokli': 'blokli',
        'blokli': 'blokli',
        # Ingliz variantlari
        'Brick': 'gishtli',
        'Panel': 'panelli',
        'Monolith': 'monolitli',
        'Block': 'blokli',
    }
    
    def __init__(self, team):
        """
        Initialization.
        
        Args:
            team: Team model instance
        """
        self.team = team
        self.imported_count = 0
        self.error_count = 0
        self.errors = []
    
    def import_all(self) -> Dict:
        """
        Barcha Google Sheets'lardan import qilish.
        
        Returns:
            {
                'success': bool,
                'imported': int,
                'errors': int,
                'error_details': list
            }
        """
        print("\n" + "="*60)
        print("📊 GOOGLE SHEETS IMPORT BOSHLANDI")
        print("="*60)
        
        self.imported_count = 0
        self.error_count = 0
        self.errors = []
        
        for sheet_name, url in self.SHEETS_URLS.items():
            print(f"\n📄 {sheet_name.upper()} ishlanmoqda...")
            print(f"   URL: {url[:50]}...")
            
            try:
                # Har bir sheet uchun 2 marta: remontli va remontsiz
                self.import_sheet(url, sheet_name, 'remontli', sheet_index=0)
                self.import_sheet(url, sheet_name, 'remontsiz', sheet_index=1)
                
            except Exception as e:
                error_msg = f"{sheet_name} xatolik: {str(e)}"
                print(f"   ❌ {error_msg}")
                self.errors.append(error_msg)
                self.error_count += 1
        
        print("\n" + "="*60)
        print(f"✅ IMPORT TUGADI")
        print(f"   Muvaffaqiyatli: {self.imported_count}")
        print(f"   Xatoliklar: {self.error_count}")
        print("="*60 + "\n")
        
        return {
            'success': self.error_count == 0,
            'imported': self.imported_count,
            'errors': self.error_count,
            'error_details': self.errors
        }
    
    def import_sheet(self, url: str, source_name: str, holat: str, sheet_index: int = 0):
        """
        Bitta sheet'dan import.
        
        Args:
            url: Google Sheets URL
            source_name: Fayl nomi (tracking uchun)
            holat: 'remontli' yoki 'remontsiz'
            sheet_index: Sheet raqami (0 yoki 1)
        """
        print(f"   📥 {holat.upper()} sheet yuklanmoqda...")
        
        try:
            # Google Sheets URL ni export format ga o'zgartirish
            # /edit?usp=... -> /export?format=csv&gid=0
            if '/edit' in url:
                base_url = url.split('/edit')[0]
                export_url = f"{base_url}/export?format=csv&gid={sheet_index}"
            else:
                export_url = url
            
            # CSV yuklab olish
            response = requests.get(export_url, timeout=30)
            response.raise_for_status()
            
            # Pandas bilan parse qilish
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            print(f"   📊 {len(df)} ta qator topildi")
            
            # Har bir qatorni qayta ishlash
            processed = 0
            skipped = 0
            
            for index, row in df.iterrows():
                try:
                    if self.process_row(row, source_name, holat):
                        processed += 1
                    else:
                        skipped += 1
                except Exception as e:
                    self.errors.append(f"{source_name} - {holat} - qator {index+1}: {str(e)}")
                    self.error_count += 1
            
            print(f"   ✅ Qayta ishlandi: {processed}, O'tkazildi: {skipped}")
            
        except requests.RequestException as e:
            error_msg = f"URL yuklanmadi: {str(e)}"
            print(f"   ❌ {error_msg}")
            self.errors.append(f"{source_name} - {holat}: {error_msg}")
            self.error_count += 1
            raise
        
        except Exception as e:
            error_msg = f"Parse xatolik: {str(e)}"
            print(f"   ❌ {error_msg}")
            self.errors.append(f"{source_name} - {holat}: {error_msg}")
            self.error_count += 1
            raise
    
    @transaction.atomic
    def process_row(self, row: pd.Series, source_name: str, holat: str) -> bool:
        """
        Bitta CSV qatorini database'ga saqlash.
        
        Args:
            row: Pandas Series obyekti
            source_name: Fayl nomi
            holat: 'remontli' yoki 'remontsiz'
        
        Returns:
            bool: True - saqlandi, False - skip qilindi
        """
        try:
            # Ustunlarni parse qilish (TZ bo'yicha)
            # Expected columns: T/r, Etaj, Xonalar soni, Qurilish turi, Maydon, Arzon, Bozor, Qimmat
            
            # T/r ni ignore qilamiz
            etaj = self._safe_int(row.get('Etaj', row.iloc[1] if len(row) > 1 else None))
            xonalar = self._safe_int(row.get('Xonalar soni', row.iloc[2] if len(row) > 2 else None))
            qurilish = str(row.get('Qurilish turi', row.iloc[3] if len(row) > 3 else '')).strip()
            maydon = self._safe_int(row.get('Maydon', row.iloc[4] if len(row) > 4 else None))
            
            arzon = self._safe_decimal(row.get('Arzon', row.iloc[5] if len(row) > 5 else None))
            bozor = self._safe_decimal(row.get('Bozor', row.iloc[6] if len(row) > 6 else None))
            qimmat = self._safe_decimal(row.get('Qimmat', row.iloc[7] if len(row) > 7 else None))
            
            # Validation - agar 0 yoki None bo'lsa skip
            if not all([etaj, xonalar, maydon, arzon, bozor, qimmat]):
                return False
            
            if arzon == 0 or bozor == 0 or qimmat == 0:
                return False
            
            # Qurilish turini normalize qilish
            qurilish_normalized = self.QURILISH_MAP.get(qurilish)
            if not qurilish_normalized:
                # Agar mapping'da yo'q bo'lsa, default gishtli deb olamiz
                print(f"   ⚠️ Noma'lum qurilish turi: '{qurilish}', gishtli deb qabul qilindi")
                qurilish_normalized = 'gishtli'
            
            # Maydon max = maydon min + 5 (TZ bo'yicha)
            maydon_max = maydon + 5
            
            # Database'ga saqlash yoki yangilash
            obj, created = MarketPriceReference.objects.update_or_create(
                team=self.team,
                etaj=etaj,
                xonalar_soni=xonalar,
                qurilish_turi=qurilish_normalized,
                holat=holat,
                maydon_min=maydon,
                defaults={
                    'maydon_max': maydon_max,
                    'arzon_narx': arzon,
                    'bozor_narx': bozor,
                    'qimmat_narx': qimmat,
                    'source_file': source_name,
                }
            )
            
            self.imported_count += 1
            
            if created:
                print(f"   ➕ Yangi: {etaj}-etaj, {xonalar}-xona, {qurilish_normalized}, {holat}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Qator qayta ishlanmadi: {str(e)}")
            return False
    
    def clear_all_data(self) -> int:
        """
        Barcha MarketPriceReference'larni o'chirish.
        
        Returns:
            int: O'chirilgan yozuvlar soni
        """
        count = MarketPriceReference.objects.filter(team=self.team).count()
        MarketPriceReference.objects.filter(team=self.team).delete()
        print(f"🗑️ {count} ta yozuv o'chirildi")
        return count
    
    # Helper methods
    
    def _safe_int(self, value) -> int:
        """String yoki boshqa typeni int ga o'girish"""
        try:
            if pd.isna(value):
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_decimal(self, value) -> Decimal:
        """String yoki boshqa typeni Decimal ga o'girish"""
        try:
            if pd.isna(value):
                return None
            return Decimal(str(value))
        except (ValueError, TypeError, InvalidOperation):
            return None
