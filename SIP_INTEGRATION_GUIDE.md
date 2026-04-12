# 📞 SIP Qo'ng'iroqlar Integratsiyasi - Hujjat

## ✅ Amalga Oshirilgan Xususiyatlar

### 1. **CRM Ulanish Sozlamalari** (`home` app)
- ✓ CRM URL, foydalanuvchi nomi va parolni saqlash
- ✓ JWT token olish va yangilash
- ✓ Token muddati bilan ishlash
- ✓ Ulanish holati monitoring

**Admin Panel**: `/admin/home/crmconfiguration/`

---

### 2. **SIP Qo'ng'iroq Xizmati** (`operators_analys/services.py`)

#### `SIPCallService` Klassi

```python
from operators_analys.services import SIPCallService

service = SIPCallService()

# CRM ga ulanganmi tekshirish
if service.is_connected():
    print("CRM ulangan")

# Qo'ng'iroqlarni olish
result = service.fetch_calls(params={'page': 1, 'page_size': 100})
if result['success']:
    calls = result['results']

# Bazaga saqlash
save_result = service.save_calls(calls)
print(f"Yangi: {save_result['created']}, Yangilangan: {save_result['updated']}")

# Barcha qo'ng'iroqlarni sync qilish
sync_result = service.sync_all_calls(page_size=100)

# Statistika
stats = service.get_stats()
print(f"Jami: {stats['total']}")
print(f"Javob berilgan: {stats['answered']}")
```

---

### 3. **Management Command** (`sync_sip_calls`)

Terminal orqali komandalarni ishlating:

#### Statistika ko'rsatish
```bash
.venv\Scripts\python manage.py sync_sip_calls --stats
```

#### Oxirgi 50 qo'ng'iroqni sync qilish
```bash
.venv\Scripts\python manage.py sync_sip_calls --latest
```

#### Barcha qo'ng'iroqlarni sync qilish (100 ta sahifada)
```bash
.venv\Scripts\python manage.py sync_sip_calls --page-size=100
```

---

### 4. **Web Interface Views** (`operators_analys/views.py`)

#### Qo'ng'iroqlarni ko'rsatish
- URL: `/operators/ip-calls/`
- Filtrlash imkoniyati (telefon, operator, turi, vaqt)
- Pagination
- Holat badge (Javob berildi, Javob berilmadi, Band)

#### API Endpoints

**Qo'ng'iroqlarni olish (JSON)**
```
GET /operators/api/ip-calls/
```

**Sync qilish (AJAX)**
```
POST /operators/api/sync-sip-calls/
```

**Statistika**
```
GET /operators/api/sip-stats/
```

---

### 5. **Template Features** (`templates/operators_analys/ip_calls.html`)

#### 🔄 Sync Tugmasi
- Bir tugmali sync
- Real-time progress
- Notification bilan natija

#### 📊 Statistika Kartasi
- Jami qo'ng'iroqlar
- Javob berilganlar (%)
- Javob berilmaganlar
- Kiruvchi/Chiquvchi

#### 🔍 Filtrlash Paneli
```
- Telefon raqam bo'yicha
- Operator bo'yicha (205, 204, all, ...)
- Qo'ng'iroq turi (Kiruvchi/Chiquvchi)
- Qidiruv (operator/mijoz ismi)
- Tartiblash (eng yangi/eng eski)
- Sahifada nechta (20/50/100)
```

#### 📋 Jadval
- Vaqt
- Telefon raqami
- Operator nomi
- Mijoz ismi
- Qo'ng'iroq turi (📥 Kiruvchi / 📤 Chiquvchi)
- Holat (✓ Javob berildi / ✗ Javob berilmadi / ⚠ Band)
- Audio yozuv havolasi

---

## 📦 Ma'lumotlar Model

### IPPhoneCall Model

```python
call_id          # Qo'ng'iroqning unikal ID si
phone            # Telefon raqami
operator_name    # Operator ismi
client_name      # Mijoz ismi
timestamp        # Qo'ng'iroq vaqti
tree_name        # Qo'ng'iroq turi (Kiruvchi/Chiquvchi)
status           # Holat (answered/missed/busy)
call_record_link # Audio yozuv URL si
src_num          # Qo'ng'iroq qiluvchi raqami
dst_num          # Qabul qiluvchi raqami
duration_seconds # Qo'ng'iroq davomiyligi
```

---

## 🔌 CRM API Sozlamalari

Admin panelda quyidagilarni kiritish kerak:

| Maydon | Qiymat | Misol |
|-------|--------|-------|
| **CRM API URL** | Base URL | `https://megapolis1.uz/api/` |
| **Username** | CRM foydalanuvchi nomi | `admin` |
| **Password** | CRM paroli | `secretPass123` |

**Tekshirish**: "Test Connection" tugmasini bosing

---

## 🚀 **Workflow**

### 1️⃣ Boshlash

```bash
# 1. CRM sozlamalarini admin panelda kiriting
#    /admin/home/crmconfiguration/

# 2. "Test Connection" bosing

# 3. Terminal orqali statistika tekshiring
.venv\Scripts\python manage.py sync_sip_calls --stats
```

### 2️⃣ Qo'ng'iroqlarni Sync Qilish

```bash
# Oxirgi qo'ng'iroqlarni olish
.venv\Scripts\python manage.py sync_sip_calls --latest

# YOKI web interfacedan
#    /operators/ip-calls/ → 🔄 Sync tugmasini bosing
```

