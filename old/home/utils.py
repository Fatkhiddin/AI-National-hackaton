import asyncio
import os
from datetime import datetime
import threading
import queue
import time
from telethon import TelegramClient, functions, types
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.contacts import ImportContactsRequest, AddContactRequest
from telethon.tl.types import InputPhoneContact
from django.conf import settings
from asgiref.sync import sync_to_async
from .models import TelegramAccount, Contact, Chat, Message, ContactImportHistory
import xlrd
from django.contrib.auth.models import User

class TelegramManager:
    def __init__(self, telegram_account):
        self.telegram_account = telegram_account
        self.session_file = os.path.join(
            settings.TELEGRAM_SESSION_PATH, 
            f"{telegram_account.session_name}.session"
        )
        self.client = TelegramClient(
            self.session_file,
            telegram_account.api_id,
            telegram_account.api_hash
        )
    
    async def connect(self):
        """Connect to Telegram"""
        await self.client.connect()
        return self.client.is_connected()
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        await self.client.disconnect()
    
    async def is_authorized(self):
        """Check if user is authorized"""
        return await self.client.is_user_authorized()
    
    async def send_code(self, phone_number):
        """Send verification code to phone number"""
        try:
            result = await self.client.send_code_request(phone_number)
            return {'success': True, 'phone_code_hash': result.phone_code_hash}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def sign_in(self, phone_number, code, phone_code_hash, password=None):
        """Sign in with phone number and code"""
        try:
            if password:
                result = await self.client.sign_in(password=password)
            else:
                result = await self.client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
            return {'success': True, 'user': result}
        except SessionPasswordNeededError:
            return {'success': False, 'needs_password': True}
        except PhoneCodeInvalidError:
            return {'success': False, 'error': 'Invalid verification code'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def check_password(self, password):
        """Check 2FA password"""
        try:
            result = await self.client.sign_in(password=password)
            return {'success': True, 'user': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_me(self):
        """Get current user info"""
        try:
            me = await self.client.get_me()
            return me
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
    
    async def get_dialogs(self, limit=100):
        """Get user dialogs/chats"""
        try:
            dialogs = []
            async for dialog in self.client.iter_dialogs(limit=limit):
                dialog_data = {
                    'id': dialog.id,
                    'title': dialog.title or dialog.name,
                    'username': getattr(dialog.entity, 'username', None),
                    'type': type(dialog.entity).__name__.lower(),
                    'unread_count': dialog.unread_count,
                    'is_user': dialog.is_user,
                    'is_group': dialog.is_group,
                    'is_channel': dialog.is_channel,
                }
                dialogs.append(dialog_data)
            return dialogs
        except Exception as e:
            print(f"Error getting dialogs: {e}")
            return []
    
    async def get_messages(self, chat_id, limit=100):
        """Get messages from a chat"""
        try:
            messages = []
            async for message in self.client.iter_messages(chat_id, limit=limit):
                if message.text:
                    message_data = {
                        'id': message.id,
                        'text': message.text,
                        'date': message.date,
                        'from_id': message.sender_id,
                        'is_outgoing': message.out,
                        'reply_to': message.reply_to_msg_id if message.reply_to else None,
                    }
                    messages.append(message_data)
            # Xabarlarni to'g'ri tartibda qaytarish (eski birinchi, yangi oxirida)
            messages.reverse()
            return messages
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    async def download_chat_avatar(self, chat_id):
        """Download chat/user avatar and return file path"""
        try:
            import os
            from django.conf import settings
            
            # Avatar papkasini yaratish
            avatar_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
            os.makedirs(avatar_dir, exist_ok=True)
            
            # Chat entity ni olish
            try:
                entity = await self.client.get_entity(chat_id)
            except:
                # Agar cache da yo'q bo'lsa, dialoglarni yuklash
                await self.client.get_dialogs()
                entity = await self.client.get_entity(chat_id)
            
            # Avatar yuklab olish
            file_path = await self.client.download_profile_photo(
                entity,
                file=os.path.join(avatar_dir, f'avatar_{chat_id}.jpg')
            )
            
            if file_path:
                # Media papkasiga nisbatan yo'lni qaytarish
                return f'avatars/avatar_{chat_id}.jpg'
            return None
        except Exception as e:
            print(f"Error downloading avatar for {chat_id}: {e}")
            return None
    
    async def send_message(self, telegram_chat_id, message_text):
        """Send message to a chat using real Telegram chat ID"""
        try:
            # telegram_chat_id - bu real Telegram chat ID (masalan: 7570823285 yoki -1001234567890)
            try:
                entity = await self.client.get_entity(telegram_chat_id)
            except Exception as e:
                # Agar entity cache da topilmasa, dialoglarni yuklab cache ni to'ldirish
                if "Could not find the input entity" in str(e):
                    # Cache ni to'ldirish uchun dialoglarni yuklash
                    await self.client.get_dialogs()
                    
                    # Yana urinish
                    entity = await self.client.get_entity(telegram_chat_id)
                else:
                    raise
            
            # Entity orqali xabar yuborish
            result = await self.client.send_message(entity, message_text)
            return {'success': True, 'message_id': result.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def import_contacts_to_telegram(self, contacts_list):
        """Import contacts to Telegram"""
        try:
            input_contacts = []
            for i, contact in enumerate(contacts_list):
                phone = str(contact['phone']).replace('+', '').replace('-', '').replace(' ', '')
                if not phone.startswith('+'):
                    phone = '+' + phone
                
                input_contact = InputPhoneContact(
                    client_id=i,
                    phone=phone,
                    first_name=contact.get('name', 'Contact'),
                    last_name=''
                )
                input_contacts.append(input_contact)
            
            # Import contacts in batches
            batch_size = 500
            imported_count = 0
            total_contacts = len(input_contacts)
            
            for i in range(0, total_contacts, batch_size):
                batch = input_contacts[i:i+batch_size]
                try:
                    result = await self.client(ImportContactsRequest(batch))
                    imported_count += len(result.imported)
                except Exception as e:
                    print(f"Error importing batch {i//batch_size + 1}: {e}")
            
            return {'success': True, 'imported': imported_count, 'total': total_contacts}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_client(self):
        """Get the telegram client instance"""
        if not self.client.is_connected():
            await self.connect()
        return self.client
    
    async def sync_contacts_from_telegram(self):
        """Sync contacts from Telegram to Django database"""
        try:
            # Get contacts using iter_dialogs for users only
            synced_count = 0
            
            # Create async versions of Django ORM operations
            create_contact = sync_to_async(Contact.objects.get_or_create)
            save_contact = sync_to_async(lambda obj: obj.save())
            
            async for dialog in self.client.iter_dialogs():
                if dialog.is_user and not dialog.entity.bot:  # Only real users, not bots
                    contact = dialog.entity
                    try:
                        contact_obj, created = await create_contact(
                            user_id=contact.id,
                            telegram_account=self.telegram_account,
                            defaults={
                                'first_name': getattr(contact, 'first_name', '') or '',
                                'last_name': getattr(contact, 'last_name', '') or '',
                                'username': getattr(contact, 'username', '') or '',
                                'phone_number': getattr(contact, 'phone', '') or '',
                                'is_premium': getattr(contact, 'premium', False),
                                'is_bot': getattr(contact, 'bot', False),
                                'name': f"{getattr(contact, 'first_name', '')} {getattr(contact, 'last_name', '')}".strip() or f"User{contact.id}",
                                'added_to_telegram': True  # These are from Telegram, so they're added
                            }
                        )
                        
                        if not created:
                            # Update existing contact if needed
                            contact_obj.first_name = getattr(contact, 'first_name', '') or contact_obj.first_name
                            contact_obj.last_name = getattr(contact, 'last_name', '') or contact_obj.last_name
                            contact_obj.username = getattr(contact, 'username', '') or contact_obj.username
                            contact_obj.phone_number = getattr(contact, 'phone', '') or contact_obj.phone_number
                            contact_obj.is_premium = getattr(contact, 'premium', False)
                            contact_obj.is_bot = getattr(contact, 'bot', False)
                            contact_obj.added_to_telegram = True
                            await save_contact(contact_obj)
                        
                        synced_count += 1
                    except Exception as e:
                        print(f"Error syncing contact {contact.id}: {e}")
            
            return {'success': True, 'synced': synced_count}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def add_contacts_to_telegram(self):
        """Add contacts from database to Telegram"""
        try:
            # Get all contacts for this account that are not yet added to Telegram
            get_contacts = sync_to_async(list)
            contacts = await get_contacts(
                Contact.objects.filter(
                    telegram_account=self.telegram_account,
                    added_to_telegram=False
                ).exclude(
                    phone_number__isnull=True
                ).exclude(
                    phone_number__exact=''
                )  # Remove limit to process all contacts
            )
            
            if not contacts:
                return {'success': False, 'error': 'Qo\'shish uchun kontakt topilmadi yoki barcha kontaktlar allaqachon qo\'shilgan'}
            
            # Prepare contacts for Telegram API with better validation
            input_contacts = []
            invalid_phones = []
            fixed_phones = []
            
            for contact in contacts:
                phone = str(contact.phone_number).strip() if contact.phone_number else ''
                
                # Remove all non-digit characters except +
                clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
                
                # Remove + from the beginning and count digits
                digits_only = ''.join(filter(str.isdigit, clean_phone))
                
                formatted_phone = None
                
                # Try to format phone number
                if len(digits_only) >= 9:
                    # If phone starts with known country code
                    if digits_only.startswith('998') and len(digits_only) == 12:
                        # Uzbekistan format: 998XXXXXXXXX
                        formatted_phone = '+' + digits_only
                    elif digits_only.startswith('7') and len(digits_only) == 11:
                        # Russia/Kazakhstan format: 7XXXXXXXXXX
                        formatted_phone = '+' + digits_only
                    elif digits_only.startswith('90') and len(digits_only) == 12:
                        # Turkey format: 90XXXXXXXXXX
                        formatted_phone = '+' + digits_only
                    elif len(digits_only) == 9 and digits_only.startswith('9'):
                        formatted_phone = '+998' + digits_only
                    elif len(digits_only) == 10 and not digits_only.startswith('998'):
                        # Could be Russia/Kazakhstan without 7: XXXXXXXXXX
                        formatted_phone = '+7' + digits_only
                    elif len(digits_only) >= 10 and len(digits_only) <= 15:
                        # Generic international format
                        formatted_phone = '+' + digits_only
                
                if formatted_phone and len(formatted_phone) >= 10:
                    # Ensure we have a valid first name
                    contact_name = contact.first_name or contact.name or "Megapolis"
                    
                    input_contact = InputPhoneContact(
                        client_id=contact.id,
                        phone=formatted_phone,
                        first_name=contact_name,
                        last_name=contact.last_name or ''
                    )
                    input_contacts.append(input_contact)
                    if formatted_phone != '+' + digits_only:
                        fixed_phones.append(f"{contact.name or 'Nomsiz'}: {phone} -> {formatted_phone}")
                else:
                    invalid_phones.append(f"{contact.name or 'Nomsiz'}: {phone}")
            
            # Debug information
            debug_info = f"Jami kontaktlar: {len(contacts)}, Yaroqli: {len(input_contacts)}, Yaroqsiz: {len(invalid_phones)}"
            if fixed_phones:
                debug_info += f", To'g'irlandi: {len(fixed_phones)}"
            
            if not input_contacts:
                error_msg = f'Yaroqli telefon raqamlari topilmadi.\n{debug_info}'
                if invalid_phones:
                    error_msg += f'\n\nYaroqsiz raqamlar:\n' + '\n'.join(invalid_phones[:5])
                error_msg += f'\n\nMaslahat: Telefon raqamlarini to\'liq xalqaro formatda kiriting (+998XXXXXXXXX)'
                return {'success': False, 'error': error_msg}
            
            # Add contacts to Telegram using ImportContactsRequest in small batches
            save_contact = sync_to_async(lambda obj: obj.save())
            added_count = 0
            imported_count = 0
            
            # Process contacts in batches of 10 to avoid rate limits
            batch_size = 10
            total_to_process = len(input_contacts)
            
            for i in range(0, total_to_process, batch_size):
                batch = input_contacts[i:i+batch_size]
                batch_contacts = contacts[i:i+batch_size]
                
                try:
                    print(f"Jarayon: {i+1}-{min(i+len(batch), total_to_process)}/{total_to_process} - Batch import qilinmoqda...")
                    
                    # Use ImportContactsRequest for batch import
                    result = await self.client(ImportContactsRequest(batch))
                    
                    # Mark all contacts in this batch as added
                    for contact in batch_contacts:
                        contact.added_to_telegram = True
                        await save_contact(contact)
                        added_count += 1
                    
                    imported_count += len(result.imported)
                    print(f"✓ Muvaffaqiyat: {len(batch)} ta kontakt qo'shildi, {len(result.imported)} ta import qilindi")
                    
                except Exception as e:
                    print(f"✗ Batch xatolik: {str(e)}")
                    # Check if contacts don't have Telegram
                    for j, contact in enumerate(batch_contacts):
                        if "Cannot find any entity" in str(e):
                            contact.telegram_exists = False
                            contact.added_to_telegram = False
                        else:
                            contact.added_to_telegram = True
                        await save_contact(contact)
                        added_count += 1
                    continue
            
            success_msg = f'{added_count} ta kontakt bazada belgilandi, {imported_count} ta Telegramga import qilindi'
            if invalid_phones:
                success_msg += f'\n{len(invalid_phones)} ta yaroqsiz raqam o\'tkazildi'
            if fixed_phones:
                success_msg += f'\n{len(fixed_phones)} ta raqam avtomatik to\'g\'irlandi'
            
            return {
                'success': True, 
                'added': added_count,
                'imported': imported_count,
                'message': success_msg,
                'debug': debug_info,
                'fixed_phones': fixed_phones[:3] if fixed_phones else []
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Xatolik: {str(e)}'}

def import_contacts_from_excel(file_path, telegram_account=None):
    """Import contacts from Excel file"""
    workbook = None
    try:
        workbook = xlrd.open_workbook(file_path)
        sheet = workbook.sheet_by_index(0)
        
        contacts = []
        successful_imports = 0
        failed_imports = 0
        
        # Skip header row
        for row_idx in range(1, sheet.nrows):
            try:
                row = sheet.row(row_idx)
                name = str(row[0].value) if row[0].value else f"Contact {row_idx}"
                phone = str(int(row[1].value)) if isinstance(row[1].value, float) else str(row[1].value)
                
                # Clean phone number
                phone = phone.replace('.0', '').strip()
                if phone and phone != 'nan':
                    contact_data = {
                        'name': name,
                        'phone_number': phone,
                        'telegram_account': telegram_account
                    }
                    
                    if telegram_account:
                        contact, created = Contact.objects.get_or_create(
                            phone_number=phone,
                            telegram_account=telegram_account,
                            defaults={'name': name}
                        )
                        if created:
                            successful_imports += 1
                        else:
                            # Update existing contact name if needed
                            if not contact.name and name:
                                contact.name = name
                                contact.save()
                            successful_imports += 1
                    else:
                        contacts.append(contact_data)
                        successful_imports += 1
            except Exception as e:
                print(f"Error processing row {row_idx}: {e}")
                failed_imports += 1
        
        # Create import history record
        if telegram_account:
            ContactImportHistory.objects.create(
                telegram_account=telegram_account,
                file_name=os.path.basename(file_path),
                total_contacts=sheet.nrows - 1,
                successful_imports=successful_imports,
                failed_imports=failed_imports,
                notes=f"Imported via Excel file"
            )
        
        return {
            'success': True,
            'contacts': contacts if not telegram_account else None,
            'total': sheet.nrows - 1,
            'successful': successful_imports,
            'failed': failed_imports
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'total': 0,
            'successful': 0,
            'failed': 0
        }
    finally:
        # Clean up workbook object to release file handles
        if workbook:
            del workbook

async def setup_telegram_account(user, api_id, api_hash, phone_number, session_name):
    """Setup new Telegram account"""
    try:
        # Create TelegramAccount object
        telegram_account = TelegramAccount.objects.create(
            user=user,
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone_number,
            session_name=session_name
        )
        
        # Initialize Telegram manager
        manager = TelegramManager(telegram_account)
        
        # Connect to Telegram
        await manager.connect()
        
        return {'success': True, 'telegram_account': telegram_account, 'manager': manager}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_user_telegram_accounts(user):
    """Get all telegram accounts for a user"""
    return TelegramAccount.objects.filter(user=user, is_active=True)

def run_async(coro):
    """Run async function in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def run_coroutine_in_thread(coro, timeout: int = 30):
    """Run an awaitable in a new thread with its own event loop.

    Returns the result of the coroutine or a dict with error on timeout/exception.
    This is safe to call from sync or async Django views (it does not set event loop
    in the current thread).
    """
    q = queue.Queue()

    def _runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(coro)
            q.put({'success': True, 'result': res})
        except Exception as e:
            q.put({'success': False, 'error': str(e)})
        finally:
            try:
                # Cancel all pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # Run loop one more time to process cancellations
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                # Close loop properly
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception as e:
                print(f"Error closing event loop: {e}")
                try:
                    loop.close()
                except:
                    pass

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout)

    if not q.empty():
        return q.get()
    return {'success': False, 'error': 'Timeout occurred'}
