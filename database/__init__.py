"""
Database Manager for VzoelFess Bot
Multi-database support: SQLite (primary), Redis (cache), MongoDB (logging)
"""

import os
from typing import Optional
from .models import Database
from .redis_manager import RedisManager
from .mongodb_manager import MongoDBManager

class DatabaseManager:
    def __init__(self, sqlite_path: str, redis_config: dict = None, mongodb_config: dict = None):
        # Primary database (SQLite)
        self.sqlite = Database(sqlite_path)

        # Cache database (Redis) - Optional
        self.redis = None
        if redis_config and redis_config.get('host'):
            try:
                self.redis = RedisManager(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 0),
                    password=redis_config.get('password')
                )
            except Exception as e:
                print(f"⚠️  Redis setup skipped: {e}")

        # Logging database (MongoDB) - Optional
        self.mongodb = None
        if mongodb_config and mongodb_config.get('uri'):
            try:
                self.mongodb = MongoDBManager(
                    uri=mongodb_config.get('uri', 'mongodb://localhost:27017'),
                    db_name=mongodb_config.get('db_name', 'vzoelfess')
                )
            except Exception as e:
                print(f"⚠️  MongoDB setup skipped: {e}")

    async def initialize(self):
        """Initialize all database connections"""
        # Initialize SQLite
        os.makedirs(os.path.dirname(self.sqlite.db_path), exist_ok=True)
        await self.sqlite.initialize()
        print(f"✅ SQLite database initialized: {self.sqlite.db_path}")

        # Initialize Redis if configured
        if self.redis:
            try:
                await self.redis.connect()
            except Exception as e:
                print(f"⚠️  Redis connection failed, continuing without cache: {e}")
                self.redis = None

        # Initialize MongoDB if configured
        if self.mongodb:
            try:
                await self.mongodb.connect()
            except Exception as e:
                print(f"⚠️  MongoDB connection failed, continuing without logging: {e}")
                self.mongodb = None

    async def close(self):
        """Close all database connections"""
        if self.redis:
            await self.redis.disconnect()

        if self.mongodb:
            await self.mongodb.disconnect()

    # Primary operations (SQLite)
    async def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add user to primary database"""
        return await self.sqlite.add_user(user_id, username, first_name, last_name)

    async def get_user(self, user_id: int):
        """Get user from primary database with Redis caching"""
        # Try cache first
        if self.redis:
            cached = await self.redis.get_user_stats_cache(user_id)
            if cached:
                return cached

        # Get from SQLite
        user = await self.sqlite.get_user(user_id)

        # Cache the result
        if self.redis and user:
            await self.redis.cache_user_stats(user_id, user, expire=300)

        return user

    async def add_menfess(self, user_id: int, message_text: str, hashtags: list):
        """Add menfess to primary database and log to MongoDB"""
        menfess_id = await self.sqlite.add_menfess(user_id, message_text, hashtags)

        # Log to MongoDB
        if self.mongodb:
            await self.mongodb.log_message(
                menfess_id=menfess_id,
                user_id=user_id,
                message_text=message_text,
                hashtags=hashtags,
                status='pending'
            )

        return menfess_id

    async def approve_menfess(self, menfess_id: int, admin_id: int, message_id: int = None):
        """Approve menfess and log action"""
        await self.sqlite.approve_menfess(menfess_id, admin_id, message_id)

        # Log to MongoDB
        if self.mongodb:
            menfess = await self.sqlite.get_menfess(menfess_id)
            if menfess:
                await self.mongodb.log_message(
                    menfess_id=menfess_id,
                    user_id=menfess['user_id'],
                    message_text=menfess['message_text'],
                    hashtags=menfess['hashtags'],
                    status='approved',
                    admin_id=admin_id
                )

                await self.mongodb.log_admin_action(
                    admin_id=admin_id,
                    action='approve_menfess',
                    menfess_id=menfess_id,
                    target_user_id=menfess['user_id']
                )

    async def reject_menfess(self, menfess_id: int, admin_id: int, reason: str = None):
        """Reject menfess and log action"""
        await self.sqlite.reject_menfess(menfess_id, admin_id, reason)

        # Log to MongoDB
        if self.mongodb:
            menfess = await self.sqlite.get_menfess(menfess_id)
            if menfess:
                await self.mongodb.log_message(
                    menfess_id=menfess_id,
                    user_id=menfess['user_id'],
                    message_text=menfess['message_text'],
                    hashtags=menfess['hashtags'],
                    status='rejected',
                    admin_id=admin_id,
                    admin_reason=reason
                )

                await self.mongodb.log_admin_action(
                    admin_id=admin_id,
                    action='reject_menfess',
                    menfess_id=menfess_id,
                    target_user_id=menfess['user_id'],
                    details={'reason': reason}
                )

    async def ban_user(self, user_id: int, reason: str, admin_id: int):
        """Ban user and log action"""
        await self.sqlite.ban_user(user_id, reason, admin_id)

        # Log to MongoDB
        if self.mongodb:
            await self.mongodb.log_admin_action(
                admin_id=admin_id,
                action='ban_user',
                target_user_id=user_id,
                details={'reason': reason}
            )

            await self.mongodb.log_user_action(
                user_id=user_id,
                action='user_banned',
                details={'reason': reason, 'admin_id': admin_id}
            )

    async def check_rate_limit(self, user_id: int, messages_per_hour: int, messages_per_day: int, cooldown_minutes: int):
        """Check rate limit with Redis and SQLite fallback"""
        # Use Redis for real-time rate limiting if available
        if self.redis:
            # Check hourly rate limit
            hourly_status = await self.redis.get_rate_limit_status(
                user_id, window_seconds=3600, max_requests=messages_per_hour
            )

            if not hourly_status['allowed']:
                return False, {
                    'reason': 'hourly_limit',
                    'hourly_count': hourly_status['current_count'],
                    'reset_in': hourly_status['reset_in']
                }

            # Check daily rate limit using SQLite
            can_send, data = await self.sqlite.check_rate_limit(
                user_id, messages_per_hour, messages_per_day, cooldown_minutes
            )

            if not can_send:
                return False, data

            # Check cooldown
            cooldown_status = await self.redis.check_cooldown(user_id)
            if cooldown_status['active']:
                return False, {
                    'reason': 'cooldown',
                    'remaining_minutes': cooldown_status['remaining_minutes']
                }

            return True, data
        else:
            # Fallback to SQLite only
            return await self.sqlite.check_rate_limit(
                user_id, messages_per_hour, messages_per_day, cooldown_minutes
            )

    async def update_rate_limit(self, user_id: int, cooldown_minutes: int = 10):
        """Update rate limit counters"""
        # Update SQLite
        await self.sqlite.update_rate_limit(user_id)

        # Update Redis rate limiting
        if self.redis:
            await self.redis.set_rate_limit(user_id, window_seconds=3600, max_requests=5)
            await self.redis.set_cooldown(user_id, cooldown_minutes)

    async def get_pending_menfess(self):
        """Get pending menfess with caching"""
        # Try cache first
        if self.redis:
            cached = await self.redis.get_pending_menfess_cache()
            if cached:
                return cached

        # Get from SQLite
        pending = await self.sqlite.get_pending_menfess()

        # Cache the result
        if self.redis:
            await self.redis.cache_pending_menfess(pending, expire=120)

        return pending

    async def get_hashtag_stats(self, limit: int = 20):
        """Get hashtag statistics with caching"""
        # Try cache first
        if self.redis:
            cached = await self.redis.get_hashtag_stats_cache()
            if cached:
                return cached[:limit]

        # Get from SQLite
        stats = await self.sqlite.get_hashtag_stats(limit)

        # Cache the result
        if self.redis:
            await self.redis.cache_hashtag_stats(stats, expire=600)

        return stats

    async def get_user_stats(self, user_id: int):
        """Get user statistics"""
        return await self.sqlite.get_user_stats(user_id)

    async def log_user_action(self, user_id: int, action: str, details: dict = None):
        """Log user action to MongoDB and Redis"""
        if self.mongodb:
            await self.mongodb.log_user_action(user_id, action, details)

        if self.redis:
            await self.redis.log_user_activity(user_id, action, details)

    async def get_analytics_data(self, days: int = 7):
        """Get analytics data from MongoDB"""
        if self.mongodb:
            return await self.mongodb.get_analytics_data(days)
        return {}

    async def backup_user_data(self, user_id: int):
        """Backup user data from MongoDB"""
        if self.mongodb:
            return await self.mongodb.backup_user_data(user_id)
        return {}

    async def delete_user_data(self, user_id: int):
        """Delete user data (GDPR compliance)"""
        success = True

        # Delete from MongoDB
        if self.mongodb:
            success &= await self.mongodb.delete_user_data(user_id)

        # Clear Redis cache
        if self.redis:
            await self.redis.clear_session_data(user_id)

        return success

    # Maintenance and monitoring
    async def set_maintenance_mode(self, enabled: bool, message: str = None):
        """Set maintenance mode"""
        if self.redis:
            await self.redis.set_maintenance_mode(enabled, message)

    async def get_maintenance_mode(self):
        """Get maintenance mode status"""
        if self.redis:
            return await self.redis.get_maintenance_mode()
        return None

    async def get_system_stats(self):
        """Get comprehensive system statistics"""
        stats = {}

        if self.mongodb:
            stats['mongodb'] = await self.mongodb.get_system_stats()

        # Add SQLite stats (basic)
        try:
            import os
            if os.path.exists(self.sqlite.db_path):
                stats['sqlite'] = {
                    'file_size': os.path.getsize(self.sqlite.db_path),
                    'path': self.sqlite.db_path
                }
        except:
            pass

        return stats