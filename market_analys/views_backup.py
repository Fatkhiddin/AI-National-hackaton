# market_analysis/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.core.paginator import Paginator
from django.contrib import messages
from .models import OLXProperty, ComparisonResult, MarketPriceReference, PropertyPriceAnalysis
from .tasks import process_olx_comparisons, compare_single_olx
from home.models import BuildHouse
from .services.price_analyzer import PriceAnalyzer
import json


@login_required
def analyze_property_view(request):
    """
    BuildHouse obyektini ID bo'yicha AI bilan tahlil qilish.
    Alohida sahifa - ID kiritish formasi bilan.
    
    YANGILANGAN: Avval eski tahlilni qidiradi, topilmasa yangisini yaratadi.
    """
    analysis = None
    property_obj = None
    error_message = None
    
    if request.method == 'POST':
        property_id = request.POST.get('property_id', '').strip()
        force_new = request.POST.get('force_new', False)  # Yangi tahlil majburlash
        
        if property_id and property_id.isdigit():
            try:
                property_id = int(property_id)
                
                # BuildHouse obyektini topish
                property_obj = BuildHouse.objects.get(
                    id=property_id,
                    team=request.team
                )
                
                # 1. AVVAL ESKI TAHLILNI QIDIRISH
                from django.contrib.contenttypes.models import ContentType
                content_type = ContentType.objects.get_for_model(BuildHouse)
                
                if not force_new:
                    try:
                        analysis = PropertyPriceAnalysis.objects.filter(
                            team=request.team,
                            content_type=content_type,
                            object_id=property_id
                        ).order_by('-created_at').first()
                        
                        if analysis:
                            print(f"✅ Eski tahlil topildi: ID {analysis.id}, Sana: {analysis.created_at}")
                            messages.info(request, f'📊 Obyekt #{property_id} ning oxirgi tahlili ko\'rsatildi ({analysis.created_at.strftime("%d.%m.%Y %H:%M")})')
                    except Exception as e:
                        print(f"⚠️ Eski tahlil qidirishda xatolik: {str(e)}")
                        analysis = None
                
                # 2. ESKI TAHLIL YO'Q BO'LSA - YANGI TAHLIL
                if not analysis:
                    print(f"🔄 Yangi tahlil boshlanmoqda - Property ID: {property_id}")
                    analyzer = PriceAnalyzer()
                    analysis = analyzer.analyze_property(property_obj, use_ai=True)
                    
                    if analysis:
                        messages.success(request, f'✅ Obyekt #{property_id} muvaffaqiyatli tahlil qilindi!')
                    else:
                        error_message = 'Tahlil amalga oshmadi. Ma\'lumotlar to\'liq emasligini tekshiring.'
                        messages.error(request, f'❌ {error_message}')
                    
            except BuildHouse.DoesNotExist:
                error_message = f'Obyekt #{property_id} topilmadi yoki sizning teamingizga tegishli emas.'
                messages.error(request, f'❌ {error_message}')
            except Exception as e:
                error_message = f'Xatolik: {str(e)}'
                messages.error(request, f'❌ {error_message}')
        else:
            error_message = 'Iltimos, to\'g\'ri obyekt ID sini kiriting.'
            messages.error(request, f'❌ {error_message}')
    
    context = {
        'analysis': analysis,
        'property_obj': property_obj,
        'error_message': error_message,
    }
    
    return render(request, 'market_analysis/analyze_property.html', context)


@login_required
def analysis_results_view(request):
    """
    Tahlil natijalarini chiroyli ko'rsatish - Frontend sahifa.
    Admin panel o'rniga ishlatiladi.
    """
    # Filter parametrlari
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Barcha tahlillar
    analyses = PropertyPriceAnalysis.objects.filter(
        team=request.team
    ).select_related(
        'content_type',
        'matched_reference'
    ).order_by('-created_at')
    
    # Status filter
    if status_filter:
        analyses = analyses.filter(status=status_filter)
    
    # Search filter (property_id bo'yicha)
    if search_query and search_query.isdigit():
        analyses = analyses.filter(property_id=int(search_query))
    
    # Statistika
    stats = {
        'total': analyses.count(),
        'juda_arzon': analyses.filter(status='juda_arzon').count(),
        'arzon': analyses.filter(status='arzon').count(),
        'normal': analyses.filter(status='normal').count(),
        'qimmat': analyses.filter(status='qimmat').count(),
        'juda_qimmat': analyses.filter(status='juda_qimmat').count(),
    }
    
    # Pagination
    paginator = Paginator(analyses, 20)  # 20 ta per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'market_analysis/analysis_results.html', context)


