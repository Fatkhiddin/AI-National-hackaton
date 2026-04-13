from telethon import TelegramClient,functions
import asyncio

api_id = 31685311
api_hash = "ee01dc12727cacf630cf888c7479e793"

client = TelegramClient("ozod.session", api_id, api_hash)


CHAT_ID = 2058181414

async def main():
    await client.start()

    # 1) Dialoglardan entity topamiz (bu 100% ishlaydi)
    dialogs = await client.get_dialogs()
    entity = None
    for d in dialogs:
        if d.id == CHAT_ID:
            entity = d.entity
            break

    if entity is None:
        print("Entity topilmadi.")
        return

    print("\n=== ENTITY ===")
    print(entity)

    # 2) Avatarlar
    try:
        photos = await client(functions.photos.GetUserPhotosRequest(
            user_id=entity.id,
            offset=0,
            max_id=0,
            limit=5
        ))
        print("\n=== PHOTOS ===")
        print(photos)
    except:
        print("\n=== PHOTOS ===")
        print("Avatarlar yo‘q yoki bu kanal/guruh.")

    # 3) Group yoki kanal bo‘lsa — participantlar
    try:
        participants = await client(functions.channels.GetParticipantsRequest(
            channel=entity,
            filter=functions.channels.ChannelParticipantsFilterEmpty(),
            offset=0,
            limit=200,
            hash=0
        ))
        print("\n=== PARTICIPANTS ===")
        print(participants)
    except:
        print("\n=== PARTICIPANTS ===")
        print("User bo‘lishi mumkin → participantlar yo‘q.")

    # 4) Oxirgi 50 ta xabar
    print("\n=== LAST MESSAGES ===")
    messages = await client.get_messages(CHAT_ID, limit=50)
    for msg in messages:
        print(msg.id, msg.sender_id, msg.text)

asyncio.run(main())