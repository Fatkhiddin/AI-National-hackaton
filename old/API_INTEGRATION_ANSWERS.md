# Megapolis CRM API Integration - Savol va Javoblar

## SAVOLLAR:

1. `/api/objects/` endpoint autentifikatsiyasiz (public) ham ishlaydi yoki faqat authenticated users uchunmi?

2. Mening JWT token bilan `/api/objects/` chaqirganimda bo'sh list [] qaytaryapti, lekin admin panelda 1974 ta obyekt ko'rsatyapti. Nima sabab?

3. Obyektlarni filter qilish uchun to'g'ri query parameter nomlari qanday?
   - xonalar soni: `rooms_numbers` yoki boshqa?
   - narx oralig'i: `min_price`, `max_price` yoki `price_starting__gte`, `price_starting__lte`?
   - kategoriya: `category` (ID) yoki `category__name`?

4. `/api/objects/` response paginated bo'ladimi? 
   - `{"count": 1974, "next": "...", "previous": null, "results": [...]}`
   - Yoki to'g'ridan list: `[{...}, {...}]`?

5. Test uchun qaysi endpoint ishlatishim mumkin va qanday parametrlar bilan?

---

## JAVOBLAR:

### 1. AUTENTIFIKATSIYA

**API Code:**
```python
class BuildHouseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BuildHouse.objects.filter(in_site=True).all()
    serializer_class = BuildHouseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
```

**Javob:** ✅ **Ha, PUBLIC ishlaydi!** 

- `IsAuthenticatedOrReadOnly` - GET so'rovlar uchun login talab qilinmaydi
- POST/PUT/DELETE uchun authentication kerak
- Telegram bot autentifikatsiyasiz ham obyektlarni olishi mumkin

---

### 2. BO'SH LIST [] QAYTARISH SABABI

**ASOSIY MUAMMO:**
```python
queryset = BuildHouse.objects.filter(in_site=True).all()
```

**Tushuntirish:**
- Admin panelda: **1974 ta obyekt**
- API qaytaradi: **Faqat `in_site=True` obyektlar**
- Agar `in_site=False` yoki `null` bo'lsa → **API ko'rsatmaydi**

**YECHIMLAR:**

#### Option A: Obyektlarni saytga chiqarish (TAVSIYA ETILADI)
```python
# fix_in_site.py
from home.models import BuildHouse

# Barcha obyektlarni saytga chiqarish
updated = BuildHouse.objects.update(in_site=True)
print(f"✅ Yangilandi: {updated} ta obyekt")
```

#### Option B: API filterni o'zgartirish (Test uchun)
```python
# api/views.py
class BuildHouseViewSet(viewsets.ReadOnlyModelViewSet):
    # queryset = BuildHouse.objects.filter(in_site=True).all()  # Eski
    queryset = BuildHouse.objects.all()  # Yangi - hammasi
```

#### Option C: Faqat arxivsiz obyektlar
```python
queryset = BuildHouse.objects.filter(is_arxiv=False).all()
```

---

### 3. TO'G'RI QUERY PARAMETER NOMLARI

**BuildHouseFilter klassidan olingan to'g'ri parameter nomlari:**

#### Asosiy filterlar:
```bash
# XONALAR SONI (exact match)
?rooms_numbers=3

# YOTOQ XONALAR SONI
?bedrooms_num=2

# NARX ORALIG'I (USD yoki UZS)
?min_price=50000&max_price=100000

# MAYDON ORALIG'I (m²)
?min_area=70&max_area=150

# QAVAT
?floor=5

# UMUMIY QAVATLAR SONI
?floor_build=9

# QURILISH YILI
?year_construction=2020

# KATEGORIYA (ID - ForeignKey)
?category=1

# SOTUV TURI (ID - ManyToMany)
?sale_type=1

# IJARA TURI (ID - ManyToMany)
?rent=1

# SUB KATEGORIYA (ID - ManyToMany)
?sub_category=2
```

#### Qo'shimcha filterlar:
```bash
# TA'MIRLASH HOLATI (ID)
?state_repair=1

# MEBEL (ID)
?furniture=1

# BALKON (ID - ManyToMany)
?balcony=1

# LIFT (ID - ManyToMany)
?elevator=1

# PARKOVKA (ID - ManyToMany)
?parking=1

# HAMMOM (ID - ManyToMany)
?bathroom=1

# ISITISH TIZIMI (ID - ManyToMany)
?heating_system=1

# GAZ (ID - ManyToMany)
?gas=1

# SUV (ID - ManyToMany)
?water=1

# GARAJ (ID - ManyToMany)
?garage=1

# AQLLI UY TIZIMI (Boolean)
?smart_home=true

# KANALIZATSIYA (Boolean)
?sewerage=true

# TEMIR YO'L (Boolean)
?railway_branch=true

# BINO TURI (ID - ForeignKey)
?type_building=1

# MULK TURI (ID - ForeignKey)
?property_type=1

# ICHIDA MAVJUD (ID - ManyToMany)
?inside_has=1

# YAQINIDA MAVJUD (ID - ManyToMany)
?nearby_has=1

# FULL TEXT SEARCH (name, address, content)
?search=Chilonzor
```

