# market_analys/management/commands/check_prices.py

from django.core.management.base import BaseCommand
from market_analys.models import MarketPriceReference


class Command(BaseCommand):
    help = 'Bozor narxlarini tekshirish'

    def handle(self, *args, **options):
        # 2 xonali, 6-qavat, gishtli, remontli
        self.stdout.write('\n🔍 2 xonali, 6-qavat, gishtli, remontli:\n')
        
        refs = MarketPriceReference.objects.filter(
            xonalar_soni=2,
            etaj=6,
            qurilish_turi='gishtli',
            holat='remontli'
        ).order_by('maydon_min')
        
        if refs.exists():
            for ref in refs:
                self.stdout.write(f'\nID: {ref.id}')
                self.stdout.write(f'Maydon: {ref.maydon_min} - {ref.maydon_max} m²')
                self.stdout.write(f'Arzon:  ${float(ref.arzon_narx):,.2f}/m²')
                self.stdout.write(f'Bozor:  ${float(ref.bozor_narx):,.2f}/m²')
                self.stdout.write(f'Qimmat: ${float(ref.qimmat_narx):,.2f}/m²')
                self.stdout.write('─' * 60)
        else:
            self.stdout.write(self.style.ERROR('❌ Topilmadi!'))
            
            # Barcha 2 xonali, 6-qavat
            self.stdout.write('\n\n🔍 BARCHA 2 xonali, 6-qavat:\n')
            all_refs = MarketPriceReference.objects.filter(
                xonalar_soni=2,
                etaj=6
            ).order_by('qurilish_turi', 'holat')
            
            for ref in all_refs[:10]:
                self.stdout.write(
                    f"ID: {ref.id} | {ref.get_qurilish_turi_display()} | "
                    f"{ref.get_holat_display()} | {ref.maydon_min}-{ref.maydon_max}m² | "
                    f"Bozor: ${float(ref.bozor_narx):,.0f}/m²"
                )
