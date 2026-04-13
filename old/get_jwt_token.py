"""
Get JWT token from Megapolis CRM
"""
import requests

BASE_URL = "https://megapolis1.uz"

# Your credentials
USERNAME = "your_username"  # O'zgartirishingiz kerak
PASSWORD = "your_password"  # O'zgartirishingiz kerak

print(f"🔐 Getting token from {BASE_URL}/api/login/...")

response = requests.post(
    f"{BASE_URL}/api/login/",
    json={"username": USERNAME, "password": PASSWORD},
    timeout=10
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    access_token = data.get('access')
    
    print(f"\n✅ SUCCESS!")
    print(f"\n📋 JWT ACCESS TOKEN:")
    print(f"{access_token}")
    print(f"\n📝 Token uzunligi: {len(access_token)} belgi")
    print(f"\n💾 Tokenni saqlang va CRM Provider'ga qo'shing")
else:
    print(f"❌ Login failed!")
    print(response.text)
