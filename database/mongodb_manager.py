"""
MongoDB Manager for VzoelFess Bot
Handle permanent logging, analytics, and backup data
"""

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
try:
    import ujson as json
except ImportError:
    import json
from bson import ObjectId

class MongoDBManager:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.uri)
            self.db = self.client[self.db_name]
            # Test connection
            await self.client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {self.db_name}")

            # Create indexes for better performance
            await self.create_indexes()
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            self.client = None
            self.db = None

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()

    async def create_indexes(self):
        """Create database indexes for better performance"""
        if not self.db:
            return

        try:
            # User logs indexes
            await self.db.user_logs.create_index([("user_id", 1), ("timestamp", -1)])
            await self.db.user_logs.create_index([("timestamp", -1)])

            # Message logs indexes
            await self.db.message_logs.create_index([("menfess_id", 1)])
            await self.db.message_logs.create_index([("user_id", 1), ("timestamp", -1)])
            await self.db.message_logs.create_index([("status", 1)])

            # Admin logs indexes
            await self.db.admin_logs.create_index([("admin_id", 1), ("timestamp", -1)])
            await self.db.admin_logs.create_index([("action", 1)])

            # Analytics indexes
            await self.db.daily_stats.create_index([("date", 1)])
            await self.db.hashtag_analytics.create_index([("hashtag", 1)])

            print("✅ MongoDB indexes created")
        except Exception as e:
            print(f"❌ Error creating MongoDB indexes: {e}")

    async def log_user_action(self, user_id: int, action: str, details: Dict = None, ip_address: str = None):
        """Log user action to MongoDB"""
        if not self.db:
            return

        try:
            log_entry = {
                'user_id': user_id,
                'action': action,
                'details': details or {},
                'ip_address': ip_address,
                'timestamp': datetime.utcnow(),
                'date': datetime.utcnow().date()
            }

            await self.db.user_logs.insert_one(log_entry)
        except Exception as e:
            print(f"MongoDB user log error: {e}")

    async def log_message(self, menfess_id: int, user_id: int, message_text: str, hashtags: List[str],
                         status: str, admin_id: int = None, admin_reason: str = None):
        """Log message to MongoDB"""
        if not self.db:
            return

        try:
            message_log = {
                'menfess_id': menfess_id,
                'user_id': user_id,
                'message_text': message_text,
                'hashtags': hashtags,
                'status': status,
                'admin_id': admin_id,
                'admin_reason': admin_reason,
                'timestamp': datetime.utcnow(),
                'date': datetime.utcnow().date(),
                'message_length': len(message_text),
                'hashtag_count': len(hashtags) if hashtags else 0
            }

            await self.db.message_logs.insert_one(message_log)
        except Exception as e:
            print(f"MongoDB message log error: {e}")

    async def log_admin_action(self, admin_id: int, action: str, target_user_id: int = None,
                              menfess_id: int = None, details: Dict = None):
        """Log admin action to MongoDB"""
        if not self.db:
            return

        try:
            admin_log = {
                'admin_id': admin_id,
                'action': action,
                'target_user_id': target_user_id,
                'menfess_id': menfess_id,
                'details': details or {},
                'timestamp': datetime.utcnow(),
                'date': datetime.utcnow().date()
            }

            await self.db.admin_logs.insert_one(admin_log)
        except Exception as e:
            print(f"MongoDB admin log error: {e}")

    async def store_daily_stats(self, date: datetime, stats: Dict):
        """Store daily statistics"""
        if not self.db:
            return

        try:
            daily_stats = {
                'date': date.date(),
                'timestamp': datetime.utcnow(),
                **stats
            }

            await self.db.daily_stats.replace_one(
                {'date': date.date()},
                daily_stats,
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB daily stats error: {e}")

    async def get_user_activity_history(self, user_id: int, days: int = 30, limit: int = 100) -> List[Dict]:
        """Get user activity history"""
        if not self.db:
            return []

        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            cursor = self.db.user_logs.find(
                {
                    'user_id': user_id,
                    'timestamp': {'$gte': start_date}
                }
            ).sort('timestamp', -1).limit(limit)

            activities = []
            async for doc in cursor:
                doc['_id'] = str(doc['_id'])
                activities.append(doc)

            return activities
        except Exception as e:
            print(f"MongoDB user activity error: {e}")
            return []

    async def get_message_history(self, user_id: int = None, status: str = None, days: int = 30, limit: int = 50) -> List[Dict]:
        """Get message history with filters"""
        if not self.db:
            return []

        try:
            query = {}

            if user_id:
                query['user_id'] = user_id

            if status:
                query['status'] = status

            if days:
                start_date = datetime.utcnow() - timedelta(days=days)
                query['timestamp'] = {'$gte': start_date}

            cursor = self.db.message_logs.find(query).sort('timestamp', -1).limit(limit)

            messages = []
            async for doc in cursor:
                doc['_id'] = str(doc['_id'])
                messages.append(doc)

            return messages
        except Exception as e:
            print(f"MongoDB message history error: {e}")
            return []

    async def get_admin_activity(self, admin_id: int = None, days: int = 7, limit: int = 100) -> List[Dict]:
        """Get admin activity logs"""
        if not self.db:
            return []

        try:
            query = {}

            if admin_id:
                query['admin_id'] = admin_id

            if days:
                start_date = datetime.utcnow() - timedelta(days=days)
                query['timestamp'] = {'$gte': start_date}

            cursor = self.db.admin_logs.find(query).sort('timestamp', -1).limit(limit)

            activities = []
            async for doc in cursor:
                doc['_id'] = str(doc['_id'])
                activities.append(doc)

            return activities
        except Exception as e:
            print(f"MongoDB admin activity error: {e}")
            return []

    async def get_analytics_data(self, days: int = 7) -> Dict:
        """Get analytics data for specified days"""
        if not self.db:
            return {}

        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Daily message counts
            daily_messages = await self.db.message_logs.aggregate([
                {'$match': {'timestamp': {'$gte': start_date}}},
                {'$group': {
                    '_id': {
                        '$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}
                    },
                    'total': {'$sum': 1},
                    'approved': {'$sum': {'$cond': [{'$eq': ['$status', 'approved']}, 1, 0]}},
                    'rejected': {'$sum': {'$cond': [{'$eq': ['$status', 'rejected']}, 1, 0]}},
                    'pending': {'$sum': {'$cond': [{'$eq': ['$status', 'pending']}, 1, 0]}}
                }},
                {'$sort': {'_id': 1}}
            ]).to_list(None)

            # Top hashtags
            top_hashtags = await self.db.message_logs.aggregate([
                {'$match': {'timestamp': {'$gte': start_date}, 'hashtags': {'$ne': []}}},
                {'$unwind': '$hashtags'},
                {'$group': {'_id': '$hashtags', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 20}
            ]).to_list(None)

            # User activity
            user_stats = await self.db.message_logs.aggregate([
                {'$match': {'timestamp': {'$gte': start_date}}},
                {'$group': {
                    '_id': None,
                    'unique_users': {'$addToSet': '$user_id'},
                    'total_messages': {'$sum': 1}
                }}
            ]).to_list(None)

            unique_users = len(user_stats[0]['unique_users']) if user_stats else 0
            total_messages = user_stats[0]['total_messages'] if user_stats else 0

            # Admin activity
            admin_actions = await self.db.admin_logs.aggregate([
                {'$match': {'timestamp': {'$gte': start_date}}},
                {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]).to_list(None)

            return {
                'period_days': days,
                'daily_messages': daily_messages,
                'top_hashtags': top_hashtags,
                'unique_users': unique_users,
                'total_messages': total_messages,
                'admin_actions': admin_actions,
                'generated_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"MongoDB analytics error: {e}")
            return {}

    async def backup_user_data(self, user_id: int) -> Dict:
        """Backup all user data"""
        if not self.db:
            return {}

        try:
            # Get user logs
            user_logs = await self.db.user_logs.find({'user_id': user_id}).to_list(None)

            # Get user messages
            user_messages = await self.db.message_logs.find({'user_id': user_id}).to_list(None)

            # Convert ObjectId to string
            for log in user_logs:
                log['_id'] = str(log['_id'])

            for msg in user_messages:
                msg['_id'] = str(msg['_id'])

            backup_data = {
                'user_id': user_id,
                'backup_date': datetime.utcnow().isoformat(),
                'user_logs': user_logs,
                'user_messages': user_messages,
                'total_logs': len(user_logs),
                'total_messages': len(user_messages)
            }

            # Store backup
            await self.db.user_backups.insert_one(backup_data.copy())

            return backup_data

        except Exception as e:
            print(f"MongoDB backup error: {e}")
            return {}

    async def delete_user_data(self, user_id: int) -> bool:
        """Delete all user data (GDPR compliance)"""
        if not self.db:
            return False

        try:
            # Create backup before deletion
            await self.backup_user_data(user_id)

            # Delete user logs
            await self.db.user_logs.delete_many({'user_id': user_id})

            # Anonymize message logs (keep for statistics but remove user info)
            await self.db.message_logs.update_many(
                {'user_id': user_id},
                {'$set': {'user_id': 0, 'message_text': '[DELETED]'}}
            )

            # Log deletion
            await self.log_admin_action(
                admin_id=0,  # System action
                action='user_data_deletion',
                target_user_id=user_id,
                details={'gdpr_deletion': True}
            )

            return True

        except Exception as e:
            print(f"MongoDB user data deletion error: {e}")
            return False

    async def get_system_stats(self) -> Dict:
        """Get system statistics"""
        if not self.db:
            return {}

        try:
            # Collection stats
            collections = ['user_logs', 'message_logs', 'admin_logs', 'daily_stats']
            collection_stats = {}

            for collection in collections:
                count = await self.db[collection].count_documents({})
                collection_stats[collection] = count

            # Recent activity (last 24 hours)
            last_24h = datetime.utcnow() - timedelta(hours=24)
            recent_messages = await self.db.message_logs.count_documents(
                {'timestamp': {'$gte': last_24h}}
            )

            recent_users = len(await self.db.user_logs.distinct(
                'user_id', {'timestamp': {'$gte': last_24h}}
            ))

            return {
                'collection_stats': collection_stats,
                'recent_activity': {
                    'messages_24h': recent_messages,
                    'active_users_24h': recent_users
                },
                'database_name': self.db_name,
                'generated_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"MongoDB system stats error: {e}")
            return {}