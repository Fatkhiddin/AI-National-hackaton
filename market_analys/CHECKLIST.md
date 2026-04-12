# ✅ PRE-DEPLOYMENT CHECKLIST

## 📋 BEFORE RUNNING

### 1. Dependencies
```bash
□ pip install anthropic
□ pip install pandas
□ pip install requests
```

**Verify:**
```bash
python -c "import anthropic; import pandas; import requests; print('✅ All OK')"
```

---

### 2. Django Settings
```python
# core/settings.py

□ INSTALLED_APPS → 'market_analysis' qo'shildi
□ ANTHROPIC_API_KEY = 'sk-ant-...' belgilandi
```

**Verify:**
```bash
python manage.py shell -c "from django.conf import settings; print('✅ API Key:', settings.ANTHROPIC_API_KEY[:20])"
```

---

### 3. Database Migration
```bash
□ python manage.py makemigrations market_analysis
□ python manage.py migrate
```

**Verify:**
```bash
python manage.py showmigrations market_analysis
# Expected: [X] 0001_initial
```

---

### 4. Admin SuperUser
```bash
□ SuperUser yaratilgan
□ Admin panel'ga kirishga ruxsat bor
```

**Verify:**
```
http://localhost:8000/admin/
```

---

## 🚀 INITIAL RUN

### Step 1: Import Market Data
```bash
python manage.py import_market_data --clear
```

**Expected Output:**
```
✅ IMPORT TUGADI
   Muvaffaqiyatli: 270+
   Xatoliklar: 0
```

**Verify in Admin:**
```
http://localhost:8000/admin/market_analysis/marketpricereference/
# Should have 270+ records
```

**Checklist:**
- □ 270+ ta yozuv import qilindi
- □ Xatoliklar 0 yoki minimal
- □ Admin panelda ko'rinadi

---

### Step 2: Test Single CRM Property
```bash
# Birinchi BuildHouse ID ni aniqlang
python manage.py shell -c "from home.models import BuildHouse; print(BuildHouse.objects.first().id)"

# Tahlil qiling (ID ni o'zgartiring)
python manage.py analyze_properties --property-id 1 --model BuildHouse
```

**Expected Output:**
```
✅ TAHLIL TUGADI:
   Status: NORMAL (yoki boshqa)
   Farq: X.X%
   Confidence: XX%
```

**Checklist:**
- □ Property ma'lumotlari to'liq
- □ Bozor ma'lumoti topildi
- □ AI tahlil ishladi (yoki fallback)
- □ Natija saqlandi

---

### Step 3: Verify in Admin
```
http://localhost:8000/admin/market_analysis/propertypriceanalysis/
```

**Checklist:**
- □ Tahlil ko'rinadi
- □ Status badge color-coded
- □ AI tahlil matnlari mavjud
- □ Farq to'g'ri hisoblangan

---

## 🔍 TESTING CHECKLIST

### Import Tests
```bash
# Test 1: Clear va import
□ python manage.py import_market_data --clear
# Expected: 270+ import

# Test 2: Qayta import (duplicate check)
□ python manage.py import_market_data
# Expected: 0 yangi (yoki update)

# Test 3: Specific team
□ python manage.py import_market_data --team 1
# Expected: Success for team 1
```

---

### Analysis Tests

#### Test 1: Single CRM Property (AI)
```bash
□ python manage.py analyze_properties --property-id X --model BuildHouse
# Expected: AI tahlil
```

#### Test 2: Single CRM Property (No AI)
```bash
□ python manage.py analyze_properties --property-id X --model BuildHouse --no-ai
# Expected: Matematik tahlil
```

#### Test 3: Bulk CRM (Limited)
```bash
□ python manage.py analyze_properties --model BuildHouse --limit 5
# Expected: 5 ta tahlil
```

#### Test 4: OLX (if available)
```bash
□ python manage.py analyze_properties --model OLXProperty --limit 5
# Expected: 5 ta OLX tahlil
```

---

### Admin Tests
```
http://localhost:8000/admin/market_analysis/
```

