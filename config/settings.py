"""
VzoelFess Bot Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API Configuration
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Bot Configuration
MENFESS_CHANNEL_ID = int(os.getenv("MENFESS_CHANNEL_ID", 0))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", 0))
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# Rate Limiting Configuration
MESSAGES_PER_HOUR = int(os.getenv("MESSAGES_PER_HOUR", 5))
MESSAGES_PER_DAY = int(os.getenv("MESSAGES_PER_DAY", 20))
COOLDOWN_MINUTES = int(os.getenv("COOLDOWN_MINUTES", 10))

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/vzoelfess.db")

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "vzoelfess")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")

# Bot Messages
WELCOME_MESSAGE = """
👋 Selamat datang di VzoelFess Bot!

📝 **Cara menggunakan:**
• Kirim pesan langsung ke bot ini untuk membuat menfess
• Gunakan hashtag untuk mengkategorikan pesan (contoh: #cinta #galau #curhat)
• Pesan akan direview admin sebelum dipublikasikan
• Identitas Anda tetap anonim

⚠️ **Aturan:**
• Maksimal {messages_per_hour} pesan per jam
• Maksimal {messages_per_day} pesan per hari
• Tidak boleh spam atau konten negatif
• Cooldown {cooldown_minutes} menit antar pesan

📊 **Status Anda:**
• Pesan terkirim: {sent_messages}
• Pesan disetujui: {approved_messages}
• Rate limit: {remaining_today} pesan tersisa hari ini

Kirim pesan Anda sekarang!
""".format(
    messages_per_hour=MESSAGES_PER_HOUR,
    messages_per_day=MESSAGES_PER_DAY,
    cooldown_minutes=COOLDOWN_MINUTES,
    sent_messages="{sent_messages}",
    approved_messages="{approved_messages}",
    remaining_today="{remaining_today}"
)

RATE_LIMIT_MESSAGE = """
⏰ **Rate Limit Tercapai!**

Anda telah mencapai batas pengiriman pesan.

📊 **Status Anda:**
• Pesan hari ini: {today_count}/{messages_per_day}
• Cooldown: {cooldown_remaining} menit
• Reset harian: {reset_time}

Silakan tunggu sebelum mengirim pesan berikutnya.
""".format(
    today_count="{today_count}",
    messages_per_day=MESSAGES_PER_DAY,
    cooldown_remaining="{cooldown_remaining}",
    reset_time="{reset_time}"
)

SUCCESS_MESSAGE = """
✅ **Pesan berhasil diterima!**

📝 **Detail:**
• ID Menfess: #{menfess_id}
• Hashtags: {hashtags}
• Status: Menunggu review admin
• Estimasi review: 1-24 jam

Pesan Anda akan dipublikasikan setelah disetujui admin.
Terima kasih! 🙏
""".format(
    menfess_id="{menfess_id}",
    hashtags="{hashtags}"
)

# Admin Messages
ADMIN_REVIEW_MESSAGE = """
📋 **Menfess Baru - #{menfess_id}**

👤 **User Info:**
• User ID: {user_id}
• Username: @{username}
• Pesan ke: {message_count}

📝 **Pesan:**
{message_text}

🏷️ **Hashtags:** {hashtags}
📅 **Waktu:** {timestamp}

**Aksi:**
• ✅ Setujui: /approve {menfess_id}
• ❌ Tolak: /reject {menfess_id} [alasan]
• 🚫 Ban user: /ban {user_id}
""".format(
    menfess_id="{menfess_id}",
    user_id="{user_id}",
    username="{username}",
    message_count="{message_count}",
    message_text="{message_text}",
    hashtags="{hashtags}",
    timestamp="{timestamp}"
)

# Channel Message Format
CHANNEL_MESSAGE_FORMAT = """
💌 **Menfess #{menfess_id}**

{message_text}

{hashtags}

📅 {timestamp}
🤖 @VzoelFessBot
"""