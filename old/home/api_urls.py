from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

from .api_views import (
    TelegramAccountViewSet, ContactViewSet, ChatViewSet,
    MessageViewSet, AutoReplyRuleViewSet, AutoReplyLogViewSet,
    AIProviderViewSet, AIAssistantViewSet, ConversationSummaryViewSet,
    CRMProviderViewSet, PropertySearchLogViewSet, PropertyInterestViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'telegram-accounts', TelegramAccountViewSet, basename='telegramaccount')
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'chats', ChatViewSet, basename='chat')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'auto-reply-rules', AutoReplyRuleViewSet, basename='autoreplyrule')
router.register(r'auto-reply-logs', AutoReplyLogViewSet, basename='autoreplylog')
router.register(r'ai-providers', AIProviderViewSet, basename='aiprovider')
router.register(r'ai-assistants', AIAssistantViewSet, basename='aiassistant')
router.register(r'conversation-summaries', ConversationSummaryViewSet, basename='conversationsummary')
router.register(r'crm-providers', CRMProviderViewSet, basename='crmprovider')
router.register(r'property-search-logs', PropertySearchLogViewSet, basename='propertysearchlog')
router.register(r'property-interests', PropertyInterestViewSet, basename='propertyinterest')

urlpatterns = [
    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API endpoints
    path('', include(router.urls)),
]
