import os
import base64
import re
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# ===== KONFIGURASI =====
BOT_TOKEN = "8622998116:AAH2PKKBuiXJFCp48-ny577B32OJuJQ4OXQ"  # Ganti dengan token asli
DOWNLOAD_DIR = "downloads"

Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

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
    
    # Encode file_path ke base64 (aman untuk callback_data)
file_path_encoded = base64.b64encode(result['file_path'].encode()).decode()

keyboard = [[InlineKeyboardButton("📥 Download", callback_data=f"dl|{file_path_encoded}")]]
reply_markup = InlineKeyboardMarkup(keyboard)

info_text = f"✅ Selesai!\n📌 {result['title']}\n📱 {platform.upper()}"

await status_msg.delete()
await update.message.reply_text(info_text, reply_markup=reply_markup)

# ===== HANDLER TOMBOL =====
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("dl|"):
        # Decode file_path dari base64
        file_path_encoded = query.data.split("|", 1)[1]
        file_path = base64.b64decode(file_path_encoded.encode()).decode()
        
        if not os.path.exists(file_path):
            await query.edit_message_text("❌ File tidak tersedia.")
            return
        
        await query.edit_message_text("📤 Mengirim file...")
        
        with open(file_path, 'rb') as f:
            await query.message.reply_video(video=f, caption="✅ Selesai!")
        
        os.remove(file_path)
# ===== MAIN =====
def main():
    # Ambil token dari Environment Variable (Railway)
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN tidak ditemukan! Set di Environment Variables Railway.")
        return
    
    app = Application.builder().token(BOT_TOKEN).read_timeout(30).write_timeout(30).build()
    
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