**MarketPriceReferenceAdmin:**
- □ List display ishlaydi
- □ Filters ishlaydi
- □ Color badges ko'rinadi
- □ CSV export ishlaydi

**PropertyPriceAnalysisAdmin:**
- □ List display ishlaydi
- □ Status badges color-coded
- □ Farq display icon bilan
- □ AI tahlil formatted
- □ Re-analyze action ishlaydi
- □ CSV export ishlaydi

---

## 🐛 TROUBLESHOOTING CHECKLIST

### Problem: "No module named 'anthropic'"
```bash
□ pip install anthropic pandas requests
□ Restart server
```

### Problem: "ANTHROPIC_API_KEY not found"
```python
# core/settings.py
□ ANTHROPIC_API_KEY = '...' qo'shilgan
□ Server restart qilindi
```

### Problem: "Import qilindi: 0 ta"
```bash
□ Internet bor
□ Google Sheets URLs to'g'ri
□ Pandas o'rnatilgan
□ CSV format to'g'ri
```

### Problem: "Property ma'lumotlari to'liq emas"
```bash
# BuildHouse obyektda tekshiring:
□ floor mavjud
□ rooms_numbers mavjud
□ total_area mavjud
□ price_owner mavjud
□ type_building mavjud (ixtiyoriy)
□ state_repair mavjud (ixtiyoriy)
```

### Problem: "Bozor ma'lumoti topilmadi"
```bash
□ import_market_data ishlagan
□ MarketPriceReference da ma'lumot bor
□ Property parametrlari valid
```

### Problem: "AI tahlil ishlamadi"
```bash
□ ANTHROPIC_API_KEY to'g'ri
□ Internet ulanishi bor
□ Fallback ishladi (matematik tahlil)
```

---

## 📊 SUCCESS CRITERIA

### Import Success:
- ✅ 270+ ta bozor narxi import qilindi
- ✅ Xatoliklar 0 yoki minimal (<5%)
- ✅ Admin panelda ko'rinadi

### Analysis Success:
- ✅ Property tahlil qilindi
- ✅ Status to'g'ri aniqlandi
- ✅ AI tahlil matnlari mavjud (yoki fallback)
- ✅ Farq to'g'ri hisoblandi
- ✅ Confidence score mantiqiy

### Admin Success:
- ✅ Barcha listlar ko'rinadi
- ✅ Filters ishlaydi
- ✅ Color-coding to'g'ri
- ✅ Actions ishlaydi
- ✅ Export ishlaydi

---

## 🎯 FINAL VERIFICATION

### Quick Test Script:
```python
# python manage.py shell

from market_analysis.services import GoogleSheetsImporter, PriceAnalyzer
from users.models import Team
from home.models import BuildHouse

# 1. Import test
team = Team.objects.first()
importer = GoogleSheetsImporter(team=team)
result = importer.import_all()
print(f"✅ Import: {result['imported']} ta")

# 2. Analysis test
analyzer = PriceAnalyzer()
house = BuildHouse.objects.filter(
    floor__isnull=False,
    rooms_numbers__isnull=False,
    total_area__isnull=False,
    price_owner__gt=0
).first()

if house:
    analysis = analyzer.analyze_property(house, use_ai=False)  # AI'siz test
    print(f"✅ Tahlil: {analysis.get_status_display()}")
else:
    print("❌ To'g'ri property topilmadi")
```

**Expected:**
```
✅ Import: 270+ ta
✅ Tahlil: NORMAL (yoki boshqa status)
```

---

## ✅ READY FOR PRODUCTION

### Barcha checklar ✅ bo'lsa:
```
□ Dependencies o'rnatildi
□ Settings sozlandi
□ Migration bajarildi
□ Import test muvaffaqiyatli
□ Analysis test muvaffaqiyatli
□ Admin panel ishlaydi
□ Troubleshooting scenarios test qilindi
□ Final verification o'tdi
```

### → Status: 🟢 **PRODUCTION READY!**

---

**Checklist Version:** 1.0  
**Date:** 2025-11-18  
**Estimated Setup Time:** 15-20 minutes  
**Estimated Test Time:** 10-15 minutes  
**Total:** 25-35 minutes
