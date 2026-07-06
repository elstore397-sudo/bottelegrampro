import os
import re
import time
import random
import base64
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# ===== KONFIGURASI =====
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Ambil dari Environment Variable Railway
DOWNLOAD_DIR = "downloads"
Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

# Cache untuk menyimpan file sementara (biar callback_data cuma ID angka)
downloads_cache = {}

# ===== FUNGSI DETEKSI PLATFORM =====
def detect_platform(url: str) -> str:
    patterns = {
        "youtube": r"(youtube\.com|youtu\.be)",
        "tiktok": r"(tiktok\.com)",
        "instagram": r"(instagram\.com|instagr\.am)",
        "facebook": r"(facebook\.com|fb\.watch|fb\.com)",
        "threads": r"(threads\.net)"
    }
    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "unknown"

# ===== FUNGSI DOWNLOAD =====
async def download_media(url: str, platform: str) -> dict:
    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'cookiefile': 'cookies.txt'
    }
    
    if platform == "youtube":
        ydl_opts['format'] = 'best[height<=720]/best'
    else:
        ydl_opts['format'] = 'best'
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')[:50]
            thumbnail = info.get('thumbnail', None)
            duration = info.get('duration', 0)
            
            ydl.download([url])
            
            downloaded_file = None
            for file in os.listdir(DOWNLOAD_DIR):
                if file.endswith(('.mp4', '.webm', '.mkv', '.mp3')):
                    if title in file or any(word in file.lower() for word in title.lower().split()[:5]):
                        downloaded_file = os.path.join(DOWNLOAD_DIR, file)
                        break
            
            if not downloaded_file:
                files = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) 
                        if f.endswith(('.mp4', '.webm', '.mkv', '.mp3'))]
                if files:
                    downloaded_file = max(files, key=os.path.getctime)
            
            return {
                'success': True,
                'file_path': downloaded_file,
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'platform': platform
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# ===== HANDLER PERINTAH =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Halo! Kirim link YouTube/TikTok/IG/FB/Threads untuk aku downloadkan.\n\n"
        "Gunakan /cancel untuk membatalkan proses."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Cara pakai:\n"
        "1. Kirim link video\n"
        "2. Tunggu proses download\n"
        "3. Klik tombol Download\n\n"
        "Perintah:\n"
        "/start - Mulai\n"
        "/help - Bantuan\n"
        "/cancel - Batalkan"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Proses dibatalkan. Kirim link baru kapan saja!")

# ===== HANDLER URL =====
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not re.match(r'https?://', url):
        await update.message.reply_text("❌ Kirimkan link URL yang valid!")
        return
    
    platform = detect_platform(url)
    if platform == "unknown":
        await update.message.reply_text("❌ Platform tidak didukung!")
        return
    
    status_msg = await update.message.reply_text(f"📥 Memproses link dari {platform.upper()}...")
    
    result = await download_media(url, platform)
    
    if not result['success']:
        await status_msg.edit_text(f"❌ Gagal: {result['error'][:200]}")
        return
    
    # ==== TOMBOL DOWNLOAD DENGAN CACHE ID ====
    # Buat ID unik (pakai timestamp + random)
    file_id = int(time.time() * 1000) + random.randint(1, 999)
    downloads_cache[file_id] = result['file_path']
    
    keyboard = [[InlineKeyboardButton("📥 Download", callback_data=f"dl_{file_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    info_text = f"✅ Selesai!\n📌 {result['title']}\n📱 {platform.upper()}"
    
    await status_msg.delete()
    await update.message.reply_text(info_text, reply_markup=reply_markup)

# ===== HANDLER TOMBOL =====
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("dl_"):
        # Ambil ID dari callback_data
        try:
            file_id = int(query.data.split("_")[1])
        except (IndexError, ValueError):
            await query.edit_message_text("❌ ID tidak valid.")
            return
        
        file_path = downloads_cache.get(file_id)
        
        if not file_path or not os.path.exists(file_path):
            await query.edit_message_text("❌ File tidak tersedia atau sudah kadaluarsa.")
            return
        
        await query.edit_message_text("📤 Mengirim file...")
        
        try:
            with open(file_path, 'rb') as f:
                await query.message.reply_video(video=f, caption="✅ Selesai!")
            os.remove(file_path)
            downloads_cache.pop(file_id, None)
        except Exception as e:
            await query.edit_message_text(f"❌ Gagal mengirim file: {str(e)}")

# ===== MAIN =====
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN tidak ditemukan! Set di Environment Variables Railway.")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Daftarkan semua handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 Bot berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
