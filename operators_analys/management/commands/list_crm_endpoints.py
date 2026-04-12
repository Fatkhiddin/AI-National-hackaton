"""
CRM API - barcha available endpointlarni ro'yxatini ko'rish
"""
from django.core.management.base import BaseCommand
from home.models import CRMConfiguration
import requests
import json


class Command(BaseCommand):
    help = "CRM API barcha endpointlarni ro'yxatini ko'rish"
    
    def handle(self, *args, **options):
        config = CRMConfiguration.get_config()
        
        # Login
        login_url = f"{config.crm_url}login/"
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
        
        self.stdout.write(self.style.SUCCESS("=== CRM API BARCHA ENDPOINTLARI ==="))
        self.stdout.write("")
        
        # Base API dan barcha endpointlarni olish
        response = requests.get(config.crm_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            self.stdout.write(self.style.SUCCESS(f"Jami {len(data)} ta endpoint:"))
            self.stdout.write("")
            
            for i, (endpoint_name, endpoint_url) in enumerate(data.items(), 1):
                self.stdout.write(f"{i:2}. {endpoint_name:<30} | {endpoint_url}")
            
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("PHONEGA TEGISHLI ENDPOINTLARNI IZLANG:"))
            self.stdout.write("(ip, phone, sip, call, qongiroq, telefon, so'rov...)")
            
            # Qidiruv
            keywords = ['phone', 'ip', 'sip', 'call', 'qongiroq', 'telefon', 'request', 'sorov', 'cdr']
            for keyword in keywords:
                matching = [name for name in data.keys() if keyword.lower() in name.lower()]
                if matching:
                    self.stdout.write(self.style.SUCCESS(f"\n'{keyword}' qidiruvi: {matching}"))
        
        else:
            self.stdout.write(self.style.ERROR(f"API xatosi: {response.status_code}"))
