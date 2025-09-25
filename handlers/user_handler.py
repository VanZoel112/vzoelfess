"""
User Message Handler for VzoelFess Bot
Handle user messages, rate limiting, and menfess creation
"""

import re
from datetime import datetime
from telethon import events
from telethon.tl.types import User
from config.settings import (
    WELCOME_MESSAGE, RATE_LIMIT_MESSAGE, SUCCESS_MESSAGE,
    MESSAGES_PER_HOUR, MESSAGES_PER_DAY, COOLDOWN_MINUTES,
    MENFESS_CHANNEL_ID, ADMIN_GROUP_ID, ADMIN_REVIEW_MESSAGE
)
from utils.helpers import (
    extract_hashtags, clean_message_text, validate_message,
    format_hashtags, format_datetime
)

class UserHandler:
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database

    async def handle_start(self, event):
        """Handle /start command"""
        user = await event.get_sender()
        await self.db.add_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name
        )

        # Log user action
        await self.db.log_user_action(
            user.id,
            'start_command',
            {'username': user.username, 'first_name': user.first_name}
        )

        # Get user stats
        stats = await self.db.get_user_stats(user.id)
        if not stats:
            stats = {
                'total_messages': 0,
                'approved_messages': 0,
                'today_count': 0
            }

        remaining_today = max(0, MESSAGES_PER_DAY - stats['today_count'])

        welcome_text = WELCOME_MESSAGE.format(
            sent_messages=stats['total_messages'],
            approved_messages=stats['approved_messages'],
            remaining_today=remaining_today
        )

        await event.reply(welcome_text, parse_mode='markdown')

    async def handle_help(self, event):
        """Handle /help command"""
        help_text = """
📖 **Panduan VzoelFess Bot**

**Perintah Tersedia:**
• `/start` - Memulai bot dan melihat status
• `/help` - Menampilkan panduan ini
• `/stats` - Melihat statistik personal
• `/hashtags` - Melihat hashtag populer

**Cara Mengirim Menfess:**
1. Tulis pesan Anda langsung di chat bot
2. Tambahkan hashtag jika diperlukan (#cinta #galau)
3. Tunggu review dari admin
4. Menfess akan dipublikasi jika disetujui

**Contoh Pesan:**
```
Hai semuanya! Aku lagi bingung soal pilihan kuliah nih 😅
Ada yang punya saran gak?

#kuliah #saran #bingung
```

**Aturan Penting:**
• Maksimal {messages_per_hour} pesan per jam
• Maksimal {messages_per_day} pesan per hari
• Cooldown {cooldown_minutes} menit antar pesan
• Tidak boleh spam atau konten negatif
• Identitas tetap anonim

**Tips:**
• Gunakan hashtag untuk kategorisasi
• Tulis dengan jelas dan sopan
• Hindari konten yang menyinggung

Selamat ber-menfess! 🎭
        """.format(
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            cooldown_minutes=COOLDOWN_MINUTES
        )

        await event.reply(help_text, parse_mode='markdown')

    async def handle_stats(self, event):
        """Handle /stats command"""
        user = await event.get_sender()
        stats = await self.db.get_user_stats(user.id)

        if not stats:
            await event.reply("❌ Data statistik tidak ditemukan. Kirim /start terlebih dahulu.")
            return

        # Calculate approval rate
        if stats['total_messages'] > 0:
            approval_rate = (stats['approved_messages'] / stats['total_messages']) * 100
        else:
            approval_rate = 0

        remaining_today = max(0, MESSAGES_PER_DAY - stats['today_count'])

        # Get recent activity from Redis
        activity_log = []
        if self.db.redis:
            activity_log = await self.db.redis.get_user_activity_log(user.id, limit=5)

        recent_activity = ""
        for activity in activity_log[:3]:
            timestamp = datetime.fromisoformat(activity['timestamp']).strftime("%d/%m %H:%M")
            recent_activity += f"• {activity['activity']} - {timestamp}\n"

        if not recent_activity:
            recent_activity = "Belum ada aktivitas terbaru"

        stats_text = f"""
📊 **Statistik Personal**

👤 **Profile:**
• User ID: `{user.id}`
• Username: @{user.username or 'Tidak ada'}
• Bergabung: {format_datetime(stats['join_date'])}
• Status: {'🚫 Banned' if stats.get('is_banned') else '✅ Aktif'}

📈 **Statistik Menfess:**
• Total terkirim: {stats['total_messages']}
• Disetujui: {stats['approved_messages']}
• Ditolak: {stats['rejected_messages']}
• Tingkat persetujuan: {approval_rate:.1f}%

📅 **Hari Ini:**
• Pesan terkirim: {stats['today_count']}/{MESSAGES_PER_DAY}
• Sisa kuota: {remaining_today} pesan
• Reset: Tengah malam

🔥 **Aktivitas Terbaru:**
{recent_activity}

Terus semangat ber-menfess! 🎭
        """

        await event.reply(stats_text, parse_mode='markdown')

    async def handle_hashtags(self, event):
        """Handle /hashtags command - show popular hashtags"""
        hashtag_stats = await self.db.get_hashtag_stats(limit=15)

        if not hashtag_stats:
            await event.reply("📊 Belum ada data hashtag. Mulai gunakan hashtag di menfess Anda!")
            return

        hashtag_text = "🏷️ **Hashtag Populer**\n\n"

        for i, hashtag in enumerate(hashtag_stats, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📍"
            hashtag_text += f"{emoji} {hashtag['hashtag']} - {hashtag['usage_count']} kali\n"

        hashtag_text += "\n💡 **Tips:** Gunakan hashtag populer agar menfess Anda mudah ditemukan!"

        await event.reply(hashtag_text, parse_mode='markdown')

    async def handle_message(self, event):
        """Handle regular messages (menfess submission)"""
        user = await event.get_sender()
        message_text = event.text.strip()

        # Skip if empty or command
        if not message_text or message_text.startswith('/'):
            return

        # Check if user is banned
        user_data = await self.db.get_user(user.id)
        if user_data and user_data.get('is_banned'):
            ban_reason = user_data.get('ban_reason', 'Tidak ada alasan')
            await event.reply(f"🚫 **Anda telah di-ban dari bot ini**\n\n**Alasan:** {ban_reason}\n\nHubungi admin jika ada kekeliruan.")
            return

        # Validate message
        is_valid, error_msg = validate_message(message_text)
        if not is_valid:
            await event.reply(f"❌ **Pesan tidak valid**\n\n{error_msg}")
            return

        # Check if hashtag is present (mandatory)
        hashtags = extract_hashtags(message_text)
        if not hashtags:
            await event.reply("""
❌ **Hashtag wajib digunakan!**

Setiap menfess harus menggunakan minimal 1 hashtag.

**Contoh penggunaan:**
```
Cerita tentang pengalaman hari ini...

#cerita #pengalaman #hari
```

**Format hashtag yang benar:**
• Dimulai dengan tanda #
• Tanpa spasi (gunakan _ jika perlu)
• Minimal 1 hashtag per menfess
• Maksimal 10 hashtag per menfess

Silakan kirim ulang menfess Anda dengan hashtag!
            """, parse_mode='markdown')
            return

        # Limit hashtag count
        if len(hashtags) > 10:
            await event.reply("❌ **Terlalu banyak hashtag!**\n\nMaksimal 10 hashtag per menfess. Silakan kurangi hashtag Anda.")
            return

        # Check rate limits
        can_send, rate_data = await self.db.check_rate_limit(
            user.id, MESSAGES_PER_HOUR, MESSAGES_PER_DAY, COOLDOWN_MINUTES
        )

        if not can_send:
            reason = rate_data.get('reason')

            if reason == 'hourly_limit':
                reset_time = f"{rate_data.get('reset_in', 0)} detik"
                error_text = f"⏰ **Rate Limit Tercapai!**\n\nAnda telah mengirim {MESSAGES_PER_HOUR} pesan dalam 1 jam terakhir.\nSilakan tunggu {reset_time} sebelum mengirim lagi."

            elif reason == 'daily_limit':
                error_text = f"📅 **Kuota Harian Habis!**\n\nAnda telah mengirim {MESSAGES_PER_DAY} pesan hari ini.\nKuota akan reset pada tengah malam."

            elif reason == 'cooldown':
                remaining_minutes = rate_data.get('remaining_minutes', 0)
                error_text = f"⏰ **Cooldown Aktif!**\n\nSilakan tunggu {remaining_minutes:.1f} menit sebelum mengirim pesan berikutnya."

            else:
                error_text = "⏰ **Rate limit tercapai.** Silakan tunggu beberapa saat."

            await event.reply(error_text)
            return

        # Clean message (hashtags already extracted and validated above)
        clean_text = clean_message_text(message_text)

        # Add user to database if not exists
        await self.db.add_user(user.id, user.username, user.first_name, user.last_name)

        # Add menfess to database
        menfess_id = await self.db.add_menfess(user.id, clean_text, hashtags)

        # Update rate limits
        await self.db.update_rate_limit(user.id, COOLDOWN_MINUTES)

        # Log user action
        await self.db.log_user_action(
            user.id,
            'submit_menfess',
            {
                'menfess_id': menfess_id,
                'hashtags': hashtags,
                'message_length': len(clean_text)
            }
        )

        # Send success message to user
        hashtag_display = format_hashtags(hashtags) if hashtags else "Tidak ada"
        success_text = SUCCESS_MESSAGE.format(
            menfess_id=menfess_id,
            hashtags=hashtag_display
        )

        await event.reply(success_text, parse_mode='markdown')

        # Send to admin group for review
        await self.send_admin_review(menfess_id, user, clean_text, hashtags)

    async def send_admin_review(self, menfess_id: int, user: User, message_text: str, hashtags: list):
        """Send menfess to admin group for review"""
        try:
            user_stats = await self.db.get_user_stats(user.id)
            message_count = user_stats['total_messages'] if user_stats else 0

            hashtag_display = format_hashtags(hashtags) if hashtags else "Tidak ada"

            admin_text = ADMIN_REVIEW_MESSAGE.format(
                menfess_id=menfess_id,
                user_id=user.id,
                username=user.username or "Tidak ada",
                message_count=message_count,
                message_text=message_text,
                hashtags=hashtag_display,
                timestamp=format_datetime(datetime.now())
            )

            # Create inline keyboard for admin actions
            buttons = [
                [
                    {'text': '✅ Setujui', 'callback_data': f'approve_{menfess_id}'},
                    {'text': '❌ Tolak', 'callback_data': f'reject_{menfess_id}'}
                ],
                [
                    {'text': '👤 Info User', 'callback_data': f'user_info_{user.id}'},
                    {'text': '🚫 Ban User', 'callback_data': f'ban_user_{user.id}'}
                ]
            ]

            await self.bot.send_message(
                ADMIN_GROUP_ID,
                admin_text,
                parse_mode='markdown',
                buttons=buttons
            )

        except Exception as e:
            print(f"Error sending admin review: {e}")

    def register_handlers(self):
        """Register all user event handlers"""
        # Start command
        @self.bot.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            await self.handle_start(event)

        # Help command
        @self.bot.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            await self.handle_help(event)

        # Stats command
        @self.bot.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            await self.handle_stats(event)

        # Hashtags command
        @self.bot.on(events.NewMessage(pattern='/hashtags'))
        async def hashtags_handler(event):
            await self.handle_hashtags(event)

        # Private message handler (menfess submission)
        @self.bot.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
        async def message_handler(event):
            await self.handle_message(event)