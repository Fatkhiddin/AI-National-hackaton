from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .models import CRMConfiguration
from .forms import CRMConfigurationForm


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
