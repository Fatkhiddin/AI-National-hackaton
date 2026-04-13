"""
Test CRM API with pagination - Get real property data
"""
import requests
import json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY0Mjc0MDMyLCJpYXQiOjE3NjQyNzA0MzIsImp0aSI6IjU1ZTE0MDc3NTgwMzQ3M2I4ZWUyOTkyMjcyMGEzZjdlIiwidXNlcl9pZCI6MTR9.knSgJuw8assYGcSYX8uJJZhXjXdnys3a5fR0EjhQNg0"
BASE_URL = "https://megapolis1.uz"

def test_pagination():
    print("=" * 70)
    print("TEST: Get properties with pagination (page 1)")
    print("=" * 70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/objects/",
            params={"page": 1, "page_size": 5},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if paginated
            if isinstance(data, dict) and 'results' in data:
                print(f"✅ PAGINATION ISHLAYAPTI!")
                print(f"   Total: {data.get('count')} ta obyekt")
                print(f"   Current page: {data.get('current_page', 1)}")
                print(f"   Total pages: {data.get('total_pages', '?')}")
                print(f"   Returned: {len(data['results'])} ta obyekt")
                print(f"   Next: {'Ha' if data.get('next') else 'Yo\'q'}")
                
                properties = data['results']
            else:
                print(f"⚠️ Response is list (no pagination)")
                properties = data[:5] if isinstance(data, list) else []
            
            # Show first property
            if properties:
                print(f"\n{'='*70}")
                print(f"BIRINCHI OBYEKT:")
                print(f"{'='*70}")
                
                prop = properties[0]
                
                print(f"📋 Sarlavha: {prop.get('name', 'N/A')}")
                
                category = prop.get('category')
                if isinstance(category, dict):
                    print(f"🏠 Kategoriya: {category.get('name', 'N/A')}")
                else:
                    print(f"🏠 Kategoriya ID: {category}")
                
                sale_types = prop.get('sale_type', [])
                if sale_types:
                    if isinstance(sale_types[0], dict):
                        print(f"💵 Sotuv turi: {', '.join([st.get('name', '') for st in sale_types])}")
                    else:
                        print(f"💵 Sotuv turi IDs: {sale_types}")
                
                print(f"\n🏢 Uy tafsilotlari:")
                print(f"   Xonalar soni: {prop.get('rooms_numbers', 'N/A')}")
                print(f"   Qavat: {prop.get('floor', 'N/A')}")
                print(f"   Umumiy qavatlar: {prop.get('floor_build', 'N/A')}")
                print(f"   Maydon: {prop.get('total_area', 'N/A')} m²")
                
                state_repair = prop.get('state_repair')
                if isinstance(state_repair, dict):
                    print(f"   Ta'mir: {state_repair.get('name', 'N/A')}")
                
                print(f"\n💰 Narxlar:")
                print(f"   Narx: {prop.get('price_starting', 'N/A')} {prop.get('price_type', 'usd')}")
                print(f"   Kelishish: {'Ha' if prop.get('price_bargain') else 'Yo\'q'}")
                
                address = prop.get('address')
                if isinstance(address, dict):
                    print(f"\n📍 Manzil: {address.get('name', 'N/A')}")
                
                house_number = prop.get('address_house_number')
                if house_number:
                    print(f"   Mo'ljal: {house_number}")
                
                images = prop.get('build_house_images', [])
                if images:
                    print(f"\n🖼️ Rasmlar: {len(images)} ta")
                    if images and isinstance(images[0], dict):
                        print(f"   Birinchi rasm: {images[0].get('image', 'N/A')}")
                
                print(f"\n📋 Available keys: {list(prop.keys())[:20]}")
                
                # Show full JSON
                print(f"\n{'='*70}")
                print(f"FULL JSON (first property):")
                print(f"{'='*70}")
                print(json.dumps(prop, indent=2, ensure_ascii=False)[:2000])
                print("...(truncated)")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:500])
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT - API hali ham juda sekin!")
        print(f"   Pagination to'g'ri sozlanmagandir")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_with_filter():
    print(f"\n{'='*70}")
    print("TEST: Filter - 1 xonali kvartira")
    print(f"{'='*70}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/objects/",
            params={
                "rooms_numbers": 1,
                "page": 1,
                "page_size": 3
            },
            timeout=20
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, dict) and 'results' in data:
                count = data.get('count', 0)
                results = data['results']
            else:
                count = len(data) if isinstance(data, list) else 0
                results = data[:3] if isinstance(data, list) else []
            
            print(f"✅ Topildi: {count} ta 1 xonali kvartira")
            
            if results:
                print(f"\nBirinchi 3 tasi:")
                for i, prop in enumerate(results, 1):
                    print(f"\n{i}. {prop.get('name', 'N/A')}")
                    print(f"   Narx: {prop.get('price_starting')} {prop.get('price_type')}")
                    print(f"   Maydon: {prop.get('total_area')} m²")
                    print(f"   Qavat: {prop.get('floor')}/{prop.get('floor_build')}")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_pagination()
    test_with_filter()
