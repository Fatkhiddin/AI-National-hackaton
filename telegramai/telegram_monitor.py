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
        self.check_interval = 2
        self.last_message_ids = {}

    def start(self):
        if self.running:
            logger.warning("Monitor already running")
            return
        self.running = True
        self.monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.monitor_thread.start()
        logger.info("Telegram monitor started")
        threading.Thread(target=self._check_pending_conversations_sync, daemon=True).start()

    def stop(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("Telegram monitor stopped")

    def _run_monitor(self):
        while self.running:
            try:
                from django.db import connection
                connection.close()
                accounts = list(TelegramAccount.objects.filter(is_active=True))
                for account in accounts:
                    try:
                        self._check_account(account)
                    except Exception as e:
                        logger.error(f"Error checking account {account.phone_number}: {e}")
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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._fetch_new_messages(account))
        finally:
            loop.close()

    async def _fetch_new_messages(self, account):
        manager = TelegramManager(account)
        try:
            await manager.connect()
            if not await manager.is_authorized():
                return
            client = await manager.get_client()

            if not hasattr(client, "_property_callback_registered"):
                client.add_event_handler(
                    lambda event: self._handle_property_callback(event, account),
                    events.CallbackQuery,
                )
                client._property_callback_registered = True
                logger.info("✅ Property callback handler registered")

            dialogs = await client.get_dialogs(limit=10)
            for dialog in dialogs:
                chat = await sync_to_async(self._get_or_create_chat)(account, dialog)
                chat_key = f"{account.id}_{dialog.id}"
                last_msg_id = self.last_message_ids.get(chat_key, 0)
                messages = await client.get_messages(dialog.id, limit=5)

                new_messages = []
                for msg in reversed(messages):
                    if msg.text and msg.id > last_msg_id:
                        new_messages.append(msg)
                        if msg.id > self.last_message_ids.get(chat_key, 0):
                            self.last_message_ids[chat_key] = msg.id

                incoming_messages = []
                for msg in new_messages:
                    await sync_to_async(self._save_message)(msg, chat, account)
                    if not msg.out:
                        incoming_messages.append(msg)

                if incoming_messages:
                    logger.info(f"Processing {len(incoming_messages)} new incoming messages in {chat.title}")
                    ai_handled = await self._check_ai_assistant_batch(incoming_messages, chat, account, client)
                    if not ai_handled:
                        for msg in incoming_messages:
                            logger.info(f"New incoming message in {chat.title}: {msg.text[:50]}...")
                            await self._check_auto_reply(msg, chat, account, client)

        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
        finally:
            try:
                await manager.disconnect()
            except Exception:
                pass

    def _get_or_create_chat(self, account, dialog):
        from django.db import connection
        connection.close()
        chat, _ = Chat.objects.get_or_create(
            telegram_account=account,
            chat_id=dialog.id,
            defaults={
                "title": dialog.name,
                "username": getattr(dialog.entity, "username", ""),
                "chat_type": "private" if dialog.is_user else "group" if dialog.is_group else "channel",
            },
        )
        return chat

    def _save_message(self, msg, chat, account):
        from django.db import connection
        connection.close()
        Message.objects.get_or_create(
            message_id=msg.id,
            chat=chat,
            telegram_account=account,
            defaults={
                "text": msg.text,
                "message_type": "text",
                "is_outgoing": msg.out,
                "date": msg.date,
                "sender_id": msg.sender_id,
            },
        )

    async def _check_auto_reply(self, msg, chat, account, client):
        try:
            rules = await sync_to_async(
                lambda: list(AutoReplyRule.objects.filter(telegram_account=account, is_active=True))
            )()
            if not rules:
                return

            current_time = datetime.now().time()
            for rule in rules:
                should_reply = await sync_to_async(self._should_apply_rule)(rule, msg, chat, current_time)
                if should_reply:
                    if rule.mark_as_read:
                        try:
                            from telethon.tl.functions.messages import ReadHistoryRequest
                            await client(ReadHistoryRequest(peer=chat.chat_id, max_id=msg.id))
                        except Exception as e:
                            logger.warning(f"Could not mark as read: {e}")

                    if rule.show_typing:
                        try:
                            from telethon.tl.functions.messages import SetTypingRequest
                            from telethon.tl.types import SendMessageTypingAction

                            async def show_typing_loop():
                                total_time = max(rule.typing_duration, rule.delay_seconds)
                                for _ in range(total_time):
                                    await client(SetTypingRequest(peer=chat.chat_id, action=SendMessageTypingAction()))
                                    await asyncio.sleep(1)

                            if rule.delay_seconds > 0:
                                typing_task = asyncio.create_task(show_typing_loop())
                                await asyncio.sleep(rule.delay_seconds)
                                typing_task.cancel()
                            else:
                                await show_typing_loop()
                        except Exception as e:
                            logger.warning(f"Could not show typing: {e}")
                            if rule.delay_seconds > 0:
                                await asyncio.sleep(rule.delay_seconds)
                    else:
                        if rule.delay_seconds > 0:
                            await asyncio.sleep(rule.delay_seconds)

                    try:
                        await client.send_message(chat.chat_id, rule.reply_message)
                        logger.info(f"✅ Auto-reply SENT: {rule.name} to {chat.title}")
                        await sync_to_async(self._log_auto_reply)(rule, msg, chat, success=True)
                        await sync_to_async(self._update_rule_stats)(rule)
                        if rule.reply_once_per_user:
                            break
                    except Exception as e:
                        logger.error(f"❌ Error sending auto-reply: {e}")
                        await sync_to_async(self._log_auto_reply)(rule, msg, chat, success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error checking auto-reply: {e}")

    def _should_apply_rule(self, rule, msg, chat, current_time):
        from django.db import connection
        connection.close()

        if rule.only_private_chats and chat.chat_type != "private":
            return False
        if rule.work_hours_only and rule.work_hours_start and rule.work_hours_end:
            if not (rule.work_hours_start <= current_time <= rule.work_hours_end):
                return False
        if rule.excluded_users:
            excluded_list = [u.strip() for u in rule.excluded_users.split("\n") if u.strip()]
            if str(msg.sender_id) in excluded_list:
                return False
        if rule.reply_once_per_user:
            already_replied = AutoReplyLog.objects.filter(rule=rule, user_id=msg.sender_id, reply_sent=True).exists()
            if already_replied:
                return False

        if rule.trigger_type == "keyword":
            keywords = rule.get_keywords_list()
            message_text = msg.text.lower() if msg.text else ""
            for keyword in keywords:
                if keyword in message_text:
                    return True
            return False
        elif rule.trigger_type == "all_messages":
            return True
        elif rule.trigger_type == "first_message":
            previous_messages = Message.objects.filter(chat=chat, sender_id=msg.sender_id).exclude(message_id=msg.id).exists()
            return not previous_messages
        return False

    def _log_auto_reply(self, rule, msg, chat, success=True, error=None):
        from django.db import connection
        connection.close()
        AutoReplyLog.objects.create(
            rule=rule,
            chat_id=chat.chat_id,
            user_id=msg.sender_id,
            username=getattr(msg.sender, "username", None) if hasattr(msg, "sender") else None,
            trigger_message=msg.text[:500],
            reply_sent=success,
            error_message=error,
        )

    def _update_rule_stats(self, rule):
        from django.db import connection
        connection.close()
        rule.messages_sent_count += 1
        rule.save(update_fields=["messages_sent_count"])

    async def _check_ai_assistant_batch(self, messages, chat, account, client):
        try:
            from .models import AIAssistant, ConversationSummary
            from .ai_service import AIService

            assistants = await sync_to_async(
                lambda: list(
                    AIAssistant.objects.filter(
                        telegram_account=account, is_active=True, auto_respond=True
                    ).select_related("ai_provider")
                )
            )()

            if not assistants:
                return False

            ai_responded = False
            for assistant in assistants:
                if assistant.only_private_chats and chat.chat_type != "private":
                    continue

                combined_messages = "\n".join([msg.text for msg in messages if msg.text])
                logger.info(f"🤖 AI Assistant '{assistant.name}' processing {len(messages)} messages...")
                ai_responded = True

                try:
                    last_msg = messages[-1]
                    summary, created = await sync_to_async(ConversationSummary.objects.get_or_create)(
                        telegram_account=account,
                        ai_assistant=assistant,
                        chat_id=chat.chat_id,
                        defaults={
                            "user_id": last_msg.sender_id,
                            "username": getattr(last_msg.sender, "username", "") if last_msg.sender else "",
                            "summary_data": {},
                            "last_user_message": combined_messages,
                        },
                    )

                    last_user_msg = await sync_to_async(lambda: summary.last_user_message)()
                    if last_user_msg == combined_messages and not created:
                        logger.info("⏭️ Skipping - already responded")
                        continue

                    await sync_to_async(summary.mark_needs_reply)(combined_messages)

                    recent_count = max(5, summary.context_window_size // 4)
                    recent_messages = await sync_to_async(
                        lambda: list(
                            Message.objects.filter(chat=chat, telegram_account=account).order_by("-date")[:recent_count]
                        )
                    )()

                    conversation_history = []
                    if summary.summary_data and not created:
                        summary_text = self._format_summary_for_context(summary.summary_data)
                        if summary_text:
                            conversation_history.append(
                                {"role": "system", "content": f"📋 Oldingi suhbat xulosasi:\n{summary_text}"}
                            )

                    for hist_msg in reversed(recent_messages):
                        if hist_msg.text and hist_msg.message_id != last_msg.id:
                            role = "assistant" if hist_msg.is_outgoing else "user"
                            conversation_history.append({"role": role, "content": hist_msg.text})

                    ai_service = AIService(
                        provider_type=assistant.ai_provider.provider_type,
                        api_key=assistant.ai_provider.api_key,
                        model=assistant.model,
                        api_endpoint=assistant.ai_provider.api_endpoint,
                    )

                    if assistant.mark_as_read:
                        try:
                            from telethon.tl.functions.messages import ReadHistoryRequest
                            await client(ReadHistoryRequest(peer=chat.chat_id, max_id=last_msg.id))
                        except Exception as e:
                            logger.warning(f"Could not mark as read: {e}")

                    if assistant.show_typing:
                        try:
                            from telethon.tl.functions.messages import SetTypingRequest
                            from telethon.tl.types import SendMessageTypingAction

                            async def show_typing_loop():
                                for _ in range(assistant.typing_duration):
                                    await client(SetTypingRequest(peer=chat.chat_id, action=SendMessageTypingAction()))
                                    await asyncio.sleep(1)

                            typing_task = asyncio.create_task(show_typing_loop())
                            if assistant.response_delay_seconds > 0:
                                await asyncio.sleep(assistant.response_delay_seconds)
                            typing_task.cancel()
                        except Exception as e:
                            logger.warning(f"Could not show typing: {e}")
                    else:
                        if assistant.response_delay_seconds > 0:
                            await asyncio.sleep(assistant.response_delay_seconds)

                    result = await ai_service.generate_response(
                        system_prompt=assistant.system_prompt,
                        user_message=combined_messages,
                        conversation_history=conversation_history,
                        max_tokens=800,
                    )

                    if result["success"]:
                        ai_response = result["response"]
                        logger.info(f"💬 AI response: {ai_response[:100]}...")

                        crm_properties = await self._try_crm_search(
                            summary, conversation_history, combined_messages, ai_service, account
                        )

                        try:
                            await client.send_message(chat.chat_id, ai_response)
                            logger.info(f"✅ AI response SENT to {chat.title}")

                            if crm_properties:
                                await self._send_crm_properties(client, chat, crm_properties)

                            await sync_to_async(self._update_ai_stats)(assistant)
                            try:
                                await self._update_conversation_summary(
                                    summary, conversation_history, combined_messages, ai_response, ai_service
                                )
                            except Exception as e:
                                logger.warning(f"Could not update summary: {e}")
                        except Exception as e:
                            logger.error(f"❌ Error sending AI response: {e}")
                    else:
                        logger.error(f"❌ AI generation failed: {result.get('error')}")

                except Exception as e:
                    logger.error(f"Error in AI assistant '{assistant.name}': {e}", exc_info=True)
                    ai_responded = False

            return ai_responded

        except Exception as e:
            logger.error(f"Error checking AI assistant batch: {e}", exc_info=True)
            return False

    def _check_pending_conversations_sync(self):
        import time
        time.sleep(3)
        try:
            from .models import ConversationSummary
            pending = ConversationSummary.objects.filter(needs_reply=True).select_related(
                "telegram_account", "ai_assistant"
            )
            count = pending.count()
            if count == 0:
                logger.info("✅ No pending conversations on startup")
            else:
                logger.info(f"⏳ Found {count} pending conversations")
                from django.utils import timezone as dj_timezone
                old_threshold = dj_timezone.now() - timedelta(hours=24)
                old_pending = pending.filter(last_interaction_at__lt=old_threshold)
                old_count = old_pending.count()
                if old_count > 0:
                    old_pending.update(needs_reply=False)
                    logger.info(f"🧹 Cleared {old_count} old pending flags (>24h)")
        except Exception as e:
            logger.warning(f"Could not check pending conversations: {e}")

    def _format_summary_for_context(self, summary_data):
        if not summary_data:
            return ""
        parts = []
        if summary_data.get("mijoz_tipi"):
            tipi_map = {
                "shunchaki_sorayapti": "❓ Shunchaki so'rayapti",
                "jiddiy_qiziqyapti": "🔥 Jiddiy qiziqyapti",
                "tez_olmoqchi": "⚡ Tez olmoqchi",
                "kutmoqda": "⏳ Kutib turgan",
                "etibor_yoq": "❄️ E'tibor yo'q",
            }
            parts.append(tipi_map.get(summary_data["mijoz_tipi"], summary_data["mijoz_tipi"]))
        if summary_data.get("mijoz_holati"):
            parts.append(f"📊 {summary_data['mijoz_holati']}")
        if summary_data.get("imkoniyatlari"):
            imk = summary_data["imkoniyatlari"]
            if imk.get("byudjet") and imk["byudjet"] != "noma'lum":
                parts.append(f"💰 {imk['byudjet']}")
            if imk.get("joy_tanlovi") and imk["joy_tanlovi"] != "noma'lum":
                parts.append(f"📍 {imk['joy_tanlovi']}")
            if imk.get("vaqt_rejasi"):
                parts.append(f"⏰ {imk['vaqt_rejasi']}")
        if summary_data.get("qiziqishi"):
            qiziq = [q for q in summary_data["qiziqishi"] if q != "noma'lum"]
            if qiziq:
                parts.append(f"🏠 {', '.join(qiziq)}")
        if summary_data.get("muhim_faktlar"):
            parts.append(f"✅ {'; '.join(summary_data['muhim_faktlar'])}")
        if summary_data.get("kayfiyat"):
            kayf_map = {
                "issiq": "😊 Issiq",
                "sovuq": "😐 Sovuq",
                "neytral": "😌 Neytral",
                "chalkash": "😕 Chalkash",
                "xafa": "😠 Xafa",
            }
            parts.append(kayf_map.get(summary_data["kayfiyat"], summary_data["kayfiyat"]))
        if summary_data.get("keyingi_qadam"):
            parts.append(f"➡️ {summary_data['keyingi_qadam']}")
        return "\n".join(parts) if parts else ""

    def _update_ai_stats(self, assistant):
        from django.db import connection
        connection.close()
        assistant.messages_processed += 1
        assistant.save(update_fields=["messages_processed"])

    async def _update_conversation_summary(self, summary, history, user_msg, ai_response, ai_service):
        try:
            await sync_to_async(summary.increment_message_count)()
            await sync_to_async(summary.mark_replied)(ai_response)
            should_update = await sync_to_async(summary.should_update_summary)()

            if should_update:
                full_conversation = history + [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": ai_response},
                ]
                result = await ai_service.generate_summary(
                    conversation_messages=full_conversation, current_summary=summary.summary_data
                )
                if result["success"]:
                    await sync_to_async(summary.update_summary)(result["summary"])
                    logger.info(f"📊 Summary updated (total: {summary.message_count} msgs)")
        except Exception as e:
            logger.error(f"Error updating conversation summary: {e}", exc_info=True)

    async def _try_crm_search(self, summary, conversation_history, user_message, ai_service, account):
        try:
            from .models import CRMProvider, PropertySearchLog
            from .crm_service import CRMService

            crm_provider = await sync_to_async(
                lambda: CRMProvider.objects.filter(user=account.user, is_active=True).first()
            )()
            if not crm_provider:
                return None

            search_keywords = [
                "kvartira", "uy", "xona", "narx", "sotib", "ijara", "turar", "joy",
                "rasm", "foto", "surat", "rasmini", "fotosini", "ko'rsating", "bor",
                "yana", "boshqa", "qani",
            ]
            has_property_intent = any(kw in user_message.lower() for kw in search_keywords)
            if not has_property_intent:
                return None

            logger.info("🔍 CRM: Property search intent detected!")
            crm_service = CRMService(crm_provider)

            extraction_context = {"latest_message": user_message, "extract_from": "latest_message_only"}
            extraction_result = await crm_service.extract_requirements_with_ai(extraction_context, ai_service)

            if not extraction_result.get("success"):
                return None

            requirements = extraction_result["requirements"]
            logger.info(f"✅ CRM: Requirements: {requirements}")

            search_result = await crm_service.search_properties(requirements)

            await sync_to_async(PropertySearchLog.objects.create)(
                crm_provider=crm_provider,
                telegram_account=account,
                chat_id=summary.chat_id,
                username=summary.username,
                extracted_requirements=requirements,
                crm_request={},
                crm_response=search_result.get("raw_response", {}),
                results_count=search_result.get("count", 0),
                status="success" if search_result.get("success") else "failed",
                error_message=search_result.get("error") if not search_result.get("success") else None,
            )

            if search_result.get("success") and search_result.get("properties"):
                return search_result["properties"][:5]
            return None
        except Exception as e:
            logger.error(f"❌ CRM search error: {e}", exc_info=True)
            return None

    async def _send_crm_properties(self, client, chat, properties, search_log_id=None):
        try:
            if not properties:
                await client.send_message(chat.chat_id, "❌ Afsuski, sizning talablaringizga mos uy topilmadi.")
                return

            intro = f"🏠 CRM dan {len(properties)} ta mos uy topildi. Har birini ko'rib chiqing:"
            await client.send_message(chat.chat_id, intro)
            await asyncio.sleep(1)

            for i, prop in enumerate(properties, 1):
                try:
                    message = self._format_property_message(prop)
                    image_url = None
                    if prop.get("images") and len(prop["images"]) > 0:
                        first_image = prop["images"][0]
                        image_url = first_image.get("image", "")
                        if image_url and not image_url.startswith("http"):
                            image_url = f"https://megapolis1.uz{image_url}"

                    property_id = str(prop.get("id", ""))
                    buttons = [
                        [
                            Button.inline("✅ Ma'qul", data=f"interested_{property_id}_{i}"),
                            Button.inline("❌ Boshqa", data=f"rejected_{property_id}_{i}"),
                        ]
                    ]

                    if image_url:
                        try:
                            await client.send_file(chat.chat_id, image_url, caption=message, buttons=buttons)
                        except Exception:
                            await client.send_message(chat.chat_id, message, buttons=buttons)
                    else:
                        await client.send_message(chat.chat_id, message, buttons=buttons)

                    await asyncio.sleep(1.5)
                except Exception as e:
                    logger.error(f"Error sending property {i}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error sending CRM properties: {e}", exc_info=True)

    def _format_property_message(self, prop, index=None):
        number = prop.get("id", "")
        message = f"#️⃣№{number} {prop.get('title', 'Uy').upper()}\n"

        landmark = prop.get("landmark") or prop.get("address_full") or prop.get("region_name")
        if landmark:
            message += f"📍Mo'ljal: {landmark}\n"

        sale_types = []
        if prop.get("sale_terms"):
            if isinstance(prop["sale_terms"], list):
                sale_types = [term.get("name") if isinstance(term, dict) else str(term) for term in prop["sale_terms"]]
            elif isinstance(prop["sale_terms"], str):
                sale_types = [prop["sale_terms"]]
        if sale_types:
            message += f"🔹Sotuv turi: {', '.join(sale_types)}\n"

        rooms = prop.get("rooms_numbers") or prop.get("rooms")
        if rooms:
            message += f"🚪Xonalar soni: {rooms}\n"

        floor = prop.get("floor")
        if floor:
            message += f"🪜Qavat: {floor}\n"

        total_floors = prop.get("total_floors")
        if total_floors:
            message += f"🏢Umumiy qavatlar soni: {total_floors}\n"

        area = prop.get("area") or prop.get("total_area")
        if area:
            message += f"📐Umumiy maydon: {area} m²\n"

        price = prop.get("price", 0)
        currency = "usd" if prop.get("price_currency") == "usd" else "uzs"
        message += f"💵Sotilish narxi: {price:,.1f} {currency}\n"

        category = prop.get("category_name") or prop.get("property_type")
        if category:
            message += f"📌Kategoriya: #{category}\n"

        repair = prop.get("repair_type_name") or prop.get("repair_type")
        if repair:
            message += f"⚒️Ta'mirlash holati: {repair}\n"

        if prop.get("slug"):
            message += f"\n🔗 https://megapolis1.uz/object/{prop['slug']}/\n"

        return message

    async def _handle_property_callback(self, event, account):
        try:
            data = event.data.decode("utf-8")
            parts = data.split("_")
            if len(parts) < 3:
                return

            action = parts[0]
            property_id = parts[1]
            chat_id = event.chat_id

            chat = await sync_to_async(Chat.objects.filter(chat_id=chat_id).first)()
            if not chat:
                await event.answer("❌ Chat topilmadi")
                return

            from .models import Contact
            contact = await sync_to_async(
                lambda: Contact.objects.filter(telegram_account=account, user_id=chat_id).first()
            )()

            property_data = {"id": property_id, "message_text": event.message.text if event.message else ""}

            if action == "interested":
                await sync_to_async(PropertyInterest.objects.update_or_create)(
                    telegram_account=account,
                    chat_id=chat_id,
                    property_id=property_id,
                    defaults={
                        "username": chat.username,
                        "contact": contact,
                        "property_data": property_data,
                        "status": "interested",
                    },
                )
                await event.answer("✅ Sizning qiziqishingiz saqlandi.")
                await event.respond(
                    f"✅ **Uy №{property_id} saqlandi!**\n\n"
                    f"Sizning kontaktingiz menegerga yuborildi. "
                    f"Tez orada siz bilan bog'lanishadi.\n\n"
                    f"📞 Savollar bo'lsa: @megapolis_admin"
                )
            elif action == "rejected":
                await sync_to_async(PropertyInterest.objects.update_or_create)(
                    telegram_account=account,
                    chat_id=chat_id,
                    property_id=property_id,
                    defaults={
                        "username": chat.username,
                        "contact": contact,
                        "property_data": property_data,
                        "status": "rejected",
                    },
                )
                await event.answer("📝 Tushunarli, keyingi variantga o'tamiz")
                await event.respond("📋 Tushunarli. Keyingi uylarni ko'rib chiqing.")
        except Exception as e:
            logger.error(f"Error handling property callback: {e}", exc_info=True)
            try:
                await event.answer("❌ Xatolik yuz berdi")
            except Exception:
                pass


# Global monitor instance
_monitor = None


def get_monitor():
    global _monitor
    if _monitor is None:
        _monitor = TelegramMonitor()
    return _monitor


def start_monitoring():
    monitor = get_monitor()
    monitor.start()


def stop_monitoring():
    monitor = get_monitor()
    monitor.stop()
