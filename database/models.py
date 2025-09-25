"""
Database Models for VzoelFess Bot
SQLite database with async support using aiosqlite
"""

import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import json

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_messages INTEGER DEFAULT 0,
                    approved_messages INTEGER DEFAULT 0,
                    rejected_messages INTEGER DEFAULT 0
                )
            ''')

            # Menfess messages table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS menfess (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_text TEXT NOT NULL,
                    hashtags TEXT,  -- JSON array of hashtags
                    status TEXT DEFAULT 'pending',  -- pending, approved, rejected
                    admin_id INTEGER,
                    admin_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at DATETIME,
                    published_at DATETIME,
                    message_id INTEGER,  -- Telegram message ID in channel
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Rate limiting table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id INTEGER,
                    message_date DATE,
                    message_count INTEGER DEFAULT 0,
                    last_message_time DATETIME,
                    PRIMARY KEY (user_id, message_date),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Hashtags statistics table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS hashtag_stats (
                    hashtag TEXT PRIMARY KEY,
                    usage_count INTEGER DEFAULT 0,
                    first_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Admin logs table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    target_user_id INTEGER,
                    menfess_id INTEGER,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Bot settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            await db.commit()

    async def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT * FROM users WHERE user_id = ?
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'last_name': row[3],
                        'is_banned': bool(row[4]),
                        'ban_reason': row[5],
                        'join_date': row[6],
                        'total_messages': row[7],
                        'approved_messages': row[8],
                        'rejected_messages': row[9]
                    }
                return None

    async def ban_user(self, user_id: int, reason: str, admin_id: int):
        """Ban a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET is_banned = TRUE, ban_reason = ? WHERE user_id = ?
            ''', (reason, user_id))

            # Log admin action
            await db.execute('''
                INSERT INTO admin_logs (admin_id, action, target_user_id, details)
                VALUES (?, 'ban_user', ?, ?)
            ''', (admin_id, user_id, reason))

            await db.commit()

    async def unban_user(self, user_id: int, admin_id: int):
        """Unban a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET is_banned = FALSE, ban_reason = NULL WHERE user_id = ?
            ''', (user_id,))

            # Log admin action
            await db.execute('''
                INSERT INTO admin_logs (admin_id, action, target_user_id)
                VALUES (?, 'unban_user', ?)
            ''', (admin_id, user_id))

            await db.commit()

    async def add_menfess(self, user_id: int, message_text: str, hashtags: List[str]) -> int:
        """Add new menfess message"""
        async with aiosqlite.connect(self.db_path) as db:
            hashtags_json = json.dumps(hashtags) if hashtags else None

            cursor = await db.execute('''
                INSERT INTO menfess (user_id, message_text, hashtags)
                VALUES (?, ?, ?)
            ''', (user_id, message_text, hashtags_json))

            menfess_id = cursor.lastrowid

            # Update user message count
            await db.execute('''
                UPDATE users SET total_messages = total_messages + 1 WHERE user_id = ?
            ''', (user_id,))

            # Update hashtag statistics
            if hashtags:
                for hashtag in hashtags:
                    await db.execute('''
                        INSERT OR REPLACE INTO hashtag_stats (hashtag, usage_count, last_used)
                        VALUES (?, COALESCE((SELECT usage_count FROM hashtag_stats WHERE hashtag = ?), 0) + 1, CURRENT_TIMESTAMP)
                    ''', (hashtag, hashtag))

            await db.commit()
            return menfess_id

    async def get_menfess(self, menfess_id: int) -> Optional[Dict]:
        """Get menfess by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT m.*, u.username, u.first_name
                FROM menfess m
                LEFT JOIN users u ON m.user_id = u.user_id
                WHERE m.id = ?
            ''', (menfess_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    hashtags = json.loads(row[3]) if row[3] else []
                    return {
                        'id': row[0],
                        'user_id': row[1],
                        'message_text': row[2],
                        'hashtags': hashtags,
                        'status': row[4],
                        'admin_id': row[5],
                        'admin_reason': row[6],
                        'created_at': row[7],
                        'reviewed_at': row[8],
                        'published_at': row[9],
                        'message_id': row[10],
                        'username': row[11],
                        'first_name': row[12]
                    }
                return None

    async def approve_menfess(self, menfess_id: int, admin_id: int, message_id: int = None):
        """Approve menfess"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE menfess
                SET status = 'approved', admin_id = ?, reviewed_at = CURRENT_TIMESTAMP,
                    published_at = CURRENT_TIMESTAMP, message_id = ?
                WHERE id = ?
            ''', (admin_id, message_id, menfess_id))

            # Get user_id for updating stats
            async with db.execute('SELECT user_id FROM menfess WHERE id = ?', (menfess_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_id = row[0]
                    await db.execute('''
                        UPDATE users SET approved_messages = approved_messages + 1 WHERE user_id = ?
                    ''', (user_id,))

            # Log admin action
            await db.execute('''
                INSERT INTO admin_logs (admin_id, action, menfess_id)
                VALUES (?, 'approve_menfess', ?)
            ''', (admin_id, menfess_id))

            await db.commit()

    async def reject_menfess(self, menfess_id: int, admin_id: int, reason: str = None):
        """Reject menfess"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE menfess
                SET status = 'rejected', admin_id = ?, admin_reason = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (admin_id, reason, menfess_id))

            # Get user_id for updating stats
            async with db.execute('SELECT user_id FROM menfess WHERE id = ?', (menfess_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_id = row[0]
                    await db.execute('''
                        UPDATE users SET rejected_messages = rejected_messages + 1 WHERE user_id = ?
                    ''', (user_id,))

            # Log admin action
            await db.execute('''
                INSERT INTO admin_logs (admin_id, action, menfess_id, details)
                VALUES (?, 'reject_menfess', ?, ?)
            ''', (admin_id, menfess_id, reason))

            await db.commit()

    async def check_rate_limit(self, user_id: int, messages_per_hour: int, messages_per_day: int, cooldown_minutes: int) -> Tuple[bool, Dict]:
        """Check if user can send message based on rate limits"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now()
            today = now.date()
            hour_ago = now - timedelta(hours=1)

            # Check daily limit
            async with db.execute('''
                SELECT message_count FROM rate_limits
                WHERE user_id = ? AND message_date = ?
            ''', (user_id, today)) as cursor:
                row = await cursor.fetchone()
                daily_count = row[0] if row else 0

            # Check hourly limit
            async with db.execute('''
                SELECT COUNT(*) FROM menfess
                WHERE user_id = ? AND created_at > ?
            ''', (user_id, hour_ago)) as cursor:
                row = await cursor.fetchone()
                hourly_count = row[0] if row else 0

            # Check cooldown
            async with db.execute('''
                SELECT last_message_time FROM rate_limits
                WHERE user_id = ? ORDER BY message_date DESC LIMIT 1
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    last_message = datetime.fromisoformat(row[0])
                    time_diff = (now - last_message).total_seconds() / 60
                    if time_diff < cooldown_minutes:
                        return False, {
                            'reason': 'cooldown',
                            'remaining_minutes': cooldown_minutes - time_diff,
                            'daily_count': daily_count,
                            'hourly_count': hourly_count
                        }

            # Check limits
            if daily_count >= messages_per_day:
                return False, {
                    'reason': 'daily_limit',
                    'daily_count': daily_count,
                    'hourly_count': hourly_count
                }

            if hourly_count >= messages_per_hour:
                return False, {
                    'reason': 'hourly_limit',
                    'daily_count': daily_count,
                    'hourly_count': hourly_count
                }

            return True, {
                'daily_count': daily_count,
                'hourly_count': hourly_count,
                'remaining_today': messages_per_day - daily_count
            }

    async def update_rate_limit(self, user_id: int):
        """Update rate limit counters"""
        async with aiosqlite.connect(self.db_path) as db:
            today = datetime.now().date()
            now = datetime.now()

            await db.execute('''
                INSERT OR REPLACE INTO rate_limits (user_id, message_date, message_count, last_message_time)
                VALUES (?, ?, COALESCE((SELECT message_count FROM rate_limits WHERE user_id = ? AND message_date = ?), 0) + 1, ?)
            ''', (user_id, today, user_id, today, now))

            await db.commit()

    async def get_pending_menfess(self) -> List[Dict]:
        """Get all pending menfess for admin review"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT m.*, u.username, u.first_name
                FROM menfess m
                LEFT JOIN users u ON m.user_id = u.user_id
                WHERE m.status = 'pending'
                ORDER BY m.created_at ASC
            ''') as cursor:
                rows = await cursor.fetchall()
                results = []
                for row in rows:
                    hashtags = json.loads(row[3]) if row[3] else []
                    results.append({
                        'id': row[0],
                        'user_id': row[1],
                        'message_text': row[2],
                        'hashtags': hashtags,
                        'status': row[4],
                        'created_at': row[7],
                        'username': row[11],
                        'first_name': row[12]
                    })
                return results

    async def get_hashtag_stats(self, limit: int = 20) -> List[Dict]:
        """Get hashtag usage statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT hashtag, usage_count, first_used, last_used
                FROM hashtag_stats
                ORDER BY usage_count DESC
                LIMIT ?
            ''', (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [{
                    'hashtag': row[0],
                    'usage_count': row[1],
                    'first_used': row[2],
                    'last_used': row[3]
                } for row in rows]

    async def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        user = await self.get_user(user_id)
        if not user:
            return None

        async with aiosqlite.connect(self.db_path) as db:
            # Get rate limit info
            today = datetime.now().date()
            async with db.execute('''
                SELECT message_count FROM rate_limits
                WHERE user_id = ? AND message_date = ?
            ''', (user_id, today)) as cursor:
                row = await cursor.fetchone()
                daily_count = row[0] if row else 0

            return {
                'total_messages': user['total_messages'],
                'approved_messages': user['approved_messages'],
                'rejected_messages': user['rejected_messages'],
                'today_count': daily_count,
                'join_date': user['join_date'],
                'is_banned': user['is_banned'],
                'ban_reason': user['ban_reason']
            }