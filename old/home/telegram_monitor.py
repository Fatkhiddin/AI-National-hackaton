"""
Telegram account monitoring - real-time message updates
"""
import asyncio
import threading
from datetime import datetime, timedelta
from django.utils import timezone
from asgiref.sync import sync_to_async
from .models import TelegramAccount, Chat, Message, AutoReplyRule, AutoReplyLog, PropertyInterest
from .utils import TelegramManager
from telethon import Button, events
import logging

logger = logging.getLogger(__name__)


class TelegramMonitor:
    """Monitor Telegram accounts for new messages"""
    
    def __init__(self):
        self.running = False
        self.monitor_thread = None
        self.check_interval = 2  # seconds - faster polling for auto-reply
        self.last_message_ids = {}  # Track last message ID per chat
        
    def start(self):
        """Start monitoring in background thread"""
        if self.running:
            logger.warning("Monitor already running")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.monitor_thread.start()
        logger.info("Telegram monitor started")
        
        # Check for pending conversations in background thread
        threading.Thread(target=self._check_pending_conversations_sync, daemon=True).start()
        
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("Telegram monitor stopped")
        
    def _run_monitor(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Get all active accounts (sync)
                from django.db import connection
                connection.close()  # Close any existing connections
                
                accounts = list(TelegramAccount.objects.filter(is_active=True))
                
                for account in accounts:
                    try:
                        self._check_account(account)
                    except Exception as e:
                        logger.error(f"Error checking account {account.phone_number}: {e}")
                
                # Wait before next check
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                import time
                time.sleep(5)
    
    def _check_account(self, account):
        """Check account for new messages"""
        # Run async code in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._fetch_new_messages(account))
        finally:
            loop.close()
    
    async def _fetch_new_messages(self, account):
        """Fetch new messages for account"""
        manager = TelegramManager(account)
        
        try:
            await manager.connect()
            
            if not await manager.is_authorized():
                return
            
            # Get recent chats
            client = await manager.get_client()
            
            # Register callback handler for inline buttons (once per client)
            if not hasattr(client, '_property_callback_registered'):
                client.add_event_handler(
                    lambda event: self._handle_property_callback(event, account),
                    events.CallbackQuery
                )
                client._property_callback_registered = True
                logger.info("✅ Property callback handler registered")
            
            dialogs = await client.get_dialogs(limit=10)
            
            for dialog in dialogs:
                # Get or create chat (sync operation)
                chat = await sync_to_async(self._get_or_create_chat)(
                    account, dialog
                )
                
                # Create unique key for tracking
                chat_key = f"{account.id}_{dialog.id}"
                
                # Get last processed message ID for this chat
                last_msg_id = self.last_message_ids.get(chat_key, 0)
                
                # Get recent messages (only check last few messages for performance)
                messages = await client.get_messages(dialog.id, limit=5)
                
                new_count = 0
                new_messages = []
                
                # Process messages from oldest to newest
                for msg in reversed(messages):
                    if msg.text and msg.id > last_msg_id:
                        new_messages.append(msg)
                        # Update last seen message ID
                        if msg.id > self.last_message_ids.get(chat_key, 0):
                            self.last_message_ids[chat_key] = msg.id
                
                # Process new messages
                incoming_messages = []
                for msg in new_messages:
                    # Save new message (sync operation)
                    await sync_to_async(self._save_message)(
                        msg, chat, account
                    )
                    new_count += 1
                    
                    # Collect incoming messages for batch processing
                    if not msg.out:  # Only for incoming messages
                        incoming_messages.append(msg)
                
                # Process all incoming messages together (batch)
                if incoming_messages:
                    logger.info(f"Processing {len(incoming_messages)} new incoming messages in {chat.title}")
                    
                    # Check if AI assistant is active first
                    ai_handled = await self._check_ai_assistant_batch(incoming_messages, chat, account, client)
                    
                    # Only use auto-reply if AI didn't handle the messages
                    if not ai_handled:
                        # For auto-reply, process each message individually
                        for msg in incoming_messages:
                            logger.info(f"New incoming message in {chat.title}: {msg.text[:50]}...")
                            await self._check_auto_reply(msg, chat, account, client)
                
                if new_count > 0:
                    logger.info(f"Processed {new_count} new messages in {chat.title}")
                    
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
        finally:
            try:
                await manager.disconnect()
            except:
                pass
    
    def _get_or_create_chat(self, account, dialog):
        """Sync helper to get or create chat"""
        from django.db import connection
        connection.close()
        
        chat, _ = Chat.objects.get_or_create(
            telegram_account=account,
            chat_id=dialog.id,
            defaults={
                'title': dialog.name,
                'username': getattr(dialog.entity, 'username', ''),
                'chat_type': 'private' if dialog.is_user else 
                           'group' if dialog.is_group else 'channel',
            }
        )
        return chat
    
    def _save_message(self, msg, chat, account):
        """Sync helper to save message"""
        from django.db import connection
        connection.close()
        
        Message.objects.get_or_create(
            message_id=msg.id,
            chat=chat,
            telegram_account=account,
            defaults={
                'text': msg.text,
                'message_type': 'text',
                'is_outgoing': msg.out,
                'date': msg.date,
                'sender_id': msg.sender_id,
            }
        )
    
    async def _check_auto_reply(self, msg, chat, account, client):
        """Check and execute auto-reply rules"""
        try:
            # Get active rules for this account
            rules = await sync_to_async(lambda: list(
                AutoReplyRule.objects.filter(
                    telegram_account=account,
                    is_active=True
                )
            ))()
            
            if not rules:
                return
            
            # Get current time for work hours check
            from datetime import datetime
            current_time = datetime.now().time()
            
            for rule in rules:
                logger.info(f"Checking rule '{rule.name}' for message: {msg.text[:50]}")
                
                # Check if rule should be applied
                should_reply = await sync_to_async(
                    self._should_apply_rule
                )(rule, msg, chat, current_time)
                
                logger.info(f"Rule '{rule.name}' should_reply: {should_reply}")
                
                if should_reply:
                    logger.info(f"Preparing to send auto-reply: {rule.name}")
                    
                    # 1. Mark message as read (double tick for sender) - if enabled
                    if rule.mark_as_read:
                        try:
                            from telethon.tl.functions.messages import ReadHistoryRequest
                            await client(ReadHistoryRequest(
                                peer=chat.chat_id,
                                max_id=msg.id
                            ))
                            logger.info(f"✓✓ Message marked as read")
                        except Exception as e:
                            logger.warning(f"Could not mark as read: {e}")
                    
                    # 2. Show typing indicator - if enabled
                    if rule.show_typing:
                        typing_duration = rule.typing_duration
                        try:
                            from telethon.tl.functions.messages import SetTypingRequest
                            from telethon.tl.types import SendMessageTypingAction
                            
                            async def show_typing_loop():
                                """Keep showing typing indicator"""
                                total_time = max(typing_duration, rule.delay_seconds)
                                for _ in range(total_time):
                                    await client(SetTypingRequest(
                                        peer=chat.chat_id,
                                        action=SendMessageTypingAction()
                                    ))
                                    await asyncio.sleep(1)
                            
                            logger.info(f"⌨️ Showing typing indicator for {max(typing_duration, rule.delay_seconds)}s...")
                            
                            # Show typing for the duration
                            if rule.delay_seconds > 0:
                                typing_task = asyncio.create_task(show_typing_loop())
                                await asyncio.sleep(rule.delay_seconds)
                                typing_task.cancel()
                            else:
                                await show_typing_loop()
                                
                        except Exception as e:
                            logger.warning(f"Could not show typing: {e}")
                            # Fallback to simple delay
                            if rule.delay_seconds > 0:
                                await asyncio.sleep(rule.delay_seconds)
                    else:
                        # Just wait without showing typing
                        if rule.delay_seconds > 0:
                            logger.info(f"⏳ Waiting {rule.delay_seconds}s before reply (no typing)")
                            await asyncio.sleep(rule.delay_seconds)
                    
                    # 3. Send the reply message
                    try:
                        sent_msg = await client.send_message(chat.chat_id, rule.reply_message)
                        logger.info(f"✅ Auto-reply SENT successfully: {rule.name} to {chat.title}")
                        
                        # Log successful reply
                        await sync_to_async(self._log_auto_reply)(
                            rule, msg, chat, success=True
                        )
                        
                        # Update rule statistics
                        await sync_to_async(self._update_rule_stats)(rule)
                        
                        # If reply_once_per_user, break after first reply
                        if rule.reply_once_per_user:
                            break
                            
                    except Exception as e:
                        logger.error(f"❌ Error sending auto-reply: {e}", exc_info=True)
                        await sync_to_async(self._log_auto_reply)(
                            rule, msg, chat, success=False, error=str(e)
                        )
                        
        except Exception as e:
            logger.error(f"Error checking auto-reply: {e}")
    
    def _should_apply_rule(self, rule, msg, chat, current_time):
        """Check if rule should be applied to this message"""
        from django.db import connection
        connection.close()
        
        logger.info(f"  Checking rule conditions for '{rule.name}':")
        logger.info(f"    - Chat type: {chat.chat_type}, Only private: {rule.only_private_chats}")
        
        # Check if private chat only
        if rule.only_private_chats and chat.chat_type != 'private':
            logger.info(f"    ❌ Rejected: not a private chat")
            return False
        
        # Check work hours
        if rule.work_hours_only:
            logger.info(f"    - Work hours check: {rule.work_hours_start} - {rule.work_hours_end}, Current: {current_time}")
            if rule.work_hours_start and rule.work_hours_end:
                if not (rule.work_hours_start <= current_time <= rule.work_hours_end):
                    logger.info(f"    ❌ Rejected: outside work hours")
                    return False
        
        # Check excluded users
        if rule.excluded_users:
            excluded_list = [u.strip() for u in rule.excluded_users.split('\n') if u.strip()]
            sender_id_str = str(msg.sender_id)
            logger.info(f"    - Excluded users: {excluded_list}, Sender: {sender_id_str}")
            if sender_id_str in excluded_list:
                logger.info(f"    ❌ Rejected: user is excluded")
                return False
        
        # Check reply_once_per_user
        if rule.reply_once_per_user:
            # Check if already replied to this user
            already_replied = AutoReplyLog.objects.filter(
                rule=rule,
                user_id=msg.sender_id,
                reply_sent=True
            ).exists()
            logger.info(f"    - Reply once per user: {rule.reply_once_per_user}, Already replied: {already_replied}")
            if already_replied:
                logger.info(f"    ❌ Rejected: already replied to this user")
                return False
        
        # Check trigger type
        logger.info(f"    - Trigger type: {rule.trigger_type}")
        
        if rule.trigger_type == 'keyword':
            keywords = rule.get_keywords_list()
            message_text = msg.text.lower() if msg.text else ''
            logger.info(f"    - Keywords: {keywords}")
            logger.info(f"    - Message text (lower): {message_text}")
            # Check if any keyword matches
            for keyword in keywords:
                if keyword in message_text:
                    logger.info(f"    ✅ MATCHED keyword: '{keyword}'")
                    return True
            logger.info(f"    ❌ No keyword matched")
            return False
            
        elif rule.trigger_type == 'all_messages':
            logger.info(f"    ✅ MATCHED: all_messages trigger")
            return True
            
        elif rule.trigger_type == 'first_message':
            # Check if this is the first message from this user in this chat
            previous_messages = Message.objects.filter(
                chat=chat,
                sender_id=msg.sender_id
            ).exclude(message_id=msg.id).exists()
            is_first = not previous_messages
            logger.info(f"    - Is first message: {is_first}")
            if is_first:
                logger.info(f"    ✅ MATCHED: first message")
            else:
                logger.info(f"    ❌ Not first message")
            return is_first
        
        logger.info(f"    ❌ Unknown trigger type or no match")
        return False
    
    def _log_auto_reply(self, rule, msg, chat, success=True, error=None):
        """Log auto-reply action"""
        from django.db import connection
        connection.close()
        
        AutoReplyLog.objects.create(
            rule=rule,
            chat_id=chat.chat_id,
            user_id=msg.sender_id,
            username=getattr(msg.sender, 'username', None) if hasattr(msg, 'sender') else None,
            trigger_message=msg.text[:500],  # Limit text length
            reply_sent=success,
            error_message=error
        )
    
    def _update_rule_stats(self, rule):
        """Update rule usage statistics"""
        from django.db import connection
        connection.close()
        
        rule.messages_sent_count += 1
        rule.save(update_fields=['messages_sent_count'])
    
    async def _check_ai_assistant_batch(self, messages, chat, account, client):
        """Check and execute AI assistant response for multiple messages. Returns True if AI handled."""
        try:
            from .models import AIAssistant, ConversationSummary
            from .ai_service import AIService
            
            # Get active AI assistant for this account
            assistants = await sync_to_async(lambda: list(
                AIAssistant.objects.filter(
                    telegram_account=account,
                    is_active=True,
                    auto_respond=True
                ).select_related('ai_provider')
            ))()
            
            if not assistants:
                return False
            
            ai_responded = False
            for assistant in assistants:
                # Check if only private chats
                if assistant.only_private_chats and chat.chat_type != 'private':
                    continue
                
                # Combine all messages into one context
                combined_messages = "\n".join([msg.text for msg in messages if msg.text])
                logger.info(f"🤖 AI Assistant '{assistant.name}' processing {len(messages)} messages...")
                ai_responded = True
                
                try:
                    # Get last message for user info
                    last_msg = messages[-1]
                    
                    # Get or create conversation summary
                    summary, created = await sync_to_async(ConversationSummary.objects.get_or_create)(
                        telegram_account=account,
                        ai_assistant=assistant,
                        chat_id=chat.chat_id,
                        defaults={
                            'user_id': last_msg.sender_id,
                            'username': getattr(last_msg.sender, 'username', '') if last_msg.sender else '',
                            'summary_data': {},
                            'last_user_message': combined_messages  # Track last message
                        }
                    )
                    
                    # ⚠️ CRITICAL FIX: Don't respond if same message was already processed
                    # Check if we already responded to this exact message
                    last_user_msg = await sync_to_async(lambda: summary.last_user_message)()
                    if last_user_msg == combined_messages and not created:
                        logger.info(f"⏭️ Skipping - already responded to this message")
                        continue
                    
                    # Mark conversation as needing reply with the new message
                    await sync_to_async(summary.mark_needs_reply)(combined_messages)
                    
                    # 🎯 HYBRID INTELLIGENCE: Summary + Recent Messages
                    from .models import Message
                    
                    # Get last N messages (configurable context window size / 4 for recent)
                    recent_count = max(5, summary.context_window_size // 4)
                    recent_messages = await sync_to_async(lambda: list(
                        Message.objects.filter(
                            chat=chat,
                            telegram_account=account
                        ).order_by('-date')[:recent_count]
                    ))()
                    
                    # Build conversation history (OPTIMIZED)
                    conversation_history = []
                    
                    # 1. Include summary if exists (long-term context)
                    if summary.summary_data and not created:
                        summary_text = self._format_summary_for_context(summary.summary_data)
                        if summary_text:
                            conversation_history.append({
                                "role": "system",
                                "content": f"📋 Oldingi suhbat xulosasi:\n{summary_text}"
                            })
                            logger.info(f"📚 Using summary with {summary.message_count} total messages tracked")
                    
                    # 2. Add recent messages (short-term context)
                    for hist_msg in reversed(recent_messages):
                        if hist_msg.text and hist_msg.message_id != last_msg.id:
                            role = "assistant" if hist_msg.is_outgoing else "user"
                            conversation_history.append({
                                "role": role,
                                "content": hist_msg.text
                            })
                    
                    logger.info(f"🎯 Smart context: summary + {len(recent_messages)} recent msgs")
                    
                    # Initialize AI service
                    ai_service = AIService(
                        provider_type=assistant.ai_provider.provider_type,
                        api_key=assistant.ai_provider.api_key,
                        model=assistant.model,
                        api_endpoint=assistant.ai_provider.api_endpoint
                    )
                    
                    # 1. Mark all messages as read if enabled
                    if assistant.mark_as_read:
                        try:
                            from telethon.tl.functions.messages import ReadHistoryRequest
                            await client(ReadHistoryRequest(
                                peer=chat.chat_id,
                                max_id=last_msg.id
                            ))
                            logger.info(f"✓✓ All {len(messages)} messages marked as read by AI assistant")
                        except Exception as e:
                            logger.warning(f"Could not mark as read: {e}")
                    
                    # 2. Show typing if enabled
                    if assistant.show_typing:
                        try:
                            from telethon.tl.functions.messages import SetTypingRequest
                            from telethon.tl.types import SendMessageTypingAction
                            
                            async def show_typing_loop():
                                for _ in range(assistant.typing_duration):
                                    await client(SetTypingRequest(
                                        peer=chat.chat_id,
                                        action=SendMessageTypingAction()
                                    ))
                                    await asyncio.sleep(1)
                            
                            logger.info(f"⌨️ AI showing typing for {assistant.typing_duration}s...")
                            typing_task = asyncio.create_task(show_typing_loop())
                            
                            # Generate AI response while showing typing
                            if assistant.response_delay_seconds > 0:
                                await asyncio.sleep(assistant.response_delay_seconds)
                            
                            typing_task.cancel()
                        except Exception as e:
                            logger.warning(f"Could not show typing: {e}")
                    else:
                        # Just delay
                        if assistant.response_delay_seconds > 0:
                            await asyncio.sleep(assistant.response_delay_seconds)
                    
                    # 3. Generate AI response for combined messages
                    logger.info(f"🧠 Generating AI response for {len(messages)} messages...")
                    logger.info(f"📝 Context: {len(conversation_history)} previous messages")
                    result = await ai_service.generate_response(
                        system_prompt=assistant.system_prompt,
                        user_message=combined_messages,
                        conversation_history=conversation_history,
                        max_tokens=800  # More tokens for better responses
                    )
                    
                    if result["success"]:
                        ai_response = result["response"]
                        logger.info(f"💬 AI response generated: {ai_response[:100]}...")
                        
                        # 🏠 CRM INTEGRATION: Check if user wants property search
                        crm_properties = await self._try_crm_search(summary, conversation_history, combined_messages, ai_service, account)
                        
                        # Send AI response
                        try:
                            sent_msg = await client.send_message(chat.chat_id, ai_response)
                            logger.info(f"✅ AI response SENT successfully to {chat.title}")
                            
                            # Send CRM properties if found
                            if crm_properties:
                                logger.info(f"🏠 Sending {len(crm_properties)} properties from CRM...")
                                await self._send_crm_properties(client, chat, crm_properties)
                            
                            # Update statistics
                            await sync_to_async(self._update_ai_stats)(assistant)
                            
                            # Update conversation summary (await to prevent task warning)
                            try:
                                await self._update_conversation_summary(
                                    summary, conversation_history, combined_messages, ai_response, ai_service
                                )
                            except Exception as e:
                                logger.warning(f"Could not update summary: {e}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error sending AI response: {e}", exc_info=True)
                    else:
                        logger.error(f"❌ AI generation failed: {result.get('error')}")
                    
                except Exception as e:
                    logger.error(f"Error in AI assistant '{assistant.name}': {e}", exc_info=True)
                    ai_responded = False
            
            return ai_responded
                    
        except Exception as e:
            logger.error(f"Error checking AI assistant batch: {e}", exc_info=True)
            return False
    
    async def _check_ai_assistant(self, msg, chat, account, client):
        """Single message compatibility - redirects to batch"""
        return await self._check_ai_assistant_batch([msg], chat, account, client)
    
    def _check_pending_conversations_sync(self):
        """Sync wrapper for checking pending conversations on startup"""
        import time
        # Wait a bit for Django to be fully ready
        time.sleep(3)
        
        try:
            from .models import ConversationSummary
            
            # Just log pending conversations, don't send responses on startup
            # (to avoid flooding users if server restarts frequently)
            pending = ConversationSummary.objects.filter(needs_reply=True).select_related(
                'telegram_account', 'ai_assistant'
            )
            
            count = pending.count()
            if count == 0:
                logger.info("✅ No pending conversations on startup")
            else:
                logger.info(f"⏳ Found {count} pending conversations (will respond when they message again)")
                # Clear old needs_reply flags (older than 24 hours)
                from django.utils import timezone as dj_timezone
                from datetime import timedelta
                old_threshold = dj_timezone.now() - timedelta(hours=24)
                old_pending = pending.filter(last_interaction_at__lt=old_threshold)
                old_count = old_pending.count()
                if old_count > 0:
                    old_pending.update(needs_reply=False)
                    logger.info(f"🧹 Cleared {old_count} old pending flags (>24h)")
            
        except Exception as e:
            logger.warning(f"Could not check pending conversations: {e}")
    
    def _format_summary_for_context(self, summary_data):
        """Format summary data into readable context for AI"""
        if not summary_data:
            return ""
        
        parts = []
        
        # Mijoz tipi va holati
        if summary_data.get('mijoz_tipi'):
            tipi_map = {
                'shunchaki_sorayapti': '❓ Shunchaki so\'rayapti',
                'jiddiy_qiziqyapti': '🔥 Jiddiy qiziqyapti',
                'tez_olmoqchi': '⚡ Tez olmoqchi',
                'kutmoqda': '⏳ Kutib turgan',
                'etibor_yoq': '❄️ E\'tibor yo\'q'
            }
            parts.append(tipi_map.get(summary_data['mijoz_tipi'], summary_data['mijoz_tipi']))
        
        if summary_data.get('mijoz_holati'):
            parts.append(f"📊 {summary_data['mijoz_holati']}")
        
        # Imkoniyatlari
        if summary_data.get('imkoniyatlari'):
            imk = summary_data['imkoniyatlari']
            if imk.get('byudjet') and imk['byudjet'] != 'noma\'lum':
                parts.append(f"💰 {imk['byudjet']}")
            if imk.get('joy_tanlovi') and imk['joy_tanlovi'] != 'noma\'lum':
                parts.append(f"📍 {imk['joy_tanlovi']}")
            if imk.get('vaqt_rejasi'):
                parts.append(f"⏰ {imk['vaqt_rejasi']}")
        
        # Qiziqishi
        if summary_data.get('qiziqishi'):
            qiziq = [q for q in summary_data['qiziqishi'] if q != 'noma\'lum']
            if qiziq:
                parts.append(f"🏠 {', '.join(qiziq)}")
        
        # Muhim faktlar
        if summary_data.get('muhim_faktlar'):
            parts.append(f"✅ {'; '.join(summary_data['muhim_faktlar'])}")
        
        # Kayfiyat
        if summary_data.get('kayfiyat'):
            kayf_map = {
                'issiq': '😊 Issiq',
                'sovuq': '😐 Sovuq',
                'neytral': '😌 Neytral',
                'chalkash': '😕 Chalkash',
                'xafa': '😠 Xafa'
            }
            parts.append(kayf_map.get(summary_data['kayfiyat'], summary_data['kayfiyat']))
        
        # Keyingi qadam
        if summary_data.get('keyingi_qadam'):
            parts.append(f"➡️ {summary_data['keyingi_qadam']}")
        
        return "\n".join(parts) if parts else ""
    
    def _update_ai_stats(self, assistant):
        """Update AI assistant statistics"""
        from django.db import connection
        connection.close()
        
        assistant.messages_processed += 1
        assistant.save(update_fields=['messages_processed'])
    
    async def _update_conversation_summary(self, summary, history, user_msg, ai_response, ai_service):
        """Update conversation summary with latest interaction"""
        try:
            # Increment message counter
            await sync_to_async(summary.increment_message_count)()
            
            # Mark as replied (clears needs_reply flag)
            await sync_to_async(summary.mark_replied)(ai_response)
            
            # Check if we need to regenerate summary
            should_update = await sync_to_async(summary.should_update_summary)()
            
            if should_update:
                logger.info(f"🔄 Regenerating summary ({summary.messages_since_summary} new messages)")
                
                # Build full conversation including latest
                full_conversation = history + [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": ai_response}
                ]
                
                # Generate updated summary
                result = await ai_service.generate_summary(
                    conversation_messages=full_conversation,
                    current_summary=summary.summary_data
                )
                
                if result["success"]:
                    await sync_to_async(summary.update_summary)(result["summary"])
                    logger.info(f"📊 Summary updated (total: {summary.message_count} msgs)")
                else:
                    logger.warning(f"Could not update summary: {result.get('error')}")
            else:
                logger.info(f"📈 Message count updated: {summary.messages_since_summary}/{summary.context_window_size}")
                
        except Exception as e:
            logger.error(f"Error updating conversation summary: {e}", exc_info=True)
    
    async def _try_crm_search(self, summary, conversation_history, user_message, ai_service, account):
        """Try to search properties in CRM if user is looking for real estate"""
        try:
            from .models import CRMProvider, PropertySearchLog
            from .crm_service import CRMService
            
            # Get active CRM provider
            crm_provider = await sync_to_async(lambda: CRMProvider.objects.filter(
                user=account.user,
                is_active=True
            ).first())()
            
            if not crm_provider:
                return None
            
            # Check if conversation is about property search
            # Look for keywords in recent messages
            search_keywords = [
                'kvartira', 'uy', 'xona', 'narx', 'sotib', 'ijara', 'turar', 'joy',
                'rasm', 'foto', 'surat', 'rasmini', 'fotosini', 'ko\'rsating', 'bor',
                'yana', 'boshqa', 'qani'
            ]
            has_property_intent = any(keyword in user_message.lower() for keyword in search_keywords)
            
            if not has_property_intent:
                return None
            
            logger.info("🔍 CRM: Property search intent detected!")
            
            # Initialize CRM service
            crm_service = CRMService(crm_provider)
            
            # Extract requirements using AI
            logger.info("🤖 CRM: Extracting property requirements with AI...")
            
            # Use ONLY the latest user message for extraction
            # Don't use summary or history - they cause confusion
            extraction_context = {
                'latest_message': user_message,
                'extract_from': 'latest_message_only'
            }
            
            extraction_result = await crm_service.extract_requirements_with_ai(
                extraction_context,
                ai_service
            )
            
            if not extraction_result.get('success'):
                logger.warning(f"CRM: Could not extract requirements: {extraction_result.get('error')}")
                return None
            
            requirements = extraction_result['requirements']
            logger.info(f"✅ CRM: Requirements extracted: {requirements}")
            
            # Search in CRM
            logger.info("🔎 CRM: Searching properties...")
            search_result = await crm_service.search_properties(requirements)
            
            # Save log
            await sync_to_async(PropertySearchLog.objects.create)(
                crm_provider=crm_provider,
                telegram_account=account,
                chat_id=summary.chat_id,
                username=summary.username,
                extracted_requirements=requirements,
                crm_request={},
                crm_response=search_result.get('raw_response', {}),
                results_count=search_result.get('count', 0),
                status='success' if search_result.get('success') else 'failed',
                error_message=search_result.get('error') if not search_result.get('success') else None
            )
            
            if search_result.get('success') and search_result.get('properties'):
                logger.info(f"✅ CRM: Found {search_result['count']} properties!")
                return search_result['properties'][:5]  # Return top 5
            else:
                logger.warning(f"⚠️ CRM: No properties found or error: {search_result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ CRM search error: {e}", exc_info=True)
            return None
    
    async def _send_crm_properties(self, client, chat, properties, search_log_id=None):
        """
        Send CRM property results to Telegram with images and inline buttons
        Har bir uy uchun: rasm + ma'lumot + tugmalar (✅ Ma'qul / ❌ Boshqa)
        """
        try:
            if not properties:
                await client.send_message(chat.chat_id, "❌ Afsuski, sizning talablaringizga mos uy topilmadi.")
                return
            
            # Send intro message
            intro = f"🏠 CRM dan {len(properties)} ta mos uy topildi. Har birini ko'rib chiqing:"
            await client.send_message(chat.chat_id, intro)
            
            await asyncio.sleep(1)
            
            # Send each property with photo and buttons
            for i, prop in enumerate(properties, 1):
                try:
                    # Format message
                    message = self._format_property_message(prop)
                    
                    # Get first image
                    image_url = None
                    if prop.get('images') and len(prop['images']) > 0:
                        first_image = prop['images'][0]
                        image_url = first_image.get('image', '')
                        
                        if image_url and not image_url.startswith('http'):
                            image_url = f"https://megapolis1.uz{image_url}"
                    
                    # Create inline buttons
                    property_id = str(prop.get('id', ''))
                    buttons = [
                        [
                            Button.inline("✅ Ma'qul", data=f"interested_{property_id}_{i}"),
                            Button.inline("❌ Boshqa", data=f"rejected_{property_id}_{i}")
                        ]
                    ]
                    
                    # Send photo with caption and buttons
                    if image_url:
                        try:
                            await client.send_file(
                                chat.chat_id,
                                image_url,
                                caption=message,
                                buttons=buttons
                            )
                            logger.info(f"📷 Sent property #{property_id} with image and buttons")
                        except Exception as e:
                            logger.warning(f"Could not send image for property #{property_id}: {e}")
                            # Fallback: send text with buttons
                            await client.send_message(chat.chat_id, message, buttons=buttons)
                    else:
                        # No image - just send text with buttons
                        await client.send_message(chat.chat_id, message, buttons=buttons)
                    
                    await asyncio.sleep(1.5)  # Delay between properties
                    
                except Exception as e:
                    logger.error(f"Error sending property {i}: {e}", exc_info=True)
                    continue
            
            logger.info(f"✅ Successfully sent {len(properties)} properties to chat")
            
        except Exception as e:
            logger.error(f"Error sending CRM properties: {e}", exc_info=True)
    
    def _format_property_message(self, prop, index=None):
        """
        Format property data for Telegram message
        Mijoz so'ragan asosiy ma'lumotlar: №, Mo'ljal, Sotuv turi, Xonalar, Qavat, Maydon, Narx, Kategoriya, Ta'mirlash
        """
        # Number (obekt ID)
        number = prop.get('id', '')
        message = f"#️⃣№{number} {prop.get('title', 'Uy').upper()}\n"
        
        # Mo'ljal (landmark/address)
        landmark = prop.get('landmark') or prop.get('address_full') or prop.get('region_name')
        if landmark:
            message += f"📍Mo'ljal: {landmark}\n"
        
        # Sotuv turi (sale type)
        sale_types = []
        if prop.get('sale_terms'):
            # sale_terms might be list of dicts like [{"name": "Bank orqali"}, {"name": "Naqd pulga"}]
            if isinstance(prop['sale_terms'], list):
                sale_types = [term.get('name') if isinstance(term, dict) else str(term) for term in prop['sale_terms']]
            elif isinstance(prop['sale_terms'], str):
                sale_types = [prop['sale_terms']]
        if sale_types:
            message += f"🔹Sotuv turi: {', '.join(sale_types)}\n"
        
        # Xonalar soni
        rooms = prop.get('rooms_numbers') or prop.get('rooms')
        if rooms:
            message += f"🚪Xonalar soni: {rooms}\n"
        
        # Qavat
        floor = prop.get('floor')
        if floor:
            message += f"🪜Qavat: {floor}\n"
        
        # Umumiy qavatlar soni
        total_floors = prop.get('total_floors')
        if total_floors:
            message += f"🏢Umumiy qavatlar soni: {total_floors}\n"
        
        # Maydon
        area = prop.get('area') or prop.get('total_area')
        if area:
            message += f"📐Umumiy maydon: {area} m²\n"
        
        # Narx
        price = prop.get('price', 0)
        currency = 'usd' if prop.get('price_currency') == 'usd' else 'uzs'
        message += f"💵Sotilish narxi: {price:,.1f} {currency}\n"
        
        # Kategoriya
        category = prop.get('category_name') or prop.get('property_type')
        if category:
            message += f"📌Kategoriya: #{category}\n"
        
        # Ta'mirlash holati
        repair = prop.get('repair_type_name') or prop.get('repair_type')
        if repair:
            message += f"⚒️Ta'mirlash holati: {repair}\n"
        
        # Link
        if prop.get('slug'):
            message += f"\n🔗 https://megapolis1.uz/object/{prop['slug']}/\n"
        
        return message
    
    async def _handle_property_callback(self, event, account):
        """
        Handle inline button clicks for properties
        Format: "interested_{property_id}_{index}" or "rejected_{property_id}_{index}"
        """
        try:
            # Parse callback data
            data = event.data.decode('utf-8')
            parts = data.split('_')
            
            if len(parts) < 3:
                return
            
            action = parts[0]  # "interested" or "rejected"
            property_id = parts[1]
            property_index = int(parts[2])
            
            chat_id = event.chat_id
            
            logger.info(f"🔘 Button clicked: {action} for property #{property_id} by chat {chat_id}")
            
            # Get chat info
            from .models import Contact
            chat = await sync_to_async(Chat.objects.filter(chat_id=chat_id).first)()
            
            if not chat:
                await event.answer("❌ Chat topilmadi")
                return
            
            # Get contact
            contact = await sync_to_async(
                lambda: Contact.objects.filter(telegram_account=account, user_id=chat_id).first()
            )()
            
            if action == "interested":
                # Mijoz qiziqdi - save PropertyInterest
                status = 'interested'
                
                # Get property data from message (from event.message)
                property_data = {
                    'id': property_id,
                    'message_text': event.message.text if event.message else ''
                }
                
                # Save interest
                await sync_to_async(PropertyInterest.objects.update_or_create)(
                    telegram_account=account,
                    chat_id=chat_id,
                    property_id=property_id,
                    defaults={
                        'username': chat.username,
                        'contact': contact,
                        'property_data': property_data,
                        'status': status
                    }
                )
                
                # Answer button click
                await event.answer("✅ Ajoyib! Sizning qiziqishingiz saqlandi. Menegerimiz tez orada bog'lanadi.")
                
                # Send confirmation message
                response = (
                    f"✅ **Uy №{property_id} saqlandi!**\n\n"
                    f"Sizning kontaktingiz menegerga yuborildi. "
                    f"Tez orada siz bilan bog'lanishadi va uyni ko'rsatish vaqtini belgilashadi.\n\n"
                    f"📞 Savollar bo'lsa: @megapolis_admin"
                )
                await event.respond(response)
                
                logger.info(f"✅ Property interest saved: chat={chat_id}, property={property_id}")
                
            elif action == "rejected":
                # Mijoz rad etdi - save as rejected
                status = 'rejected'
                
                property_data = {
                    'id': property_id,
                    'message_text': event.message.text if event.message else ''
                }
                
                await sync_to_async(PropertyInterest.objects.update_or_create)(
                    telegram_account=account,
                    chat_id=chat_id,
                    property_id=property_id,
                    defaults={
                        'username': chat.username,
                        'contact': contact,
                        'property_data': property_data,
                        'status': status
                    }
                )
                
                await event.answer("📝 Tushunarli, keyingi variantga o'tamiz")
                
                # Send message
                response = "📋 Tushunarli. Keyingi uylarni ko'rib chiqing."
                await event.respond(response)
                
                logger.info(f"❌ Property rejected: chat={chat_id}, property={property_id}")
            
        except Exception as e:
            logger.error(f"Error handling property callback: {e}", exc_info=True)
            try:
                await event.answer("❌ Xatolik yuz berdi")
            except:
                pass


# Global monitor instance
_monitor = None


def get_monitor():
    """Get or create monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = TelegramMonitor()
    return _monitor


def start_monitoring():
    """Start Telegram monitoring"""
    monitor = get_monitor()
    monitor.start()
    

def stop_monitoring():
    """Stop Telegram monitoring"""
    monitor = get_monitor()
    monitor.stop()
