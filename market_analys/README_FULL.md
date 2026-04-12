# Market Analysis - COMPREHENSIVE README

## 📊 LOYIHA HAQIDA

**Market Analysis** - CRM tizimida mavjud ko'chmas mulk (uy-joy) obyektlarining narxlarini bozor narxlari bilan taqqoslash va AI yordamida tahlil qilish tizimi. 

**Muhim:** Bu tizim HAM CRM (BuildHouse) HAM OLX propertylar bilan ishlaydi!

---

## 🎯 ASOSIY FUNKSIYALAR

1. ✅ **Google Sheets Import** - 3 ta Google Sheets fayldan bozor narxlarini avtomatik import
2. ✅ **AI Tahlil** - Claude AI yordamida narxlarni tahlil qilish
3. ✅ **CRM Integration** - BuildHouse obyektlarini tahlil qilish
4. ✅ **OLX Integration** - OLX.uz dan olingan e'lonlarni tahlil qilish
5. ✅ **Management Commands** - Terminal orqali import va tahlil
6. ✅ **Admin Panel** - To'liq admin interface
7. ✅ **Fallback System** - AI ishlamasa oddiy matematik tahlil

---

## 📦 INSTALLATION

### 1. Dependencies o'rnatish

```bash
pip install anthropic>=0.30.0
pip install pandas>=2.0.0
pip install requests>=2.31.0
```

Yoki:

```bash
pip install -r requirements.txt
```

### 2. Settings.py sozlash

```python
# core/settings.py

INSTALLED_APPS = [
    # ...
    'market_analysis',
]

# Claude AI API Key
ANTHROPIC_API_KEY = 'sk-ant-api03-...'  # https://console.anthropic.com dan oling
```

### 3. Database Migration

```bash
python manage.py makemigrations market_analysis
python manage.py migrate
```

---

## 🚀 QUICK START

### 1. Bozor narxlarini import qilish

```bash
# Oddiy import
python manage.py import_market_data

# Avval o'chirib import
python manage.py import_market_data --clear

# Ma'lum team uchun
python manage.py import_market_data --team 1
```

### 2. CRM propertylarni tahlil qilish

```bash
# Bitta property
python manage.py analyze_properties --property-id 123 --model BuildHouse

# Barcha propertylar (AI bilan)
python manage.py analyze_properties --model BuildHouse

# AI'siz tahlil
python manage.py analyze_properties --model BuildHouse --no-ai

# Birinchi 50 ta
python manage.py analyze_properties --model BuildHouse --limit 50
```

### 3. OLX propertylarni tahlil qilish

```bash
# Bitta OLX property
python manage.py analyze_properties --property-id 456 --model OLXProperty

# Barcha OLX propertylar
python manage.py analyze_properties --model OLXProperty
```

---

## 💻 PYTHON API USAGE

### Google Sheets Import

```python
from market_analysis.services import GoogleSheetsImporter
from users.models import Team

team = Team.objects.first()
importer = GoogleSheetsImporter(team=team)

# Import qilish
result = importer.import_all()
print(f"Import qilindi: {result['imported']} ta")

# Ma'lumotlarni o'chirish
importer.clear_all_data()
```

### Property Tahlil (AI bilan)

```python
from market_analysis.services import PriceAnalyzer
from home.models import BuildHouse

analyzer = PriceAnalyzer()

# Bitta property
house = BuildHouse.objects.get(id=123)
analysis = analyzer.analyze_property(house, use_ai=True)

print(f"Status: {analysis.get_status_display()}")
print(f"Farq: {analysis.farq_foiz}%")
print(f"Tavsiya: {analysis.tavsiya}")

# Bulk tahlil
houses = BuildHouse.objects.filter(in_site=True)
result = analyzer.bulk_analyze(houses, use_ai=True)
```

### OLX Property Tahlil

