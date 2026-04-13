# 2ta Django Loyihani 1ta Serverda Ishlatish

## Arxitektura: Mikroservis + Nginx Reverse Proxy

### 1. Server Strukturasi
```
Server (1 domen)
├── Nginx (Port 80/443)
├── Django CRM Loyiha (Port 8001)
└── Django Telegram Loyiha (Port 8002)
```

### 2. Nginx Konfiguratsiyasi

```nginx
# /etc/nginx/sites-available/your-domain.conf

# CRM loyiha
server {
    listen 80;
    server_name crm.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/crm/static/;
    }

    location /media/ {
        alias /var/www/crm/media/;
    }
}

# Telegram loyiha
server {
    listen 80;
    server_name telegram.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/telegram/static/;
    }

    location /media/ {
        alias /var/www/telegram/media/;
    }
}

# Yoki 1ta domen, turli path bilan:
server {
    listen 80;
    server_name yourdomain.com;

    location /crm/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /telegram/ {
        proxy_pass http://127.0.0.1:8002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Systemd Service (Linux)

#### CRM Service
```ini
# /etc/systemd/system/crm.service
[Unit]
Description=CRM Django Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/crm
Environment="PATH=/var/www/crm/venv/bin"
ExecStart=/var/www/crm/venv/bin/gunicorn core.wsgi:application --bind 127.0.0.1:8001 --workers 3

[Install]
WantedBy=multi-user.target
```

#### Telegram Service
```ini
# /etc/systemd/system/telegram.service
[Unit]
Description=Telegram Django Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/telegram
Environment="PATH=/var/www/telegram/venv/bin"
ExecStart=/var/www/telegram/venv/bin/gunicorn core.wsgi:application --bind 127.0.0.1:8002 --workers 3

[Install]
WantedBy=multi-user.target
```

### 4. Windows Server (IIS yoki Manual)

#### Option A: 2ta PowerShell terminali
```powershell
# Terminal 1 - CRM
cd C:\www\crm
.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8001

# Terminal 2 - Telegram
cd C:\www\telegram
.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8002
```

#### Option B: Windows Service (NSSM bilan)
```powershell
# NSSM yuklab oling
# CRM uchun service
nssm install CRM_Django "C:\www\crm\.venv\Scripts\python.exe"
nssm set CRM_Django AppParameters "manage.py runserver 127.0.0.1:8001"
nssm set CRM_Django AppDirectory "C:\www\crm"

# Telegram uchun service
nssm install Telegram_Django "C:\www\telegram\.venv\Scripts\python.exe"
nssm set Telegram_Django AppParameters "manage.py runserver 127.0.0.1:8002"
nssm set Telegram_Django AppDirectory "C:\www\telegram"

# Ishga tushirish
nssm start CRM_Django
nssm start Telegram_Django
```

### 5. Database Strategiyasi

#### Option A: Har birining o'z databasesi (Tavsiya)
```python
# CRM settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'crm_db',
        'USER': 'crm_user',
        'PASSWORD': 'password',
    }
}

# Telegram settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'telegram_db',
        'USER': 'telegram_user',
        'PASSWORD': 'password',
    }
}
```

#### Option B: 1ta database, turli schema (PostgreSQL)
```python
# CRM settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'main_db',
        'USER': 'user',
        'OPTIONS': {
            'options': '-c search_path=crm_schema'
        }
    }
}

# Telegram settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'main_db',
        'USER': 'user',
        'OPTIONS': {
            'options': '-c search_path=telegram_schema'
        }
    }
}
```

### 6. Ma'lumot almashish (agar kerak bo'lsa)

#### REST API orqali
```python
# CRM loyihada API
# crm/api/views.py
from rest_framework.views import APIView

class ClientDataAPI(APIView):
    def get(self, request):
        # Ma'lumot qaytarish
        pass

# Telegram loyihada ishlatish
import requests

def get_crm_data():
    response = requests.get('http://127.0.0.1:8001/api/clients/')
    return response.json()
```

#### Shared Database orqali (agar zarur bo'lsa)
```python
# settings.py (ikkalasida ham)
DATABASES = {
    'default': {
        # O'z databasesi
    },
    'shared': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'shared_db',
        # Umumiy ma'lumotlar uchun
    }
}
```

### 7. ALLOWED_HOSTS sozlash

```python
# CRM settings.py
ALLOWED_HOSTS = ['crm.yourdomain.com', '127.0.0.1', 'localhost']

# Telegram settings.py
ALLOWED_HOSTS = ['telegram.yourdomain.com', '127.0.0.1', 'localhost']

# Yoki 1ta domen bo'lsa
ALLOWED_HOSTS = ['yourdomain.com', '127.0.0.1', 'localhost']
```

### 8. Requirements

```txt
# Har ikkala loyihada
gunicorn==21.2.0  # Production uchun
psycopg2-binary==2.9.9  # PostgreSQL uchun
requests==2.31.0  # API uchun
```

### 9. Ishga tushirish

```bash
# Linux
sudo systemctl start crm
sudo systemctl start telegram
sudo systemctl enable crm
sudo systemctl enable telegram
sudo systemctl restart nginx

# Windows (NSSM bilan)
nssm start CRM_Django
nssm start Telegram_Django
```

## Afzalliklar:

1. ✅ Har bir loyiha mustaqil ishlaydi
2. ✅ Alohida deploy qilish mumkin
3. ✅ Bir loyiha ishlamasa, ikkinchisi ishlaydi
4. ✅ Database yuklanishi taqsimlangan
5. ✅ Scaling oson
6. ✅ 1ta domen, 2ta subdomain

## Xulosa:

**Sizning holatda eng yaxshi variant:**
- 2ta alohida loyiha
- 2ta subdomain (`crm.domain.com`, `telegram.domain.com`)
- Har birining o'z databasesi
- Nginx reverse proxy
- Kerak bo'lsa REST API orqali ma'lumot almashish

Bu yondashuv professional, scalable va maintain qilish oson!