### 3️⃣ Qo'ng'iroqlarni Ko'rish

```
http://127.0.0.1:8000/operators/ip-calls/
```

---

## 📱 **API Reference**

### CRM API Endpoints

| Metod | Endpoint | Tavsif |
|-------|----------|--------|
| POST | `/api/login/` | Kirish |
| POST | `/api/token/refresh/` | Token yangilash |
| GET | `/api/ip-phone/` | Qo'ng'iroqlar ro'yxati |
| GET | `/api/ip-phone/<id>/` | Bitta qo'ng'iroq |

### Django Endpoints

| Metod | URL | Tavsif |
|-------|-----|--------|
| GET | `/operators/ip-calls/` | Qo'ng'iroqlar sahifasi |
| GET | `/operators/api/ip-calls/` | Qo'ng'iroqlar (JSON) |
| POST | `/operators/api/sync-sip-calls/` | Sync (AJAX) |
| GET | `/operators/api/sip-stats/` | Statistika (JSON) |

---

## ⚙️ **Konfiguratsiya**

### Settings

```python
# core/settings.py - Installed apps
INSTALLED_APPS = [
    ...
    'home',  # CRM Configuration
    'operators_analys',  # SIP Calls
]
```

### URLs

```python
# core/urls.py
urlpatterns = [
    ...
    path('operators/', include('operators_analys.urls')),
]

# operators_analys/urls.py
urlpatterns = [
    path('ip-calls/', views.ip_calls_view, name='ip_calls'),
    path('api/ip-calls/', views.ip_calls_api, name='ip_calls_api'),
    path('api/sync-sip-calls/', views.sync_sip_calls_view, name='sync_sip_calls'),
    path('api/sip-stats/', views.sip_calls_stats_view, name='sip_stats'),
]
```

---

## 🐛 **Troubleshooting**

### ❌ "CRM ulangan emas"
- [ ] Admin paneldan CRM URL, username, password kiritinganmi?
- [ ] "Test Connection" tugmasini bosdinmi?
- [ ] CRM serverida masalalar bormi? (https://megapolis1.uz/api/swagger/)

### ❌ "404 - ip-phone/ topilmadi"
- [ ] CRM API URL to'g'rimi? (`https://megapolis1.uz/api/`)
- [ ] Token muddati o'tganmi? (Admin paneldan yangilash)
- [ ] CRM serverida bu endpoint bormi?

### ❌ Qo'ng'iroqlar ko'rsatilmayapti
- [ ] Bazada ma'lumot bormi? (`--stats` bilan tekshiring)
- [ ] Sync qildingizmi? (`--latest` bilan sync qiling)
- [ ] Filterlar to'g'rimi?

---

## 📊 **Data Flow**

```
┌─────────────────┐
│  CRM API Server │ (https://megapolis1.uz/api/)
└────────┬────────┘
         │ Login → Token
         │
┌────────▼────────────────────────┐
│  CRM Configuration (home/models)│
│ - access_token                  │
│ - refresh_token                 │
│ - is_connected                  │
└────────┬────────────────────────┘
         │
┌────────▼──────────────────────┐
│  SIPCallService (fetch/save)   │
│ - fetch_calls()                │
│ - save_calls()                 │
│ - sync_all_calls()             │
└────────┬──────────────────────┘
         │
┌────────▼────────────────────────┐
│  IPPhoneCall Model (Database)   │
│ - call_id                       │
│ - phone, operator, status...    │
└────────┬────────────────────────┘
         │
┌────────▼──────────────────────┐
│  Web Interface (/ip-calls/)    │
│  - Jadval                      │
│  - Filtrlash                   │
│  - Statistika                  │
└────────────────────────────────┘
```

---

## 🎯 **Keyingi Qadam**

- [ ] Cron job qo'shish (avtomatik sync har saat)
- [ ] Export (CSV, Excel)
- [ ] Real-time WebSocket notifications
- [ ] Call recording download
- [ ] Advanced analytics dashboard
- [ ] Slack/Telegram notifications

---

## 📝 **File Structure**

```
operators_analys/
├── models.py                    # IPPhoneCall model
├── views.py                     # Views (ip_calls, sync, stats)
├── services.py                  # SIPCallService class
├── urls.py                      # API endpoints
├── admin.py                     # Admin registration
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       └── sync_sip_calls.py   # Management command
└── tests.py

home/
├── models.py                    # CRMConfiguration model
├── views.py                     # CRM settings view
├── forms.py                     # CRMConfigurationForm
├── admin.py                     # Admin panel

templates/
└── operators_analys/
    └── ip_calls.html            # UI with sync/filter
```

---

## ✨ **Xulosa**

✅ **SIP qo'ng'iroqlar integratsiyasi to'lik amalga oshirildi:**

1. ✓ CRM API ga ulanish
2. ✓ JWT token bilan autentifikatsiya
3. ✓ Qo'ng'iroqlarni CRM dan olish
4. ✓ Bazaga saqlash (create/update)
5. ✓ Web interface (jadval, filtrlash, statistika)
6. ✓ Management command
7. ✓ API endpoints (JSON)
8. ✓ One-click sync tugmasi

**Ishlash** uchun admin paneldan CRM sozlamalarini kiritib, sync qiling! 🚀

---

*Oxirgi yangilash: 2026-04-13*
