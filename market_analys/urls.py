# market_analys/urls.py

from django.urls import path
from . import views

app_name = 'market_analys'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # CRM Obyektlar (API orqali)
    path('objects/', views.crm_objects_view, name='crm_objects'),
    path('objects/<int:object_id>/', views.crm_object_detail, name='crm_object_detail'),

    # Tahlil
    path('analyze/', views.analyze_property_view, name='analyze_property'),
    path('results/', views.analysis_results_view, name='analysis_results'),

    # Bozor narxlari
    path('market-prices/', views.market_prices_view, name='market_prices'),

    # AJAX endpoints
    path('api/sync/', views.sync_crm_objects, name='sync_crm'),
    path('api/analyze/', views.api_analyze_object, name='api_analyze'),
]
