"""
Django test - CRM integration end-to-end
"""
import os
import django
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from home.models import CRMProvider, TelegramAccount, User
from home.crm_service import CRMService
from home.ai_service import AIService

async def test_crm_integration():
    print("=" * 70)
    print("TEST: CRM Integration with Django")
    print("=" * 70)
    
    # Get CRM provider (sync)
    from asgiref.sync import sync_to_async
    crm_provider = await sync_to_async(lambda: CRMProvider.objects.filter(is_active=True).first())()
    
    if not crm_provider:
        print("❌ CRM Provider topilmadi!")
        return
    
    print(f"✅ CRM Provider: {crm_provider.name}")
    print(f"   API URL: {crm_provider.api_url}")
    print(f"   Request template: {crm_provider.request_template}")
    
    # Initialize CRM service
    crm_service = CRMService(crm_provider)
    
    # Simulate AI extracted requirements
    requirements = {
        'property_type': 'apartment',
        'price_min': 50000,
        'price_max': 80000,
        'rooms': 3,
        'area_min': 0,
        'area_max': 0,
        'location': None,
        'district': None
    }
    
    print(f"\n📋 Requirements:")
    print(f"   Rooms: {requirements['rooms']}")
    print(f"   Price: ${requirements['price_min']:,} - ${requirements['price_max']:,}")
    
    # Search properties
    print(f"\n🔍 Searching properties...")
    result = await crm_service.search_properties(requirements)
    
    print(f"\n📊 Search Result:")
    print(f"   Success: {result.get('success')}")
    print(f"   Count: {result.get('count', 0)}")
    
    if result.get('success'):
        properties = result.get('properties', [])
        print(f"\n✅ Found {len(properties)} properties!")
        
        if properties:
            # Show first property
            prop = properties[0]
            print(f"\n{'='*70}")
            print(f"BIRINCHI OBYEKT:")
            print(f"{'='*70}")
            print(f"📋 Sarlavha: {prop.get('title', 'N/A')}")
            print(f"💰 Narx: {prop.get('price', 'N/A')} {prop.get('price_currency', 'usd')}")
            print(f"🚪 Xonalar: {prop.get('rooms', 'N/A')}")
            print(f"📐 Maydon: {prop.get('area', 'N/A')} m²")
            print(f"🏢 Qavat: {prop.get('floor', 'N/A')}/{prop.get('total_floors', 'N/A')}")
            print(f"📍 Manzil: {prop.get('address_full', 'N/A')}")
            
            # Show all keys
            print(f"\n🔑 Available keys: {list(prop.keys())}")
            
            # Format for Telegram
            from home.telegram_monitor import TelegramMonitor
            monitor = TelegramMonitor()
            telegram_message = monitor._format_property_message(prop, 1)
            
            print(f"\n{'='*70}")
            print(f"TELEGRAM MESSAGE FORMAT:")
            print(f"{'='*70}")
            print(telegram_message)
        else:
            print("⚠️ Properties list is empty")
    else:
        print(f"❌ Error: {result.get('error')}")
        if 'details' in result:
            print(f"   Details: {result['details'][:200]}")

# Run test
if __name__ == "__main__":
    asyncio.run(test_crm_integration())