@login_required
def market_prices_view(request):
    """
    Bozor narxlari ro'yxati - Chiroyli frontend sahifa.
    Admin panel o'rniga ishlatiladi.
    """
    # Filter parametrlari
    building_filter = request.GET.get('building', '')
    holat_filter = request.GET.get('holat', '')
    rooms_filter = request.GET.get('rooms', '')
    search_query = request.GET.get('search', '')
    
    # Barcha bozor narxlari
    prices = MarketPriceReference.objects.filter(
        team=request.team
    ).order_by('-updated_at')
    
    # Building type filter
    if building_filter:
        prices = prices.filter(qurilish_turi=building_filter)
    
    # Holat filter
    if holat_filter:
        prices = prices.filter(holat=holat_filter)
    
    # Rooms filter
    if rooms_filter and rooms_filter.isdigit():
        prices = prices.filter(xonalar_soni=int(rooms_filter))
    
    # Search filter (etaj yoki maydon)
    if search_query and search_query.isdigit():
        search_num = int(search_query)
        prices = prices.filter(
            Q(etaj=search_num) | 
            Q(maydon_min__lte=search_num, maydon_max__gte=search_num)
        )
    
    # Statistika
    stats = {
        'total': MarketPriceReference.objects.filter(team=request.team).count(),
        'gishtli': prices.filter(qurilish_turi='gishtli').count(),
        'panelli': prices.filter(qurilish_turi='panelli').count(),
        'monolitli': prices.filter(qurilish_turi='monolitli').count(),
        'blokli': prices.filter(qurilish_turi='blokli').count(),
        'remontli': prices.filter(holat='remontli').count(),
        'remontsiz': prices.filter(holat='remontsiz').count(),
    }
    
    # Get unique values for filters
    building_types = MarketPriceReference.objects.filter(
        team=request.team
    ).values_list('qurilish_turi', flat=True).distinct()
    
    rooms_options = MarketPriceReference.objects.filter(
        team=request.team
    ).values_list('xonalar_soni', flat=True).distinct().order_by('xonalar_soni')
    
    # Pagination
    paginator = Paginator(prices, 20)  # 20 ta per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'building_filter': building_filter,
        'holat_filter': holat_filter,
        'rooms_filter': rooms_filter,
        'search_query': search_query,
        'building_types': building_types,
        'rooms_options': rooms_options,
    }
    
    return render(request, 'market_analysis/market_prices.html', context)


@login_required
def invest_panel(request):
    """
    INVEST PANEL - Boss uchun asosiy dashboard
    Barcha market analysis funksiyalari
    """
    # Faqat boss ko'ra oladi
    if request.user.role != 'boss':
        messages.error(request, "❌ Bu panel faqat Boss uchun!")
        return redirect('home:home')
    
    # ============================================
    # STATISTIKA - UMUMIY
    # ============================================
    
    # Market Price Reference
    market_prices_count = MarketPriceReference.objects.filter(team=request.team).count()
    
    # Qurilish turi bo'yicha
    market_by_building = MarketPriceReference.objects.filter(
        team=request.team
    ).values('qurilish_turi').annotate(count=Count('id'))
    
    # Holat bo'yicha
    market_by_holat = MarketPriceReference.objects.filter(
        team=request.team
    ).values('holat').annotate(count=Count('id'))
    
    # Property Price Analysis
    analyses_count = PropertyPriceAnalysis.objects.filter(team=request.team).count()
    
    # Status bo'yicha
    analyses_by_status = PropertyPriceAnalysis.objects.filter(
        team=request.team
    ).values('status').annotate(count=Count('id'))
    
    # BuildHouse tahlillari
    crm_analyses_count = PropertyPriceAnalysis.objects.filter(
        team=request.team,
        content_type__model='buildhouse'
    ).count()
    
    # OLX tahlillari
    olx_analyses_count = PropertyPriceAnalysis.objects.filter(
        team=request.team,
        content_type__model='olxproperty'
    ).count()
    
    # O'rtacha confidence
    avg_confidence = PropertyPriceAnalysis.objects.filter(
        team=request.team
    ).aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0
    
    # ============================================
    # TOP ARZON TAKLIFLAR
    # ============================================
    
    # CRM dan eng arzon
    cheap_crm = PropertyPriceAnalysis.objects.filter(
        team=request.team,
        content_type__model='buildhouse',
        status__in=['juda_arzon', 'arzon']
    ).select_related('matched_reference').order_by('farq_foiz')[:10]
    
    # OLX dan eng arzon
    cheap_olx = PropertyPriceAnalysis.objects.filter(
        team=request.team,
        content_type__model='olxproperty',
        status__in=['juda_arzon', 'arzon']
    ).select_related('matched_reference').order_by('farq_foiz')[:10]
    
    # ============================================
    # OXIRGI TAHLILLAR
    # ============================================
    
    recent_analyses = PropertyPriceAnalysis.objects.filter(
        team=request.team
    ).select_related(
        'matched_reference', 'content_type'
    ).order_by('-analyzed_at')[:20]
    
    # ============================================
    # OLX STATISTIKA
    # ============================================
    
    olx_stats = {
        'total_olx': OLXProperty.objects.filter(team=request.team).count(),
        'new_olx': OLXProperty.objects.filter(team=request.team, is_processed=False).count(),
        'total_comparisons': ComparisonResult.objects.filter(olx_property__team=request.team).count(),
        'cheaper_count': ComparisonResult.objects.filter(
            olx_property__team=request.team, 
            status='cheaper'
        ).count(),
    }
    
    # ============================================
    # CONTEXT
    # ============================================
    
    context = {
        # Umumiy statistika
        'market_prices_count': market_prices_count,
        'analyses_count': analyses_count,
        'crm_analyses_count': crm_analyses_count,
        'olx_analyses_count': olx_analyses_count,
        'avg_confidence': avg_confidence,
        
        # Bo'limlar
        'market_by_building': market_by_building,
        'market_by_holat': market_by_holat,
        'analyses_by_status': analyses_by_status,
        
        # Top takliflar
        'cheap_crm': cheap_crm,
        'cheap_olx': cheap_olx,
        
        # Oxirgi tahlillar
        'recent_analyses': recent_analyses,
        
        # OLX
        'olx_stats': olx_stats,
        
        # Rang mapping
        'status_colors': {
            'juda_arzon': '#00C853',
            'arzon': '#64DD17',
            'normal': '#FFC107',
            'qimmat': '#FF6F00',
            'juda_qimmat': '#D32F2F',
        },
        'building_colors': {
            'gishtli': '#F44336',
            'panelli': '#2196F3',
            'monolitli': '#4CAF50',
            'blokli': '#FF9800',
        }
    }
    
    return render(request, 'market_analysis/invest_panel.html', context)


