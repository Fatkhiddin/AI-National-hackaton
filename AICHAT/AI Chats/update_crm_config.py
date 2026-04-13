"""
Update CRM Provider configuration to use correct endpoint
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from home.models import CRMProvider

# Get the Megapolis CRM provider
provider = CRMProvider.objects.filter(crm_type='custom', name__icontains='Megapolis').first()

if provider:
    print(f"✅ Found provider: {provider.name}")
    print(f"Current API URL: {provider.api_url}")
    print(f"Current request template: {provider.request_template}")
    
    # Update to correct configuration
    provider.request_template = {
        "method": "GET",
        "endpoint": "/api/objects/",
        "headers": {
            "Authorization": "Bearer {api_key}"
        }
    }
    
    provider.field_mapping = {
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
    }
    
    provider.save()
    
    print("\n✅ CRM Provider updated successfully!")
    print(f"New endpoint: {provider.request_template['endpoint']}")
    print(f"Method: {provider.request_template['method']}")
    
else:
    print("❌ CRM Provider not found")
    print("Please create one via admin panel or CRM dashboard")
