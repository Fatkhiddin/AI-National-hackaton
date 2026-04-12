# market_analys/views.py
# CRM API orqali ishlaydigan views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.core.paginator import Paginator
from django.contrib import messages

from .models import OLXProperty, ComparisonResult, MarketPriceReference, PropertyPriceAnalysis
from .crm_api import CRMAPIClient


@login_required
def dashboard(request):
    """Asosiy Market Analysis dashboard"""
    crm_connected = False
    crm_stats = {}
    crm_objects = []
    error_message = None

    try:
        client = CRMAPIClient()
        crm_connected = client.is_connected()

        if crm_connected:
            # CRM dan obyektlar
            data = client.get_objects(page=1, page_size=10, ordering='-created_at')
            if data:
                crm_stats['total_objects'] = data.get('count', 0)
                crm_objects = data.get('results', [])
    except Exception as e:
        error_message = str(e)

    # Lokal statistika
    local_stats = {
        'market_prices': MarketPriceReference.objects.count(),
        'analyses': PropertyPriceAnalysis.objects.count(),
        'olx_properties': OLXProperty.objects.count(),
        'comparisons': ComparisonResult.objects.count(),
        'analyses_by_status': {
            'juda_arzon': PropertyPriceAnalysis.objects.filter(status='juda_arzon').count(),
            'arzon': PropertyPriceAnalysis.objects.filter(status='arzon').count(),
            'normal': PropertyPriceAnalysis.objects.filter(status='normal').count(),
            'qimmat': PropertyPriceAnalysis.objects.filter(status='qimmat').count(),
            'juda_qimmat': PropertyPriceAnalysis.objects.filter(status='juda_qimmat').count(),
        },
    }

    context = {
        'crm_connected': crm_connected,
        'crm_stats': crm_stats,
        'crm_objects': crm_objects,
        'local_stats': local_stats,
        'error_message': error_message,
    }
    return render(request, 'market_analys/dashboard.html', context)


@login_required
def crm_objects_view(request):
    """CRM dan BuildHouse obyektlarini ko'rish (API orqali)"""
    objects = []
    pagination = {}
    error_message = None
    filters = {}

    try:
        client = CRMAPIClient()

        # Filter parametrlarini olish
        filters = {
            'page': request.GET.get('page', 1),
            'page_size': request.GET.get('page_size', 20),
            'search': request.GET.get('search', ''),
            'rooms_numbers': request.GET.get('rooms_numbers', ''),
            'min_price': request.GET.get('min_price', ''),
            'max_price': request.GET.get('max_price', ''),
            'min_area': request.GET.get('min_area', ''),
            'max_area': request.GET.get('max_area', ''),
            'ordering': request.GET.get('ordering', '-created_at'),
            'state_repair': request.GET.get('state_repair', ''),
            'type_building': request.GET.get('type_building', ''),
        }

        # API ga so'rov
        data = client.get_objects(**{k: v for k, v in filters.items() if v})

        if data:
            objects = data.get('results', [])
            pagination = {
                'count': data.get('count', 0),
                'total_pages': data.get('total_pages', 1),
                'current_page': data.get('current_page', 1),
                'has_next': data.get('next') is not None,
                'has_prev': data.get('previous') is not None,
            }

    except Exception as e:
        error_message = str(e)

    context = {
        'objects': objects,
        'pagination': pagination,
        'filters': filters,
        'error_message': error_message,
    }
    return render(request, 'market_analys/crm_objects.html', context)


@login_required
def crm_object_detail(request, object_id):
    """CRM dan bitta BuildHouse obyektini ko'rish"""
    obj = None
    analysis = None
    error_message = None

    try:
        client = CRMAPIClient()
        obj = client.get_object(object_id)

        if not obj:
            error_message = f"Obyekt #{object_id} topilmadi"

        # Bu obyekt uchun mavjud tahlilni qidirish
        analysis = PropertyPriceAnalysis.objects.filter(
            property_id=object_id,
            property_type='buildhouse'
        ).order_by('-analyzed_at').first()

    except Exception as e:
        error_message = str(e)

    context = {
        'obj': obj,
        'analysis': analysis,
        'error_message': error_message,
    }
    return render(request, 'market_analys/crm_object_detail.html', context)