@login_required
def dashboard(request):
    """
    Asosiy dashboard - statistika
    """
    # Faqat direktor va boss ko'ra oladi
    if request.user.role not in ['direktor', 'boss']:
        return render(request, '403.html', status=403)
    
    # Statistika
    stats = {
        'total_olx': OLXProperty.objects.filter(team=request.team).count(),
        'new_olx': OLXProperty.objects.filter(team=request.team, is_processed=False).count(),
        'total_comparisons': ComparisonResult.objects.filter(olx_property__team=request.team).count(),
        'cheaper_count': ComparisonResult.objects.filter(
            olx_property__team=request.team, 
            status='cheaper'
        ).count(),
        'avg_similarity': ComparisonResult.objects.filter(
            olx_property__team=request.team
        ).aggregate(Avg('similarity_score'))['similarity_score__avg'] or 0,
    }
    
    # TOP arzon takliflar (oxirgi 10ta)
    cheap_offers = ComparisonResult.objects.filter(
        olx_property__team=request.team,
        status='cheaper',
        is_notified=False
    ).select_related(
        'olx_property', 'crm_object', 'crm_object__user'
    ).order_by('-priority_score')[:10]
    
    # Oxirgi OLX obyektlar
    recent_olx = OLXProperty.objects.filter(
        team=request.team
    ).order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'cheap_offers': cheap_offers,
        'recent_olx': recent_olx,
    }
    
    return render(request, 'market_analysis/dashboard.html', context)


