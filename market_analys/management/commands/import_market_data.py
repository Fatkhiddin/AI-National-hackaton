# market_analysis/management/commands/import_market_data.py

"""
Management command: Google Sheets dan bozor narxlarini import qilish.

Usage:
    python manage.py import_market_data
    python manage.py import_market_data --clear
    python manage.py import_market_data --team 1
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from users.models import Team
from market_analys.services import GoogleSheetsImporter


class Command(BaseCommand):
    help = 'Google Sheets dan bozor narxlarini import qilish'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Avval barcha ma\'lumotlarni o\'chirish'
        )
        
        parser.add_argument(
            '--team',
            type=int,
            help='Team ID (agar berilmasa, birinchi team ishlatiladi)'
        )
    
    def handle(self, *args, **options):
        """Main command logic"""
        
        # Team ni aniqlash
        team_id = options.get('team')
        
        if team_id:
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                raise CommandError(f'Team ID {team_id} topilmadi')
        else:
            team = Team.objects.first()
            if not team:
                raise CommandError('Hech qanday Team topilmadi!')
        
        self.stdout.write(f"\n🏢 Team: {team.name} (ID: {team.id})\n")
        
        # Importer yaratish
        importer = GoogleSheetsImporter(team=team)
        
        # Agar --clear berilgan bo'lsa, avval o'chirish
        if options['clear']:
            self.stdout.write(self.style.WARNING('⚠️ Barcha ma\'lumotlar o\'chirilmoqda...'))
            deleted_count = importer.clear_all_data()
            self.stdout.write(
                self.style.SUCCESS(f'✅ {deleted_count} ta yozuv o\'chirildi\n')
            )
        
        # Import boshlash
        self.stdout.write(self.style.MIGRATE_HEADING('📊 IMPORT BOSHLANDI\n'))
        
        try:
            result = importer.import_all()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ IMPORT MUVAFFAQIYATLI TUGADI!\n'
                        f'   Import qilindi: {result["imported"]} ta yozuv\n'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n⚠️ IMPORT TUGADI (ba\'zi xatoliklar bor)\n'
                        f'   Import qilindi: {result["imported"]} ta yozuv\n'
                        f'   Xatoliklar: {result["errors"]}\n'
                    )
                )
                
                if result['error_details']:
                    self.stdout.write(self.style.ERROR('\nXATOLIKLAR:'))
                    for error in result['error_details'][:10]:  # Birinchi 10tasi
                        self.stdout.write(f'  - {error}')
                    
                    if len(result['error_details']) > 10:
                        self.stdout.write(f'  ... va yana {len(result["error_details"]) - 10} ta\n')
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR('\n\n❌ Import bekor qilindi (Ctrl+C)\n'))
            raise CommandError('Import bekor qilindi')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ XATOLIK: {str(e)}\n')
            )
            raise CommandError(f'Import xatolik: {str(e)}')
