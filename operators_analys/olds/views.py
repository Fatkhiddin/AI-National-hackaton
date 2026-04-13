# employee_analytics/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.conf import settings
from datetime import datetime, timedelta

from .models import AIConfiguration, STTRecord, AIAnalysis, OperatorPerformance
from .services import process_call_recording, analyze_text_with_ai
from operators_managements.models import SipuniCallRecord
from home.models import SIPCall
from users.models import CustomUser


# ═══════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════

def analytics_permission_required(view_func):
    """
    Faqat boss, direktor, lider operator ruxsati
    """
    def wrapper(request, *args, **kwargs):
        from operators_managements.models import OperatorLeader
        
        # Autentifikatsiya tekshiruvi
        if not request.user.is_authenticated:
            # AJAX so'rov uchun JSON qaytarish
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': 'Tizimga kirish kerak. Iltimos qaytadan login qiling.'
                }, status=401)
            # Oddiy so'rov uchun redirect
            return redirect('users:login')
        
        is_leader = OperatorLeader.objects.filter(user=request.user).exists()
        
        # Ruxsat tekshiruvi
        if request.user.role not in ['direktor', 'boss'] and not is_leader:
            # AJAX so'rov uchun JSON qaytarish
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': "Ruxsat yo'q - faqat rahbarlar va lider operatorlar uchun"
                }, status=403)
            # Oddiy so'rov uchun redirect
            messages.error(request, "Ruxsat yo'q - faqat rahbarlar va lider operatorlar uchun")
            return redirect('home:index')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


# ═══════════════════════════════════════════════════════
# AJAX ENDPOINTS
# ═══════════════════════════════════════════════════════

@analytics_permission_required
def convert_to_text_ajax(request, call_id, call_type):
    """
    AJAX: Qo'ng'iroqni textga o'girish
    
    Args:
        call_id: Qo'ng'iroq ID
        call_type: 'sipuni' yoki 'sipcall'
    """
    # Debug logging
    print(f"=== convert_to_text_ajax called ===")
    print(f"Method: {request.method}")
    print(f"Call ID: {call_id}")
    print(f"Call Type: {call_type}")
    print(f"Headers: {dict(request.headers)}")
    print(f"User: {request.user}")
    print(f"User authenticated: {request.user.is_authenticated}")
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Faqat POST metod'})
    
    try:
        # Qo'ng'iroqni topish
        if call_type == 'sipuni':
            call_record = get_object_or_404(SipuniCallRecord, id=call_id)
            audio_url = call_record.record_url
        elif call_type == 'sipcall':
            call_record = get_object_or_404(SIPCall, id=call_id)
            audio_url = call_record.call_record_link
        else:
            return JsonResponse({'success': False, 'error': 'Noto\'g\'ri call_type'})
        
        if not audio_url:
            return JsonResponse({'success': False, 'error': 'Audio URL topilmadi'})
        
        # API key olish
        uzbekvoice_api_key = request.POST.get('uzbekvoice_api_key')
        if not uzbekvoice_api_key:
            # Default key (settings.py dan)
            uzbekvoice_api_key = settings.UZBEKVOICE_API_KEY
            
            # Debug: API key mavjudligini tekshirish
            print(f"DEBUG: UZBEKVOICE_API_KEY = {uzbekvoice_api_key}")
            
            if not uzbekvoice_api_key:
                return JsonResponse({
                    'success': False,
                    'error': 'UzbekVoice.ai API key topilmadi. Iltimos .env fayliga UZBEKVOICE_API_KEY qo\'shing.'
                })
        
        # Parametrlar
        language = request.POST.get('language', 'uz')
        run_diarization = request.POST.get('run_diarization', 'false') == 'true'
        analyze_with_ai = request.POST.get('analyze_with_ai', 'true') == 'true'
        
        # Processing
        result = process_call_recording(
            audio_url=audio_url,
            uzbekvoice_api_key=uzbekvoice_api_key,
            call_record_object=call_record,
            user=request.user,
            language=language,
            run_diarization=run_diarization,
            analyze_with_ai=analyze_with_ai
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Xatolik: {str(e)}'
        })


