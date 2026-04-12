"""
SIP qo'ng'iroqlarni CRM dan sync qilish uchun management command
"""
from django.core.management.base import BaseCommand, CommandError
from operators_analys.services import SIPCallService
from home.models import CRMConfiguration


class Command(BaseCommand):
    help = "CRM dan SIP qo'ng'iroqlarni bazaga saqlash"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--page-size",
            type=int,
            default=100,
            help="Bir soruvda nechta qo'ng'iroq olish"
        )
        parser.add_argument(
            "--latest",
            action="store_true",
            help="Faqat oxirgi qo'ng'iroqlarni olish"
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Qo'ng'iroqlar statistikasini ko'rsatish"
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Sync boshlanding..."))
        self.stdout.write("")
        
        config = CRMConfiguration.get_config()
        
        if not config.is_connected or not config.access_token:
            self.stdout.write(self.style.ERROR("ERROR: CRM ulangan emas!"))
            raise CommandError("CRM ulangan emas")
        
        self.stdout.write(self.style.SUCCESS(f"CRM: {config.crm_url}"))
        self.stdout.write("")
        
        service = SIPCallService()
        
        if options["stats"]:
            stats = service.get_stats()
            self.stdout.write(self.style.WARNING("Statistika:"))
            self.stdout.write(f"  Jami: {stats['total']} ta")
            self.stdout.write(f"  Javob: {stats['answered']}")
            self.stdout.write(f"  Javob yo'q: {stats['missed']}")
            self.stdout.write(f"  Band: {stats['busy']}")
            self.stdout.write(f"  Kiruvchi: {stats['incoming']}")
            self.stdout.write(f"  Chiquvchi: {stats['outgoing']}")
            self.stdout.write("")
            return
        
        page_size = options["page_size"]
        
        if options["latest"]:
            self.stdout.write("Oxirgi qo'ng'iroqlar olinmoqda...")
            result = service.fetch_calls({"page_size": 50})
        else:
            self.stdout.write(f"Barcha qo'ng'iroqlar olinmoqda ({page_size} sahifada)...")
            result = service.sync_all_calls(page_size=page_size)
        
        self.stdout.write("")
        
        if result.get("success") or result.get("results"):
            if options["latest"]:
                calls = result.get("results", [])
                save_result = service.save_calls(calls)
                
                self.stdout.write(self.style.SUCCESS("Saqlash tugadi:"))
                self.stdout.write(f"  Yangi: {save_result['created']}")
                self.stdout.write(f"  Yangilangan: {save_result['updated']}")
                self.stdout.write(f"  Xatolar: {save_result['errors']}")
            else:
                self.stdout.write(self.style.SUCCESS("Sync tugadi:"))
                self.stdout.write(f"  Yangi: {result['total_created']}")
                self.stdout.write(f"  Yangilangan: {result['total_updated']}")
                self.stdout.write(f"  Xatolar: {result['total_errors']}")
        else:
            error = result.get("error", "Unknown error")
            self.stdout.write(self.style.ERROR(f"ERROR: {error}"))
            raise CommandError(error)
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("OK!"))
