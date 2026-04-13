# employee_analytics/urls.py

from django.urls import path
from . import views

app_name = 'employee_analytics'

urlpatterns = [
    # AI Analitika - tahlil qilingan suhbatlar
    path('', views.analyzed_calls_list, name='analyzed_calls_list'),
    
    # AJAX endpoints
    path('ajax/convert/<str:call_type>/<int:call_id>/', views.convert_to_text_ajax, name='convert_to_text_ajax'),
    path('ajax/stt-status/<int:stt_record_id>/', views.get_stt_status_ajax, name='get_stt_status_ajax'),
    path('ajax/analyze-stt/<int:stt_record_id>/', views.analyze_existing_stt_ajax, name='analyze_existing_stt_ajax'),
    
    # Detail views
    path('operator/<int:operator_id>/', views.operator_analytics_detail, name='operator_detail'),
    path('stt/<int:stt_id>/', views.stt_detail_view, name='stt_detail'),
    
    # AI Config (admin only)
    path('ai-config/', views.ai_config_list, name='ai_config_list'),
]