@analytics_permission_required
def get_stt_status_ajax(request, stt_record_id):
    """
    AJAX: STT natijasini olish
    """
    try:
        stt_record = get_object_or_404(STTRecord, id=stt_record_id)
        
        data = {
            'success': True,
            'status': stt_record.status,
            'transcribed_text': stt_record.transcribed_text,
            'error_message': stt_record.error_message,
        }
        
        # AI tahlil
        try:
            ai_analysis = stt_record.ai_analysis
            data['ai_analysis'] = {
                'id': ai_analysis.id,
                'status': ai_analysis.status,
                'analysis_text': ai_analysis.analysis_text,
                'overall_score': ai_analysis.overall_score,
                'customer_satisfaction': ai_analysis.get_customer_satisfaction_display(),
                'error_message': ai_analysis.error_message,
            }
        except AIAnalysis.DoesNotExist:
            data['ai_analysis'] = None
        
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@analytics_permission_required
def analyze_existing_stt_ajax(request, stt_record_id):
    """
    AJAX: Mavjud STT natijasini AI bilan tahlil qilish
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Faqat POST metod'})
    
    try:
        stt_record = get_object_or_404(STTRecord, id=stt_record_id)
        
        if stt_record.status != 'completed':
            return JsonResponse({
                'success': False,
                'error': 'STT hali tugallanmagan'
            })
        
        # Oldindan tahlil qilinganligini tekshirish
        existing_analysis = AIAnalysis.objects.filter(
            stt_record=stt_record,
            status='completed'
        ).first()
        
        if existing_analysis:
            return JsonResponse({
                'success': True,
                'ai_analysis_id': existing_analysis.id,
                'analysis_text': existing_analysis.analysis_text,
                'overall_score': existing_analysis.overall_score,
                'customer_satisfaction': existing_analysis.get_customer_satisfaction_display(),
                'message': 'Bu suhbat allaqachon tahlil qilingan. Qayta tahlil qilish shart emas.',
                'already_analyzed': True
            })
        
        # AI tahlil
        result = analyze_text_with_ai(
            stt_record=stt_record,
            analyzed_by=request.user
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ═══════════════════════════════════════════════════════
# ANALYTICS DASHBOARD
# ═══════════════════════════════════════════════════════

@analytics_permission_required
def analytics_dashboard(request):
    """
    Employee Analytics Dashboard
    URL: /analytics/
    """
    from operators_managements.models import OperatorLeader
    
    # User ma'lumotlari
    is_boss_or_director = request.user.role in ['direktor', 'boss']
    is_leader = OperatorLeader.objects.filter(user=request.user).exists()
    
    # Statistika
    total_stt = STTRecord.objects.count()
    completed_stt = STTRecord.objects.filter(status='completed').count()
    total_ai_analysis = AIAnalysis.objects.filter(status='completed').count()
    
    # Oxirgi 30 kunlik
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_stt = STTRecord.objects.filter(created_at__gte=thirty_days_ago)
    recent_ai = AIAnalysis.objects.filter(created_at__gte=thirty_days_ago)
    
    # O'rtacha baho
    avg_score = AIAnalysis.objects.filter(
        status='completed',
        overall_score__isnull=False
    ).aggregate(Avg('overall_score'))['overall_score__avg']
    
    # Mijoz qoniqishi
    satisfaction_stats = AIAnalysis.objects.filter(
        status='completed'
    ).values('customer_satisfaction').annotate(count=Count('id'))
    
    # Tahlil qilingan suhbatlar ro'yxati (oxirgi 50 ta)
    analyzed_calls = AIAnalysis.objects.filter(
        status='completed'
    ).select_related(
        'stt_record',
        'ai_config',
        'analyzed_by'
    ).order_by('-analyzed_at')[:50]
    
    context = {
        'is_boss_or_director': is_boss_or_director,
        'is_leader': is_leader,
        'total_stt': total_stt,
        'completed_stt': completed_stt,
        'total_ai_analysis': total_ai_analysis,
        'recent_stt_count': recent_stt.count(),
        'recent_ai_count': recent_ai.count(),
        'avg_score': round(avg_score, 2) if avg_score else None,
        'satisfaction_stats': list(satisfaction_stats),
        'analyzed_calls': analyzed_calls,
    }
    
    return render(request, 'hackathon/employee_analytics/dashboard.html', context)


@analytics_permission_required
def analyzed_calls_list(request):
    """
    Tahlil qilingan suhbatlar ro'yxati
    URL: /analytics/
    """
    from operators_managements.models import OperatorLeader
    
    # User ma'lumotlari
    is_boss_or_director = request.user.role in ['direktor', 'boss']
    is_leader = OperatorLeader.objects.filter(user=request.user).exists()
    
    # Filterlar
    status_filter = request.GET.get('status', 'completed')
    satisfaction_filter = request.GET.get('satisfaction', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    queryset = AIAnalysis.objects.select_related(
        'stt_record',
        'ai_config',
        'analyzed_by'
    ).order_by('-analyzed_at')
    
    # Statusga qarab filter
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Mijoz qoniqishiga qarab
    if satisfaction_filter:
        queryset = queryset.filter(customer_satisfaction=satisfaction_filter)
    
    # Sana oralig'i
    if date_from:
        queryset = queryset.filter(analyzed_at__gte=date_from)
    if date_to:
        queryset = queryset.filter(analyzed_at__lte=date_to)
    
    # Statistika
    total_analyzed = queryset.filter(status='completed').count()
    avg_score = queryset.filter(
        status='completed',
        overall_score__isnull=False
    ).aggregate(Avg('overall_score'))['overall_score__avg']
    
    # Mijoz qoniqishi statistikasi
    satisfaction_stats = queryset.filter(
        status='completed'
    ).values('customer_satisfaction').annotate(count=Count('id'))
    
    context = {
        'is_boss_or_director': is_boss_or_director,
        'is_leader': is_leader,
        'analyzed_calls': queryset,
        'total_analyzed': total_analyzed,
        'avg_score': round(avg_score, 2) if avg_score else None,
        'satisfaction_stats': list(satisfaction_stats),
        'status_filter': status_filter,
        'satisfaction_filter': satisfaction_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'hackathon/employee_analytics/analyzed_calls_list.html', context)


@analytics_permission_required
def operator_analytics_detail(request, operator_id):
    """
    Operator uchun batafsil analitika
    URL: /analytics/operator/<id>/
    """
    operator = get_object_or_404(CustomUser, id=operator_id, role='operator')
    
    # STT records
    content_type_sipuni = ContentType.objects.get_for_model(SipuniCallRecord)
    content_type_sipcall = ContentType.objects.get_for_model(SIPCall)
    
    # Operator qo'ng'iroqlari
    sipuni_calls = SipuniCallRecord.objects.filter(operator=operator)
    sip_calls = SIPCall.objects.filter(user=operator)  # user field ni tekshiring
    
    # STT records (operator qo'ng'iroqlari uchun)
    stt_records = STTRecord.objects.filter(
        Q(content_type=content_type_sipuni, object_id__in=sipuni_calls.values_list('id', flat=True)) |
        Q(content_type=content_type_sipcall, object_id__in=sip_calls.values_list('id', flat=True))
    ).select_related('ai_analysis')
    
    # Statistika
    total_analyzed = stt_records.filter(status='completed').count()
    
    ai_analyses = AIAnalysis.objects.filter(
        stt_record__in=stt_records,
        status='completed'
    )
    
    avg_score = ai_analyses.aggregate(Avg('overall_score'))['overall_score__avg']
    
    # Davr filteri
    period = request.GET.get('period', '30')  # 7, 30, 90 days
    if period.isdigit():
        days = int(period)
        start_date = timezone.now() - timedelta(days=days)
        stt_records = stt_records.filter(created_at__gte=start_date)
        ai_analyses = ai_analyses.filter(created_at__gte=start_date)
    
    context = {
        'operator': operator,
        'stt_records': stt_records[:50],  # Oxirgi 50 ta
        'total_analyzed': total_analyzed,
        'avg_score': round(avg_score, 2) if avg_score else None,
        'ai_analyses': ai_analyses[:20],  # Oxirgi 20 ta
        'period': period,
    }
    
    return render(request, 'employee_analytics/operator_detail.html', context)


@analytics_permission_required
def stt_detail_view(request, stt_id):
    """
    STT natijasini ko'rish
    URL: /analytics/stt/<id>/
    """
    stt_record = get_object_or_404(STTRecord, id=stt_id)
    
    try:
        ai_analysis = stt_record.ai_analysis
    except AIAnalysis.DoesNotExist:
        ai_analysis = None
    
    context = {
        'stt_record': stt_record,
        'ai_analysis': ai_analysis,
    }
    
    return render(request, 'hackathon/employee_analytics/stt_detail.html', context)


@analytics_permission_required
def ai_config_list(request):
    """
    AI konfiguratsiyalar ro'yxati (faqat boss/direktor uchun)
    """
    if request.user.role not in ['direktor', 'boss']:
        messages.error(request, "Faqat boss va direktor ko'ra oladi")
        return redirect('employee_analytics:dashboard')
    
    configs = AIConfiguration.objects.all()
    
    context = {
        'configs': configs,
    }
    
    return render(request, 'employee_analytics/ai_config_list.html', context)
