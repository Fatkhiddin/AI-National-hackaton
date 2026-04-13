from rest_framework import serializers
from .models import (
    TelegramAccount, Contact, Chat, Message, 
    AutoReplyRule, AutoReplyLog, AIProvider, 
    AIAssistant, ConversationSummary, CRMProvider,
    PropertySearchLog, PropertyInterest
)


class TelegramAccountSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    
    class Meta:
        model = TelegramAccount
        fields = [
            'id', 'user', 'api_id', 'phone_number', 
            'session_name', 'is_active', 'is_spam_blocked',
            'spam_block_until', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ContactSerializer(serializers.ModelSerializer):
    telegram_account = serializers.StringRelatedField()
    
    class Meta:
        model = Contact
        fields = [
            'id', 'telegram_account', 'name', 'phone_number',
            'username', 'user_id', 'first_name', 'last_name',
            'is_premium', 'is_bot', 'added_to_telegram',
            'telegram_exists', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ChatSerializer(serializers.ModelSerializer):
    telegram_account = serializers.StringRelatedField()
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = [
            'id', 'telegram_account', 'chat_id', 'title',
            'username', 'chat_type', 'member_count',
            'is_verified', 'is_restricted', 'avatar',
            'message_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class MessageSerializer(serializers.ModelSerializer):
    telegram_account = serializers.StringRelatedField()
    chat = serializers.StringRelatedField()
    contact = serializers.StringRelatedField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'telegram_account', 'chat', 'contact',
            'message_id', 'sender_id', 'text', 'message_type',
            'is_outgoing', 'date', 'reply_to_message_id', 
            'media_path', 'created_at'
        ]
        read_only_fields = ['created_at']


class AutoReplyRuleSerializer(serializers.ModelSerializer):
    telegram_account = serializers.StringRelatedField()
    
    class Meta:
        model = AutoReplyRule
        fields = [
            'id', 'telegram_account', 'name', 'is_active',
            'trigger_type', 'keywords', 'reply_message',
            'delay_seconds', 'reply_once_per_user', 
            'work_hours_only', 'only_private_chats',
            'mark_as_read', 'show_typing', 'typing_duration',
            'messages_sent_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'messages_sent_count']


class AutoReplyLogSerializer(serializers.ModelSerializer):
    rule = serializers.StringRelatedField()
    
    class Meta:
        model = AutoReplyLog
        fields = [
            'id', 'rule', 'chat_id', 'user_id', 'username',
            'trigger_message', 'reply_sent', 'error_message', 'sent_at'
        ]
        read_only_fields = ['sent_at']


class AIProviderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    
    class Meta:
        model = AIProvider
        fields = [
            'id', 'user', 'name', 'provider_type',
            'api_key', 'api_endpoint', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True}
        }


class AIAssistantSerializer(serializers.ModelSerializer):
    telegram_account = serializers.StringRelatedField()
    ai_provider = serializers.StringRelatedField()
    
    class Meta:
        model = AIAssistant
        fields = [
            'id', 'telegram_account', 'ai_provider', 'name', 'model',
            'system_prompt', 'is_active', 'auto_respond', 
            'only_private_chats', 'response_delay_seconds',
            'mark_as_read', 'show_typing', 'typing_duration',
            'messages_processed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'messages_processed']


class ConversationSummarySerializer(serializers.ModelSerializer):
    ai_assistant = serializers.StringRelatedField()
    telegram_account = serializers.StringRelatedField()
    
    class Meta:
        model = ConversationSummary
        fields = [
            'id', 'telegram_account', 'ai_assistant', 'chat_id', 
            'user_id', 'username', 'summary_data', 'message_count', 
            'messages_since_summary', 'context_window_size',
            'needs_reply', 'last_user_message', 'last_ai_message',
            'last_message_at', 'last_interaction_at', 'last_summary_at',
            'created_at'
        ]
        read_only_fields = ['created_at', 'last_message_at', 'last_interaction_at']


class CRMProviderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    
    class Meta:
        model = CRMProvider
        fields = [
            'id', 'user', 'name', 'crm_type', 'api_url', 
            'api_key', 'field_mapping', 'request_template',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'api_secret': {'write_only': True}
        }


class PropertySearchLogSerializer(serializers.ModelSerializer):
    crm_provider = serializers.StringRelatedField()
    telegram_account = serializers.StringRelatedField()
    
    class Meta:
        model = PropertySearchLog
        fields = [
            'id', 'crm_provider', 'telegram_account', 'chat_id',
            'username', 'extracted_requirements', 'crm_request',
            'crm_response', 'results_count', 'results_sent',
            'status', 'created_at'
        ]
        read_only_fields = ['created_at']


class PropertyInterestSerializer(serializers.ModelSerializer):
    telegram_account = serializers.StringRelatedField()
    contact = serializers.StringRelatedField()
    search_log = serializers.StringRelatedField()
    
    class Meta:
        model = PropertyInterest
        fields = [
            'id', 'telegram_account', 'search_log', 'contact',
            'chat_id', 'username', 'property_id', 'property_data',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
