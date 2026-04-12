# 🚀 MARKET ANALYSIS - QUICK SETUP GUIDE

## BOSHLASH UCHUN 5 QADAM

### ✅ STEP 1: Dependencies o'rnatish

```bash
cd d:\megapolis-crm
pip install anthropic pandas requests
```

Yoki:

```bash
pip install -r market_analysis/requirements.txt
```

---

### ✅ STEP 2: Settings.py sozlash

`core/settings.py` fayliga qo'shing:

```python
# market_analysis app qo'shish
INSTALLED_APPS = [
    # ... boshqa applar
    'market_analysis',
]

# Claude AI API Key
ANTHROPIC_API_KEY = 'sk-ant-api03-...'  # https://console.anthropic.com dan oling
```

**Claude API Key olish:**
1. https://console.anthropic.com ga kiring
2. API Keys → Create Key
3. Key'ni nusxalang va settings.py ga qo'ying

---

### ✅ STEP 3: Database Migration

```powershell
python manage.py makemigrations market_analysis
python manage.py migrate
```

**Natija:**
```
Running migrations:
  Applying market_analysis.0001_initial... OK
```

---

### ✅ STEP 4: Bozor narxlarini import qilish

```powershell
python manage.py import_market_data --clear
```

**Natija:**
```
📊 GOOGLE SHEETS IMPORT BOSHLANDI
================================================
📄 SHEET1 ishlanmoqda...
   📥 REMONTLI sheet yuklanmoqda...
   📊 50 ta qator topildi
   ✅ Qayta ishlandi: 45, O'tkazildi: 5
...
✅ IMPORT TUGADI
   Muvaffaqiyatli: 270
   Xatoliklar: 0
```

---

### ✅ STEP 5: Test qilish

#### A) Admin Panel
```
http://localhost:8000/admin/market_analysis/
```

**Tekshirish:**
- MarketPriceReference: 270+ ta yozuv bo'lishi kerak
- PropertyPriceAnalysis: Hali bo'sh

#### B) Bitta Property tahlil qilish
```powershell
python manage.py analyze_properties --property-id 1 --model BuildHouse
```

**Natija:**
```
🔍 TAHLIL BOSHLANDI: BuildHouse #1
=====================================
✅ Property ma'lumotlari tayyorlandi:
   Etaj: 5
   Xonalar: 3
   Qurilish: gishtli
   Maydon: 75 m²
   Holat: remontli
   Narx/m²: 28,000,000 so'm

✅ Bozor ma'lumoti topildi
   Arzon: 25,000,000 so'm/m²
   Bozor: 28,000,000 so'm/m²
   Qimmat: 31,000,000 so'm/m²

🤖 Claude AI ga so'rov yuborilmoqda...
✅ AI javob olindi

✅ TAHLIL TUGADI:
   Status: NORMAL
   Farq: 0.0%
   Confidence: 85%
```

---

## 🎯 KEYINGI QADAMLAR

### 1. Bulk tahlil (CRM)
```powershell
python manage.py analyze_properties --model BuildHouse --limit 10
```

### 2. OLX tahlil (agar OLX ma'lumotlar bo'lsa)
```powershell
python manage.py analyze_properties --model OLXProperty --limit 10
```

### 3. Admin Panelda ko'rish
```
http://localhost:8000/admin/market_analysis/propertypriceanalysis/
```

---

## 🐛 TROUBLESHOOTING

### ❌ Problem: "ANTHROPIC_API_KEY not found"

**Solution:**
```python
# core/settings.py
ANTHROPIC_API_KEY = 'your-api-key-here'
```

### ❌ Problem: "No module named 'anthropic'"

**Solution:**
```bash
pip install anthropic pandas requests
```

### ❌ Problem: "Import qilindi: 0 ta"

**Solution:**
- Internet ulanishini tekshiring
- Google Sheets URL'larni tekshiring
- Pandas o'rnatilganini tekshiring

### ❌ Problem: "Property ma'lumotlari to'liq emas"

**Solution:**
BuildHouse obyektda to'ldiring:
- `floor` (qavat)
- `rooms_numbers` (xonalar)
- `total_area` (maydon)
- `price_owner` (narx)

---

## 📊 EXPECTED RESULTS

### Import
✅ **270+ ta** bozor narxi import qilinishi kerak (3 sheet × 2 holat × ~45 qator)

### Tahlil
✅ **Status:** juda_arzon, arzon, normal, qimmat, juda_qimmat
✅ **AI Tahlil:** 100-200 so'z batafsil tahlil
✅ **Tavsiya:** Xaridor va sotuvchi uchun tavsiya

---

## ✅ SUCCESS CRITERIA

1. ✅ Dependencies o'rnatildi
2. ✅ Settings sozlandi
3. ✅ Migration bajarildi
4. ✅ 270+ ta bozor narxi import qilindi
5. ✅ Bitta property muvaffaqiyatli tahlil qilindi
6. ✅ Admin panelda natijalar ko'rinadi

---

## 🎉 TAYYOR!

Agar barcha checklar ✅ bo'lsa, tizim ishga tayyor!

**Keyingi qadamlar:**
1. Barcha CRM propertylarni tahlil qilish
2. OLX scraper'ni ishga tushirish
3. Celery task'larni sozlash (avtomatik tahlil)
4. Frontend UI yaratish

---

**Setup Time:** ~10 daqiqa  
**Testing Time:** ~5 daqiqa  
**Total:** 15 daqiqa

**Status:** 🟢 PRODUCTION READY
