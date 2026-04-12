# market_analysis/olx_scraper.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from decimal import Decimal
import re
from .models import OLXProperty
from users.models import Team


class OLXScraper:
    """OLX.uz dan ko'chmas mulk ma'lumotlarini yig'ish"""
    
    def __init__(self, team):
        self.team = team
        self.driver = None
    
    def setup_driver(self):
        """Browser sozlash"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Oynasiz ishlash
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Webdriver manager bilan avtomatik chromedriver yuklab olish
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
    
    def scrape_and_save(self, base_url, max_pages=2):
        """
        OLX dan ma'lumotlarni yig'ish va database ga saqlash
        
        Args:
            base_url: OLX kategoriya URL
            max_pages: Nechta sahifadan yig'ish
        
        Returns:
            dict: Statistika
        """
        self.setup_driver()
        
        try:
            print(f"🔄 Scraping boshlandi: {base_url}")
            
            # 1. Linklar yig'ish
            ad_links = self.get_all_ad_links(base_url, max_pages)
            print(f"📋 {len(ad_links)} ta e'lon topildi")
            
            if not ad_links:
                print("❌ Hech qanday e'lon topilmadi")
                return {'success': False, 'total': 0}
            
            # 2. Har birini parse va saqlash
            saved_count = 0
            updated_count = 0
            error_count = 0
            skipped_count = 0  # Allaqachon mavjud
            
            for i, ad_link in enumerate(ad_links, 1):
                print(f"\n[{i}/{len(ad_links)}] 🔍 {ad_link}")
                
                try:
                    # OLX ID ni olish
                    olx_id = ad_link.split('/')[-1].replace('.html', '')
                    
                    # Bazada borligini tekshirish
                    if OLXProperty.objects.filter(olx_id=olx_id, team=self.team).exists():
                        print(f"⏭️ Bazada mavjud: {olx_id}")
                        skipped_count += 1
                        continue
                    
                    ad_data = self.scrape_ad_details(ad_link)
                    
                    if ad_data:
                        olx_obj, created = self.save_to_database(ad_data)
                        
                        if created:
                            print(f"✅ Saqlandi: {olx_obj.title[:50]}")
                            saved_count += 1
                        else:
                            print(f"♻️ Yangilandi: {olx_obj.title[:50]}")
                            updated_count += 1
                    else:
                        error_count += 1
                    
                    time.sleep(2)  # Server ga yuk bermaslik
                    
                except Exception as e:
                    print(f"❌ Xatolik: {e}")
                    error_count += 1
                    continue
            
            print(f"\n🎉 Tugadi! Yangi: {saved_count}, Yangilandi: {updated_count}, O'tkazildi: {skipped_count}, Xato: {error_count}")
            
            return {
                'success': True,
                'total': len(ad_links),
                'saved': saved_count,
                'updated': updated_count,
                'skipped': skipped_count,
                'errors': error_count
            }
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def get_all_ad_links(self, base_url, max_pages):
        """Barcha e'lon linklar"""
        all_links = []
        
        for page in range(1, max_pages + 1):
            try:
                url = base_url if page == 1 else f"{base_url}?page={page}"
                print(f"📄 Sahifa {page}: {url}")
                
                self.driver.get(url)
                time.sleep(3)
                
                # E'lon kartochkalar
                cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-cy="l-card"]')
                print(f"   {len(cards)} ta kartochka topildi")
                
                for card in cards:
                    try:
                        link = card.find_element(By.CSS_SELECTOR, 'a[href*="/d/oz/obyavlenie/"]')
                        ad_link = link.get_attribute('href')
                        
                        if ad_link and ad_link not in all_links:
                            all_links.append(ad_link)
                    except:
                        continue
                
            except Exception as e:
                print(f"❌ Sahifa {page} xatolik: {e}")
                continue
        
        return all_links
    
    def scrape_ad_details(self, ad_url):
        """Bitta e'lon detallarini olish"""
        try:
            self.driver.get(ad_url)
            time.sleep(3)
            
            # Sarlavha
            title = self.driver.find_element(
                By.CSS_SELECTOR, '[data-cy="offer_title"] h4'
            ).text.strip()
            
            # Narx
            price = self.driver.find_element(
                By.CSS_SELECTOR, '[data-testid="ad-price-container"] h3'
            ).text.strip()
            
            # Telefon
            phone = self.get_phone_number()
            
            # Parametrlar
            details = self.get_property_details()
            
            # Tavsif
            description = self.get_description()
            
            # Rasm
            image_url = self.get_main_image()
            
            return {
                'url': ad_url,
                'title': title,
                'price': price,
                'phone': phone,
                'details': details,
                'description': description,
                'image_url': image_url
            }
            
        except Exception as e:
            print(f"   ❌ Parse xatolik: {e}")
            return None
    
    def get_phone_number(self):
        """Telefon raqam"""
        try:
            btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="show-phone"]'))
            )
            btn.click()
            time.sleep(2)
            
            phone = self.driver.find_element(By.CSS_SELECTOR, '.css-c9sbhm').text.strip()
            return phone if phone != "xxx xxx xxx" else None
        except:
            return None
    
    def get_property_details(self):
        """Parametrlar"""
        details = {}
        try:
            params = self.driver.find_elements(
                By.CSS_SELECTOR, 
                '[data-testid="ad-parameters-container"] .css-13x8d99'
            )
            
            for param in params:
                text = param.text.strip()
                if ':' in text:
                    key, value = text.split(':', 1)
                    details[key.strip()] = value.strip()
                elif text:
                    details[text] = "Ha"
        except:
            pass
        return details
    
    def get_description(self):
        """Tavsif"""
        try:
            return self.driver.find_element(
                By.CSS_SELECTOR, '[data-cy="ad_description"] .css-19duwlz'
            ).text.strip()
        except:
            return None
    
    def get_main_image(self):
        """Rasm"""
        try:
            img = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="swiper-image"]')
            img_url = img.get_attribute('src')
            
            # Yuqori sifatli rasm
            if 's=750x1000' in img_url:
                return img_url
            else:
                return img_url.replace('s=216x152', 's=750x1000')
        except:
            return None
    
    def save_to_database(self, ad_data):
        """Database ga saqlash"""
        # OLX ID (URL dan)
        olx_id = ad_data['url'].split('/')[-1].replace('.html', '')
        
        # Narx parse
        price_str = ad_data['price'].replace('у.е.', '').replace(' ', '').strip()
        try:
            price_usd = Decimal(price_str)
        except:
            price_usd = Decimal('0')
        
        # Xonalar
        rooms = self._parse_int(ad_data['details'].get('Xonalar soni'))
        
        # Maydonlar
        area_total = self._parse_decimal(
            ad_data['details'].get('Umumiy maydon', '').replace('m²', '')
        )
        area_living = self._parse_decimal(
            ad_data['details'].get('Yashash maydoni', '').replace('m²', '')
        )
        area_kitchen = self._parse_decimal(
            ad_data['details'].get('Oshxona maydoni', '').replace('m²', '')
        )
        
        # Qavat
        floor = self._parse_int(ad_data['details'].get('Qavati'))
        total_floors = self._parse_int(ad_data['details'].get('Uy qavatliligi'))
        
        # Telefon
        phone = ad_data.get('phone')
        if phone:
            phone = re.sub(r'\D', '', phone)[-9:]
        
        # Saqlash
        olx_property, created = OLXProperty.objects.update_or_create(
            olx_id=olx_id,
            defaults={
                'title': ad_data['title'],
                'url': ad_data['url'],
                'price_usd': price_usd,
                'city': 'Buxoro',  # Yoki dinamik
                'address_text': ad_data.get('address', 'Buxoro'),
                'rooms': rooms,
                'area_total': area_total,
                'area_living': area_living,
                'area_kitchen': area_kitchen,
                'floor': floor,
                'total_floors': total_floors,
                'building_type': ad_data['details'].get('Qurilish turi'),
                'repair_state': ad_data['details'].get('Taʼmiri'),
                'layout': ad_data['details'].get('Rejasi'),
                'furniture': 'Mebelli' in str(ad_data['details'].get('Kvartirada bor', '')),
                'bathroom': ad_data['details'].get('Sanuzel'),
                'description': ad_data.get('description'),
                'image_url': ad_data.get('image_url'),
                'phone': phone,
                'seller_type': ad_data['details'].get('Jismoniy shaxs', 'Ha'),
                'team': self.team,
                'is_processed': False,
                'raw_data': ad_data
            }
        )
        
        return olx_property, created
    
    def _parse_int(self, value):
        """String -> int"""
        try:
            return int(re.sub(r'\D', '', str(value))) if value else None
        except:
            return None
    
    def _parse_decimal(self, value):
        """String -> Decimal"""
        try:
            clean = re.sub(r'[^\d.]', '', str(value))
            return Decimal(clean) if clean else None
        except:
            return None


# ============================================
# HELPER FUNKSIYALAR
# ============================================

def run_olx_scraping(city='buhara', max_pages=2, team=None):
    """
    OLX scraping ishga tushirish
    
    Args:
        city: Shahar (buhara, toshkent...)
        max_pages: Sahifalar soni
        team: Team obyekti (ixtiyoriy)
    """
    if team is None:
        from users.models import Team
        team = Team.objects.first()
        
        if not team:
            print("❌ Team topilmadi!")
            return {'success': False, 'error': 'No team'}
    
    print(f"✅ Team: {team.name}")  # Tekshirish
    
    # Yangi link formatiga o'zgartirish
    base_url = f"https://www.olx.uz/nedvizhimost/kvartiry/{city}/?currency=UYE&search%5Bprivate_business%5D=private"
    
    scraper = OLXScraper(team)
    result = scraper.scrape_and_save(base_url, max_pages)
    
    return result