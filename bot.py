import os
import re
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# ===== FUNGSI UNTUK PERINTAH =====
async def start(update, context):
    await update.message.reply_text(
        "Halo! 👋 Kirimkan link TikTok, nanti aku downloadin buat kamu.\n\n"
        "Gunakan /cancel untuk membatalkan proses."
    )

async def help_command(update, context):
    await update.message.reply_text(
        "📌 Cara pakai:\n"
        "1. Kirim link TikTok\n"
        "2. Pilih format (video/audio)\n"
        "3. Tunggu proses selesai\n\n"
        "Perintah yang tersedia:\n"
        "/start - Mulai\n"
        "/help - Bantuan\n"
        "/cancel - Batalkan proses"
    )

async def cancel(update, context):
    # Hapus data user dari memory (kalau pakai dictionary)
    user_id = update.effective_user.id
    if user_id in user_data:  # Kalau kamu pakai user_data
        user_data.pop(user_id, None)
    await update.message.reply_text("✅ Proses dibatalkan. Kirim link baru kapan saja!")

# ===== DAFTARKAN HANDLER =====
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("cancel", cancel))

BOT_TOKEN = "8622998116:AAH2PKKBuiXJFCp48-ny577B32OJuJQ4OXQ"  # Ganti dengan token asli
DOWNLOAD_DIR = "downloads"

Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

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

async def download_media(url: str, platform: str) -> dict:
    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    
    # Konfigurasi default yt-dlp
    ydl_opts = {
        'outtmpl': output_template,  # <-- perbaiki: outtmpl (bukan outtmp1)
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'cookiefile': 'cookies.txt'  # <-- pakai cookies
    }
    
    # Pengaturan khusus per platform
    if platform == "youtube":
        ydl_opts['format'] = 'best[height<=720]/best'
    elif platform == "tiktok":
        ydl_opts['format'] = 'best'
    elif platform == "instagram":
        ydl_opts['format'] = 'best'
    elif platform == "facebook":
        ydl_opts['format'] = 'best'
    elif platform == "threads":
        ydl_opts['format'] = 'best'
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info dulu (tanpa download)
            info = ydl.extract_info(url, download=False)  # <-- perbaiki: download=False
            
            # Dapatkan judul dan thumbnail
            title = info.get('title', 'video')[:50]
            thumbnail = info.get('thumbnail', None)
            duration = info.get('duration', 0)
            
            # Lakukan download
            print(f"Downloading: {title}")
            ydl.download([url])
            
            # Cari file hasil download
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

def format_duration(seconds: int) -> str:
    if not seconds:
        return "N/A"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Kirim link YouTube/TikTok/IG/FB/Threads untuk download!")

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
    
    keyboard = [[InlineKeyboardButton("📥 Download", callback_data=f"dl|{result['file_path']}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    info_text = f"✅ Selesai!\n📌 {result['title']}\n📱 {platform.upper()}"
    
    await status_msg.delete()
    await update.message.reply_text(info_text, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("dl|"):
        file_path = query.data.split("|", 1)[1]
        
        if not os.path.exists(file_path):
            await query.edit_message_text("❌ File tidak tersedia.")
            return
        
        await query.edit_message_text("📤 Mengirim file...")
        
        with open(file_path, 'rb') as f:
            await query.message.reply_video(video=f, caption="✅ Selesai!")
        
        os.remove(file_path)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Mulai\n/help - Bantuan")

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Ganti BOT_TOKEN dulu!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 Bot berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
