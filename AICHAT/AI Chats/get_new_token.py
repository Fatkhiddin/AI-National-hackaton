"""
Get new JWT token from Megapolis CRM
"""
import requests

BASE_URL = "https://megapolis1.uz"

# Login credentials
username = input("Username: ")
password = input("Password: ")

print(f"\n🔐 Logging in to {BASE_URL}...")

response = requests.post(
    f"{BASE_URL}/api/login/",
    json={"username": username, "password": password}
)

if response.status_code == 200:
    data = response.json()
    access_token = data.get('access')
    refresh_token = data.get('refresh')
    
    print(f"\n✅ Login successful!")
    print(f"\n📋 ACCESS TOKEN:")
    print(f"{access_token}")
    print(f"\n🔄 REFRESH TOKEN:")
    print(f"{refresh_token}")
    
    print(f"\n💾 Copy this token and update CRM Provider in admin panel")
    print(f"\nOr run:")
    print(f'python -c "from home.models import CRMProvider; p=CRMProvider.objects.first(); p.api_key=\\"{access_token}\\"; p.save(); print(\\'✅ Updated\\')"')
else:
    print(f"❌ Login failed: {response.status_code}")
    print(response.text)
