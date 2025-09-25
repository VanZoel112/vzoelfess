"""
Admin Handler for VzoelFess Bot
Handle admin commands and menfess moderation
"""

from datetime import datetime
from telethon import events
from telethon.tl.types import User
from config.settings import (
    OWNER_ID, ADMIN_GROUP_ID, MENFESS_CHANNEL_ID,
    CHANNEL_MESSAGE_FORMAT
)
from utils.helpers import format_datetime, format_hashtags

class AdminHandler:
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
        self.admin_ids = [OWNER_ID]  # Can be extended to include more admins

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.admin_ids

    async def handle_approve(self, event, menfess_id: int):
        """Handle menfess approval"""
        user = await event.get_sender()
        if not self.is_admin(user.id):
            await event.reply("❌ Anda tidak memiliki akses admin.")
            return

        # Get menfess data
        menfess = await self.db.sqlite.get_menfess(menfess_id)
        if not menfess:
            await event.reply(f"❌ Menfess #{menfess_id} tidak ditemukan.")
            return

        if menfess['status'] != 'pending':
            await event.reply(f"❌ Menfess #{menfess_id} sudah di-{menfess['status']}.")
            return

        try:
            # Format message for channel
            hashtag_text = format_hashtags(menfess['hashtags']) if menfess['hashtags'] else ""

            channel_text = CHANNEL_MESSAGE_FORMAT.format(
                menfess_id=menfess_id,
                message_text=menfess['message_text'],
                hashtags=hashtag_text,
                timestamp=format_datetime(datetime.now())
            )

            # Send to channel
            channel_msg = await self.bot.send_message(
                MENFESS_CHANNEL_ID,
                channel_text,
                parse_mode='markdown'
            )

            # Update database
            await self.db.approve_menfess(menfess_id, user.id, channel_msg.id)

            # Send confirmation
            await event.reply(f"✅ Menfess #{menfess_id} berhasil disetujui dan dipublikasi!")

            # Log action
            await self.db.log_user_action(
                user.id,
                'approve_menfess',
                {'menfess_id': menfess_id, 'channel_message_id': channel_msg.id}
            )

        except Exception as e:
            await event.reply(f"❌ Error saat approve menfess: {str(e)}")
            print(f"Approve error: {e}")

    async def handle_reject(self, event, menfess_id: int, reason: str = None):
        """Handle menfess rejection"""
        user = await event.get_sender()
        if not self.is_admin(user.id):
            await event.reply("❌ Anda tidak memiliki akses admin.")
            return

        # Get menfess data
        menfess = await self.db.sqlite.get_menfess(menfess_id)
        if not menfess:
            await event.reply(f"❌ Menfess #{menfess_id} tidak ditemukan.")
            return

        if menfess['status'] != 'pending':
            await event.reply(f"❌ Menfess #{menfess_id} sudah di-{menfess['status']}.")
            return

        try:
            # Update database
            await self.db.reject_menfess(menfess_id, user.id, reason)

            # Send confirmation
            reject_text = f"❌ Menfess #{menfess_id} ditolak."
            if reason:
                reject_text += f"\n**Alasan:** {reason}"

            await event.reply(reject_text, parse_mode='markdown')

            # Optionally notify user about rejection
            try:
                user_notification = f"""
🚫 **Menfess Ditolak**

Menfess #{menfess_id} Anda telah ditolak oleh admin.

**Alasan:** {reason or 'Tidak sesuai dengan aturan'}

Anda dapat mengirim menfess baru dengan konten yang lebih sesuai.
                """
                await self.bot.send_message(menfess['user_id'], user_notification)
            except:
                pass  # User might have blocked the bot

            # Log action
            await self.db.log_user_action(
                user.id,
                'reject_menfess',
                {'menfess_id': menfess_id, 'reason': reason}
            )

        except Exception as e:
            await event.reply(f"❌ Error saat reject menfess: {str(e)}")
            print(f"Reject error: {e}")

    async def handle_ban_user(self, event, user_id: int, reason: str = None):
        """Handle user banning"""
        admin = await event.get_sender()
        if not self.is_admin(admin.id):
            await event.reply("❌ Anda tidak memiliki akses admin.")
            return

        try:
            # Ban user
            ban_reason = reason or "Melanggar aturan bot"
            await self.db.ban_user(user_id, ban_reason, admin.id)

            await event.reply(f"🚫 User {user_id} berhasil di-ban.\n**Alasan:** {ban_reason}")

            # Notify user about ban
            try:
                ban_notification = f"""
🚫 **Anda Telah Di-Ban**

Akun Anda telah di-ban dari VzoelFess Bot.

**Alasan:** {ban_reason}

Jika Anda merasa ini adalah kesalahan, hubungi admin.
                """
                await self.bot.send_message(user_id, ban_notification)
            except:
                pass  # User might have blocked the bot

        except Exception as e:
            await event.reply(f"❌ Error saat ban user: {str(e)}")
            print(f"Ban error: {e}")

    async def handle_unban_user(self, event, user_id: int):
        """Handle user unbanning"""
        admin = await event.get_sender()
        if not self.is_admin(admin.id):
            await event.reply("❌ Anda tidak memiliki akses admin.")
            return

        try:
            await self.db.sqlite.unban_user(user_id, admin.id)
            await event.reply(f"✅ User {user_id} berhasil di-unban.")

            # Notify user
            try:
                unban_notification = """
✅ **Ban Dicabut**

Akun Anda telah di-unban dari VzoelFess Bot.
Anda dapat kembali menggunakan bot dengan normal.

Harap patuhi aturan yang berlaku.
                """
                await self.bot.send_message(user_id, unban_notification)
            except:
                pass

        except Exception as e:
            await event.reply(f"❌ Error saat unban user: {str(e)}")

    async def handle_user_info(self, event, user_id: int):
        """Handle user info request"""
        admin = await event.get_sender()
        if not self.is_admin(admin.id):
            await event.reply("❌ Anda tidak memiliki akses admin.")
            return

        try:
            # Get user data
            user_data = await self.db.get_user(user_id)
            if not user_data:
                await event.reply(f"❌ User {user_id} tidak ditemukan.")
                return

            # Get user stats
            stats = await self.db.get_user_stats(user_id)

            # Calculate approval rate
            if stats['total_messages'] > 0:
                approval_rate = (stats['approved_messages'] / stats['total_messages']) * 100
            else:
                approval_rate = 0

            # Get recent activity if available
            recent_activity = ""
            if self.db.redis:
                activity_log = await self.db.redis.get_user_activity_log(user_id, limit=3)
                for activity in activity_log:
                    timestamp = datetime.fromisoformat(activity['timestamp']).strftime("%d/%m %H:%M")
                    recent_activity += f"• {activity['activity']} - {timestamp}\n"

            if not recent_activity:
                recent_activity = "Tidak ada data aktivitas terbaru"

            info_text = f"""
👤 **Info User #{user_id}**

**Profile:**
• Username: @{user_data.get('username', 'Tidak ada')}
• Nama: {user_data.get('first_name', '')} {user_data.get('last_name', '') or ''}
• Bergabung: {format_datetime(user_data['join_date'])}
• Status: {'🚫 Banned' if user_data['is_banned'] else '✅ Aktif'}

**Statistik:**
• Total menfess: {stats['total_messages']}
• Disetujui: {stats['approved_messages']}
• Ditolak: {stats['rejected_messages']}
• Rate persetujuan: {approval_rate:.1f}%
• Pesan hari ini: {stats['today_count']}

**Aktivitas Terbaru:**
{recent_activity}

**Admin Actions:**
• `/ban {user_id} [alasan]` - Ban user
• `/unban {user_id}` - Unban user
            """

            await event.reply(info_text, parse_mode='markdown')

        except Exception as e:
            await event.reply(f"❌ Error getting user info: {str(e)}")

    async def handle_pending(self, event):
        """Handle pending menfess list"""
        admin = await event.get_sender()
        if not self.is_admin(admin.id):
            await event.reply("❌ Anda tidak memiliki akses admin.")
            return

        try:
            pending_menfess = await self.db.get_pending_menfess()

            if not pending_menfess:
                await event.reply("✅ Tidak ada menfess yang menunggu review.")
                return

            pending_text = f"📋 **Menfess Pending ({len(pending_menfess)})**\n\n"

            for menfess in pending_menfess[:10]:  # Limit to 10 for readability
                hashtags = format_hashtags(menfess['hashtags']) if menfess['hashtags'] else "Tidak ada"
                created_time = format_datetime(menfess['created_at'])

                preview = menfess['message_text'][:100]
                if len(menfess['message_text']) > 100:
                    preview += "..."

                pending_text += f"""
**#{menfess['id']}** - @{menfess.get('username', 'NoUsername')}
📝 {preview}
🏷️ {hashtags}
📅 {created_time}

**Aksi:** `/approve {menfess['id']}` atau `/reject {menfess['id']} [alasan]`
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            if len(pending_menfess) > 10:
                pending_text += f"\n... dan {len(pending_menfess) - 10} menfess lainnya."

            await event.reply(pending_text, parse_mode='markdown')

        except Exception as e:
            await event.reply(f"❌ Error getting pending menfess: {str(e)}")

    async def handle_stats_admin(self, event):
        """Handle admin statistics"""
        admin = await event.get_sender()
        if not self.is_admin(admin.id):
            await event.reply("❌ Anda tidak memiliki akses admin.")
            return

        try:
            # Get system stats
            system_stats = await self.db.get_system_stats()

            # Get analytics if available
            analytics = await self.db.get_analytics_data(days=7)

            stats_text = """
