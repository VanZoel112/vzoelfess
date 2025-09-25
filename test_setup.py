#!/usr/bin/env python3
"""
VzoelFess Bot Setup Test
Test database connections and basic functionality
"""

import asyncio
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from utils.helpers import extract_hashtags, validate_message, format_hashtags
from config.settings import DATABASE_PATH, REDIS_HOST, REDIS_PORT, MONGODB_URI

async def test_database_setup():
    """Test database initialization and basic operations"""
    print("🔍 Testing Database Setup...")

    # Setup database manager
    redis_config = None
    if REDIS_HOST:
        redis_config = {
            'host': REDIS_HOST,
            'port': REDIS_PORT,
            'db': 0,
            'password': None
        }

    mongodb_config = None
    if MONGODB_URI:
        mongodb_config = {
            'uri': MONGODB_URI,
            'db_name': 'vzoelfess_test'
        }

    db = DatabaseManager(
        sqlite_path="data/test_vzoelfess.db",
        redis_config=redis_config,
        mongodb_config=mongodb_config
    )

    try:
        # Initialize databases
        await db.initialize()
        print("✅ Database initialization successful")

        # Test user operations
        print("\n📝 Testing user operations...")
        await db.add_user(12345, "testuser", "Test", "User")

        user = await db.get_user(12345)
        assert user is not None
        print(f"✅ User created: {user['username']}")

        # Test menfess operations
        print("\n💌 Testing menfess operations...")
        test_message = "Test message untuk menfess #test #example #demo"
        hashtags = extract_hashtags(test_message)

        menfess_id = await db.add_menfess(12345, test_message, hashtags)
        print(f"✅ Menfess created with ID: {menfess_id}")

        menfess = await db.sqlite.get_menfess(menfess_id)
        assert menfess is not None
        print(f"✅ Menfess retrieved: {len(menfess['message_text'])} chars")

        # Test rate limiting
        print("\n⏰ Testing rate limiting...")
        can_send, data = await db.check_rate_limit(12345, 5, 20, 10)
        print(f"✅ Rate limit check: {can_send} - {data}")

        # Test hashtag stats
        print("\n🏷️ Testing hashtag statistics...")
        hashtag_stats = await db.get_hashtag_stats(10)
        print(f"✅ Hashtag stats: {len(hashtag_stats)} hashtags found")

        # Test pending menfess
        print("\n📋 Testing pending menfess...")
        pending = await db.get_pending_menfess()
        print(f"✅ Pending menfess: {len(pending)} items")

        print(f"\n🎉 All database tests passed!")

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    finally:
        await db.close()

    return True

def test_utilities():
    """Test utility functions"""
    print("\n🛠️ Testing Utility Functions...")

    # Test hashtag extraction
    test_messages = [
        "Hello world #test #example",
        "No hashtags here",
        "#single",
        "Multiple #hash #tags #here #yes #no",
        "Mixed content #test with text #example and more"
    ]

    for msg in test_messages:
        hashtags = extract_hashtags(msg)
        print(f"'{msg[:30]}...' → {len(hashtags)} hashtags: {hashtags}")

    # Test message validation
    print("\n✅ Testing message validation...")
    test_validations = [
        ("Valid message with content", True),
        ("", False),  # Empty
        ("Short", False),  # Too short
        ("A" * 5000, False),  # Too long
        ("Valid length message here for testing purposes", True)
    ]

    for msg, expected in test_validations:
        is_valid, error = validate_message(msg)
        status = "✅" if is_valid == expected else "❌"
        print(f"{status} '{msg[:20]}...' → Valid: {is_valid}")

    # Test hashtag formatting
    print("\n🏷️ Testing hashtag formatting...")
    test_hashtags = [
        ["#test", "#example"],
        ["#single"],
        [],
        ["#many", "#different", "#hashtags", "#here"]
    ]

    for tags in test_hashtags:
        formatted = format_hashtags(tags)
        print(f"{tags} → '{formatted}'")

    print("✅ All utility tests completed!")

def test_environment():
    """Test environment configuration"""
    print("\n🌍 Testing Environment Configuration...")

    required_vars = [
        ("API_ID", os.getenv("API_ID")),
        ("API_HASH", os.getenv("API_HASH")),
        ("BOT_TOKEN", os.getenv("BOT_TOKEN")),
        ("MENFESS_CHANNEL_ID", os.getenv("MENFESS_CHANNEL_ID")),
        ("ADMIN_GROUP_ID", os.getenv("ADMIN_GROUP_ID")),
        ("OWNER_ID", os.getenv("OWNER_ID")),
    ]

    optional_vars = [
        ("REDIS_HOST", os.getenv("REDIS_HOST")),
        ("MONGODB_URI", os.getenv("MONGODB_URI")),
    ]

    print("📋 Required Configuration:")
    all_good = True
    for var_name, value in required_vars:
        status = "✅" if value else "❌ MISSING"
        print(f"  {var_name}: {status}")
        if not value:
            all_good = False

    print("\n📋 Optional Configuration:")
    for var_name, value in optional_vars:
        status = "✅ SET" if value else "⚪ Not set (optional)"
        print(f"  {var_name}: {status}")

    if not all_good:
        print("\n❌ Missing required environment variables!")
        print("Please copy .env.example to .env and configure it.")
        return False

    print(f"\n✅ Environment configuration is valid!")
    return True

async def main():
    """Run all tests"""
    print("🤖 VzoelFess Bot Setup Test")
    print("=" * 50)

    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Test environment
    env_ok = test_environment()
    if not env_ok:
        print("\n❌ Environment test failed. Please fix configuration first.")
        return

    # Test utilities
    test_utilities()

    # Test database if environment is OK
    if env_ok:
        db_ok = await test_database_setup()
        if not db_ok:
            print("\n❌ Database test failed.")
            return

    print("\n" + "=" * 50)
    print("🎉 All tests completed successfully!")
    print("\nNext steps:")
    print("1. Configure your .env file properly")
    print("2. Set up your Telegram channel and admin group")
    print("3. Run: python main.py")
    print("\nBot is ready to use! 🚀")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()