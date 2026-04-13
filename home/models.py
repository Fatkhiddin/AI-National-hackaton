from django.db import models
import requests
from urllib.parse import urljoin


class CRMConfiguration(models.Model):
    """
    CRM Integration yaratish va sozlamalarni saqlash
    """
    crm_url = models.URLField(
        verbose_name="CRM API URL",
        help_text="Base URL: masalan https://megapolis1.uz/api/",
        blank=True,
        null=True,
        default=""
    )
    username = models.CharField(
        max_length=255,
        verbose_name="CRM Username",
        blank=True,
        default=""
    )
    password = models.CharField(
        max_length=255,
        verbose_name="CRM Password",
        blank=True,
        default=""
    )
    access_token = models.TextField(
        blank=True,
        null=True,
        verbose_name="JWT Access Token"
    )
    refresh_token = models.TextField(
        blank=True,
        null=True,
        verbose_name="JWT Refresh Token"
    )
    token_expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Token muddati"
    )
    is_connected = models.BooleanField(
        default=False,
        verbose_name="Ulanish holati"
    )
    last_connection_attempt = models.DateTimeField(
        auto_now=True,
        verbose_name="Oxirgi ulanish urinishi"
    )
    connection_error_message = models.TextField(
        blank=True,
        verbose_name="Agar xato bo'lsa, xabar"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "CRM Configuration"
        verbose_name_plural = "CRM Configurations"
        ordering = ['-updated_at']

    def __str__(self):
        status = "✓ Ulangan" if self.is_connected else "✗ Ulanmagan"
        return f"CRM - {self.crm_url} ({status})"

    def test_connection(self):
        """
        CRM ga ulanish tekshirish
        """
        # CRM ma'lumotlari bo'sh bo'lsa, xato qaytarish
        if not self.crm_url or not self.username or not self.password:
            self.is_connected = False
            self.connection_error_message = "CRM sozlamalari to'liq emas. Iltimos, CRM URL, username va passwordni kiriting."
            self.save()
            return False, "CRM sozlamalari to'liq emas"
        
        try:
            login_url = urljoin(self.crm_url, 'login/')
            
            response = requests.post(
                login_url,
                json={
                    "username": self.username,
                    "password": self.password
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                self.is_connected = True
                self.connection_error_message = ""
                self.save()
                return True, "✓ CRM ga muvaffaqiyatli ulandik!"
            else:
                self.is_connected = False
                self.connection_error_message = f"Status {response.status_code}: {response.text}"
                self.save()
                return False, f"Xato: {response.status_code} - {response.text}"
                
        except requests.exceptions.Timeout:
            self.is_connected = False
            self.connection_error_message = "Timeout: CRM javob bermadi"
            self.save()
            return False, "Timeout xatosi"
        except requests.exceptions.ConnectionError:
            self.is_connected = False
            self.connection_error_message = "Ulanish xatosi"
            self.save()
            return False, "Ulanish xatosi"
        except Exception as e:
            self.is_connected = False
            self.connection_error_message = str(e)
            self.save()
            return False, f"Xato: {str(e)}"

    def get_headers(self):
        """
        CRM API uchun headers
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def refresh_access_token(self):
        """
        Access tokenni yangilash
        """
        if not self.refresh_token:
            return False, "Refresh token yo'q"
        
        try:
            refresh_url = urljoin(self.crm_url, 'token/refresh/')
            response = requests.post(
                refresh_url,
                json={"refresh": self.refresh_token},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access')
                self.save()
                return True, "Token yangilandi"
            else:
                return False, f"Token yangilash xatosi: {response.status_code}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_config():
        """
        Yangi yoki mavjud CRM konfiguratsiyasini olish
        """
        config, created = CRMConfiguration.objects.get_or_create(id=1)
        return config


class AIConfiguration(models.Model):
    """
    AI API konfiguratsiyasi (Anthropic Claude / OpenAI)
    """
    AI_PROVIDER_CHOICES = [
        ('anthropic', 'Anthropic (Claude)'),
        ('openai', 'OpenAI (GPT)'),
    ]

    provider = models.CharField(
        max_length=20,
        verbose_name="AI Provider",
        choices=AI_PROVIDER_CHOICES,
        default="anthropic"
    )
    api_key = models.CharField(
        max_length=255,
        verbose_name="API Key",
        help_text="Anthropic yoki OpenAI API kaliti",
        blank=True,
        default=""
    )
    model = models.CharField(
        max_length=100,
        verbose_name="AI Model",
        default="claude-sonnet-4-20250514",
        help_text="Masalan: claude-sonnet-4-20250514, gpt-4o"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "AI Configuration"
        verbose_name_plural = "AI Configurations"
        ordering = ['-updated_at']

    def __str__(self):
        provider_name = dict(self.AI_PROVIDER_CHOICES).get(self.provider, self.provider)
        return f"{provider_name} - {'Sozlangan' if self.api_key else 'Sozlanmagan'}"

    @staticmethod
    def get_config():
        """
        Yangi yoki mavjud AI konfiguratsiyasini olish
        """
        config, created = AIConfiguration.objects.get_or_create(id=1)
        return config


class UzbekVoiceConfiguration(models.Model):
    """
    UzbekVoice.ai STT API konfiguratsiyasi
    Admin paneldan UZBEKVOICE_API_KEY kiritiladi
    """
    api_key = models.CharField(
        max_length=500,
        verbose_name="UzbekVoice API Key",
        help_text="UzbekVoice.ai dan olingan API kalit (Authorization header uchun)",
        blank=True,
        default=""
    )
    api_url = models.URLField(
        max_length=500,
        verbose_name="API URL",
        default="https://uzbekvoice.ai/api/v1/stt",
        help_text="UzbekVoice.ai STT API endpoint"
    )
    default_language = models.CharField(
        max_length=10,
        choices=[
            ('uz', "O'zbek"),
            ('ru', 'Rus'),
            ('ru-uz', "O'zbek-Rus (Aralash)"),
        ],
        default='uz',
        verbose_name="Default til"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "UzbekVoice STT Configuration"
        verbose_name_plural = "UzbekVoice STT Configurations"

    def __str__(self):
        status = "✓ Sozlangan" if self.api_key else "✗ Sozlanmagan"
        return f"UzbekVoice STT ({status})"

    @staticmethod
    def get_config():
        config, created = UzbekVoiceConfiguration.objects.get_or_create(id=1)
        return config