@login_required
def analyze_property_view(request):
    """BuildHouse obyektini AI bilan tahlil qilish"""
    analysis = None
    property_data = None
    error_message = None

    if request.method == 'POST':
        property_id = request.POST.get('property_id', '').strip()

        if property_id and property_id.isdigit():
            property_id = int(property_id)

            try:
                # CRM dan obyektni olish
                client = CRMAPIClient()
                api_obj = client.get_object(property_id)

                if not api_obj:
                    error_message = f"Obyekt #{property_id} CRM da topilmadi"
                else:
                    property_data = client.extract_property_data(api_obj)

                    # Avval mavjud tahlilni qidirish
                    analysis = PropertyPriceAnalysis.objects.filter(
                        property_id=property_id,
                        property_type='buildhouse'
                    ).order_by('-analyzed_at').first()

                    if not analysis:
                        # Yangi tahlil
                        from .services.price_analyzer import PriceAnalyzerAPI
                        analyzer = PriceAnalyzerAPI()
                        analysis = analyzer.analyze_from_api(property_data)

                        if analysis:
                            messages.success(request, f'✅ Obyekt #{property_id} muvaffaqiyatli tahlil qilindi!')
                        else:
                            error_message = "Tahlil amalga oshmadi. Bozor ma'lumotlari yetarli emas."
                    else:
                        messages.info(request, f'📊 Obyekt #{property_id} ning mavjud tahlili ko\'rsatildi')

            except Exception as e:
                error_message = f'Xatolik: {str(e)}'
        else:
            error_message = "To'g'ri obyekt ID kiriting"

    context = {
        'analysis': analysis,
        'property_data': property_data,
        'error_message': error_message,
    }
    return render(request, 'market_analys/analyze_property.html', context)