@login_required
def olx_property_list(request):
    """OLX obyektlar ro'yxati"""
    if request.user.role not in ['direktor', 'boss', 'operator']:
        return render(request, '403.html', status=403)
    
    # Filterlar
    queryset = OLXProperty.objects.filter(team=request.team).order_by('-created_at')
    
    # Qidiruv
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(address_text__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # Filter - processed
    is_processed = request.GET.get('processed', '')
    if is_processed == 'yes':
        queryset = queryset.filter(is_processed=True)
    elif is_processed == 'no':
        queryset = queryset.filter(is_processed=False)
    
    # Filter - xonalar
    rooms = request.GET.get('rooms', '')
    if rooms:
        queryset = queryset.filter(rooms=rooms)
    
    # Pagination
    paginator = Paginator(queryset, 20)  # 20ta/sahifa
    page = request.GET.get('page', 1)
    olx_properties = paginator.get_page(page)
    
    context = {
        'olx_properties': olx_properties,
        'search': search,
        'is_processed': is_processed,
        'rooms': rooms,
    }
    
    return render(request, 'market_analysis/olx_list.html', context)


@login_required
def comparison_list(request):
    """Taqqoslash natijalari"""
    if request.user.role not in ['direktor', 'boss', 'operator']:
        return render(request, '403.html', status=403)
    
    # Filterlar
    queryset = ComparisonResult.objects.filter(
        olx_property__team=request.team
    ).select_related(
        'olx_property', 'crm_object', 'crm_object__user'
    ).order_by('-priority_score', '-created_at')
    
    # Filter - status
    status = request.GET.get('status', '')
    if status:
        queryset = queryset.filter(status=status)
    
    # Filter - similarity
    min_similarity = request.GET.get('min_similarity', '')
    if min_similarity:
        queryset = queryset.filter(similarity_score__gte=min_similarity)
    
    # Filter - notified
    notified = request.GET.get('notified', '')
    if notified == 'yes':
        queryset = queryset.filter(is_notified=True)
    elif notified == 'no':
        queryset = queryset.filter(is_notified=False)
    
    # Pagination
    paginator = Paginator(queryset, 20)
    page = request.GET.get('page', 1)
    comparisons = paginator.get_page(page)
    
    context = {
        'comparisons': comparisons,
        'status': status,
        'min_similarity': min_similarity,
        'notified': notified,
    }
    
    return render(request, 'market_analysis/comparison_list.html', context)


@login_required
def comparison_detail(request, pk):
    """Taqqoslash batafsil"""
    if request.user.role not in ['direktor', 'boss', 'operator', 'agent']:
        return render(request, '403.html', status=403)
    
    comparison = get_object_or_404(
        ComparisonResult.objects.select_related(
            'olx_property', 'crm_object', 'crm_object__user', 'crm_object__address'
        ),
        pk=pk,
        olx_property__team=request.team
    )
    
    context = {
        'comparison': comparison,
    }
    
    return render(request, 'market_analysis/comparison_detail.html', context)


@login_required
def trigger_comparison(request):
    """Taqqoslashni ishga tushirish (AJAX)"""
    if request.user.role not in ['direktor', 'boss']:
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)
    
    if request.method == 'POST':
        # Barcha yangi obyektlarni taqqoslash
        task = process_olx_comparisons.delay()
        
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'message': 'Taqqoslash boshlandi'
        })
    
    return JsonResponse({'error': 'Faqat POST'}, status=405)


@login_required
def recompare_olx(request, pk):
    """Bitta OLX ni qayta taqqoslash (AJAX)"""
    if request.user.role not in ['direktor', 'boss', 'operator']:
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)
    
    if request.method == 'POST':
        olx = get_object_or_404(OLXProperty, pk=pk, team=request.team)
        
        # Qayta taqqoslash
        task = compare_single_olx.delay(olx.id)
        
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'message': f'{olx.title} qayta taqqoslanmoqda'
        })
    
    return JsonResponse({'error': 'Faqat POST'}, status=405)


@login_required
def mark_notified(request, pk):
    """Notification deb belgilash (AJAX)"""
    if request.user.role not in ['direktor', 'boss', 'operator']:
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)
    
    if request.method == 'POST':
        comparison = get_object_or_404(
            ComparisonResult, 
            pk=pk, 
            olx_property__team=request.team
        )
        
        comparison.mark_as_notified()
        
        return JsonResponse({
            'success': True,
            'message': 'Belgilandi'
        })
    
    return JsonResponse({'error': 'Faqat POST'}, status=405)


@login_required
def olx_import_view(request):
    """OLX dan import qilish sahifasi"""
    if request.user.role not in ['direktor', 'boss', 'operator']:
        messages.error(request, '❌ Sizda bu funksiyaga ruxsat yo\'q!')
        return redirect('home:home')
    
    if request.method == 'POST':
        try:
            # OLX scraper importini lazy load qilish
            from .olx_scraper import run_olx_scraping
            
            max_pages = int(request.POST.get('max_pages', 1))
            
            # Limit
            if max_pages < 1 or max_pages > 10:
                return JsonResponse({
                    'success': False,
                    'error': 'Sahifalar soni 1 dan 10 gacha bo\'lishi kerak'
                })
            
            # Import boshlash
            result = run_olx_scraping(
                city='buhara',
                max_pages=max_pages,
                team=request.team
            )
            
            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(result)
            
            # Browser response
            if result.get('success'):
                messages.success(
                    request,
                    f'✅ Import tugadi! Yangi: {result["saved"]}, Yangilandi: {result["updated"]}'
                )
            else:
                messages.error(request, f'❌ Xatolik: {result.get("error", "Noma\'lum xatolik")}')
            
            return redirect('market_analys:olx_import')
            
        except Exception as e:
            error_msg = f'Xatolik: {str(e)}'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            
            messages.error(request, f'❌ {error_msg}')
            return redirect('market_analys:olx_import')
    
    # GET request - forma ko'rsatish
    return render(request, 'market_analysis/olx_import.html')
    
    return JsonResponse({'error': 'Faqat POST'}, status=405)