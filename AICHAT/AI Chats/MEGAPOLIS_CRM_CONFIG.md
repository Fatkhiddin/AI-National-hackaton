# Megapolis CRM - Pre-configured Settings
# Bu faylni CRM dashboard ga ko'chirib oling

## 1. FIELD MAPPING JSON:

```json
{
  "property_fields": {
    "price_min": "min_price",
    "price_max": "max_price",
    "rooms": "rooms_numbers",
    "bedrooms": "bedrooms_num",
    "area_min": "min_area",
    "area_max": "max_area",
    "floor": "floor",
    "floor_max": "floor_build",
    "location": "search",
    "district": "search",
    "year_construction": "year_construction"
  },
  "special_mappings": {
    "property_type": {
      "apartment": "category",
      "house": "category",
      "villa": "category",
      "commercial": "category",
      "land": "category",
      "note": "Category ID kerak: /api/Categorys/ dan oling"
    },
    "furnished": {
      "field": "furniture",
      "note": "Furniture ID kerak: /api/Furnitures/ dan oling"
    },
    "has_elevator": {
      "field": "elevator",
      "note": "Elevator ID kerak: /api/Elevators/ dan oling"
    },
    "has_parking": {
      "field": "parking",
      "note": "Parking ID kerak: /api/Parking/ dan oling"
    },
    "repair_state": {
      "field": "state_repair",
      "note": "State Repair ID kerak: /api/StateRepairs/ dan oling"
    }
  },
  "response_format": {
    "id": "id",
    "title": "name",
    "slug": "slug",
    "price": "price_starting",
    "price_currency": "price_type",
    "price_bargain": "price_bargain",
    "description": "content",
    "short_description": "content_advertising",
    "rooms": "rooms_numbers",
    "bedrooms": "bedrooms_num",
    "floor": "floor",
    "total_floors": "floor_build",
    "area": "total_area",
    "living_area": "living_area",
    "year_built": "year_construction",
    "address_full": "address.full_address",
    "address_district": "address.name",
    "address_landmark": "address_landwarkr",
    "house_number": "address_house_number",
    "repair_state": "state_repair",
    "furniture": "furniture",
    "property_type": "category.name",
    "building_type": "type_building",
    "elevator": "elevator",
    "parking": "parking",
    "smart_home": "smart_home",
    "images": "build_house_images",
    "google_maps": "google_map",
    "created_at": "created_at",
    "updated_at": "updated_at"
  }
}
```

## 2. REQUEST TEMPLATE JSON:

```json
{
  "method": "GET",
  "endpoint": "/api/objects/",
  "headers": {
    "Authorization": "Bearer {api_key}",
    "Content-Type": "application/json"
  },
  "body_template": {},
  "note": "GET request uses query parameters, not body"
}
```

## 3. AUTHENTICATION:

**Login qilib JWT token olish:**
- POST https://megapolis1.uz/api/login/
- Body: {"username": "your_username", "password": "your_password"}
- Response: {"access": "jwt_token", "refresh": "refresh_token"}

**Access Token** ni API Key sifatida saqlang!

## 4. CRM SOZLASH QADAMLARI:

### CRM Dashboard ga o'ting:
```
http://localhost:8000/crm/
```

### "CRM Qo'shish" tugmasini bosing:

**ASOSIY TAB:**
- CRM Nomi: `Megapolis CRM`
- CRM Turi: `Custom API`
- API URL: `https://megapolis1.uz`
- API Key: `JWT Access Token ni kiriting` (login dan olgan)
- API Secret: `Bo'sh qoldiring`

**FIELD MAPPING TAB:**
Yuqoridagi birinchi JSON ni ko'chiring

**REQUEST TEMPLATE TAB:**
Yuqoridagi ikkinchi JSON ni ko'chiring

**AI PROMPT TAB:**
Bo'sh qoldiring (default prompt yetarli)

### Test qiling va Saqlang!

---

## 5. QIDIRUV MISOLLARI:

### Misol 1: Oddiy qidiruv
```
AI Input:
{
  "property_type": "apartment",
  "rooms": 3,
  "price_min": 50000,
  "price_max": 80000,
  "location": "Chilonzor"
}

CRM Query:
GET /api/objects/?rooms_numbers=3&min_price=50000&max_price=80000&search=Chilonzor
```

### Misol 2: Yangi bino
```
AI Input:
{
  "rooms": 3,
  "new_building": true,
  "area_min": 70,
  "area_max": 100
}

CRM Query:
GET /api/objects/?rooms_numbers=3&year_construction__gte=2020&min_area=70&max_area=100
```

---

## 6. TELEGRAM MESSAGE FORMAT:

```python
def format_property_for_telegram(property_data):
    message = f"🏠 **{property_data['name']}**\n\n"
    
    # Narx
    price = property_data['price_starting']
    currency = '💵 USD' if property_data['price_type'] == 'usd' else '💰 UZS'
    message += f"💰 Narx: {price:,.0f} {currency}\n"
    
    if property_data.get('price_bargain'):
        message += "✅ Kelishish mumkin\n"
    
    # Xonalar va maydon
    message += f"🚪 Xonalar: {property_data['rooms_numbers']}\n"
    if property_data.get('bedrooms_num'):
        message += f"🛏 Yotoq xonalar: {property_data['bedrooms_num']}\n"
    message += f"📐 Maydon: {property_data['total_area']} m²\n"
    
    # Qavat
    message += f"🏢 Qavat: {property_data['floor']}/{property_data['floor_build']}\n"
    
    # Yil
    if property_data.get('year_construction'):
        message += f"📅 Qurilish yili: {property_data['year_construction']}\n"
    
    # Manzil
    if property_data.get('address'):
        address = property_data['address']['full_address']
        message += f"📍 Manzil: {address}\n"
        
        if property_data.get('address_landwarkr'):
            message += f"🗺 Mo'ljal: {property_data['address_landwarkr']}\n"
    
    # Qo'shimcha
    if property_data.get('furniture'):
        message += f"🪑 {property_data['furniture']}\n"
    
    if property_data.get('state_repair'):
        message += f"🔧 {property_data['state_repair']}\n"
    
    if property_data.get('smart_home'):
        message += "🤖 Aqlli uy tizimi\n"
    
    # Tavsif
    if property_data.get('content_advertising'):
        message += f"\n📝 {property_data['content_advertising']}\n"
    
    # Link
    slug = property_data.get('slug')
    if slug:
        message += f"\n🔗 https://megapolis1.uz/object/{slug}/\n"
    
    return message
```

---

## 7. MUHIM ESLATMALAR:

⚠️ **JWT Token muddati:**
- Access token 1-2 soat ishlaydi
- Expires bo'lsa, refresh token bilan yangilash kerak
- Yoki qayta login qiling

⚠️ **Category ID lar:**
- Kvartira, Uy, Villa uchun ID lar turlicha
- `/api/Categorys/` dan olishingiz kerak
- Property type mapping da ID ishlatish kerak

⚠️ **Search parameter:**
- Full-text search (name, address, content)
- Location va district uchun ishlatiladi

⚠️ **Range filters:**
- `min_price`, `max_price` - narx oralig'i
- `min_area`, `max_area` - maydon oralig'i
- `year_construction__gte` - yildan katta yoki teng (yangi bino)

---

Barcha tayyor! CRM Dashboard ga o'ting va sozlang! 🚀
