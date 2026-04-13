"""
Simple test - get single object by ID
"""
import requests

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY0Mjc0MDMyLCJpYXQiOjE3NjQyNzA0MzIsImp0aSI6IjU1ZTE0MDc3NTgwMzQ3M2I4ZWUyOTkyMjcyMGEzZjdlIiwidXNlcl9pZCI6MTR9.knSgJuw8assYGcSYX8uJJZhXjXdnys3a5fR0EjhQNg0"
BASE_URL = "https://megapolis1.uz"

print("Testing single object by ID...")

# Try getting object with ID 1
for obj_id in [1, 2, 3, 100, 500]:
    try:
        response = requests.get(
            f"{BASE_URL}/api/objects/{obj_id}/",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Object ID {obj_id} found:")
            print(f"   Name: {data.get('name')}")
            print(f"   Rooms: {data.get('rooms_numbers')}")
            print(f"   Price: {data.get('price_starting')} {data.get('price_type')}")
            print(f"   Area: {data.get('total_area')} m²")
            print(f"   Keys: {list(data.keys())[:10]}")
            break
        elif response.status_code == 404:
            print(f"❌ Object ID {obj_id} not found")
        else:
            print(f"⚠️ Object ID {obj_id}: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Error with ID {obj_id}: {e}")
