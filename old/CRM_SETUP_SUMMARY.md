# CRM Integration - QISQA YO'RIQNOMA

## ✅ NIMA QILDIK?

### 1. **Database Models** (models.py)
- `CRMProvider` - CRM tizimni saqlash (API, field mapping, etc.)
- `PropertySearchLog` - Qidiruvlar tarixini saqlash

### 2. **CRM Service** (crm_service.py)
- AI bilan suhbatni tahlil qilish
- CRM API ga so'rov yuborish
- Field mapping (AI -> CRM format)
- Natijalarni parse qilish

### 3. **Views** (views.py)
- CRM Provider CRUD
- API test qilish
- Property search (AI + CRM)

### 4. **UI** (templates/crm_dashboard.html)
- CRM provider qo'shish modal
- Field mapping JSON editor
- Test qilish interface

### 5. **Admin Panel** (admin.py)
- CRM Provider admin
- Search logs admin

---

## 📝 COPILOT GA NIMA DEYISH KERAK?

`CRM_INTEGRATION_GUIDE.md` faylini oching va ichidagi **PROMPT** ni ko'chiring:

```
Men uy-joy sotish CRM tizimini Telegram bilan integratsiya qilyapman...
```

Copilot sizga beradi:
1. ✅ Database structure
2. ✅ API endpoints
3. ✅ Field mapping JSON
4. ✅ Request template JSON
5. ✅ Response format

---

## 🚀 QANDAY ISHLATISH?

### 1-qadam: Migration yarating
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2-qadam: CRM Dashboard ga o'ting
```
http://localhost:8000/crm/
```

### 3-qadam: CRM Provider qo'shing
- **"CRM Qo'shish"** tugmasini bosing
- **Asosiy** tab: API URL, API Key kiriting
- **Field Mapping** tab: Copilot dan JSON kiriting
- **Connection Test** qiling
- **Saqlang**

### 4-qadam: Test qiling!
1. Telegram da mijoz bilan suhbat
2. AI Assistant yoqilgan bo'lsin
3. Mijoz: "3 xonali kvartira kerak, narx 50,000-100,000"
4. CRM avtomatik uylarni topadi va yuboradi! 🎉

---

## 📂 QAYSI FAYLLAR O'ZGARDI?

```
home/
├── models.py                  ✅ CRMProvider, PropertySearchLog
├── crm_service.py            ✅ YANGI - CRM logic
├── views.py                  ✅ CRM views
├── urls.py                   ✅ CRM URLs
├── admin.py                  ✅ CRM Admin
templates/
├── base.html                 ✅ Navigation
└── home/
    └── crm_dashboard.html    ✅ YANGI - CRM UI
docs/
└── CRM_INTEGRATION_GUIDE.md  ✅ YANGI - Copilot prompt
```

---

## 🔥 MUHIM!

### Field Mapping nima?

AI dan keladigan field larni CRM field lariga moslashtirish:

```json
{
  "property_fields": {
    "price_min": "price.min",      ← AI: price_min → CRM: price.min
    "price_max": "price.max",      ← AI: price_max → CRM: price.max
    "rooms": "rooms",              ← AI: rooms → CRM: rooms
    "location": "district"         ← AI: location → CRM: district
  }
}
```

### Request Template nima?

CRM ga qanday so'rov yuborishni ko'rsatadi:

```json
{
  "method": "POST",
  "endpoint": "/api/properties/search",
  "headers": {
    "Authorization": "Bearer {api_key}"
  },
  "body_template": {
    "filters": "{search_criteria}",
    "limit": 10
  }
}
```

---

## ❓ SAVOL-JAVOB

**Q: CRM API yo'q, faqat database bormi?**
→ Custom API endpoint yozing yoki "Simple JSON File" dan foydalaning

**Q: Har xil CRM uchun ishlaydimi?**
→ HA! Field mapping orqali istalgan CRM ga moslashadi

**Q: Bir nechta CRM bilan ishlay olamanmi?**
→ HA! Har bir CRM uchun alohida provider yarating

**Q: AI noto'g'ri tahlil qilsachi?**
→ Custom extraction prompt yozing (AI Prompt tab)

---

## 🎯 KEYINGI QADAMLAR

1. ✅ Migration yaratish
2. ✅ Copilot ga so'rash (CRM strukturani olish)
3. ✅ CRM Provider sozlash
4. ✅ Test qilish
5. ✅ Production ga o'tkazish

---

## 💡 MASLAHAT

- **Test muhim!** Har doim "Connection Test" ni ishlating
- **Field Mapping** ni ehtiyotkorlik bilan to'ldiring
- **Error messages** ni o'qing - ularda ko'p ma'lumot bor
- **Search Logs** ga qarang - nima bo'layotganini ko'rasiz

---

**Barcha tayyor! Copilot ga yuboring va CRM strukturangizni oling!** 🚀
