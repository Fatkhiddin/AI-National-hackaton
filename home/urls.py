from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('crm-settings/', views.crm_settings_view, name='crm_settings'),
    path('api/crm-test-connection/', views.crm_test_connection_view, name='crm_test_connection'),
    path('api/crm-status/', views.crm_status_view, name='crm_status'),
]
