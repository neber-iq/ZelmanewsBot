import asyncio
from telethon import TelegramClient

API_ID = 37953123
API_HASH = 'a1858aa76f97afdeb67fcf457696b6c3'

async def main():
    client = TelegramClient('new_session', API_ID, API_HASH)
    await client.start()
    print("✅ تم إنشاء الجلسة الجديدة بنجاح!")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())