"""
Direct API test - 3 xonali, 50k-80k
"""
import requests

BASE_URL = "https://megapolis1.uz"

print("=" * 70)
print("TEST: 3 xonali kvartira, 50,000 dan 80,000 gacha")
print("=" * 70)

# Build params
params = {
    'rooms_numbers': 3,
    'min_price': 50000,
    'max_price': 80000,
    'page_size': 5  # Birinchi 5 ta
}

print(f"\n📦 Params: {params}")
print(f"🌐 URL: {BASE_URL}/api/objects/")

try:
    response = requests.get(
        f"{BASE_URL}/api/objects/",
        params=params,
        timeout=60  # 60 sekund kutamiz
    )
    
    print(f"\n📨 Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        # Check response format
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            total = data.get('count', 0)
            results = data['results']
            print(f"✅ PAGINATION ishlayapti!")
            print(f"   Total: {total} ta obyekt")
        elif isinstance(data, list):
            # Direct list
            results = data
            total = len(data)
            print(f"⚠️ Direct list (pagination yo'q)")
        else:
            results = []
            total = 0
        
        print(f"📊 Topildi: {total} ta 3 xonali kvartira ($50k-$80k)")
        
        if results:
            print(f"\n{'='*70}")
            print(f"BIRINCHI UY:")
            print(f"{'='*70}")
            
            prop = results[0]
            
            # Extract data
            name = prop.get('name', 'N/A')
            rooms = prop.get('rooms_numbers', 'N/A')
            price = prop.get('price_starting', 'N/A')
            price_type = prop.get('price_type', 'usd')
            area = prop.get('total_area', 'N/A')
            floor = prop.get('floor', 'N/A')
            floor_build = prop.get('floor_build', 'N/A')
            
            # Category
            category = prop.get('category')
            if isinstance(category, dict):
                category_name = category.get('name', 'N/A')
            else:
                category_name = f"ID: {category}"
            
            # Sale type
            sale_types = prop.get('sale_type', [])
            if sale_types and isinstance(sale_types[0], dict):
                sale_type_name = ', '.join([st.get('name', '') for st in sale_types])
            else:
                sale_type_name = 'N/A'
            
            # State repair
            state_repair = prop.get('state_repair')
            if isinstance(state_repair, dict):
                repair_name = state_repair.get('name', 'N/A')
            else:
                repair_name = 'N/A'
            
            # Address
            address = prop.get('address')
            if isinstance(address, dict):
                address_name = address.get('name', 'N/A')
            else:
                address_name = 'N/A'
            
            mo_ljal = prop.get('address_house_number', 'N/A')
            
            # Print formatted
            print(f"📋 Sarlavha: {name}")
            print(f"🏠 Kategoriya: {category_name}")
            print(f"💵 Sotuv turi: {sale_type_name}")
            print(f"\n🏢 Uy tafsilotlari:")
            print(f"   Xonalar soni: {rooms}")
            print(f"   Qavat: {floor}")
            print(f"   Umumiy qavatlar soni: {floor_build}")
            print(f"   Umumiy maydon: {area} m²")
            print(f"   Ta'mirlash holati: {repair_name}")
            print(f"\n📍 Manzil:")
            print(f"   Hudud: {address_name}")
            print(f"   Mo'ljal: {mo_ljal}")
            print(f"\n💰 Narxlar:")
            print(f"   Sotilish narxi: {price} {price_type}")
            
            # Images
            images = prop.get('build_house_images', [])
            if images:
                print(f"\n🖼️ Rasmlar: {len(images)} ta")
            
            print(f"\n{'='*70}")
            print(f"YANA 4 TA UY:")
            print(f"{'='*70}")
            
            for i, prop in enumerate(results[1:5], 2):
                print(f"\n{i}. {prop.get('name', 'N/A')}")
                print(f"   Narx: {prop.get('price_starting')} {prop.get('price_type')}")
                print(f"   Xonalar: {prop.get('rooms_numbers')}")
                print(f"   Maydon: {prop.get('total_area')} m²")
                print(f"   Qavat: {prop.get('floor')}/{prop.get('floor_build')}")
        else:
            print("\n❌ Hech qanday uy topilmadi bu filterlar bilan")
            
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text[:500])
        
except requests.exceptions.Timeout:
    print("\n❌ TIMEOUT - Server javob bermadi (60 sekund)")
    print("   Pagination ishlamagan bo'lishi mumkin")
except Exception as e:
    print(f"\n❌ Error: {e}")
