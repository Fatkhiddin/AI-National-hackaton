"""
CRM API test - oddiy va to'liq jarayon
"""
from django.core.management.base import BaseCommand
from home.models import CRMConfiguration
import requests
from urllib.parse import urljoin


class Command(BaseCommand):
    help = "CRM API testini bosqichma-bosqich qilish"
    
    def handle(self, *args, **options):
        config = CRMConfiguration.get_config()
        
        self.stdout.write(self.style.WARNING("=== CRM API TEST ==="))
        self.stdout.write("")
        
        # BOSQICH 1: CRM sozlamalarini ko'rsatish
        self.stdout.write(self.style.SUCCESS("BOSQICH 1: CRM SOZLAMALARI"))
        self.stdout.write(f"  URL: {config.crm_url}")
        self.stdout.write(f"  Username: {config.username}")
        self.stdout.write(f"  Connected: {config.is_connected}")
        self.stdout.write("")
        
        if not config.crm_url or not config.username or not config.password:
            self.stdout.write(self.style.ERROR("ERROR: CRM sozlamalari to'liq emas!"))
            return
        
        # BOSQICH 2: Login qilish
        self.stdout.write(self.style.SUCCESS("BOSQICH 2: LOGIN"))
        login_url = urljoin(config.crm_url, 'login/')
        self.stdout.write(f"  POST: {login_url}")
        
        try:
            response = requests.post(
                login_url,
                json={"username": config.username, "password": config.password},
                timeout=10
            )
            
            self.stdout.write(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')
                self.stdout.write(self.style.SUCCESS(f"  Token: {access_token[:50]}..."))
                self.stdout.write("")
                
                # BOSQICH 3: IP-Phone API qilish
                self.stdout.write(self.style.SUCCESS("BOSQICH 3: IP-PHONE API CHAQIRISH"))
                
                api_url = urljoin(config.crm_url, 'ip-phone/')
                self.stdout.write(f"  GET: {api_url}")
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                params = {
                    'page': 1,
                    'page_size': 5,
                    'ordering': '-timestamp'
                }
                
                self.stdout.write(f"  Params: {params}")
                
                api_response = requests.get(
                    api_url,
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                self.stdout.write(f"  Status: {api_response.status_code}")
                self.stdout.write("")
                
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    
                    self.stdout.write(self.style.SUCCESS("BOSQICH 4: JAVOB"))
                    self.stdout.write(f"  Jami: {api_data.get('count', 0)} ta")
                    self.stdout.write(f"  Sahifa: {api_data.get('current_page', 1)}")
                    self.stdout.write(f"  Jami sahifalar: {api_data.get('total_pages', 0)}")
                    self.stdout.write("")
                    
                    results = api_data.get('results', [])
                    self.stdout.write(f"  Shu sahifadagi: {len(results)} ta")
                    
                    if results:
                        self.stdout.write("")
                        self.stdout.write(self.style.SUCCESS("BOSQICH 5: BIRINCHI QO'NG'IROQ"))
                        call = results[0]
                        self.stdout.write(f"  ID: {call.get('id')}")
                        self.stdout.write(f"  Phone: {call.get('phone')}")
                        self.stdout.write(f"  Operator: {call.get('operator_name')}")
                        self.stdout.write(f"  Status: {call.get('status')}")
                        self.stdout.write(f"  Type: {call.get('treeName')}")
                        self.stdout.write(f"  Time: {call.get('date_time')}")
                    else:
                        self.stdout.write(self.style.WARNING("  Qo'ng'iroq topilmadi"))
                
                else:
                    self.stdout.write(self.style.ERROR(f"API xatosi: {api_response.status_code}"))
                    self.stdout.write(f"  Response: {api_response.text[:200]}")
            
            else:
                self.stdout.write(self.style.ERROR(f"Login xatosi: {response.status_code}"))
                self.stdout.write(f"  Response: {response.text}")
        
        except requests.exceptions.Timeout:
            self.stdout.write(self.style.ERROR("ERROR: Timeout (CRM javob bermadi)"))
        except requests.exceptions.ConnectionError:
            self.stdout.write(self.style.ERROR("ERROR: Ulanish xatosi"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERROR: {str(e)}"))
