"""
CRM API - barcha available endpointlarni tekshirish
"""
from django.core.management.base import BaseCommand
from home.models import CRMConfiguration
import requests
from urllib.parse import urljoin


class Command(BaseCommand):
    help = "CRM API barcha endpointlarni probe qilish"
    
    def handle(self, *args, **options):
        config = CRMConfiguration.get_config()
        
        # Login
        login_url = urljoin(config.crm_url, 'login/')
        login_response = requests.post(
            login_url,
            json={"username": config.username, "password": config.password},
            timeout=10
        )
        
        if login_response.status_code != 200:
            self.stdout.write(self.style.ERROR("Login xatosi"))
            return
        
        token = login_response.json().get('access_token')
        headers = {"Authorization": f"Bearer {token}"}
        
        self.stdout.write(self.style.SUCCESS("Token olindi. Endpointlarni probe qilmoqda..."))
        self.stdout.write("")
        
        # Tekshirilishi kerak bo'lgan endpointlar
        endpoints = [
            'ip-phone/',
            'sip-calls/',
            'sipCall/',
            'sip_calls/',
            'ip_phone/',
            'phone-calls/',
            'calls/',
            'qongiroq/',
            '',  # Base API
        ]
        
        for endpoint in endpoints:
            try:
                test_url = urljoin(config.crm_url, endpoint)
                response = requests.get(test_url, headers=headers, timeout=5)
                
                status_color = 'SUCCESS' if response.status_code == 200 else 'WARNING'
                
                self.stdout.write(
                    self.style.WARNING(f"{response.status_code} | {endpoint or '[BASE]':<30} | {test_url}")
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            keys = list(data.keys())[:5]
                            self.stdout.write(f"          Keys: {keys}")
                        elif isinstance(data, list):
                            self.stdout.write(f"          List: {len(data)} items")
                    except:
                        pass
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"ERR  | {endpoint or '[BASE]':<30} | {str(e)[:50]}")
                )
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Probe tugadi. Agar 200 ko'rsatilsa - endpoint topildi!"))
