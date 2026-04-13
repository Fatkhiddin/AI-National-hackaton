"""
Test Megapolis CRM API - Real requests
"""
import requests
import json

# Sizning token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY0Mjc0MDMyLCJpYXQiOjE3NjQyNzA0MzIsImp0aSI6IjU1ZTE0MDc3NTgwMzQ3M2I4ZWUyOTkyMjcyMGEzZjdlIiwidXNlcl9pZCI6MTR9.knSgJuw8assYGcSYX8uJJZhXjXdnys3a5fR0EjhQNg0"

BASE_URL = "https://megapolis1.uz"

def test_api():
    print("🧪 Testing Megapolis CRM API...\n")
    
    # Test 1: Get all objects without filters
    print("=" * 60)
    print("Test 1: GET /api/objects/ (no filters)")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    response = requests.get(f"{BASE_URL}/api/objects/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        
        if isinstance(data, dict):
            print(f"Response keys: {list(data.keys())}")
            
            if 'results' in data:
                print(f"Total count: {data.get('count', 0)}")
                print(f"Results found: {len(data['results'])}")
                
                if data['results']:
                    first = data['results'][0]
                    print(f"\nFirst property sample:")
                    print(f"  ID: {first.get('id')}")
                    print(f"  Name: {first.get('name')}")
                    print(f"  Rooms: {first.get('rooms_numbers')}")
                    print(f"  Price: {first.get('price_starting')} {first.get('price_type')}")
                    print(f"  Area: {first.get('total_area')} m²")
                    print(f"  Floor: {first.get('floor')}/{first.get('floor_build')}")
        elif isinstance(data, list):
            print(f"Response is a list with {len(data)} items")
            if data:
                first = data[0]
                print(f"\nFirst property sample:")
                print(f"  ID: {first.get('id')}")
                print(f"  Name: {first.get('name')}")
                print(f"  Rooms: {first.get('rooms_numbers')}")
                print(f"  Price: {first.get('price_starting')} {first.get('price_type')}")
                print(f"  Area: {first.get('total_area')} m²")
                print(f"  Keys: {list(first.keys())[:10]}")
        else:
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
    
    print("\n")
    
    # Test 2: Search with filters (3 xona, 50k-80k)
    print("=" * 60)
    print("Test 2: GET /api/objects/ with filters")
    print("Query: 3 xonali, 50,000-80,000")
    print("=" * 60)
    
    params = {
        'rooms_numbers': 3,
        'min_price': 50000,
        'max_price': 80000
    }
    
    print(f"Params: {params}")
    
    response = requests.get(f"{BASE_URL}/api/objects/", headers=headers, params=params)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        
        properties = data.get('results', data) if isinstance(data, dict) else data
        print(f"Total matches: {data.get('count', len(properties)) if isinstance(data, dict) else len(properties)}")
        
        if properties:
            print(f"\nFound {len(properties)} properties (showing first 3):")
            for i, prop in enumerate(properties[:3], 1):
                print(f"\n  {i}. {prop.get('name', 'N/A')}")
                print(f"     Rooms: {prop.get('rooms_numbers')}")
                print(f"     Price: {prop.get('price_starting')} {prop.get('price_type')}")
                print(f"     Area: {prop.get('total_area')} m²")
        else:
            print("No properties found with these filters")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
    
    print("\n")
    
    # Test 3: Get categories
    print("=" * 60)
    print("Test 3: GET /api/Categorys/ (to get category IDs)")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/Categorys/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        
        if isinstance(data, list):
            print(f"Categories ({len(data)}):")
            for cat in data:
                print(f"  ID: {cat.get('id')} - {cat.get('name')}")
        else:
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
    else:
        print(f"❌ Error: {response.status_code}")

if __name__ == "__main__":
    test_api()
