from django.urls import path
from . import views
from .mass_messaging_views import (
    mass_messaging_view, get_contacts_for_accounts, 
    start_campaign, campaign_status, stop_campaign
)

urlpatterns = [
    # Authentication URLs
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/register/', views.register_view, name='register'),
    
    # Main URLs
    path('', views.dashboard, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('accounts/', views.telegram_accounts, name='telegram_accounts'),
    path('accounts/add/', views.add_telegram_account, name='add_telegram_account'),
    path('accounts/verify/', views.verify_telegram_account, name='verify_telegram_account'),
    path('accounts/check-status/<int:account_id>/', views.check_account_status, name='check_account_status'),
    path('accounts/settings/<int:account_id>/', views.telegram_account_settings, name='telegram_account_settings'),
    path('accounts/delete-contacts/<int:account_id>/', views.delete_all_contacts, name='delete_all_contacts'),
    path('accounts/delete-chats/<int:account_id>/', views.delete_all_chats, name='delete_all_chats'),
    path('accounts/update-profile/<int:account_id>/', views.update_telegram_profile, name='update_telegram_profile'),
    path('accounts/delete/<int:account_id>/', views.delete_telegram_account, name='delete_telegram_account'),
    path('contacts/', views.contacts_list, name='contacts_list'),
    path('contacts/import/', views.import_contacts, name='import_contacts'),
    path('contacts/sync/<int:account_id>/', views.sync_telegram_contacts, name='sync_telegram_contacts'),
    path('contacts/add-to-telegram/<int:account_id>/', views.add_contacts_to_telegram, name='add_contacts_to_telegram'),
    path('contacts/fix-phones/<int:account_id>/', views.fix_phone_numbers, name='fix_phone_numbers'),
    path('contacts/reset-status/<int:account_id>/', views.reset_contacts_status, name='reset_contacts_status'),
    path('contacts/export/', views.export_contacts, name='export_contacts'),
    path('chats/', views.chats_list, name='chats_list'),
    path('chats/new/', views.chats_list_new, name='chats_list_new'),
    path('chats/<int:account_id>/<int:chat_id>/', views.chats_detail, name='chats_detail'),
    path('chats/<int:account_id>/<int:chat_id>/messages/', views.chat_messages, name='chat_messages'),
    path('chats/<int:account_id>/<int:chat_id>/send/', views.send_message_to_chat, name='send_message_to_chat'),
    path('telegram/', views.telegram_web_client, name='telegram_web_client'),
    path('api/messages/<int:account_id>/<int:chat_id>/', views.get_chat_messages_api, name='get_chat_messages_api'),
    path('api/chat/<int:account_id>/<int:chat_id>/', views.get_chat_info_api, name='get_chat_info_api'),
    path('ai/', views.ai_integration, name='ai_integration'),
    path('ai/provider/<str:provider>/', views.ai_provider_setup, name='ai_provider_setup'),
    path('ai/provider/<str:provider>/test/', views.test_ai_provider, name='test_ai_provider'),
    path('ai/chat/<int:account_id>/', views.ai_chat_interface, name='ai_chat_interface'),
    path('ai/test/<int:account_id>/', views.test_ai_integration, name='test_ai_integration'),
    path('ai/send/<int:account_id>/<int:chat_id>/', views.send_ai_message_to_chat, name='send_ai_message_to_chat'),
    path('chats/<int:account_id>/<int:chat_id>/ai-send/', views.send_ai_message, name='send_ai_message'),
    
    # Real-time monitoring
    path('api/check-new-messages/<int:account_id>/', views.check_new_messages, name='check_new_messages'),
    path('api/unread-count/', views.get_unread_count, name='get_unread_count'),
    path('api/get-chats/<int:account_id>/', views.get_chats_api, name='get_chats_api'),
    
    # Mass Messaging
    path('mass-messaging/', mass_messaging_view, name='mass_messaging'),
    path('api/get-contacts-for-accounts/', get_contacts_for_accounts, name='get_contacts_for_accounts'),
    path('api/start-campaign/', start_campaign, name='start_campaign'),
    path('api/campaign-status/<int:campaign_id>/', campaign_status, name='campaign_status'),
    path('api/stop-campaign/<int:campaign_id>/', stop_campaign, name='stop_campaign'),
    
    # Auto-Reply
    path('auto-reply/<int:account_id>/', views.list_auto_reply_rules, name='list_auto_reply_rules'),
    path('auto-reply/<int:account_id>/create/', views.create_auto_reply_rule, name='create_auto_reply_rule'),
    path('auto-reply/update/<int:rule_id>/', views.update_auto_reply_rule, name='update_auto_reply_rule'),
    path('auto-reply/delete/<int:rule_id>/', views.delete_auto_reply_rule, name='delete_auto_reply_rule'),
    path('auto-reply/toggle/<int:rule_id>/', views.toggle_auto_reply_rule, name='toggle_auto_reply_rule'),
    path('monitoring/start/', views.start_monitoring_view, name='start_monitoring'),
    path('monitoring/status/', views.monitoring_status, name='monitoring_status'),
    
    # AI Assistant
    path('ai-dashboard/', views.ai_dashboard, name='ai_dashboard'),
    path('ai/providers/', views.ai_provider_manage, name='ai_provider_list'),
    path('ai/providers/create/', views.ai_provider_manage, name='ai_provider_create'),
    path('ai/providers/<int:provider_id>/', views.ai_provider_manage, name='ai_provider_detail'),
    path('ai/providers/<int:provider_id>/delete/', views.ai_provider_delete, name='ai_provider_delete'),
    path('ai/assistants/', views.ai_assistant_manage, name='ai_assistant_list'),
    path('ai/assistants/create/', views.ai_assistant_manage, name='ai_assistant_create'),
    path('ai/assistants/<int:assistant_id>/', views.ai_assistant_manage, name='ai_assistant_detail'),
    path('ai/assistants/<int:assistant_id>/delete/', views.ai_assistant_delete, name='ai_assistant_delete'),
    path('ai/assistants/<int:assistant_id>/toggle/', views.ai_assistant_toggle, name='ai_assistant_toggle'),
    path('ai/summaries/<int:account_id>/', views.ai_conversation_summaries, name='ai_conversation_summaries'),
    
    # CRM Integration
    path('crm/', views.crm_integration_dashboard, name='crm_dashboard'),
    path('crm/providers/', views.crm_provider_manage, name='crm_provider_list'),
    path('crm/providers/create/', views.crm_provider_manage, name='crm_provider_create'),
    path('crm/providers/<int:provider_id>/', views.crm_provider_manage, name='crm_provider_detail'),
    path('crm/providers/<int:provider_id>/delete/', views.crm_provider_delete, name='crm_provider_delete'),
    path('crm/providers/<int:provider_id>/test/', views.crm_test_connection, name='crm_test_connection'),
    path('crm/search/', views.crm_search_properties, name='crm_search_properties'),
    
    # Property Interests (Takliflar)
    path('property-interests/', views.property_interests_dashboard, name='property_interests'),
    path('property-interests/<int:interest_id>/', views.property_interest_detail, name='property_interest_detail'),
]