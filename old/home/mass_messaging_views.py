"""
Mass Messaging Views
Handle mass messaging campaigns with AI integration and spam detection
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import json
import asyncio
import time
import logging
from .models import (
    TelegramAccount, Contact, MessagingCampaign, 
    CampaignMessageLog, AIIntegration
)
from .utils import TelegramManager
import openai
from django.conf import settings

logger = logging.getLogger(__name__)

@login_required
def mass_messaging_view(request):
    """Mass messaging interface"""
    accounts = TelegramAccount.objects.filter(
        user=request.user, 
        is_active=True
    ).order_by('-created_at')
    
    context = {
        'accounts': accounts,
    }
    return render(request, 'home/mass_messaging.html', context)

@login_required
@require_http_methods(["POST"])
def get_contacts_for_accounts(request):
    """Get contacts for selected accounts"""
    try:
        data = json.loads(request.body)
        account_ids = data.get('account_ids', [])
        
        if not account_ids:
            return JsonResponse({'error': 'No accounts selected'}, status=400)
        
        # Get contacts from selected accounts
        contacts = Contact.objects.filter(
            telegram_account_id__in=account_ids,
            telegram_account__user=request.user,
            telegram_exists=True
        ).select_related('telegram_account')
        
        contacts_data = []
        for contact in contacts:
            contacts_data.append({
                'id': contact.id,
                'name': contact.name or contact.first_name,
                'phone_number': contact.phone_number,
                'username': contact.username,
                'account_phone': contact.telegram_account.phone_number
            })
        
        return JsonResponse({
            'success': True,
            'contacts': contacts_data,
            'total': len(contacts_data)
        })
    
    except Exception as e:
        logger.error(f"Error getting contacts: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def start_campaign(request):
    """Start mass messaging campaign"""
    try:
        data = json.loads(request.body)
        
        account_ids = data.get('account_ids', [])
        contact_ids = data.get('contact_ids', [])
        message_template = data.get('message_template', '')
        ai_prompt = data.get('ai_prompt', '')
        use_ai = data.get('use_ai', False)
        campaign_title = data.get('campaign_title', 'Untitled Campaign')
        delay = data.get('delay_between_messages', 5)
        
        if not account_ids or not contact_ids:
            return JsonResponse({'error': 'Accounts and contacts required'}, status=400)
        
        # Create campaign
        campaign = MessagingCampaign.objects.create(
            user=request.user,
            title=campaign_title,
            message_template=message_template,
            ai_prompt=ai_prompt,
            use_ai=use_ai,
            total_contacts=len(contact_ids),
            delay_between_messages=delay,
            status='running',
            started_at=timezone.now()
        )
        
        # Add accounts and contacts
        campaign.accounts.set(account_ids)
        campaign.contacts.set(contact_ids)
        
        # Start sending in background
        from threading import Thread
        thread = Thread(target=run_campaign, args=(campaign.id,))
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'campaign_id': campaign.id,
            'message': 'Campaign started'
        })
    
    except Exception as e:
        logger.error(f"Error starting campaign: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def campaign_status(request, campaign_id):
    """Get campaign status"""
    try:
        campaign = MessagingCampaign.objects.get(id=campaign_id, user=request.user)
        
        # Get latest logs
        latest_logs = CampaignMessageLog.objects.filter(
            campaign=campaign
        ).order_by('-created_at')[:10]
        
        logs_data = []
        for log in latest_logs:
            status_message = f"{log.contact.phone_number}: {log.status}"
            if log.error_message:
                status_message += f" - {log.error_message}"
            
            logs_data.append({
                'message': status_message,
                'status': log.status,
                'timestamp': log.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'status': campaign.status,
            'sent_count': campaign.sent_count,
            'failed_count': campaign.failed_count,
            'spam_blocked_count': campaign.spam_blocked_count,
            'total_contacts': campaign.total_contacts,
            'latest_logs': logs_data
        })
    
    except MessagingCampaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting campaign status: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def stop_campaign(request, campaign_id):
    """Stop running campaign"""
    try:
        campaign = MessagingCampaign.objects.get(id=campaign_id, user=request.user)
        campaign.status = 'stopped'
        campaign.completed_at = timezone.now()
        campaign.save()
        
        return JsonResponse({'success': True, 'message': 'Campaign stopped'})
    
    except MessagingCampaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)
    except Exception as e:
        logger.error(f"Error stopping campaign: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def run_campaign(campaign_id):
    """Run campaign in background"""
    try:
        campaign = MessagingCampaign.objects.get(id=campaign_id)
        
        # Get accounts and contacts
        accounts = list(campaign.accounts.filter(is_active=True, is_spam_blocked=False))
        contacts = list(campaign.contacts.all())
        
        if not accounts:
            campaign.status = 'stopped'
            campaign.completed_at = timezone.now()
            campaign.save()
            logger.error("No active accounts for campaign")
            return
        
        account_index = 0
        
        for contact in contacts:
            # Check if campaign is still running
            campaign.refresh_from_db()
            if campaign.status != 'running':
                break
            
            # Round-robin account selection
            account = accounts[account_index % len(accounts)]
            account_index += 1
            
            # Check if account is spam blocked
            if account.is_spam_blocked:
                # Skip this account, try next
                accounts.remove(account)
                if not accounts:
                    campaign.status = 'stopped'
                    campaign.completed_at = timezone.now()
                    campaign.save()
                    break
                continue
            
            # Generate message
            if campaign.use_ai:
                message_text = generate_ai_message(campaign.ai_prompt, contact, account)
            else:
                message_text = campaign.message_template
            
            # Create log entry
            log = CampaignMessageLog.objects.create(
                campaign=campaign,
                account=account,
                contact=contact,
                message_text=message_text,
                status='pending'
            )
            
            # Send message
            success, error = send_message_to_contact(account, contact, message_text)
            
            if success:
                log.status = 'sent'
                log.sent_at = timezone.now()
                campaign.sent_count += 1
            else:
                log.status = 'failed'
                log.error_message = error
                campaign.failed_count += 1
                
                # Check for spam errors
                if 'FLOOD_WAIT' in error or 'spam' in error.lower():
                    log.status = 'spam_blocked'
                    campaign.spam_blocked_count += 1
                    
                    # Mark account as spam blocked
                    account.is_spam_blocked = True
                    account.spam_info = f"Blocked during campaign: {error}"
                    account.spam_block_until = timezone.now() + timedelta(hours=24)
                    account.save()
                    
                    # Remove from available accounts
                    accounts.remove(account)
                    if not accounts:
                        campaign.status = 'stopped'
                        campaign.completed_at = timezone.now()
                        campaign.save()
                        break
            
            log.save()
            campaign.save()
            
            # Delay between messages
            time.sleep(campaign.delay_between_messages)
        
        # Mark campaign as completed
        campaign.status = 'completed'
        campaign.completed_at = timezone.now()
        campaign.save()
        
    except Exception as e:
        logger.error(f"Error running campaign: {e}")
        try:
            campaign = MessagingCampaign.objects.get(id=campaign_id)
            campaign.status = 'stopped'
            campaign.completed_at = timezone.now()
            campaign.save()
        except:
            pass

def generate_ai_message(prompt, contact, account):
    """Generate AI message for contact"""
    try:
        # Get AI integration for account
        ai_integration = AIIntegration.objects.filter(
            telegram_account=account,
            is_active=True
        ).first()
        
        if not ai_integration:
            return f"Assalomu alaykum, {contact.name or contact.first_name or 'Hurmatli mijoz'}!"
        
        # Use OpenAI
        if ai_integration.provider == 'openai':
            openai.api_key = ai_integration.api_key
            
            system_prompt = ai_integration.system_prompt or "You are a helpful assistant."
            user_prompt = f"{prompt}\n\nContact info: Name: {contact.name or contact.first_name}, Phone: {contact.phone_number}"
            
            response = openai.chat.completions.create(
                model=ai_integration.model_name or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=ai_integration.max_tokens,
                temperature=ai_integration.temperature
            )
            
            return response.choices[0].message.content.strip()
        
        # Default fallback
        return f"Assalomu alaykum, {contact.name or contact.first_name or 'Hurmatli mijoz'}!"
    
    except Exception as e:
        logger.error(f"Error generating AI message: {e}")
        return f"Assalomu alaykum, {contact.name or contact.first_name or 'Hurmatli mijoz'}!"

def send_message_to_contact(account, contact, message):
    """Send message to a contact"""
    try:
        manager = TelegramManager(
            session_name=account.session_name,
            api_id=account.api_id,
            api_hash=account.api_hash,
            phone_number=account.phone_number
        )
        
        # Try to send by username first, then by phone
        if contact.username:
            result = asyncio.run(manager.send_message(contact.username, message))
        else:
            result = asyncio.run(manager.send_message(contact.phone_number, message))
        
        return True, None
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error sending message to {contact.phone_number}: {error_msg}")
        return False, error_msg