@login_required
def analysis_results_view(request):
    """Tahlil natijalarini ko'rish"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')

    analyses = PropertyPriceAnalysis.objects.all().select_related('matched_reference').order_by('-analyzed_at')

    if status_filter:
        analyses = analyses.filter(status=status_filter)

    if search_query and search_query.isdigit():
        analyses = analyses.filter(property_id=int(search_query))

    stats = {
        'total': analyses.count(),
        'juda_arzon': analyses.filter(status='juda_arzon').count(),
        'arzon': analyses.filter(status='arzon').count(),
        'normal': analyses.filter(status='normal').count(),
        'qimmat': analyses.filter(status='qimmat').count(),
        'juda_qimmat': analyses.filter(status='juda_qimmat').count(),
    }

    paginator = Paginator(analyses, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'market_analys/analysis_results.html', context)


@login_required
@login_required
def market_prices_view(request):
    """Bozor narxlari — CRM API dan"""
    building_filter = request.GET.get('building', '')
    holat_filter = request.GET.get('holat', '')
    rooms_filter = request.GET.get('rooms', '')
    ordering = request.GET.get('ordering', '')
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', '20')

    error_message = None
    prices_data = None
    stats = {'total': 0, 'gishtli': 0, 'panelli': 0, 'monolitli': 0, 'blokli': 0}

    try:
        client = CRMAPIClient()

        # API ga so'rov
        params = {
            'page': page,
            'page_size': page_size,
        }
        if building_filter:
            params['qurilish_turi'] = building_filter
        if holat_filter:
            params['holat'] = holat_filter
        if rooms_filter and rooms_filter.isdigit():
            params['xonalar_soni'] = int(rooms_filter)
        if ordering:
            params['ordering'] = ordering
        else:
            params['ordering'] = 'etaj'

        prices_data = client.get_market_prices(**params)

        if prices_data:
            stats['total'] = prices_data.get('count', 0)

            # Qurilish turi bo'yicha stats (alohida so'rovlar)
            for qt in ['gishtli', 'panelli', 'monolitli', 'blokli']:
                qt_params = {'page': 1, 'page_size': 1, 'qurilish_turi': qt}
                if holat_filter:
                    qt_params['holat'] = holat_filter
                if rooms_filter and rooms_filter.isdigit():
                    qt_params['xonalar_soni'] = int(rooms_filter)
                qt_data = client.get_market_prices(**qt_params)
                if qt_data:
                    stats[qt] = qt_data.get('count', 0)

    except Exception as e:
        error_message = str(e)

    context = {
        'prices_data': prices_data,
        'results': prices_data.get('results', []) if prices_data else [],
        'total_pages': prices_data.get('total_pages', 1) if prices_data else 1,
        'current_page': int(prices_data.get('current_page', 1)) if prices_data else 1,
        'has_next': prices_data.get('next') is not None if prices_data else False,
        'has_previous': prices_data.get('previous') is not None if prices_data else False,
        'stats': stats,
        'building_filter': building_filter,
        'holat_filter': holat_filter,
        'rooms_filter': rooms_filter,
        'ordering': ordering,
        'error_message': error_message,
    }
    return render(request, 'market_analys/market_prices.html', context)


@login_required
def sync_market_prices(request):
    """CRM dan bozor narxlarini lokal DB ga sync qilish (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Faqat POST'}, status=405)

    try:
        client = CRMAPIClient()
        created, updated, errors = client.sync_market_prices_to_db()
        return JsonResponse({
            'success': True,
            'created': created,
            'updated': updated,
            'errors': errors,
            'message': f"Sync tugadi: +{created} yangi, ↻{updated} yangilangan, ❌{errors} xato"
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ==========================================
# AJAX Endpoints
# ==========================================

@login_required
def sync_crm_objects(request):
    """CRM dan obyektlarni sync qilish (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Faqat POST'}, status=405)

    try:
        client = CRMAPIClient()
        data = client.get_objects(page=1, page_size=1)

        if data:
            return JsonResponse({
                'success': True,
                'total_objects': data.get('count', 0),
                'message': f"CRM da {data.get('count', 0)} ta obyekt mavjud"
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'CRM dan ma\'lumot olib bo\'lmadi'
            })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def api_analyze_object(request):
    """AJAX: Obyektni tahlil qilish"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Faqat POST'}, status=405)

    import json
    body = json.loads(request.body)
    property_id = body.get('property_id')

    if not property_id:
        return JsonResponse({'error': 'property_id kerak'}, status=400)

    try:
        client = CRMAPIClient()
        api_obj = client.get_object(property_id)

        if not api_obj:
            return JsonResponse({'error': f'Obyekt #{property_id} topilmadi'}, status=404)

        property_data = client.extract_property_data(api_obj)

        from .services.price_analyzer import PriceAnalyzerAPI
        analyzer = PriceAnalyzerAPI()
        analysis = analyzer.analyze_from_api(property_data)

        if analysis:
            return JsonResponse({
                'success': True,
                'analysis': {
                    'id': analysis.id,
                    'status': analysis.get_status_display(),
                    'status_code': analysis.status,
                    'bozor_narxi': float(analysis.bozor_narxi),
                    'joriy_narxi': float(analysis.joriy_narxi),
                    'farq_foiz': float(analysis.farq_foiz),
                    'farq_summa': float(analysis.farq_summa),
                    'ai_tahlil': analysis.ai_tahlil,
                    'tavsiya': analysis.tavsiya,
                    'confidence_score': float(analysis.confidence_score),
                }
            })
        else:
            return JsonResponse({'error': 'Tahlil amalga oshmadi'}, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
