from django import forms
from .models import CRMConfiguration, AIConfiguration


class CRMConfigurationForm(forms.ModelForm):
    """
    CRM Konfiguratsiya formi frontend uchun
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'CRM parolni kiriting'
        }),
        help_text="Parol shifrlangan ko'rinishda saqlanadi"
    )

    class Meta:
        model = CRMConfiguration
        fields = ('crm_url', 'username', 'password')
        widgets = {
            'crm_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://megapolis1.uz/api/'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CRM foydalanuvchi nomi'
            }),
        }


class AIConfigurationForm(forms.ModelForm):
    """
    AI Konfiguratsiya formi frontend uchun
    """
    api_key = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'sk-ant-... yoki sk-...'
        }),
        help_text="API kaliti xavfsiz saqlanadi",
        required=False
    )

    class Meta:
        model = AIConfiguration
        fields = ('provider', 'api_key', 'model')
        widgets = {
            'provider': forms.Select(attrs={
                'class': 'form-control',
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'claude-sonnet-4-20250514'
            }),
        }

    def clean_crm_url(self):
        url = self.cleaned_data.get('crm_url')
        if url and not url.endswith('/'):
            url = url + '/'
        return url
