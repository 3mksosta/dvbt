import os
import re
import time
import telebot
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# ===== إعدادات البوت =====
TELEGRAM_BOT_TOKEN = "5596991298:AAHAuBVKhJvwqk1IRw5yNebOatf7sQRK_lg"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="Markdown")

# ===== إعدادات Google Drive API =====
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = "credentials.json"

credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# ===== استخراج ID من رابط جوجل درايف =====
def get_drive_id(url):
    match = re.search(r'[-\w]{25,}', url)
    return match.group(0) if match else None

# ===== بدء البوت مع الأزرار =====
@bot.message_handler(commands=['start'])
def start_message(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(
        telebot.types.InlineKeyboardButton("📋 نسخ", callback_data="copy"),
        telebot.types.InlineKeyboardButton("📤 نقل إلى تليجرام", callback_data="upload")
    )
    keyboard.add(
        telebot.types.InlineKeyboardButton("ℹ️ شرح الاستخدام", callback_data="help")
    )
    bot.send_message(message.chat.id, "🔹 *اختر العملية:*", reply_markup=keyboard)

# ===== التعامل مع الأزرار =====
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "copy":
        bot.send_message(call.message.chat.id, "📋 *أرسل رابط جوجل درايف للنسخ:*")
        bot.register_next_step_handler(call.message, copy_file_handler)
    elif call.data == "upload":
        bot.send_message(call.message.chat.id, "📤 *أرسل رابط جوجل درايف لتحميله ورفعه إلى تليجرام:*")
        bot.register_next_step_handler(call.message, upload_file_handler)
    elif call.data == "help":
        help_text = "ℹ️ *طريقة الاستخدام:*\n"
        help_text += "1️⃣ اضغط على *نسخ* لو عايز تنسخ ملف داخل جوجل درايف.\n"
        help_text += "2️⃣ اضغط على *نقل إلى تليجرام* لو عايز تحمل الملف وترفعه على تليجرام.\n"
        help_text += "3️⃣ يدعم الملفات حتى *2GB+* ويعرض سرعة التحميل والرفع وكل التفاصيل.\n"
        bot.send_message(call.message.chat.id, help_text)

# ===== نسخ الملف داخل درايف =====
def copy_file_handler(message):
    url = message.text
    file_id = get_drive_id(url)

    if not file_id:
        bot.send_message(message.chat.id, "❌ *الرابط غير صالح، حاول مرة أخرى!*")
        return

    try:
        file_metadata = drive_service.files().get(fileId=file_id, fields="name").execute()
        file_name = file_metadata.get("name")

        copied_file = drive_service.files().copy(fileId=file_id, body={}).execute()
        copied_link = f"https://drive.google.com/file/d/{copied_file.get('id')}/view"

        bot.send_message(message.chat.id, f"✅ *تم النسخ بنجاح!*\n📂 *الملف:* `{file_name}`\n🔗 [رابط الملف]({copied_link})")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ *حدث خطأ أثناء النسخ:*\n```{str(e)}```")

# ===== تحميل ورفع الملف إلى تليجرام =====
def upload_file_handler(message):
    url = message.text
    file_id = get_drive_id(url)

    if not file_id:
        bot.send_message(message.chat.id, "❌ *الرابط غير صالح، حاول مرة أخرى!*")
        return

    try:
        start_time = time.time()

        # جلب بيانات الملف
        file_metadata = drive_service.files().get(fileId=file_id, fields="name, size").execute()
        file_name = file_metadata.get("name")
        file_size = int(file_metadata.get("size", 0))

        bot.send_message(message.chat.id, f"⏳ *جاري تحميل:* `{file_name}` ({file_size / (1024*1024):.2f} MB)")

        # تحميل الملف من درايف
        request = drive_service.files().get_media(fileId=file_id)
        file = BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        download_time = time.time() - start_time
        speed = file_size / download_time / (1024*1024)

        file.seek(0)
        bot.send_document(message.chat.id, document=file, filename=file_name)

        upload_time = time.time() - start_time - download_time
        total_time = time.time() - start_time

        bot.send_message(
            message.chat.id,
            f"✅ *تم الرفع بنجاح!*\n"
            f"📂 *الملف:* `{file_name}`\n"
            f"📥 *وقت التحميل:* {download_time:.2f} ثانية\n"
            f"📤 *وقت الرفع:* {upload_time:.2f} ثانية\n"
            f"⚡ *السرعة:* {speed:.2f} MB/s\n"
            f"⏳ *الوقت الكلي:* {total_time:.2f} ثانية"
        )

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ *حدث خطأ أثناء التحميل:*\n```{str(e)}```")

# ===== تشغيل البوت =====
bot.polling(none_stop=True)
