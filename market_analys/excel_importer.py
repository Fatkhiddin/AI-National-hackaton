# market_analysis/services/excel_importer.py

import pandas as pd
from decimal import Decimal
from django.db import transaction
from .models import PriceReference


class ExcelImporter:
    """
    Excel fayldan narxlarni import qilish
    """
    
    def __init__(self, team):
        self.team = team
    
    def import_from_google_sheets(self, sheet_url):
        """
        Google Sheets dan import
        URL: https://docs.google.com/spreadsheets/d/11hg22AxGAv2yKkZbRbIUreXnjGASyrvIIZIkk-eVMUk/edit
        """
        # Google Sheets URL ni Excel URL ga o'zgartirish
        excel_url = sheet_url.replace('/edit', '/export?format=xlsx')
        
        try:
            # Sheet 1: Remontli
            df_renovated = pd.read_excel(excel_url, sheet_name=0)
            count_renovated = self._import_sheet(df_renovated, is_renovated=True, sheet_name='renovated')
            
            # Sheet 2: Remontsiz
            df_not_renovated = pd.read_excel(excel_url, sheet_name=1)
            count_not_renovated = self._import_sheet(df_not_renovated, is_renovated=False, sheet_name='not_renovated')
            
            return {
                'success': True,
                'renovated_count': count_renovated,
                'not_renovated_count': count_not_renovated,
                'total': count_renovated + count_not_renovated
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def import_from_file(self, file_path):
        """
        Local Excel fayldan import
        """
        try:
            # Sheet 1: Remontli
            df_renovated = pd.read_excel(file_path, sheet_name=0)
            count_renovated = self._import_sheet(df_renovated, is_renovated=True, sheet_name='renovated')
            
            # Sheet 2: Remontsiz
            df_not_renovated = pd.read_excel(file_path, sheet_name=1)
            count_not_renovated = self._import_sheet(df_not_renovated, is_renovated=False, sheet_name='not_renovated')
            
            return {
                'success': True,
                'renovated_count': count_renovated,
                'not_renovated_count': count_not_renovated,
                'total': count_renovated + count_not_renovated
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @transaction.atomic
    def _import_sheet(self, df, is_renovated, sheet_name):
        """
        Bitta sheet dan ma'lumot import qilish
        """
        count = 0
        
        # Ustun nomlarini aniqlash (sizning Excel formatida)
        # Misol: Etaj | Xonalar | Maydon (dan-gacha) | Arzon | Bozor | Qimmat
        
        for index, row in df.iterrows():
            try:
                # Ustunlarni o'qish (sizning Excel strukturangizga qarab o'zgartiring)
                floor = int(row.get('Etaj', row.iloc[0]))
                rooms = int(row.get('Xonalar', row.iloc[1]))
                
                # Maydon oralig'i (misol: "50-60" yoki "50-60 m²")
                area_range = str(row.get('Maydon', row.iloc[2]))
                area_from, area_to = self._parse_area_range(area_range)
                
                # Narxlar
                price_low = Decimal(str(row.get('Arzon', row.iloc[3])))
                price_market = Decimal(str(row.get('Bozor', row.iloc[4])))
                price_high = Decimal(str(row.get('Qimmat', row.iloc[5])))
                
                # Database ga saqlash
                PriceReference.objects.update_or_create(
                    team=self.team,
                    floor_number=floor,
                    room_count=rooms,
                    area_from=area_from,
                    area_to=area_to,
                    is_renovated=is_renovated,
                    defaults={
                        'price_low': price_low,
                        'price_market': price_market,
                        'price_high': price_high,
                        'source_sheet': sheet_name,
                        'excel_row': index + 2,  # Excel da 1-qator header
                        'is_active': True,
                    }
                )
                count += 1
                
            except Exception as e:
                print(f"Row {index + 2} da xatolik: {e}")
                continue
        
        return count
    
    def _parse_area_range(self, area_str):
        """
        Maydon oralig'ini ajratish
        Input: "50-60" yoki "50-60 m²" yoki "50"
        Output: (50.0, 60.0)
        """
        # m² ni o'chirish
        area_str = str(area_str).replace('m²', '').replace('м²', '').strip()
        
        if '-' in area_str:
            parts = area_str.split('-')
            area_from = float(parts[0].strip())
            area_to = float(parts[1].strip())
        else:
            # Agar diapazon bo'lmasa, +10 qo'shamiz
            area_from = float(area_str)
            area_to = area_from + 10
        
        return Decimal(str(area_from)), Decimal(str(area_to))