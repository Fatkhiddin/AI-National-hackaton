# market_analysis/management/commands/analyze_properties.py

"""
Management command: Propertylarni narx bo'yicha tahlil qilish.

Usage:
    # Bitta property
    python manage.py analyze_properties --property-id 123
    python manage.py analyze_properties --property-id 123 --model BuildHouse
    
    # Barcha propertylar
    python manage.py analyze_properties --model BuildHouse
    python manage.py analyze_properties --model OLXProperty
    
    # AI'siz tahlil
    python manage.py analyze_properties --no-ai
    
    # Cheklangan miqdor
    python manage.py analyze_properties --limit 50
"""

from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from market_analys.services import PriceAnalyzer


class Command(BaseCommand):
    help = 'Propertylarni narx bo\'yicha tahlil qilish (CRM va OLX)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--property-id',
            type=int,
            help='Bitta propertyni tahlil qilish uchun ID'
        )
        
        parser.add_argument(
            '--model',
            type=str,
            choices=['BuildHouse', 'OLXProperty'],
            default='BuildHouse',
            help='Property model (default: BuildHouse)'
        )
        
        parser.add_argument(
            '--no-ai',
            action='store_true',
            help='AI ishlatmasdan oddiy matematik tahlil'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='Nechta property tahlil qilish (bulk uchun)'
        )
        
        parser.add_argument(
            '--team',
            type=int,
            help='Team ID filter (ixtiyoriy)'
        )
    
    def handle(self, *args, **options):
        """Main command logic"""
        
        # Model ni olish
        model_name = options['model']
        
        if model_name == 'BuildHouse':
            Model = apps.get_model('home', 'BuildHouse')
            model_display = 'BuildHouse (CRM)'
        else:
            Model = apps.get_model('market_analysis', 'OLXProperty')
            model_display = 'OLXProperty'
        
        # AI yoki yo'q
        use_ai = not options['no_ai']
        ai_text = "AI bilan" if use_ai else "AI'siz"
        
        # PriceAnalyzer yaratish
        analyzer = PriceAnalyzer()
        
        # Bitta property tahlili
        if options['property_id']:
            property_id = options['property_id']
            
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f'\n🔍 {model_display} #{property_id} TAHLIL QILINMOQDA ({ai_text})\n'
                )
            )
            
            try:
                property_obj = Model.objects.get(id=property_id)
            except Model.DoesNotExist:
                raise CommandError(f'{model_name} ID {property_id} topilmadi')
            
            try:
                analysis = analyzer.analyze_property(property_obj, use_ai=use_ai)
                
                if analysis:
                    self._display_analysis_result(analysis)
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            '\n⚠️ Tahlil amalga oshmadi (ma\'lumot yetarli emas)\n'
                        )
                    )
            
            except Exception as e:
                raise CommandError(f'Tahlil xatolik: {str(e)}')
        
        # Bulk tahlil
        else:
            # QuerySet yaratish
            queryset = Model.objects.all()
            
            # Team filter
            if options['team']:
                queryset = queryset.filter(team_id=options['team'])
            
            # Limit
            limit = options.get('limit')
            if limit:
                queryset = queryset[:limit]
                self.stdout.write(
                    self.style.MIGRATE_HEADING(
                        f'\n🚀 {model_display} - BIRINCHI {limit} TA TAHLIL ({ai_text})\n'
                    )
                )
            else:
                self.stdout.write(
                    self.style.MIGRATE_HEADING(
                        f'\n🚀 {model_display} - BARCHA PROPERTYLAR TAHLIL ({ai_text})\n'
                    )
                )
            
            total = queryset.count()
            
            if total == 0:
                self.stdout.write(
                    self.style.WARNING('\n⚠️ Hech qanday property topilmadi\n')
                )
                return
            
            self.stdout.write(f'📊 Jami: {total} ta property\n')
            
            # Tasdiqlash
            if total > 10 and not options['limit']:
                confirm = input(f'\n⚠️ {total} ta property tahlil qilinadi. Davom etasizmi? (yes/no): ')
                if confirm.lower() not in ['yes', 'y', 'ha']:
                    self.stdout.write(self.style.WARNING('\n❌ Bekor qilindi\n'))
                    return
            
            try:
                result = analyzer.bulk_analyze(queryset, use_ai=use_ai)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ BULK TAHLIL TUGADI\n'
                        f'   Jami: {result["total"]}\n'
                        f'   Muvaffaqiyatli: {result["analyzed"]}\n'
                        f'   Xatolik: {result["failed"]}\n'
                    )
                )
                
                if result['analyzed'] > 0:
                    self.stdout.write(self.style.MIGRATE_HEADING('\n📊 STATUS STATISTIKASI:'))
                    for status, count in result['statuses'].items():
                        if count > 0:
                            emoji = self._get_status_emoji(status)
                            self.stdout.write(f'   {emoji} {status.upper()}: {count}')
                    self.stdout.write('')
            
            except KeyboardInterrupt:
                self.stdout.write(self.style.ERROR('\n\n❌ Tahlil bekor qilindi (Ctrl+C)\n'))
                raise CommandError('Tahlil bekor qilindi')
            
            except Exception as e:
                raise CommandError(f'Bulk tahlil xatolik: {str(e)}')
    
    def _display_analysis_result(self, analysis):
        """Bitta tahlil natijasini chiroyli ko'rsatish"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ TAHLIL NATIJALARI'))
        self.stdout.write('='*60)
        
        # Status
        status_color = self._get_status_style(analysis.status)
        self.stdout.write(
            f'\n📊 STATUS: {status_color(analysis.get_status_display().upper())}'
        )
        
        # Narxlar
        self.stdout.write(f'\n💰 NARXLAR:')
        self.stdout.write(f'   Joriy narx: {analysis.joriy_narxi:,.0f} so\'m/m²')
        self.stdout.write(f'   Bozor narxi: {analysis.bozor_narxi:,.0f} so\'m/m²')
        
        # Farq
        farq_style = self.style.SUCCESS if analysis.farq_foiz < 0 else self.style.ERROR
        farq_icon = '▼' if analysis.farq_foiz < 0 else '▲'
        self.stdout.write(
            f'\n📈 FARQ: {farq_style(f"{farq_icon} {analysis.farq_foiz:.1f}%")} '
            f'({analysis.farq_summa:,.0f} so\'m)'
        )
        
        # Confidence
        self.stdout.write(f'\n🎯 ISHONCH: {analysis.confidence_score}%')
        
        # AI Tahlil
        if analysis.ai_tahlil:
            self.stdout.write(f'\n📝 AI TAHLIL:')
            self.stdout.write(self.style.WARNING(f'{analysis.ai_tahlil}\n'))
        
        # Tavsiya
        if analysis.tavsiya:
            self.stdout.write(f'💡 TAVSIYA:')
            self.stdout.write(self.style.NOTICE(f'{analysis.tavsiya}\n'))
        
        self.stdout.write('='*60 + '\n')
    
    def _get_status_style(self, status):
        """Status bo'yicha rang"""
        styles = {
            'juda_arzon': self.style.SUCCESS,
            'arzon': self.style.SUCCESS,
            'normal': self.style.WARNING,
            'qimmat': self.style.ERROR,
            'juda_qimmat': self.style.ERROR,
        }
        return styles.get(status, self.style.WARNING)
    
    def _get_status_emoji(self, status):
        """Status bo'yicha emoji"""
        emojis = {
            'juda_arzon': '💚',
            'arzon': '✅',
            'normal': '⚖️',
            'qimmat': '⚠️',
            'juda_qimmat': '🔴',
        }
        return emojis.get(status, '❓')
