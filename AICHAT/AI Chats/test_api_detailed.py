"""
Detailed CRM API Test - Check what data exists
"""
import requests
import json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY0Mjc0MDMyLCJpYXQiOjE3NjQyNzA0MzIsImp0aSI6IjU1ZTE0MDc3NTgwMzQ3M2I4ZWUyOTkyMjcyMGEzZjdlIiwidXNlcl9pZCI6MTR9.knSgJuw8assYGcSYX8uJJZhXjXdnys3a5fR0EjhQNg0"
BASE_URL = "https://megapolis1.uz"

headers = {"Authorization": f"Bearer {TOKEN}"}

print("=" * 70)
print("TEST 1: Get first 10 objects without any filters")
print("=" * 70)

response = requests.get(
    f"{BASE_URL}/api/objects/", 
    headers=headers, 
    params={"page_size": 5},  # Try page_size instead of limit
    timeout=30
)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    
    if isinstance(data, dict) and 'results' in data:
        properties = data['results']
        total = data.get('count', 0)
    elif isinstance(data, list):
        properties = data
        total = len(data)
    else:
        properties = []
        total = 0
    
    print(f"✅ Total in database: {total}")
    print(f"📦 Returned: {len(properties)}")
    
    if properties:
        print(f"\n📋 First 3 properties sample:\n")
        for i, prop in enumerate(properties[:3], 1):
            print(f"{i}. {prop.get('name', 'N/A')}")
            print(f"   ID: {prop.get('id')}")
            print(f"   Rooms: {prop.get('rooms_numbers')}")
            print(f"   Price: {prop.get('price_starting')} {prop.get('price_type')}")
            print(f"   Area: {prop.get('total_area')} m²")
            print(f"   Category: {prop.get('category')}")
            print(f"   Available keys: {list(prop.keys())[:15]}")
            print()
    else:
        print("❌ No properties returned!")
        print(f"Response type: {type(data)}")
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
else:
    print(f"❌ Error {response.status_code}")
    print(response.text[:500])

print("\n" + "=" * 70)
print("TEST 2: Try with category filter (Turar = 1)")
print("=" * 70)

response = requests.get(f"{BASE_URL}/api/objects/", headers=headers, params={"category": 1, "limit": 5})
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    properties = data.get('results', data) if isinstance(data, dict) else data
    print(f"Found: {len(properties)} properties with category=1")
    
    if properties:
        first = properties[0]
        print(f"\nFirst property:")
        print(f"  Name: {first.get('name')}")
        print(f"  Rooms: {first.get('rooms_numbers')}")
        print(f"  Price: {first.get('price_starting')}")

print("\n" + "=" * 70)
print("TEST 3: Try exact field from documentation")
print("=" * 70)

# Try different parameter combinations
test_params = [
    {"rooms_numbers": 3},
    {"rooms_numbers": 2},
    {"min_price": 30000},
    {"price_starting__gte": 50000, "price_starting__lte": 80000},
]

for params in test_params:
    print(f"\nTrying params: {params}")
    response = requests.get(f"{BASE_URL}/api/objects/", headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        count = data.get('count', len(data)) if isinstance(data, dict) else len(data)
        print(f"  ✅ Found: {count} properties")
    else:
        print(f"  ❌ Error: {response.status_code}")
