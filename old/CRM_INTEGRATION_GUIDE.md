# CRM Integration - Copilot Chat Prompt

## Sizning vazifa:

Sizda CRM tizimi bor (uy-joy sotuvi uchun). Bu CRM ni Telegram bilan integratsiya qilish kerak.

## Copilot Chat ga berish kerak bo'lgan PROMPT:

```
Men uy-joy sotish CRM tizimini Telegram bilan integratsiya qilyapman. 
Telegram suhbatdan AI mijoz talablarini aniqlaydi va CRM dan mos uylarni qidiradi.

Mening CRM tizimimni tahlil qiling va quyidagilarni bering:

1. CRM DATABASE STRUCTURE:
   - Uylar jadvali (properties/houses) qanday tuzilgan?
   - Qaysi fieldlar bor? (price, rooms, area, location, etc.)
   - Field nomlari va ma'lumot turlari

2. CRM API ENDPOINTS:
   - Uylarni qidirish uchun qaysi API endpoint ishlatiladi?
   - HTTP Method? (GET/POST)
   - Request format (JSON, query params, etc.)
   - Authentication usuli (API Key, Bearer Token, etc.)

3. FIELD MAPPING JSON:
   AI dan keladigan standart fieldlarni CRM fieldlariga moslashtirish uchun JSON yarating:
   
   AI dan keladigan fieldlar:
   - property_type (apartment/house/villa)
   - price_min, price_max
   - rooms
   - area_min, area_max
   - location, district
   - floor_min, floor_max
   - furnished, new_building
   
   CRM ga mos keltirilgan JSON:
   {
     "property_fields": {
       "price_min": "SIZNING_CRM_FIELD_NOMI",
       "price_max": "SIZNING_CRM_FIELD_NOMI",
       ...
     },
     "response_format": {
       "id": "SIZNING_CRM_FIELD_NOMI",
       "title": "SIZNING_CRM_FIELD_NOMI",
       "price": "SIZNING_CRM_FIELD_NOMI",
       "description": "SIZNING_CRM_FIELD_NOMI"
     }
   }

4. REQUEST TEMPLATE JSON:
   API so'rov qilish uchun template:
   {
     "method": "POST",
     "endpoint": "/api/properties/search",
     "headers": {
       "Authorization": "Bearer {api_key}",
       "Content-Type": "application/json"
     },
     "body_template": {
       "filters": "{search_criteria}",
       "limit": 10
     }
   }

5. API RESPONSE FORMAT:
   CRM dan qanday formatda javob keladi?
   - Array yoki Object?
   - Uylar ro'yxati qaysi fieldda? (data, properties, items, results?)
   - Har bir uy obyekti qanday ko'rinadi?

MISOL JAVOB FORMATI:

CRM Database Structure:
- Table: properties
  - id (INT)
  - title (VARCHAR)
  - price (DECIMAL)
  - rooms (INT)
  - area (FLOAT)
  - location (VARCHAR)
  - district (VARCHAR)
  - floor (INT)
  - total_floors (INT)
  - property_type (ENUM: apartment, house, villa)
  - is_furnished (BOOLEAN)
  - is_new_building (BOOLEAN)
  - description (TEXT)
  - images (JSON)
  - created_at (DATETIME)

API Endpoint:
- URL: https://your-crm.com/api/v1/properties/search
- Method: POST
- Headers: 
  - Authorization: Bearer YOUR_API_KEY
  - Content-Type: application/json
- Request Body:
  {
    "filters": {
      "price_range": {"min": 50000, "max": 100000},
      "rooms": 3,
      "area_range": {"min": 70, "max": 120},
      "location": "Tashkent",
      "property_type": "apartment"
    },
    "limit": 10,
    "offset": 0
  }
- Response:
  {
    "success": true,
    "data": [
      {
        "id": 123,
        "title": "3-xonali kvartira",
        "price": 75000,
        "rooms": 3,
        "area": 85,
        "location": "Tashkent",
        "district": "Yunusobod",
        "floor": 5,
        "total_floors": 12,
        "property_type": "apartment",
        "is_furnished": true,
        "description": "...",
        "images": ["url1", "url2"]
      }
    ],
    "total": 45,
    "page": 1
  }

Field Mapping JSON:
{
  "property_fields": {
    "price_min": "price_range.min",
    "price_max": "price_range.max",
    "rooms": "rooms",
    "area_min": "area_range.min",
    "area_max": "area_range.max",
    "location": "location",
    "district": "district",
    "property_type": "property_type",
    "floor_min": "floor",
    "furnished": "is_furnished",
    "new_building": "is_new_building"
  },
  "response_format": {
    "id": "id",
    "title": "title",
    "price": "price",
    "description": "description",
    "images": "images",
    "rooms": "rooms",
    "area": "area",
    "location": "location"
  }
}

Request Template JSON:
{
  "method": "POST",
  "endpoint": "/api/v1/properties/search",
  "headers": {
    "Authorization": "Bearer {api_key}",
    "Content-Type": "application/json"
  },
  "body_template": {
    "filters": "{search_criteria}",
    "limit": 10,
    "offset": 0
  }
}
```

---

## Copilot dan javob kelgach:

1. **CRM Dashboard** ga o'ting: `http://localhost:8000/crm/`
2. **"CRM Qo'shish"** tugmasini bosing
3. Formani to'ldiring:
   - **Asosiy** tab: API URL, API Key
   - **Field Mapping** tab: Copilot dan kelgan JSON ni kiriting
   - **AI Prompt** tab: Bo'sh qoldiring (default ishlatiladi)
4. **"Connection Test"** qiling
5. **Saqlang**

---

## Test qilish:

1. Telegram da mijoz bilan suhbat oching
2. AI Assistant yoqing
3. Mijoz uy talablarini aytsin:
   - "3 xonali kvartira kerak"
   - "Narx 50,000 dan 100,000 gacha"
   - "Yunusobod tumani"
4. CRM avtomatik qidiradi va natijalarni yuboradi!

---

## Qo'shimcha sozlamalar:

### Custom AI Extraction Prompt:

Agar default prompt yetarli bo'lmasa, o'zingiznikini yozishingiz mumkin:

```
Siz uy-joy ekspertisiz. Quyidagi suhbatdan mijoz talablarini chiqaring:

SUHBAT: {summary_json}

JAVOB (faqat JSON):
{
  "property_type": "...",
  "price_min": 0,
  "price_max": 0,
  "rooms": 0,
  "area_min": 0,
  "location": "...",
  "urgent": true/false
}
```

### Multiple CRM Support:

Har xil CRM uchun alohida provider yaratishingiz mumkin:
- **CRM 1**: Tashkent uylar
- **CRM 2**: Samarqand uylar
- **CRM 3**: Yangi qurilish

Har biri o'z API va field mapping ga ega!

---

## Savol-javoblar:

**Q: CRM API yo'qmi?**
A: "Simple JSON File" turini tanlang va JSON file dan o'qing

**Q: CRM authentication murakkabmi?**
A: Request Template da headers ni sozlang (OAuth, JWT, etc.)

**Q: Field nomlar mos kelmasami?**
A: Field Mapping da nested structure ishlatishingiz mumkin: `"price.min"` -> `{"price": {"min": 50000}}`

**Q: AI noto'g'ri tahlil qilyaptimi?**
A: Custom extraction prompt yozing va aniqroq ko'rsatma bering

---

Bu tayyor! Copilot ga yuboring va javobni kutamiz! 🚀
