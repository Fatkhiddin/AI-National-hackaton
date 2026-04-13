"""

Create Megapolis CRM Provider with correct configuration
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from home.models import CRMProvider
from django.contrib.auth.models import User

# Get user (assuming first user or create one)
user = User.objects.first()
if not user:
    print("❌ No users found. Please create a user first.")
    exit()

print(f"Using user: {user.username}")

# Delete old providers
old_count = CRMProvider.objects.filter(user=user).count()
if old_count > 0:
    print(f"Deleting {old_count} old CRM providers...")
    CRMProvider.objects.filter(user=user).delete()

# Create new Megapolis CRM provider
provider = CRMProvider.objects.create(
    user=user,
    name="Megapolis CRM",
    crm_type="custom",
    api_url="https://megapolis1.uz",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY0Mjc0MDMyLCJpYXQiOjE3NjQyNzA0MzIsImp0aSI6IjU1ZTE0MDc3NTgwMzQ3M2I4ZWUyOTkyMjcyMGEzZjdlIiwidXNlcl9pZCI6MTR9.knSgJuw8assYGcSYX8uJJZhXjXdnys3a5fR0EjhQNg0",
    is_active=True,
    request_template={
        "method": "GET",
        "endpoint": "/api/objects/",
        "headers": {
            "Authorization": "Bearer {api_key}"
        }
    },
    field_mapping={
        "property_fields": {
            "rooms": "rooms_numbers",
            "price_min": "min_price",
            "price_max": "max_price",
            "area_min": "min_area",
            "area_max": "max_area",
            "location": "search"
        },
        "response_format": {
            "id": "id",
            "title": "name",
            "rooms": "rooms_numbers",
            "bedrooms": "bedrooms_num",
            "price": "price_starting",
            "price_currency": "price_type",
            "price_bargain": "price_bargain",
            "area": "total_area",
            "floor": "floor",
            "total_floors": "floor_build",
            "year_built": "year_construction",
            "address_full": "address_house_number",
            "short_description": "short_description",
            "slug": "slug",
            "images": "build_house_images"
        }
    },
    extraction_prompt="""Suhbatdan uy-joy talablarini JSON formatda ajrating:
- rooms: xonalar soni (int)
- price_min, price_max: narx oralig'i (USD)
- area_min, area_max: maydon (m²)
- location: hudud/manzil (string)
"""
)

print(f"\n✅ Created CRM Provider: {provider.name}")
print(f"   API URL: {provider.api_url}")
print(f"   Endpoint: /api/objects/")
print(f"   Method: GET")
print(f"   Active: {provider.is_active}")
print(f"\n🎉 CRM Provider ready for testing!")
