"""
Ma'lumotlar bazasini JSON formatda backup qilish
Run: python backup_db.py
"""
import os
import sys
import django
from datetime import datetime
import json

# Django sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core import serializers
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

def backup_database():
    """Barcha modellarni JSON formatda export qilish"""
    
    # Backup fayl nomi (sana bilan)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'database_backup_{timestamp}.json'
    
    print(f"🔄 Ma'lumotlar bazasi backup qilinmoqda...")
    print(f"📁 Fayl: {backup_file}")
    
    all_data = []
    
    # Barcha ilovalarni va modellarni olish
    for app_config in apps.get_app_configs():
        # sessions va migrations ni o'tkazib yuborish
        if app_config.name in ['django.contrib.sessions', 'django.contrib.migrations']:
            continue
            
        for model in app_config.get_models():
            model_name = model._meta.label
            print(f"  ⏳ {model_name} exportlanmoqda...")
            
            try:
                # Modeldan barcha ma'lumotlarni olish
                queryset = model.objects.all()
                count = queryset.count()
                
                if count > 0:
                    # JSON formatga o'tkazish
                    serialized = serializers.serialize('json', queryset)
                    data = json.loads(serialized)
                    all_data.extend(data)
                    print(f"    ✅ {count} ta yozuv export qilindi")
                else:
                    print(f"    ⚠️  Bo'sh model")
                    
            except Exception as e:
                print(f"    ❌ Xato: {str(e)}")
    
    # Faylga yozish
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
        print(f"\n✅ Backup muvaffaqiyatli yaratildi!")
        print(f"📊 Jami yozuvlar: {len(all_data)}")
        print(f"💾 Fayl hajmi: {file_size:.2f} MB")
        print(f"📂 Joylashuv: {os.path.abspath(backup_file)}")
        
        return backup_file
        
    except Exception as e:
        print(f"\n❌ Faylga yozishda xato: {str(e)}")
        return None

if __name__ == '__main__':
    try:
        backup_file = backup_database()
        if backup_file:
            print(f"\n💡 Restore qilish uchun: python restore_db.py {backup_file}")
    except Exception as e:
        print(f"\n❌ Umumiy xato: {str(e)}")
        sys.exit(1)
