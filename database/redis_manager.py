"""
Redis Manager for VzoelFess Bot
Handle caching, rate limiting, and temporary data
"""

import redis.asyncio as redis
try:
    import ujson as json
except ImportError:
    import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import asyncio

class RedisManager:
    def __init__(self, host: str, port: int, db: int = 0, password: str = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis = None

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password if self.password else None,
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            print(f"✅ Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            self.redis = None

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()

    async def set_cache(self, key: str, value: Any, expire: int = 3600):
        """Set cache with expiration"""
        if not self.redis:
            return False

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            await self.redis.set(key, value, ex=expire)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except:
                    return value
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None

    async def delete_cache(self, key: str):
        """Delete cache key"""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False

    async def set_rate_limit(self, user_id: int, window_seconds: int = 3600, max_requests: int = 5):
        """Set rate limit using sliding window"""
        if not self.redis:
            return False

        try:
            key = f"rate_limit:{user_id}"
            current_time = datetime.now().timestamp()

            # Remove old entries outside the window
            await self.redis.zremrangebyscore(key, 0, current_time - window_seconds)

            # Count current requests in the window
            current_count = await self.redis.zcard(key)

            if current_count >= max_requests:
                return False

            # Add current request
            await self.redis.zadd(key, {str(current_time): current_time})

            # Set expiration for the key
            await self.redis.expire(key, window_seconds)

            return True
        except Exception as e:
            print(f"Redis rate limit error: {e}")
            return False

    async def get_rate_limit_status(self, user_id: int, window_seconds: int = 3600, max_requests: int = 5) -> Dict:
        """Get rate limit status"""
        if not self.redis:
            return {'allowed': True, 'remaining': max_requests, 'reset_in': 0}

        try:
            key = f"rate_limit:{user_id}"
            current_time = datetime.now().timestamp()

            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, current_time - window_seconds)

            # Get current count
            current_count = await self.redis.zcard(key)

            # Get oldest entry to calculate reset time
            oldest_entries = await self.redis.zrange(key, 0, 0, withscores=True)
            reset_in = 0
            if oldest_entries:
                oldest_time = oldest_entries[0][1]
                reset_in = max(0, int(window_seconds - (current_time - oldest_time)))

            return {
                'allowed': current_count < max_requests,
                'remaining': max(0, max_requests - current_count),
                'current_count': current_count,
                'reset_in': reset_in
            }
        except Exception as e:
            print(f"Redis rate limit status error: {e}")
            return {'allowed': True, 'remaining': max_requests, 'reset_in': 0}

    async def set_cooldown(self, user_id: int, cooldown_minutes: int):
        """Set user cooldown"""
        if not self.redis:
            return False

        try:
            key = f"cooldown:{user_id}"
            expire_seconds = cooldown_minutes * 60
            await self.redis.set(key, "1", ex=expire_seconds)
            return True
        except Exception as e:
            print(f"Redis cooldown error: {e}")
            return False

    async def check_cooldown(self, user_id: int) -> Dict:
        """Check user cooldown status"""
        if not self.redis:
            return {'active': False, 'remaining': 0}

        try:
            key = f"cooldown:{user_id}"
            ttl = await self.redis.ttl(key)

            if ttl > 0:
                return {
                    'active': True,
                    'remaining_seconds': ttl,
                    'remaining_minutes': round(ttl / 60, 1)
                }
            return {'active': False, 'remaining': 0}
        except Exception as e:
            print(f"Redis cooldown check error: {e}")
            return {'active': False, 'remaining': 0}

    async def cache_user_stats(self, user_id: int, stats: Dict, expire: int = 300):
        """Cache user statistics"""
        key = f"user_stats:{user_id}"
        await self.set_cache(key, stats, expire)

    async def get_user_stats_cache(self, user_id: int) -> Optional[Dict]:
        """Get cached user statistics"""
        key = f"user_stats:{user_id}"
        return await self.get_cache(key)

    async def cache_pending_menfess(self, menfess_list: List[Dict], expire: int = 120):
        """Cache pending menfess list for admin"""
        key = "pending_menfess"
        await self.set_cache(key, menfess_list, expire)

    async def get_pending_menfess_cache(self) -> Optional[List[Dict]]:
        """Get cached pending menfess list"""
        key = "pending_menfess"
        return await self.get_cache(key)

    async def cache_hashtag_stats(self, stats: List[Dict], expire: int = 600):
        """Cache hashtag statistics"""
        key = "hashtag_stats"
        await self.set_cache(key, stats, expire)

    async def get_hashtag_stats_cache(self) -> Optional[List[Dict]]:
        """Get cached hashtag statistics"""
        key = "hashtag_stats"
        return await self.get_cache(key)

    async def set_session_data(self, user_id: int, session_data: Dict, expire: int = 1800):
        """Set user session data"""
        key = f"session:{user_id}"
        await self.set_cache(key, session_data, expire)

    async def get_session_data(self, user_id: int) -> Optional[Dict]:
        """Get user session data"""
        key = f"session:{user_id}"
        return await self.get_cache(key)

    async def clear_session_data(self, user_id: int):
        """Clear user session data"""
        key = f"session:{user_id}"
        await self.delete_cache(key)

    async def increment_counter(self, key: str, expire: int = None) -> int:
        """Increment counter and return new value"""
        if not self.redis:
            return 0

        try:
            new_value = await self.redis.incr(key)
            if expire and new_value == 1:  # Set expiration only on first increment
                await self.redis.expire(key, expire)
            return new_value
        except Exception as e:
            print(f"Redis increment error: {e}")
            return 0

    async def get_counter(self, key: str) -> int:
        """Get counter value"""
        if not self.redis:
            return 0

        try:
            value = await self.redis.get(key)
            return int(value) if value else 0
        except Exception as e:
            print(f"Redis get counter error: {e}")
            return 0

    async def set_maintenance_mode(self, enabled: bool, message: str = None):
        """Set maintenance mode"""
        key = "maintenance_mode"
        data = {
            'enabled': enabled,
            'message': message or "Bot sedang dalam maintenance",
            'timestamp': datetime.now().isoformat()
        }
        await self.set_cache(key, data, expire=86400)  # 24 hours

    async def get_maintenance_mode(self) -> Optional[Dict]:
        """Get maintenance mode status"""
        key = "maintenance_mode"
        return await self.get_cache(key)

    async def log_user_activity(self, user_id: int, activity: str, details: Dict = None):
        """Log user activity to Redis"""
        if not self.redis:
            return

        try:
            key = f"activity_log:{user_id}"
            activity_data = {
                'activity': activity,
                'timestamp': datetime.now().isoformat(),
                'details': details or {}
            }

            # Add to list (keep last 100 activities)
            await self.redis.lpush(key, json.dumps(activity_data))
            await self.redis.ltrim(key, 0, 99)
            await self.redis.expire(key, 604800)  # 7 days
        except Exception as e:
            print(f"Redis activity log error: {e}")

    async def get_user_activity_log(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user activity log"""
        if not self.redis:
            return []

        try:
            key = f"activity_log:{user_id}"
            activities = await self.redis.lrange(key, 0, limit - 1)

            result = []
            for activity_json in activities:
                try:
                    result.append(json.loads(activity_json))
                except:
                    continue
            return result
        except Exception as e:
            print(f"Redis activity log get error: {e}")
            return []