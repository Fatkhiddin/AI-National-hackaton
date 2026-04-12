from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from home.models import CRMConfiguration
from urllib.parse import urljoin
import requests
from django.contrib import messages
from .services import SIPCallService
from .models import IPPhoneCall


@login_required(login_url='user:login')
@require_http_methods(["GET"])
def ip_calls_view(request):
    """
    CRM dan IP telefon qo'ng'iroqlarini ko'rsatish
    """
    config = CRMConfiguration.get_config()
    calls = []
    error_message = None
    context = {}
    
    if not config.is_connected or not config.access_token:
        error_message = "CRM ulangan emas. Admin paneldan CRM konfiguratsiyasini tekshiring."
        context = {
            'calls': [],
            'error_message': error_message,
            'crm_connected': False,
            'count': 0,
            'total_pages': 0,
            'page': 1,
        }
    else:
        try:
            # CRM API dan qo'ng'iroqlarni fetch qilish
            api_url = urljoin(config.crm_url, 'ip-phone/')
            
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            
            params = {
                'page': page,
                'page_size': page_size,
                'ordering': request.GET.get('ordering', '-timestamp'),
            }
            
            # Filter parametrlari
            if request.GET.get('operator'):
                params['operator'] = request.GET.get('operator')
            if request.GET.get('treeName'):
                params['treeName'] = request.GET.get('treeName')
            if request.GET.get('phone'):
                params['phone'] = request.GET.get('phone')
            if request.GET.get('search'):
                params['search'] = request.GET.get('search')
            
            headers = config.get_headers()
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                calls = data.get('results', [])
                count = data.get('count', 0)
                total_pages = data.get('total_pages', 1)
                
                context = {
                    'calls': calls,
                    'count': count,
                    'total_pages': total_pages,
                    'current_page': data.get('current_page', page),
                    'next': data.get('next'),
                    'previous': data.get('previous'),
                    'page': page,
                    'page_size': page_size,
                    'crm_connected': True,
                }
            elif response.status_code == 401:
                error_message = "CRM token muddati o'tgan. Iltimos, CRM sozlamalarini yangilang."
                context = {
                    'calls': [],
                    'error_message': error_message,
                    'crm_connected': False,
                    'count': 0,
                    'total_pages': 0,
                    'page': 1,
                }
            elif response.status_code == 404:
                error_message = "CRM API endpoint topilmadi. API endpointi noto'g'ri bo'lishi mumkin."
                context = {
                    'calls': [],
                    'error_message': error_message,
                    'crm_connected': False,
                    'count': 0,
                    'total_pages': 0,
                    'page': 1,
                }
            else:
                error_message = f"CRM xatosi: {response.status_code} - {response.text[:200]}"
                context = {
                    'calls': [],
                    'error_message': error_message,
                    'crm_connected': False,
                    'count': 0,
                    'total_pages': 0,
                    'page': 1,
                }
        except requests.exceptions.Timeout:
            error_message = "CRM javob bermadi (Timeout). Iltimos, CRM serverini tekshiring."
            context = {
                'calls': [],
                'error_message': error_message,
                'crm_connected': False,
                'count': 0,
                'total_pages': 0,
                'page': 1,
            }
        except requests.exceptions.ConnectionError:
            error_message = "CRM serveriga ulanib bo'lmadi."
            context = {
                'calls': [],
                'error_message': error_message,
                'crm_connected': False,
                'count': 0,
                'total_pages': 0,
                'page': 1,
            }
        except Exception as e:
            error_message = f"Xato: {str(e)}"
            context = {
                'calls': [],
                'error_message': error_message,
                'crm_connected': False,
                'count': 0,
                'total_pages': 0,
                'page': 1,
            }
    
    return render(request, 'operators_analys/ip_calls.html', context)


@login_required(login_url='user:login')
@require_http_methods(["GET"])
def ip_calls_api(request):
    """
    AJAX uchun IP qo'ng'iroqlarni JSON formatida qaytarish
    """
    config = CRMConfiguration.get_config()
    
    if not config.is_connected or not config.access_token:
        return JsonResponse({'error': 'CRM ulangan emas'}, status=400)
    
    try:
        api_url = urljoin(config.crm_url, 'ip-phone/')
        
        params = {
            'page': request.GET.get('page', 1),
            'page_size': request.GET.get('page_size', 20),
            'ordering': request.GET.get('ordering', '-timestamp'),
        }
        
        if request.GET.get('operator'):
            params['operator'] = request.GET.get('operator')
        if request.GET.get('treeName'):
            params['treeName'] = request.GET.get('treeName')
        
        headers = config.get_headers()
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': f'CRM xatosi: {response.status_code}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required(login_url='user:login')
@require_http_methods(["POST"])
def sync_sip_calls_view(request):
    """
    CRM dan SIP qo'ng'iroqlarni sync qilish (AJAX)
    """
    try:
        service = SIPCallService()
        
        if not service.is_connected():
            return JsonResponse({
                'success': False,
                'error': 'CRM ulangan emas'
            }, status=400)
        
        # Oxirgi qo'ng'iroqlarni olish (bir sahifa)
        result = service.fetch_calls({'page_size': 100})
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
        
        # Bazaga saqlash
        calls = result.get('results', [])
        save_result = service.save_calls(calls)
        
        messages.success(request, f"✓ SIP Qo'ng'iroqlar sync qilindi: +{save_result['created']} yangi, ↻{save_result['updated']} yangilangan")
        
        return JsonResponse({
            'success': True,
            'created': save_result['created'],
            'updated': save_result['updated'],
            'errors': save_result['errors'],
            'message': save_result['message']
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required(login_url='user:login')
@require_http_methods(["GET"])
def sip_calls_stats_view(request):
    """
    SIP qo'ng'iroqlar statistikasini JSON formatida qaytarish
    """
    try:
        service = SIPCallService()
        stats = service.get_stats()
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

