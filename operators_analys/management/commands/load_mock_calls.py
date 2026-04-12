"""
Mock IP Phone Calls - test uchun
"""
from django.core.management.base import BaseCommand
from operators_analys.models import IPPhoneCall
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Mock IP Phone qo'ng'iroqlarni bazaga qo'shish"
    
    def handle(self, *args, **options):
        # Eski qo'ng'iroqlarni o'chirish
        IPPhoneCall.objects.all().delete()
        
        # Mock ma'lumotlar
        mock_calls = [
            {
                "call_id": "call_001",
                "phone": "+998 914440428",
                "operator_name": "Megapolis",
                "client_name": "Ali Raximov",
                "tree_name": "Kiruvchi",
                "status": "answered",
                "src_num": "998914440428",
                "dst_num": "998712345678",
                "call_record_link": "https://example.com/calls/rec001.mp3"
            },
            {
                "call_id": "call_002",
                "phone": "+998 994570031",
                "operator_name": "Megapolis",
                "client_name": "Botir Qodiriy",
                "tree_name": "Kiruvchi",
                "status": "answered",
                "src_num": "998994570031",
                "dst_num": "998712345678",
                "call_record_link": "https://example.com/calls/rec002.mp3"
            },
            {
                "call_id": "call_003",
                "phone": "+998 509500558",
                "operator_name": "Megapolis",
                "client_name": "Doha Investment",
                "tree_name": "Kiruvchi",
                "status": "answered",
                "src_num": "998509500558",
                "dst_num": "998712345678",
                "call_record_link": "https://example.com/calls/rec003.mp3"
            },
            {
                "call_id": "call_004",
                "phone": "+998 992542727",
                "operator_name": "Megapolis",
                "client_name": "Xasan Babaev",
                "tree_name": "Chiquvchi",
                "status": "missed",
                "src_num": "998712345678",
                "dst_num": "998992542727",
                "call_record_link": ""
            },
            {
                "call_id": "call_005",
                "phone": "+998 900800322",
                "operator_name": "Nifugar",
                "client_name": "Lazizbek Rofiyev",
                "tree_name": "Kiruvchi",
                "status": "answered",
                "src_num": "998900800322",
                "dst_num": "998712345679",
                "call_record_link": "https://example.com/calls/rec005.mp3"
            },
            {
                "call_id": "call_006",
                "phone": "+998 912345678",
                "operator_name": "Client Support",
                "client_name": "Nodira Shodmonova",
                "tree_name": "Chiquvchi",
                "status": "answered",
                "src_num": "998712345678",
                "dst_num": "998912345678",
                "call_record_link": "https://example.com/calls/rec006.mp3"
            },
        ]
        
        # Qo'ng'iroqlarni yaratish
        base_time = timezone.now()
        for i, call_data in enumerate(mock_calls):
            IPPhoneCall.objects.create(
                call_id=call_data["call_id"],
                phone=call_data["phone"],
                operator_name=call_data["operator_name"],
                client_name=call_data["client_name"],
                timestamp=base_time - timedelta(hours=i+1),
                tree_name=call_data["tree_name"],
                status=call_data["status"],
                call_record_link=call_data["call_record_link"],
                src_num=call_data["src_num"],
                dst_num=call_data["dst_num"],
                duration_seconds=60 + i*10
            )
        
        self.stdout.write(self.style.SUCCESS(f"✓ {len(mock_calls)} ta mock qo'ng'iroq yaratildi!"))
