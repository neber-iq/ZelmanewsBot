import asyncio
import os
import re
import io
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from flask import Flask
import threading

# تحميل التوكن من متغيرات البيئة (آمن)
load_dotenv()
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8991871240:AAFi9vFtAPKMmFhVrg-8Pqos2UjH78b3eA0')

# بيانات الدخول حق حسابك الشخصي
API_ID = 37953123
API_HASH = 'a1858aa76f97afdeb67fcf457696b6c3'

# قنوات المصدر (كلها)
SOURCE_CHATS = [
    -1001006840823, -1001370990432, -1001033300734, -1002016299106,
    -1001364992115, -1001680998191, -1001048208601, -1001116498519,
    -1002159277098, -1001491094605, -1001002129373, -1001002400952,
    -1001602192088, -1001110380808, -1001822939306, -1001317489146,
    -1001032666411, -1001336945221, -1001670244580, -1002062736232,
    -1002189724818, -1001778074725
]

# قناتك الهدف
TARGET_CHAT = -1004368707352
HASHTAG = '\n\n#جمهورية_الزلم_الاخبارية'
CHANNEL_MENTION = '\n\n@Zelma_News'

sent_cache = set()
messages_count = 0
start_time = datetime.now()
latest_messages = []

# ========== Flask للـ Health Check ==========
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/ping')
def ping():
    return "Bot is alive! ✅"

def run_flask():
    flask_app.run(host='0.0.0.0', port=10000)
# ===========================================