📊 **Statistik Admin - 7 Hari Terakhir**

**Database Status:**
• SQLite: ✅ Aktif
"""

            if self.db.redis:
                stats_text += "• Redis: ✅ Aktif\n"
            else:
                stats_text += "• Redis: ❌ Tidak aktif\n"

            if self.db.mongodb:
                stats_text += "• MongoDB: ✅ Aktif\n"
            else:
                stats_text += "• MongoDB: ❌ Tidak aktif\n"

            if analytics:
                stats_text += f"""
**Aktivitas:**
• Total pesan: {analytics.get('total_messages', 0)}
• User unik: {analytics.get('unique_users', 0)}
• Hashtag populer: {len(analytics.get('top_hashtags', []))}

**Top 3 Hashtag:**
"""
                for i, hashtag in enumerate(analytics.get('top_hashtags', [])[:3], 1):
                    stats_text += f"{i}. {hashtag['_id']} ({hashtag['count']}x)\n"

            await event.reply(stats_text, parse_mode='markdown')

        except Exception as e:
            await event.reply(f"❌ Error getting admin stats: {str(e)}")

    def register_handlers(self):
        """Register all admin event handlers"""

        # Approve command
        @self.bot.on(events.NewMessage(pattern=r'/approve (\d+)'))
        async def approve_handler(event):
            menfess_id = int(event.pattern_match.group(1))
            await self.handle_approve(event, menfess_id)

        # Reject command
        @self.bot.on(events.NewMessage(pattern=r'/reject (\d+)(?:\s+(.+))?'))
        async def reject_handler(event):
            menfess_id = int(event.pattern_match.group(1))
            reason = event.pattern_match.group(2) if event.pattern_match.group(2) else None
            await self.handle_reject(event, menfess_id, reason)

        # Ban command
        @self.bot.on(events.NewMessage(pattern=r'/ban (\d+)(?:\s+(.+))?'))
        async def ban_handler(event):
            user_id = int(event.pattern_match.group(1))
            reason = event.pattern_match.group(2) if event.pattern_match.group(2) else None
            await self.handle_ban_user(event, user_id, reason)

        # Unban command
        @self.bot.on(events.NewMessage(pattern=r'/unban (\d+)'))
        async def unban_handler(event):
            user_id = int(event.pattern_match.group(1))
            await self.handle_unban_user(event, user_id)

        # User info command
        @self.bot.on(events.NewMessage(pattern=r'/user (\d+)'))
        async def user_info_handler(event):
            user_id = int(event.pattern_match.group(1))
            await self.handle_user_info(event, user_id)

        # Pending menfess command
        @self.bot.on(events.NewMessage(pattern='/pending'))
        async def pending_handler(event):
            await self.handle_pending(event)

        # Admin stats command
        @self.bot.on(events.NewMessage(pattern='/adminstats'))
        async def admin_stats_handler(event):
            await self.handle_stats_admin(event)

        # Callback query handler for inline buttons
        @self.bot.on(events.CallbackQuery)
        async def callback_handler(event):
            data = event.data.decode('utf-8')

            if data.startswith('approve_'):
                menfess_id = int(data.split('_')[1])
                await self.handle_approve(event, menfess_id)
                await event.edit(f"✅ Menfess #{menfess_id} disetujui!")

            elif data.startswith('reject_'):
                menfess_id = int(data.split('_')[1])
                await self.handle_reject(event, menfess_id)
                await event.edit(f"❌ Menfess #{menfess_id} ditolak!")

            elif data.startswith('user_info_'):
                user_id = int(data.split('_')[2])
                await self.handle_user_info(event, user_id)

            elif data.startswith('ban_user_'):
                user_id = int(data.split('_')[2])
                await self.handle_ban_user(event, user_id, "Banned via quick action")
                await event.edit(f"🚫 User {user_id} telah di-ban!")