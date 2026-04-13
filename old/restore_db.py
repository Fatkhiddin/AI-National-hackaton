"""
JSON backup faylidan ma'lumotlar bazasini tiklash
Run: python restore_db.py database_backup_20241207_123456.json
"""
import os
import sys
import django
import json

# Django sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core import serializers
from django.db import transaction
from io import StringIO

def restore_database(backup_file):
    """JSON fayldan ma'lumotlarni import qilish"""
    
    if not os.path.exists(backup_file):
        print(f"❌ Fayl topilmadi: {backup_file}")
        return False
    
    print(f"🔄 Ma'lumotlar bazasi tiklanmoqda...")
    print(f"📁 Fayl: {backup_file}")
    
    try:
        # Faylni o'qish
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 Jami yozuvlar: {len(data)}")
        
        # Ma'lumotlarni model tartibida saralash
        # Avval bog'liq bo'lmagan modellar, keyin bog'liq modellar
        model_order = [
            'contenttypes.contenttype',
            'auth.permission',
            'auth.group',
            'auth.user',
            'admin.logentry',
            'home.telegramaccount',
            'home.chat',
            'home.contact',
            'home.message',
            'home.autoreplyrule',
            'home.autoreplylog',
            'home.aiprovider',
            'home.aiassistant',
            'home.conversationsummary',
            'home.crmprovider',
            'home.propertysearchlog',
            'home.propertyinterest',
        ]
        
        # Ma'lumotlarni model bo'yicha guruhlash
        grouped_data = {}
        for item in data:
            model = item.get('model', '')
            if model not in grouped_data:
                grouped_data[model] = []
            grouped_data[model].append(item)
        
        print("\n📋 Modellar ro'yxati:")
        for model, items in grouped_data.items():
            print(f"  - {model}: {len(items)} ta yozuv")
        
        imported = 0
        errors = 0
        error_details = []
        
        print("\n⏳ Import jarayoni boshlandi...")
        
        # Har bir modelni alohida transaction ichida import qilish
        # Avval tartibdagi modellarni import qilish
        for model_name in model_order:
            if model_name in grouped_data:
                print(f"\n  📦 {model_name} import qilinmoqda...")
                items = grouped_data[model_name]
                model_imported = 0
                model_errors = 0
                
                for obj in serializers.deserialize('json', json.dumps(items)):
                    try:
                        # get_or_create for contenttypes to avoid duplicates
                        if model_name == 'contenttypes.contenttype':
                            # Contenttype ni update_or_create qilish
                            from django.contrib.contenttypes.models import ContentType
                            ct_data = obj.object
                            ContentType.objects.get_or_create(
                                app_label=ct_data.app_label,
                                model=ct_data.model,
                                defaults={'id': ct_data.id}
                            )
                            imported += 1
                            model_imported += 1
                        else:
                            with transaction.atomic():
                                obj.save()
                                imported += 1
                                model_imported += 1
                    except Exception as e:
                        errors += 1
                        model_errors += 1
                        if len(error_details) < 10:
                            error_details.append(f"{model_name}: {str(e)[:100]}")
                
                print(f"    ✅ {model_imported} ta yozuv import qilindi", end="")
                if model_errors > 0:
                    print(f" (⚠️ {model_errors} ta xato)")
                else:
                    print()
        
        # Qolgan modellarni import qilish
        remaining_models = set(grouped_data.keys()) - set(model_order)
        if remaining_models:
            print(f"\n  📦 Qolgan modellar import qilinmoqda...")
            for model_name in remaining_models:
                print(f"    - {model_name}...")
                items = grouped_data[model_name]
                model_imported = 0
                model_errors = 0
                
                for obj in serializers.deserialize('json', json.dumps(items)):
                    try:
                        with transaction.atomic():
                            obj.save()
                            imported += 1
                            model_imported += 1
                    except Exception as e:
                        errors += 1
                        model_errors += 1
                        if len(error_details) < 10:
                            error_details.append(f"{model_name}: {str(e)}")
                
                print(f"      ✅ {model_imported} ta import qilindi", end="")
                if model_errors > 0:
                    print(f" (⚠️ {model_errors} ta xato)")
                else:
                    print()
        
        print(f"\n✅ Restore muvaffaqiyatli yakunlandi!")
        print(f"📈 Import qilindi: {imported} ta yozuv")
        if errors > 0:
            print(f"⚠️  Xatolar: {errors} ta yozuv")
            if error_details:
                print("\n❌ Xato tafsilotlari:")
                for detail in error_details:
                    print(f"  - {detail}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON fayl noto'g'ri formatda: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Restore jarayonida xato: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def clear_database():
    """Ma'lumotlar bazasini tozalash (ixtiyoriy)"""
    from django.apps import apps
    from django.db import connection
    from django.conf import settings
    
    response = input("\n⚠️  Avval mavjud ma'lumotlarni o'chirib tashlashni xohlaysizmi? (yes/no): ")
    
    if response.lower() in ['yes', 'y', 'ha']:
        print("\n🗑️  Ma'lumotlar bazasi tozalanmoqda...")
        
        # Ma'lumotlar bazasi turini aniqlash
        db_engine = settings.DATABASES['default']['ENGINE']
        is_postgresql = 'postgresql' in db_engine or 'psycopg' in db_engine
        is_sqlite = 'sqlite' in db_engine
        
        # Foreign key constraint larni o'chirish
        with connection.cursor() as cursor:
            if is_sqlite:
                cursor.execute('PRAGMA foreign_keys = OFF;')
            elif is_postgresql:
                cursor.execute('SET CONSTRAINTS ALL DEFERRED;')
        
        # Modellarni teskari tartibda o'chirish (bog'liq modellardan boshlab)
        delete_order = [
            'home.propertyinterest',
            'home.propertysearchlog',
            'home.crmprovider',
            'home.conversationsummary',
            'home.aiassistant',
            'home.aiprovider',
            'home.autoreplylog',
            'home.autoreplyrule',
            'home.message',
            'home.contact',
            'home.chat',
            'home.telegramaccount',
            'admin.logentry',
        ]
        
        for model_label in delete_order:
            try:
                app_label, model_name = model_label.split('.')
                model = apps.get_model(app_label, model_name)
                count = model.objects.count()
                if count > 0:
                    model.objects.all().delete()
                    print(f"  🗑️  {model_label}: {count} ta yozuv o'chirildi")
            except Exception as e:
                print(f"  ⚠️  {model_label}: {str(e)}")
        
        # Foreign key constraint larni qayta yoqish
        with connection.cursor() as cursor:
            if is_sqlite:
                cursor.execute('PRAGMA foreign_keys = ON;')
            # PostgreSQL uchun DEFERRED mode avtomatik qayta tiklanadi
        
        print("✅ Ma'lumotlar bazasi tozalandi\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("❌ Foydalanish: python restore_db.py <backup_fayl.json>")
        print("\n📂 Mavjud backup fayllar:")
        
        # Backup fayllarni ko'rsatish
        backup_files = [f for f in os.listdir('.') if f.startswith('database_backup_') and f.endswith('.json')]
        if backup_files:
            for i, f in enumerate(sorted(backup_files, reverse=True), 1):
                size = os.path.getsize(f) / (1024 * 1024)
                print(f"  {i}. {f} ({size:.2f} MB)")
        else:
            print("  ⚠️  Backup fayl topilmadi")
        
        sys.exit(1)
    
    backup_file = sys.argv[1]
    
    try:
        # Ixtiyoriy: avval ma'lumotlarni tozalash
        clear_database()
        
        # Ma'lumotlarni tiklash
        success = restore_database(backup_file)
        
        if success:
            print("\n🎉 Restore jarayoni tugadi!")
        else:
            print("\n❌ Restore jarayonida muammo yuz berdi")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Jarayon to'xtatildi")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Umumiy xato: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
