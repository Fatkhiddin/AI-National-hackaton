from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .models import CRMConfiguration, AIConfiguration
from .forms import CRMConfigurationForm, AIConfigurationForm


@login_required(login_url='user:login')
@require_http_methods(["GET", "POST"])
def crm_settings_view(request):
    """
    CRM sozlamalarini tahrirish va tekshirish
    """
    config = CRMConfiguration.get_config()
    
    if request.method == 'POST':
        form = CRMConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save()
            messages.success(request, "✓ CRM sozlamalari saqlandi!")
            return redirect('home:crm_settings')
        else:
            messages.error(request, "Xato: Forma noto'g'ri!")
    else:
        form = CRMConfigurationForm(instance=config)
    
    context = {
        'form': form,
        'config': config,
    }
    return render(request, 'home/crm_settings.html', context)


@login_required(login_url='user:login')
@require_http_methods(["POST"])
def crm_test_connection_view(request):
    """
    CRM ulanishini tekshirish (AJAX)
    """
    config = CRMConfiguration.get_config()
    success, message = config.test_connection()
    
    return JsonResponse({
        'success': success,
        'message': message,
        'is_connected': config.is_connected,
        'error_message': config.connection_error_message
    })


@login_required(login_url='user:login')
def crm_status_view(request):
    """
    CRM ulanish holatini ko'rsatish (AJAX)
    """
    config = CRMConfiguration.get_config()
    
    return JsonResponse({
        'is_connected': config.is_connected,
        'crm_url': config.crm_url,
        'last_connection_attempt': config.last_connection_attempt.isoformat() if config.last_connection_attempt else None,
        'error_message': config.connection_error_message,
        'has_token': bool(config.access_token)
    })


@login_required(login_url='user:login')
@require_http_methods(["GET", "POST"])
def ai_settings_view(request):
    """
    AI sozlamalarini tahrirlash
    """
    config = AIConfiguration.get_config()

    if request.method == 'POST':
        form = AIConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "✓ AI sozlamalari saqlandi!")
            return redirect('home:ai_settings')
        else:
            messages.error(request, "Xato: Forma noto'g'ri!")
    else:
        form = AIConfigurationForm(instance=config)

    context = {
        'form': form,
        'config': config,
    }
    return render(request, 'home/ai_settings.html', context)


@login_required(login_url='user:login')
@require_http_methods(["POST"])
def ai_test_connection_view(request):
    """
    AI API ulanishini tekshirish (AJAX)
    """
    config = AIConfiguration.get_config()

    if not config.api_key:
        return JsonResponse({'success': False, 'message': 'API Key kiritilmagan!'})

    try:
        import requests as req
        if config.provider == 'anthropic':
            resp = req.get(
                'https://api.anthropic.com/v1/models',
                headers={
                    'x-api-key': config.api_key,
                    'anthropic-version': '2023-06-01'
                },
                timeout=10
            )
        else:
            resp = req.get(
                'https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {config.api_key}'},
                timeout=10
            )

        if resp.status_code == 200:
            return JsonResponse({'success': True, 'message': '✓ AI API muvaffaqiyatli ulandi!'})
        elif resp.status_code == 401:
            return JsonResponse({'success': False, 'message': 'API Key noto\'g\'ri!'})
        else:
            return JsonResponse({'success': False, 'message': f'Xato: {resp.status_code}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ulanish xatosi: {str(e)}'})