def clean_text(text):
    if not text:
        return ''

    # حذف جميع أنواع الروابط (حتى .net بدون http)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(/\S*)?', '', text)
    
    # حذف النطاقات الشهيرة
    text = re.sub(r'\b[a-zA-Z0-9-]+\.(com|net|org|io|tv|me|app|xyz|info|online|site|tech|store|blog|co)\b', '', text)
    
    # حذف روابط تيليجرام
    text = re.sub(r't\.me/\S+', '', text)
    text = re.sub(r'telegram\.me/\S+', '', text)
    
    # حذف الهاشتاجات والمنشنات
    text = re.sub(r'#[\u0600-\u06FFa-zA-Z0-9_]+', '', text)
    text = re.sub(r'@[\u0600-\u06FFa-zA-Z0-9_]+', '', text)
    
    # حذف جملة الاشتراك (وأي نص يشبهها)
    text = re.sub(r'اشترك الآن في خدمة نجوم الرابعة.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'اشترك الآن.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'للاشتراك.*', '', text, flags=re.IGNORECASE)
    
    # حذف أي نص يبدأ بـ "من خلال الرابط" أو يحتوي على كلمة "رابط"
    text = re.sub(r'من خلال الرابط\s*\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'عبر الرابط\s*\S*', '', text, flags=re.IGNORECASE)
    
    # تنظيف المسافات والفواصل الزائدة
    text = re.sub(r'\s+', ' ', text).strip()
    
    # حذف الشرطات الزائدة في بداية أو نهاية النص
    text = re.sub(r'^[\s\-—]+', '', text)
    text = re.sub(r'[\s\-—]+$', '', text)
    
    return text

async def main():
    global messages_count, start_time, latest_messages
    
    # تشغيل Flask في خلفية
    threading.Thread(target=run_flask, daemon=True).start()
    
    # إنشاء العميلين
    user_client = TelegramClient('user_session', API_ID, API_HASH)
    bot_client = await TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

    # ========== أمر /start ==========
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_command(event):
        buttons = [
            [Button.inline("📨 اختبار النشر", b"test_publish")],
            [Button.inline("📰 آخر الأخبار", b"latest_news")],
            [Button.inline("📊 حالة البوت", b"bot_status")],
            [Button.inline("🔄 إعادة تشغيل", b"restart_bot")],
            [Button.url("📢 قناتي", "https://t.me/Zelma_News")]
        ]
        await event.reply(
            "🤖 **بوت جمهورية الزلم الإخباري**\n\n"
            "أهلاً بك! البوت شغال وينقل الأخبار من 22 قناة إلى قناتك.\n\n"
            "📌 استخدم الأزرار أدناه للتحكم والفحص:",
            buttons=buttons,
            parse_mode='markdown'
        )

    # ========== أمر /latest ==========
    @bot_client.on(events.NewMessage(pattern='/latest'))
    async def latest_command(event):
        await send_latest_news(event)

    # ========== معالجة أزرار البوت ==========
    @bot_client.on(events.CallbackQuery)
    async def callback_handler(event):
        global messages_count, start_time, latest_messages
        
        data = event.data.decode('utf-8')
        
        if data == "test_publish":
            test_message = f"🧪 **رسالة اختبارية**\n\nتم النشر بنجاح ✅\nالوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await bot_client.send_message(TARGET_CHAT, test_message + HASHTAG + CHANNEL_MENTION, parse_mode='markdown')
            await event.answer("✅ تم إرسال رسالة اختبارية للقناة!", alert=True)
            
        elif data == "latest_news":
            await send_latest_news(event)
            
        elif data == "bot_status":
            uptime = datetime.now() - start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            status_text = (
                f"📊 **حالة البوت**\n\n"
                f"✅ الحالة: **شغال**\n"
                f"🕐 وقت التشغيل: {hours} ساعة {minutes} دقيقة\n"
                f"📨 الأخبار المنشورة: **{messages_count}**\n"
                f"📡 عدد القنوات المصدر: **{len(SOURCE_CHATS)}**\n"
                f"🎯 القناة الهدف: **جمهورية الزلم الاخبارية**"
            )
            await event.edit(status_text + HASHTAG + CHANNEL_MENTION, parse_mode='markdown')
            await event.answer("📊 تم تحديث الحالة", alert=True)
            
        elif data == "restart_bot":
            await event.answer("🔄 جاري إعادة التشغيل...", alert=True)
            sent_cache.clear()
            messages_count = 0
            start_time = datetime.now()
            latest_messages.clear()
            await event.edit("🔄 **تم إعادة تشغيل البوت بنجاح!**\n\nتم مسح الذاكرة المؤقتة وإعادة ضبط العداد." + HASHTAG + CHANNEL_MENTION, parse_mode='markdown')

    # ========== دالة إرسال آخر الأخبار ==========
    async def send_latest_news(event):
        if not latest_messages:
            await event.edit("📰 **لا توجد أخبار حديثة**\n\nالبوت لم يستقبل أي أخبار جديدة من القنوات المصدر بعد." + HASHTAG + CHANNEL_MENTION, parse_mode='markdown')
            await event.answer("لا توجد أخبار", alert=True)
            return
        
        news_text = "📰 **آخر الأخبار المنشورة**\n\n"
        for i, msg in enumerate(latest_messages[-5:], 1):
            news_text += f"{i}. {msg['text']}\n"
            if msg.get('link'):
                news_text += f"   🔗 [المصدر]({msg['link']})\n"
            news_text += "\n"
        
        news_text += HASHTAG + CHANNEL_MENTION
        
        if len(news_text) > 4000:
            parts = [news_text[i:i+4000] for i in range(0, len(news_text), 4000)]
            for part in parts:
                await event.reply(part, parse_mode='markdown')
        else:
            await event.edit(news_text, parse_mode='markdown')
        await event.answer("📰 تم عرض آخر الأخبار", alert=True)

    # ========== نقل الأخبار من القنوات المصدر (النسخة النهائية) ==========
    @user_client.on(events.NewMessage)
    async def forward_to_bot(event):
        global messages_count, latest_messages
        
        # التأكد من أن الرسالة من قناة مدرجة في القائمة
        if event.chat_id not in SOURCE_CHATS:
            return
            
        try:
            msg_key = f"{event.chat_id}_{event.message.id}"
            if msg_key in sent_cache:
                return
            sent_cache.add(msg_key)
            if len(sent_cache) > 300:
                sent_cache.pop()

            raw_text = event.message.text or event.message.caption or ''
            cleaned = clean_text(raw_text)
            
            # إضافة الهاشتاج والمنشن معاً
            final_text = cleaned + HASHTAG + CHANNEL_MENTION if cleaned else HASHTAG + CHANNEL_MENTION

            # تخزين آخر الأخبار لعرضها
            if cleaned:
                news_entry = {
                    'text': cleaned[:200] + ('...' if len(cleaned) > 200 else ''),
                    'link': f"https://t.me/c/{str(event.chat_id)[4:]}/{event.message.id}" if event.chat_id else None
                }
                latest_messages.append(news_entry)
                if len(latest_messages) > 20:
                    latest_messages.pop(0)

            # ====== معالجة الميديا (صور، فيديوهات) ======
            if event.message.media:
                # إعادة توجيه الميديا مباشرة بدون تحميل
                await bot_client.forward_messages(
                    TARGET_CHAT,
                    messages=event.message,
                    from_peer=event.chat_id
                )
                # إرسال النص المنظف كرسالة منفصلة مع الهاشتاج والمنشن
                if final_text:
                    await bot_client.send_message(TARGET_CHAT, final_text)
            else:
                # رسالة نصية فقط
                await bot_client.send_message(TARGET_CHAT, final_text)

            messages_count += 1
            print(f"✅ تم النشر من: {event.chat_id}")

        except Exception as e:
            print(f"❌ خطأ من القناة {event.chat_id}: {e}")

    # ========== اختبار وصول الرسائل من جميع القنوات ==========
    @user_client.on(events.NewMessage)
    async def test_all_messages(event):
        # طباعة أي رسالة تصل من أي قناة (للتشخيص)
        if event.chat_id in SOURCE_CHATS:
            print(f"📩 واصلتني رسالة من قناة مصدر: {event.chat_id}")
        else:
            print(f"📩 واصلتني رسالة من قناة أخرى: {event.chat_id}")

    print("🚀 شغال...")
    await user_client.start()
    print("✅ البوت جاهز وينقل الأخبار...")
    print("💡 أرسل /start للبوت @Zelma_News_Bot عشان تظهر الأزرار")
    print("💡 أرسل /latest عشان تشوف آخر الأخبار المستلمة")
    await user_client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