```python
from market_analysis.services import PriceAnalyzer
from market_analysis.models import OLXProperty

analyzer = PriceAnalyzer()

# OLX property tahlil
olx = OLXProperty.objects.get(id=456)
analysis = analyzer.analyze_property(olx, use_ai=True)

print(f"Status: {analysis.get_status_display()}")
print(f"AI tahlil: {analysis.ai_tahlil}")
```

---

## 📊 DATABASE MODELS

### MarketPriceReference
Bozor narxlari ma'lumotnomasi (Google Sheets dan)

**Fields:**
- `etaj` - Qavat raqami
- `xonalar_soni` - Xonalar soni
- `qurilish_turi` - gishtli, panelli, monolitli, blokli
- `holat` - remontli, remontsiz
- `maydon_min`, `maydon_max` - Maydon diapazon (m²)
- `arzon_narx`, `bozor_narx`, `qimmat_narx` - Narxlar (so'm/m²)

### PropertyPriceAnalysis
Narx tahlil natijalari (CRM va OLX uchun)

**Fields:**
- `content_type`, `object_id` - Generic relation (BuildHouse yoki OLXProperty)
- `status` - juda_arzon, arzon, normal, qimmat, juda_qimmat
- `bozor_narxi`, `joriy_narxi` - Narxlar (so'm/m²)
- `farq_foiz`, `farq_summa` - Narx farqi
- `ai_tahlil`, `tavsiya` - AI tahlil matni
- `confidence_score` - Ishonch darajasi (0-100%)

### OLXProperty
OLX.uz dan olingan e'lonlar

**Fields:**
- `olx_id`, `url`, `title` - Asosiy ma'lumotlar
- `price_usd` - Narx (USD)
- `rooms`, `area_total`, `floor` - Property parametrlari
- `building_type`, `repair_state` - Bino va holat
- `is_processed` - Qayta ishlanganmi

---

## 🎨 ADMIN PANEL

### MarketPriceReferenceAdmin
- ✅ Color-coded qurilish turi va holat
- ✅ Narxlar (Arzon / Bozor / Qimmat)
- ✅ Filterlar: qurilish_turi, holat, xonalar, etaj
- ✅ CSV export

### PropertyPriceAnalysisAdmin
- ✅ Status badges (color-coded)
- ✅ Narx taqqoslash
- ✅ Farq ko'rsatish (icon + foiz)
- ✅ Confidence badge
- ✅ AI tahlil va tavsiya (formatted)
- ✅ Qayta tahlil qilish action
- ✅ CSV export

**Admin URL:** `/admin/market_analysis/`

---

## 🔧 CONFIGURATION

### Google Sheets URLs

3 ta Google Sheets URL `services/google_sheets_importer.py` da:

```python
SHEETS_URLS = {
    'sheet1': 'https://docs.google.com/spreadsheets/d/1hVwC09Wlz4HPcQCnZpkGsznFHEfZ0Z9B575Sgq8aaRk/edit?usp=sharing',
    'sheet2': 'https://docs.google.com/spreadsheets/d/1OCjZjtwIV4rzKRDoGsudOus3rSIzN6zzT8nFsysLcRw/edit?usp=drivesdk',
    'sheet3': 'https://docs.google.com/spreadsheets/d/11hg22AxGAv2yKkZbRbIUreXnjGASyrvIIZIkk-eVMUk/edit?usp=drivesdk',
}
```

### Qurilish Turi Mapping

`services/price_analyzer.py` da field mapping'lar:

```python
BUILDING_TYPE_MAP = {
    'кирпич': 'gishtli',
    'панель': 'panelli',
    'монолит': 'monolitli',
    'блок': 'blokli',
    # ...
}
```

### USD to UZS Rate

OLX narxlarini tahlil qilishda `_prepare_olx_data()` funksiyasida:

```python
USD_TO_UZS = 12700  # Update this regularly
```

---

## 🧪 TESTING

### 1. Import Test

```bash
python manage.py import_market_data --clear
```

**Expected:** ✅ Import qilindi: 100+ ta yozuv

### 2. Tahlil Test

```bash
python manage.py analyze_properties --property-id 1 --model BuildHouse
```

**Expected:** ✅ Tahlil natijasi ko'rsatiladi

### 3. Django Shell Test

```python
python manage.py shell

from market_analysis.services import *
from home.models import BuildHouse

# Import test
team = Team.objects.first()
importer = GoogleSheetsImporter(team=team)
result = importer.import_all()

# Tahlil test
analyzer = PriceAnalyzer()
house = BuildHouse.objects.first()
analysis = analyzer.analyze_property(house, use_ai=False)  # AI'siz test
print(analysis)
```

---

## 🐛 TROUBLESHOOTING

### Problem 1: ANTHROPIC_API_KEY not found

**Solution:**
```python
# core/settings.py
ANTHROPIC_API_KEY = 'sk-ant-api03-...'
```

### Problem 2: Import xatolik (Google Sheets)

**Solution:**
- Google Sheets URL'larni tekshiring
- Internet ulanishini tekshiring
- Pandas o'rnatilganini tekshiring: `pip install pandas`

### Problem 3: Property ma'lumotlari to'liq emas

**Solution:**
- BuildHouse obyektda `floor`, `rooms_numbers`, `total_area`, `price_owner` to'ldirilganini tekshiring
- OLXProperty obyektda `floor`, `rooms`, `area_total`, `price_usd` mavjudligini tekshiring

### Problem 4: Bozor ma'lumoti topilmadi

**Solution:**
- Avval `import_market_data` command'ini ishga tushiring
- MarketPriceReference jadvalida ma'lumotlar borligini tekshiring

---

## 📈 STATUS MEANINGS

| Status | Icon | Ma'nosi | Farq |
|--------|------|---------|------|
| juda_arzon | 💚 | Juda arzon | -20% va kamroq |
| arzon | ✅ | Arzon | -10% dan -20% |
| normal | ⚖️ | Normal | -10% dan +10% |
| qimmat | ⚠️ | Qimmat | +10% dan +20% |
| juda_qimmat | 🔴 | Juda qimmat | +20% va ko'proq |

---

## 🔐 SECURITY

1. **API Key:** `ANTHROPIC_API_KEY` ni GitHub'ga commit qilmang!
2. **Environment Variables:** `.env` fayldan foydalaning
3. **Permissions:** Admin panel faqat `direktor` va `boss` uchun

---

## 📝 NOTES

1. **AI Cost:** Claude AI har bir tahlil uchun ~$0.01-0.02 to'laydi
2. **Performance:** Bulk tahlilda progress bar ko'rsatiladi
3. **Fallback:** AI ishlamasa avtomatik oddiy matematik tahlilga o'tadi
4. **Team Filter:** Hamma modellar team bilan bog'langan

---

## 🆘 SUPPORT

Muammolar yoki savollar bo'lsa:
1. Django logs'ni tekshiring: `logs/django_log_*.txt`
2. Terminal output'ni o'qing - batafsil xabarlar bor
3. Admin panel orqali ma'lumotlarni tekshiring

---

## 📚 API ENDPOINTS (kelajakda)

```python
# TODO: REST API endpoints
GET /api/market-prices/
GET /api/price-analysis/{property_id}/
POST /api/analyze-property/
POST /api/import-market-data/
```

---

## ✅ CHECKLIST

- [x] Models yaratildi
- [x] Services yaratildi (Google Sheets, Claude AI, Price Analyzer)
- [x] Management commands yaratildi
- [x] Admin panel sozlandi
- [x] README yaratildi
- [ ] Tests yozildi
- [ ] REST API yaratildi
- [ ] Frontend UI yaratildi

---

**Version:** 1.0.0  
**Last Updated:** 2025-11-18  
**Author:** Megapolis CRM Team