#### MUHIM ESLATMALAR:
- **ForeignKey** fieldlar → ID orqali: `?category=1`
- **ManyToMany** fieldlar → ID orqali: `?parking=1` 
- **Boolean** fieldlar → `true/false`: `?smart_home=true`
- **Number** fieldlar → Raqam: `?rooms_numbers=3`
- **Range** fieldlar → `min_/max_` prefix: `?min_price=50000&max_price=100000`

---

### 4. RESPONSE FORMAT

**Javob:** ✅ **Ha, PAGINATED format**

**Django REST Framework default pagination:**
```json
{
  "count": 1974,
  "next": "http://megapolis1.uz/api/objects/?page=2",
  "previous": null,
  "results": [
    {
      "id": 123,
      "name": "3 xonali kvartira Chilonzor tumani",
      "slug": "3-xonali-kvartira-chilonzor-tumani-123",
      "created_at": "2025-03-15T10:30:00Z",
      "updated_at": "2025-03-20T14:20:00Z",
      "category": {
        "id": 1,
        "name": "Kvartira"
      },
      "rooms_numbers": 3,
      "floor": 5,
      "floor_build": 9,
      "total_area": 85.5,
      "price_starting": 75000.0,
      "price_type": "usd",
      "address": {
        "id": 45,
        "name": "Chilonzor",
        "full_address": "Toshkent, Chilonzor tumani"
      },
      "build_house_images": [
        {
          "image": "/media/houses/image1.jpg"
        }
      ]
    }
  ]
}
```

**Sahifalash:**
- Default: Birinchi sahifa
- `?page=2` - Ikkinchi sahifa
- `?page=3` - Uchinchi sahifa
- `count` - Jami obyektlar soni
- `next` - Keyingi sahifa URL
- `previous` - Oldingi sahifa URL

---

### 5. TEST ENDPOINTLAR

#### 🔧 AVVAL: Obyektlarni saytga chiqarish
```bash
# Terminal da
cd d:\megapolis-crm
python fix_in_site.py
```

#### 📡 TEST SO'ROVLAR:

##### A) Oddiy testlar:
```bash
# 1. Barcha obyektlar (birinchi sahifa)
GET http://megapolis1.uz/api/objects/

# 2. Ikkinchi sahifa
GET http://megapolis1.uz/api/objects/?page=2

# 3. Bitta obyekt (detail)
GET http://megapolis1.uz/api/objects/123/
```

##### B) Filter testlar:
```bash
# 4. 3 xonali kvartiralar
GET http://megapolis1.uz/api/objects/?rooms_numbers=3

# 5. Narx oralig'i: $50k-$100k
GET http://megapolis1.uz/api/objects/?min_price=50000&max_price=100000

# 6. Maydon: 70-150 m²
GET http://megapolis1.uz/api/objects/?min_area=70&max_area=150

# 7. Chilonzorda qidirish
GET http://megapolis1.uz/api/objects/?search=Chilonzor

# 8. 2020 yildan keyingi yangi binolar
GET http://megapolis1.uz/api/objects/?year_construction=2020
```

##### C) Ko'p filterli testlar:
```bash
# 9. 3 xonali, 70-100m², $50k-$80k, Chilonzor
GET http://megapolis1.uz/api/objects/?rooms_numbers=3&min_area=70&max_area=100&min_price=50000&max_price=80000&search=Chilonzor

# 10. Liftli, parkovkali, aqlli uy
GET http://megapolis1.uz/api/objects/?elevator=1&parking=1&smart_home=true

# 11. Kvartira kategoriyasi, mebellanmagan
GET http://megapolis1.uz/api/objects/?category=1&furniture=1
```

##### D) Reference data testlar:
```bash
# 12. Kategoriyalar ro'yxati
GET http://megapolis1.uz/api/Categorys/

# 13. Sub kategoriyalar
GET http://megapolis1.uz/api/SubCategorys/

# 14. Ta'mirlash holatlari
GET http://megapolis1.uz/api/StateRepairs/

# 15. Mebel turlari
GET http://megapolis1.uz/api/Furnitures/

# 16. Manzillar
GET http://megapolis1.uz/api/addresses/
```

