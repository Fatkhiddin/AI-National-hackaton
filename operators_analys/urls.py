from django.urls import path
from . import views

app_name = 'operators_analys'

urlpatterns = [
    path('ip-calls/', views.ip_calls_view, name='ip_calls'),
    path('api/ip-calls/', views.ip_calls_api, name='ip_calls_api'),
    path('api/sync-sip-calls/', views.sync_sip_calls_view, name='sync_sip_calls'),
    path('api/sip-stats/', views.sip_calls_stats_view, name='sip_stats'),
    
    # STT + AI Tahlil
    path('api/process-recording/', views.process_recording_view, name='process_recording'),
    path('api/stt-status/<int:stt_record_id>/', views.stt_status_view, name='stt_status'),
    path('api/analyze-stt/<int:stt_record_id>/', views.analyze_existing_stt_view, name='analyze_stt'),
]
