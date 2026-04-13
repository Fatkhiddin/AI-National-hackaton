"""
CRM Integration Test Script
Megapolis CRM bilan ulanishni test qilish
"""
import os
import django
import asyncio
import json

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from home.models import CRMProvider, AIProvider
from home.crm_service import CRMService
from home.ai_service import AIService


async def test_crm_integration():
    """Test CRM integration end-to-end"""
    
    print("=" * 60)
    print("🧪 CRM INTEGRATION TEST")
    print("=" * 60)
    
    # 1. Get CRM Provider
    print("\n1️⃣ CRM Provider topilmoqda...")
    try:
        crm_provider = CRMProvider.objects.filter(is_active=True).first()
        if not crm_provider:
            print("❌ Faol CRM provider topilmadi!")
            print("💡 CRM Dashboard da provider qo'shing: http://localhost:8000/crm/")
            return
        
        print(f"✅ CRM Provider topildi: {crm_provider.name}")
        print(f"   API URL: {crm_provider.api_url}")
        print(f"   Type: {crm_provider.get_crm_type_display()}")
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        return
    
    # 2. Test CRM Connection
    print("\n2️⃣ CRM Connection test qilinmoqda...")
    crm_service = CRMService(crm_provider)
    
    connection_test = await crm_service.test_connection()
    if connection_test.get('success'):
        print(f"✅ {connection_test['message']}")
    else:
        print(f"❌ Connection xatolik: {connection_test.get('error')}")
        print("💡 API URL va API Key ni tekshiring")
        return
    
    # 3. Get AI Provider
    print("\n3️⃣ AI Provider topilmoqda...")
    try:
        ai_provider = AIProvider.objects.filter(is_active=True).first()
        if not ai_provider:
            print("⚠️ AI Provider topilmadi - Default test qilamiz")
            ai_service = None
        else:
            print(f"✅ AI Provider: {ai_provider.name}")
            ai_service = AIService(
                provider_type=ai_provider.provider_type,
                api_key=ai_provider.api_key,
                model='gpt-3.5-turbo',
                api_endpoint=ai_provider.api_endpoint
            )
    except Exception as e:
        print(f"⚠️ AI Provider xatolik: {e}")
        ai_service = None
    
    # 4. Test with mock conversation data
    print("\n4️⃣ Test suhbat ma'lumotlari bilan qidiruv...")
    
    mock_conversation = {
        "user_info": {
            "name": "Test User",
            "phone": "+998901234567"
        },
        "conversation_history": [
            "Salom, uy kerak",
            "3 xonali kvartira qidiraman",
            "Narx 50,000 dan 80,000 gacha",
            "Chilonzor tumani",
            "Yangi bino bo'lsa yaxshi"
        ],
        "requirements": {
            "property_type": "kvartira",
            "rooms": 3,
            "price_range": "50,000 - 80,000 USD",
            "location": "Chilonzor",
            "new_building": True
        }
    }
    
    print("\n📝 Suhbat ma'lumotlari:")
    print(json.dumps(mock_conversation, ensure_ascii=False, indent=2))
    
    # 5. Extract requirements with AI (or use mock)
    print("\n5️⃣ Talablar chiqarilmoqda...")
    
    if ai_service:
        print("🤖 AI dan tahlil qilinmoqda...")
        extraction_result = await crm_service.extract_requirements_with_ai(
            mock_conversation,
            ai_service
        )
        
        if extraction_result.get('success'):
            requirements = extraction_result['requirements']
            print("✅ AI tahlili muvaffaqiyatli:")
            print(json.dumps(requirements, ensure_ascii=False, indent=2))
        else:
            print(f"⚠️ AI tahlil xatolik: {extraction_result.get('error')}")
            print("📝 Mock ma'lumotlar ishlatiladi...")
            requirements = {
                "property_type": "apartment",
                "rooms": 3,
                "price_min": 50000,
                "price_max": 80000,
                "location": "Chilonzor",
                "new_building": True,
                "area_min": 70
            }
    else:
        print("📝 AI yo'q, mock ma'lumotlar ishlatiladi...")
        requirements = {
            "property_type": "apartment",
            "rooms": 3,
            "price_min": 50000,
            "price_max": 80000,
            "location": "Chilonzor",
            "new_building": True,
            "area_min": 70
        }
        print(json.dumps(requirements, ensure_ascii=False, indent=2))
    
    # 6. Search in CRM
    print("\n6️⃣ CRM da qidirilmoqda...")
    print("🔍 Query parametrlari:")
    mapped_params = crm_service.map_requirements_to_crm(requirements)
    print(json.dumps(mapped_params, ensure_ascii=False, indent=2))
    
    search_result = await crm_service.search_properties(requirements)
    
    if search_result.get('success'):
        properties = search_result.get('properties', [])
        count = search_result.get('count', 0)
        
        print(f"\n✅ CRM dan {count} ta uy topildi!")
        
        if properties:
            print("\n🏠 Birinchi 3 ta natija:")
            for i, prop in enumerate(properties[:3], 1):
                print(f"\n{i}. {prop.get('title', 'N/A')}")
                print(f"   💰 Narx: {prop.get('price', 'N/A')} {prop.get('price_currency', 'USD')}")
                print(f"   🚪 Xonalar: {prop.get('rooms', 'N/A')}")
                print(f"   📐 Maydon: {prop.get('area', 'N/A')} m²")
                print(f"   🏢 Qavat: {prop.get('floor', 'N/A')}/{prop.get('total_floors', 'N/A')}")
                print(f"   📍 Manzil: {prop.get('address_full', 'N/A')}")
        else:
            print("⚠️ Natijalar ro'yxati bo'sh")
            print("💡 Query parametrlarini tekshiring yoki CRM da ma'lumotlar borligini tasdiqlang")
    else:
        print(f"\n❌ CRM qidiruv xatolik:")
        print(f"   {search_result.get('error')}")
        if search_result.get('details'):
            print(f"   Details: {search_result.get('details')[:200]}")
    
    print("\n" + "=" * 60)
    print("🏁 TEST TUGADI")
    print("=" * 60)


async def quick_search_test():
    """Quick test with simple parameters"""
    print("\n🚀 TEZKOR TEST - Oddiy qidiruv\n")
    
    crm_provider = CRMProvider.objects.filter(is_active=True).first()
    if not crm_provider:
        print("❌ CRM Provider topilmadi")
        return
    
    crm_service = CRMService(crm_provider)
    
    # Simple search
    simple_requirements = {
        "rooms": 3,
        "price_min": 50000,
        "price_max": 100000
    }
    
    print(f"🔍 Qidiruv: {simple_requirements}")
    result = await crm_service.search_properties(simple_requirements)
    
    if result.get('success'):
        print(f"✅ {result.get('count', 0)} ta uy topildi")
        
        for prop in result.get('properties', [])[:5]:
            print(f"  • {prop.get('title')} - ${prop.get('price')}")
    else:
        print(f"❌ Xatolik: {result.get('error')}")


if __name__ == "__main__":
    print("\n" + "🏠" * 30)
    print("MEGAPOLIS CRM INTEGRATION TEST")
    print("🏠" * 30 + "\n")
    
    print("Qaysi test kerak?")
    print("1. To'liq test (AI + CRM)")
    print("2. Tezkor test (faqat CRM qidiruv)")
    
    choice = input("\nTanlang (1/2): ").strip()
    
    if choice == "1":
        asyncio.run(test_crm_integration())
    elif choice == "2":
        asyncio.run(quick_search_test())
    else:
        print("❌ Noto'g'ri tanlov")