---

## TELEGRAM BOT UCHUN SAMPLE CODE

```python
import requests

class MegapolisCRM:
    def __init__(self, base_url="https://megapolis1.uz"):
        self.base_url = base_url
    
    def search_properties(self, filters):
        """
        Obyektlarni qidirish
        
        filters = {
            'rooms_numbers': 3,
            'min_price': 50000,
            'max_price': 80000,
            'min_area': 70,
            'max_area': 100,
            'search': 'Chilonzor'
        }
        """
        url = f"{self.base_url}/api/objects/"
        response = requests.get(url, params=filters)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.status_code, "message": response.text}
    
    def get_categories(self):
        """Kategoriyalar ro'yxati"""
        url = f"{self.base_url}/api/Categorys/"
        response = requests.get(url)
        return response.json()
    
    def format_for_telegram(self, property_data):
        """CRM obyektini Telegram message formatiga o'girish"""
        message = f"🏠 **{property_data['name']}**\n\n"
        
        # Narx
        price = property_data.get('price_starting')
        currency = property_data.get('price_type', 'usd')
        if price:
            symbol = "$" if currency == 'usd' else "so'm"
            message += f"💰 Narx: {price:,.0f} {symbol}\n"
        
        # Xonalar
        rooms = property_data.get('rooms_numbers')
        if rooms:
            message += f"🚪 Xonalar: {rooms} ta\n"
        
        # Maydon
        area = property_data.get('total_area')
        if area:
            message += f"📐 Maydon: {area} m²\n"
        
        # Qavat
        floor = property_data.get('floor')
        floor_build = property_data.get('floor_build')
        if floor and floor_build:
            message += f"🏢 Qavat: {floor}/{floor_build}\n"
        
        # Yili
        year = property_data.get('year_construction')
        if year:
            message += f"📅 Yil: {year}\n"
        
        # Manzil
        address = property_data.get('address', {})
        if address:
            full_addr = address.get('full_address', address.get('name', ''))
            message += f"📍 Manzil: {full_addr}\n"
        
        # Qisqa tavsif
        content_adv = property_data.get('content_advertising')
        if content_adv:
            message += f"\n{content_adv}\n"
        
        # Rasmlar
        images = property_data.get('build_house_images', [])
        if images:
            message += f"\n🖼️ {len(images)} ta rasm"
        
        return message

# Ishlatish namunasi
crm = MegapolisCRM()

# 1. Kategoriyalarni olish
categories = crm.get_categories()
print("Kategoriyalar:", categories)

# 2. Obyektlarni qidirish
results = crm.search_properties({
    'rooms_numbers': 3,
    'min_price': 50000,
    'max_price': 80000,
    'search': 'Chilonzor'
})

print(f"Topildi: {results['count']} ta obyekt")

# 3. Birinchi natijani Telegram formatda ko'rsatish
if results['results']:
    first_property = results['results'][0]
    telegram_message = crm.format_for_telegram(first_property)
    print(telegram_message)
```

---

## CURL MISOLLAR

```bash
# 1. Barcha obyektlar
curl -X GET "http://megapolis1.uz/api/objects/"

# 2. Filterli qidiruv
curl -X GET "http://megapolis1.uz/api/objects/?rooms_numbers=3&min_price=50000&max_price=100000"

# 3. Full text search
curl -X GET "http://megapolis1.uz/api/objects/?search=Chilonzor"

# 4. Kategoriyalar
curl -X GET "http://megapolis1.uz/api/Categorys/"

# 5. JWT bilan (agar kerak bo'lsa)
curl -X POST "http://megapolis1.uz/api/login/" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_user", "password": "your_pass"}'

# Token bilan so'rov
curl -X GET "http://megapolis1.uz/api/objects/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## XULOSA

| Savol | Javob |
|-------|-------|
| **1. Public API?** | ✅ Ha, autentifikatsiya talab qilinmaydi (GET uchun) |
| **2. Bo'sh list sababi?** | ❌ `in_site=True` filter - obyektlar saytda yo'q. `fix_in_site.py` ni ishga tushiring |
| **3. Parameter nomlari?** | ✅ `rooms_numbers`, `min_price`, `max_price`, `category`, `search` |
| **4. Pagination?** | ✅ Ha, `{count, next, previous, results}` format |
| **5. Test endpoint?** | ✅ Yuqoridagi URL larni sinab ko'ring |

**Birinchi qadam:** `python fix_in_site.py` - Obyektlarni saytga chiqarish! 🚀
