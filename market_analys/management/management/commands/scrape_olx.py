# market_analysis/management/commands/scrape_olx.py

from django.core.management.base import BaseCommand
from market_analys.olx_scraper import run_olx_scraping


class Command(BaseCommand):
    help = 'OLX dan ma\'lumotlarni yig\'ish'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            default='buhara',
            help='Shahar nomi (buhara, toshkent...)'
        )
        parser.add_argument(
            '--pages',
            type=int,
            default=2,
            help='Nechta sahifa'
        )
    
    def handle(self, *args, **options):
        city = options['city']
        pages = options['pages']
        
        self.stdout.write(f'🔄 Scraping boshlandi: {city}, {pages} sahifa')
        
        result = run_olx_scraping(city=city, max_pages=pages)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Tayyor! Yangi: {result['saved']}, "
                    f"Yangilandi: {result['updated']}, Xato: {result['errors']}"
                )
            )
        else:
            self.stdout.write(self.style.ERROR('❌ Xatolik yuz berdi'))