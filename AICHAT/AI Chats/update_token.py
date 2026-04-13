"""
Update CRM Provider token
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from home.models import CRMProvider

# New token
NEW_TOKEN = "3fe181e499921b48ee7c9c042e2bb8956115e433"

# Update provider
provider = CRMProvider.objects.filter(is_active=True).first()

if provider:
    provider.api_key = NEW_TOKEN
    provider.save()
    
    print(f"✅ Token yangilandi!")
    print(f"   Provider: {provider.name}")
    print(f"   Token: {NEW_TOKEN[:20]}...")
else:
    print("❌ CRM Provider topilmadi")
