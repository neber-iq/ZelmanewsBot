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
import json
import hashlib
import requests
from PIL import Image

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
    -1002159277098, -1001491094605, -1001002129373,
    -1001110380808, -1001822939306, -1001317489146,
    -1001032666411, -1001336945221, -1001670244580, -1002062736232,
    -1002189724818, -1001778074725,
    -1001765747111,
    -1003613542415,
    -1001429963311
]

# قناتك الهدف
TARGET_CHAT = -1004368707352
HASHTAG = '\n\n#جمهورية_الزلم_الاخبارية'
CHANNEL_MENTION = '\n\n@Zelma_News'

# ========== العلامة المائية ==========
WATERMARK_IMAGE_URL = "https://i.imgur.com/26EA7uJ.png"
# ===================================

# ========== نظام منع التكرار ==========
CACHE_FILE = 'sent_cache.json'

def load_cache():
    try:
        with open(CACHE_FILE, 'r') as f:
            return set(json.load(f))
    except:
        return set()

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(list(cache), f)

sent_cache = load_cache()
print(f"📂 تم تحميل {len(sent_cache)} خبر من الكاش")
# =========================================

messages_count = 0
start_time = datetime.now()
latest_messages = []

# ========== Flask ==========
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
    
    # حذف جميع أنواع الروابط
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(/\S*)?', '', text)
    text = re.sub(r'\b[a-zA-Z0-9-]+\.(com|net|org|io|tv|me|app|xyz|info|online|site|tech|store|blog|co)\b', '', text)
    text = re.sub(r't\.me/\S+', '', text)
    text = re.sub(r'telegram\.me/\S+', '', text)
    
    # حذف الهاشتاجات والمنشنات
    text = re.sub(r'#[\u0600-\u06FFa-zA-Z0-9_]+', '', text)
    text = re.sub(r'@[\u0600-\u06FFa-zA-Z0-9_]+', '', text)
    
    # 🎯 حذف جميع عبارات الاشتراك والإعلانات
    text = re.sub(r'اشترك الآن في خدمة نجوم الرابعة.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'اشترك الآن.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'للاشتراك.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'من خلال الرابط\s*\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'عبر الرابط\s*\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'لتحميل تطبيقات وكالة الانباء العراقية.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'تحميل تطبيقات وكالة الانباء العراقية.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'وكالة الانباء العراقية.*', '', text, flags=re.IGNORECASE)
    
    # تنظيف المسافات والفواصل الزائدة
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[\s\-—]+', '', text)
    text = re.sub(r'[\s\-—]+$', '', text)
    
    return text

def get_text_hash(text):
    """إنشاء هاش للنص لمنع التكرار"""
    if not text:
        return None
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return hashlib.md5(cleaned.encode('utf-8')).hexdigest()

# ========== تحميل العلامة المائية ==========
def download_watermark(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            watermark_path = "watermark.png"
            with open(watermark_path, 'wb') as f:
                f.write(response.content)
            return watermark_path
        return None
    except Exception as e:
        print(f"⚠️ خطأ في تحميل العلامة المائية: {e}")
        return None

# ========== إضافة العلامة المائية ==========
def add_watermark_to_image(image_path, output_path, watermark_path):
    try:
        base_img = Image.open(image_path).convert("RGBA")
        watermark = Image.open(watermark_path).convert("RGBA")
        
        width, height = base_img.size
        wm_width = int(width * 0.15)
        wm_height = int(watermark.height * (wm_width / watermark.width))
        watermark = watermark.resize((wm_width, wm_height), Image.LANCZOS)
        
        position = (width - wm_width - 20, height - wm_height - 20)
        
        transparent = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
        transparent.paste(base_img, (0, 0))
        transparent.paste(watermark, position, watermark)
        
        transparent.convert("RGB").save(output_path, "JPEG", quality=95)
        return True
    except Exception as e:
        print(f"⚠️ خطأ في إضافة العلامة المائية: {e}")
        return False

# ========== معالجة الميديا ==========
async def process_media(event, final_text):
    try:
        watermark_path = download_watermark(WATERMARK_IMAGE_URL)
        if not watermark_path:
            return None
        
        file_path = await event.message.download_media()
        if not file_path:
            return None
        
        file_ext = os.path.splitext(file_path)[1].lower()
        output_path = f"watermarked_{os.path.basename(file_path)}"
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']:
            success = add_watermark_to_image(file_path, output_path, watermark_path)
        else:
            os.rename(file_path, output_path)
            success = True
        
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(watermark_path):
            os.remove(watermark_path)
        
        if success and os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        print(f"⚠️ خطأ في معالجة الميديا: {e}")
        return None

async def main():
    global messages_count, start_time, latest_messages, sent_cache
    
    threading.Thread(target=run_flask, daemon=True).start()
    
    user_client = TelegramClient('user_session', API_ID, API_HASH)
    bot_client = await TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

    # ========== أوامر البوت ==========
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
            "أهلاً بك! البوت شغال وينقل الأخبار مع العلامة المائية.\n\n"
            f"📡 عدد القنوات المصدر: {len(SOURCE_CHATS)}\n\n"
            "📌 استخدم الأزرار أدناه للتحكم والفحص:",
            buttons=buttons,
            parse_mode='markdown'
        )

    @bot_client.on(events.NewMessage(pattern='/latest'))
    async def latest_command(event):
        await send_latest_news(event)

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
            save_cache(sent_cache)
            messages_count = 0
            start_time = datetime.now()
            latest_messages.clear()
            await event.edit("🔄 **تم إعادة تشغيل البوت بنجاح!**\n\nتم مسح الذاكرة المؤقتة وإعادة ضبط العداد." + HASHTAG + CHANNEL_MENTION, parse_mode='markdown')

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

    # ========== معالج الألبومات ==========
    @user_client.on(events.Album)
    async def handle_album(event):
        global messages_count, latest_messages, sent_cache
        
        if event.chat_id not in SOURCE_CHATS:
            return
            
        try:
            album_key = f"album_{event.chat_id}_{event.messages[0].id}"
            if album_key in sent_cache:
                return
            sent_cache.add(album_key)
            save_cache(sent_cache)

            caption = event.messages[0].text if event.messages and event.messages[0].text else ''
            cleaned = clean_text(caption)
            final_text = cleaned + HASHTAG + CHANNEL_MENTION if cleaned else HASHTAG + CHANNEL_MENTION

            if cleaned:
                text_hash = get_text_hash(cleaned)
                if text_hash:
                    hash_key = f"hash_{text_hash}"
                    if hash_key in sent_cache:
                        return
                    sent_cache.add(hash_key)
                    save_cache(sent_cache)
                
                news_entry = {
                    'text': cleaned[:200] + ('...' if len(cleaned) > 200 else ''),
                    'link': f"https://t.me/c/{str(event.chat_id)[4:]}/{event.messages[0].id}" if event.chat_id else None
                }
                latest_messages.append(news_entry)
                if len(latest_messages) > 20:
                    latest_messages.pop(0)

            watermarked_files = []
            for msg in event.messages:
                if msg.media:
                    processed = await process_media(msg, final_text)
                    if processed:
                        watermarked_files.append(processed)
            
            if watermarked_files:
                await bot_client.send_file(
                    TARGET_CHAT,
                    watermarked_files,
                    caption=final_text
                )
                for f in watermarked_files:
                    if os.path.exists(f):
                        os.remove(f)
            else:
                await bot_client.send_file(
                    TARGET_CHAT,
                    file=event.messages,
                    caption=final_text
                )

            messages_count += 1
            print(f"✅ تم نشر ألبوم من: {event.chat_id}")

        except Exception as e:
            print(f"❌ خطأ في الألبوم: {e}")

    # ========== معالج الرسائل العادية ==========
    @user_client.on(events.NewMessage)
    async def forward_to_bot(event):
        global messages_count, latest_messages, sent_cache

        if event.out:
            return
            
        if event.grouped_id:
            return

        if event.chat_id not in SOURCE_CHATS:
            return

        try:
            raw_text = event.message.text or event.message.caption or ''
            cleaned = clean_text(raw_text)
            
            # ====== منع التكرار النصي ======
            if cleaned:
                text_hash = get_text_hash(cleaned)
                if text_hash:
                    hash_key = f"hash_{text_hash}"
                    if hash_key in sent_cache:
                        print(f"⚠️ تم تجاهل خبر مكرر: {cleaned[:50]}...")
                        return
                    sent_cache.add(hash_key)
                    save_cache(sent_cache)
            
            msg_key = f"{event.chat_id}_{event.message.id}"
            if msg_key in sent_cache:
                return
            sent_cache.add(msg_key)
            save_cache(sent_cache)

            final_text = cleaned + HASHTAG + CHANNEL_MENTION if cleaned else HASHTAG + CHANNEL_MENTION

            if cleaned:
                news_entry = {
                    'text': cleaned[:200] + ('...' if len(cleaned) > 200 else ''),
                    'link': f"https://t.me/c/{str(event.chat_id)[4:]}/{event.message.id}" if event.chat_id else None
                }
                latest_messages.append(news_entry)
                if len(latest_messages) > 20:
                    latest_messages.pop(0)

            if event.message.media:
                processed_file = await process_media(event, final_text)
                if processed_file:
                    await bot_client.send_file(
                        TARGET_CHAT,
                        processed_file,
                        caption=final_text
                    )
                    if os.path.exists(processed_file):
                        os.remove(processed_file)
                else:
                    await bot_client.forward_messages(
                        TARGET_CHAT,
                        messages=event.message.id,
                        from_peer=event.chat_id
                    )
                    if final_text:
                        await bot_client.send_message(TARGET_CHAT, final_text)
            else:
                await bot_client.send_message(TARGET_CHAT, final_text)

            messages_count += 1
            print(f"✅ تم النشر من: {event.chat_id}")

        except Exception as e:
            print(f"❌ خطأ من القناة {event.chat_id}: {e}")

    @user_client.on(events.NewMessage)
    async def test_all_messages(event):
        if event.chat_id in SOURCE_CHATS and not event.out:
            print(f"📩 واصلتني رسالة من قناة مصدر: {event.chat_id}")

    print("🚀 شغال...")
    await user_client.start()
    print("✅ البوت جاهز وينقل الأخبار مع العلامة المائية...")
    await user_client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
