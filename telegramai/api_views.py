from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q

from .models import (
    TelegramAccount, Contact, Chat, Message,
    AutoReplyRule, AutoReplyLog, AIProvider,
    AIAssistant, ConversationSummary, CRMProvider,
    PropertySearchLog, PropertyInterest
)
from .serializers import (
    TelegramAccountSerializer, ContactSerializer,
    ChatSerializer, MessageSerializer,
    AutoReplyRuleSerializer, AutoReplyLogSerializer,
    AIProviderSerializer, AIAssistantSerializer,
    ConversationSummarySerializer, CRMProviderSerializer,
    PropertySearchLogSerializer, PropertyInterestSerializer
)


class TelegramAccountViewSet(viewsets.ModelViewSet):
    serializer_class = TelegramAccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['phone_number', 'session_name']
    ordering_fields = ['created_at', 'phone_number']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return TelegramAccount.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        account = self.get_object()
        account.is_active = True
        account.save()
        return Response({'status': 'account activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        account = self.get_object()
        account.is_active = False
        account.save()
        return Response({'status': 'account deactivated'})


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_premium', 'is_bot', 'telegram_exists', 'added_to_telegram']
    search_fields = ['name', 'phone_number', 'username', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Contact.objects.filter(
            telegram_account__user=self.request.user
        )
    
    @action(detail=False, methods=['get'])
    def premium_users(self, request):
        contacts = self.get_queryset().filter(is_premium=True)
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def telegram_users(self, request):
        contacts = self.get_queryset().filter(telegram_exists=True)
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)


class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['chat_type', 'is_verified', 'is_restricted']
    search_fields = ['title', 'username']
    ordering_fields = ['created_at', 'title', 'member_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Chat.objects.filter(
            telegram_account__user=self.request.user
        ).annotate(
            message_count=Count('messages')
        )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        chat = self.get_object()
        messages = Message.objects.filter(chat=chat).order_by('-created_at')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def private(self, request):
        chats = self.get_queryset().filter(chat_type='private')
        serializer = self.get_serializer(chats, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def groups(self, request):
        chats = self.get_queryset().filter(
            Q(chat_type='group') | Q(chat_type='supergroup')
        )
        serializer = self.get_serializer(chats, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['message_type', 'is_outgoing']
    search_fields = ['text']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']
    
    def get_queryset(self):
        return Message.objects.filter(
            telegram_account__user=self.request.user
        )
    
    @action(detail=False, methods=['get'])
    def outgoing(self, request):
        messages = self.get_queryset().filter(is_outgoing=True)
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


class AutoReplyRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AutoReplyRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'keywords']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return AutoReplyRule.objects.filter(
            telegram_account__user=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save()
        return Response({'status': 'toggled', 'is_active': rule.is_active})


class AutoReplyLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AutoReplyLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        return AutoReplyLog.objects.filter(
            rule__telegram_account__user=self.request.user
        )


class AIProviderViewSet(viewsets.ModelViewSet):
    serializer_class = AIProviderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'provider_type']
    
    def get_queryset(self):
        return AIProvider.objects.filter(user=self.request.user)


class AIAssistantViewSet(viewsets.ModelViewSet):
    serializer_class = AIAssistantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    def get_queryset(self):
        return AIAssistant.objects.filter(
            telegram_account__user=self.request.user
        )


class ConversationSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSummarySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['last_message_at', 'created_at']
    ordering = ['-last_message_at']
    
    def get_queryset(self):
        return ConversationSummary.objects.filter(
            telegram_account__user=self.request.user
        )


class CRMProviderViewSet(viewsets.ModelViewSet):
    serializer_class = CRMProviderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    def get_queryset(self):
        return CRMProvider.objects.filter(user=self.request.user)


class PropertySearchLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PropertySearchLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return PropertySearchLog.objects.filter(
            telegram_account__user=self.request.user
        )


class PropertyInterestViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyInterestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return PropertyInterest.objects.filter(
            telegram_account__user=self.request.user
        )
