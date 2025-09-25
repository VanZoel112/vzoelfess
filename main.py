"""
VzoelFess Bot - Anonymous Confession Telegram Bot
Main entry point with Telethon
"""

import asyncio
import os
import logging
from telethon import TelegramClient
from datetime import datetime

# Import configuration
from config.settings import (
    API_ID, API_HASH, BOT_TOKEN,
    DATABASE_PATH, LOG_FILE, LOG_LEVEL,
    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD,
    MONGODB_URI, MONGODB_DB
)

# Import database manager
from database import DatabaseManager

# Import handlers
from handlers.user_handler import UserHandler
from handlers.admin_handler import AdminHandler

class VzoelFessBot:
    def __init__(self):
        self.bot = None
        self.db = None
        self.user_handler = None
        self.admin_handler = None

    async def initialize(self):
        """Initialize bot and database"""
        print("🤖 Initializing VzoelFess Bot...")

        # Setup logging
        self.setup_logging()

        # Initialize Telegram client
        self.bot = TelegramClient('vzoelfess_bot', API_ID, API_HASH)
        await self.bot.start(bot_token=BOT_TOKEN)

        bot_me = await self.bot.get_me()
        print(f"✅ Bot connected as @{bot_me.username}")

        # Initialize database with optional Redis and MongoDB
        redis_config = None
        if REDIS_HOST:
            redis_config = {
                'host': REDIS_HOST,
                'port': REDIS_PORT,
                'db': REDIS_DB,
                'password': REDIS_PASSWORD
            }

        mongodb_config = None
        if MONGODB_URI:
            mongodb_config = {
                'uri': MONGODB_URI,
                'db_name': MONGODB_DB
            }

        self.db = DatabaseManager(
            sqlite_path=DATABASE_PATH,
            redis_config=redis_config,
            mongodb_config=mongodb_config
        )

        await self.db.initialize()

        # Initialize handlers
        self.user_handler = UserHandler(self.bot, self.db)
        self.admin_handler = AdminHandler(self.bot, self.db)

        # Register event handlers
        self.user_handler.register_handlers()
        self.admin_handler.register_handlers()

        print("✅ Bot initialization complete!")

    def setup_logging(self):
        """Setup logging configuration"""
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )

        # Reduce telethon logging
        logging.getLogger('telethon').setLevel(logging.WARNING)

    async def start(self):
        """Start the bot"""
        try:
            await self.initialize()

            print("🚀 VzoelFess Bot is running...")
            print("Press Ctrl+C to stop")

            await self.bot.run_until_disconnected()

        except Exception as e:
            print(f"❌ Bot error: {e}")
            logging.error(f"Bot error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        print("🧹 Cleaning up...")

        if self.db:
            await self.db.close()

        if self.bot:
            await self.bot.disconnect()

        print("👋 Bot stopped")

async def main():
    """Main entry point"""
    # Check required environment variables
    if not all([API_ID, API_HASH, BOT_TOKEN]):
        print("❌ Missing required environment variables!")
        print("Please check API_ID, API_HASH, and BOT_TOKEN in your .env file")
        return

    bot = VzoelFessBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Run the bot
    asyncio.run(main())