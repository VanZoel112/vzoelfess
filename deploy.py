#!/usr/bin/env python3
"""
VzoelFess Bot Deployment Script
Setup bot untuk production dengan validasi lengkap
"""

import os
import sys
import asyncio
from datetime import datetime

def check_environment():
    """Check environment variables and system requirements"""
    print("🔍 Checking Environment...")

    required_vars = {
        'API_ID': 'Telegram API ID dari my.telegram.org',
        'API_HASH': 'Telegram API Hash dari my.telegram.org',
        'BOT_TOKEN': 'Bot token dari @BotFather',
        'MENFESS_CHANNEL_ID': 'Channel ID untuk posting menfess',
        'ADMIN_GROUP_ID': 'Group ID untuk admin review',
        'OWNER_ID': 'User ID owner bot'
    }

    missing = []
    for var, desc in required_vars.items():
        if not os.getenv(var):
            missing.append(f"❌ {var}: {desc}")
        else:
            print(f"✅ {var}: Set")

    if missing:
        print("\n🚨 Missing Required Environment Variables:")
        for item in missing:
            print(f"  {item}")
        print("\nPlease add these to your .env file")
        return False

    print("✅ All required environment variables are set")
    return True

def setup_directories():
    """Create necessary directories"""
    print("\n📁 Setting up directories...")

    directories = ['data', 'logs']

    for dir_name in directories:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"✅ Created: {dir_name}/")
        else:
            print(f"✅ Exists: {dir_name}/")

def check_dependencies():
    """Check if all dependencies are installed"""
    print("\n📦 Checking Dependencies...")

    required_packages = [
        'telethon',
        'aiosqlite',
        'python-dotenv',
        'asyncio-throttle',
        'cryptography',
        'python-dateutil'
    ]

    optional_packages = [
        ('redis', 'Redis caching support'),
        ('motor', 'MongoDB logging support'),
        ('ujson', 'Faster JSON processing')
    ]

    missing = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package}")

    if missing:
        print(f"\n🚨 Missing required packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False

    print("\n📦 Optional Packages:")
    for package, desc in optional_packages:
        try:
            __import__(package)
            print(f"✅ {package}: {desc}")
        except ImportError:
            print(f"⚪ {package}: {desc} (not installed)")

    return True

async def test_database():
    """Test database connections"""
    print("\n💾 Testing Database Connections...")

    try:
        from database import DatabaseManager
        from config.settings import DATABASE_PATH, REDIS_HOST, MONGODB_URI

        # Configure optional databases
        redis_config = {'host': REDIS_HOST} if REDIS_HOST else None
        mongodb_config = {'uri': MONGODB_URI, 'db_name': 'vzoelfess'} if MONGODB_URI else None

        db = DatabaseManager(
            sqlite_path=DATABASE_PATH,
            redis_config=redis_config,
            mongodb_config=mongodb_config
        )

        await db.initialize()
        print("✅ Database connections established")

        # Test basic operations
        await db.add_user(999999, "test_deploy", "Deploy", "Test")
        user = await db.get_user(999999)

        if user:
            print("✅ Database operations working")

        await db.close()
        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def create_service_file():
    """Create systemd service file for Linux"""
    if os.name != 'posix':
        return

    print("\n🔧 Creating Service File...")

    current_dir = os.getcwd()
    python_path = sys.executable

    service_content = f"""[Unit]
Description=VzoelFess Bot - Anonymous Confession Telegram Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User={os.environ.get('USER', 'bot')}
WorkingDirectory={current_dir}
Environment=PYTHONPATH={current_dir}
ExecStart={python_path} main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    service_path = "vzoelfess-bot.service"

    try:
        with open(service_path, 'w') as f:
            f.write(service_content)

        print(f"✅ Service file created: {service_path}")
        print("To install the service:")
        print(f"  sudo cp {service_path} /etc/systemd/system/")
        print("  sudo systemctl enable vzoelfess-bot")
        print("  sudo systemctl start vzoelfess-bot")

    except Exception as e:
        print(f"⚠️  Could not create service file: {e}")

def create_docker_files():
    """Create Docker configuration files"""
    print("\n🐳 Creating Docker Files...")

    dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs

# Run the bot
CMD ["python", "main.py"]
"""

    docker_compose_content = """version: '3.8'

services:
  vzoelfess-bot:
    build: .
    container_name: vzoelfess-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
      - mongodb

  redis:
    image: redis:7-alpine
    container_name: vzoelfess-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data

  mongodb:
    image: mongo:7
    container_name: vzoelfess-mongodb
    restart: unless-stopped
    environment:
      MONGO_INITDB_DATABASE: vzoelfess
    volumes:
      - mongodb_data:/data/db

volumes:
  redis_data:
  mongodb_data:
"""

    try:
        with open('Dockerfile', 'w') as f:
            f.write(dockerfile_content)
        print("✅ Dockerfile created")

        with open('docker-compose.yml', 'w') as f:
            f.write(docker_compose_content)
        print("✅ docker-compose.yml created")

        print("To deploy with Docker:")
        print("  docker-compose up -d")

    except Exception as e:
        print(f"⚠️  Could not create Docker files: {e}")

def create_backup_script():
    """Create backup script"""
    print("\n💾 Creating Backup Script...")

    backup_script = """#!/bin/bash
# VzoelFess Bot Backup Script

DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups"
BOT_DIR="$(dirname "$0")"

mkdir -p "$BACKUP_DIR"

echo "🔄 Creating backup: vzoelfess_backup_$DATE.tar.gz"

tar -czf "$BACKUP_DIR/vzoelfess_backup_$DATE.tar.gz" \\
    --exclude="$BACKUP_DIR" \\
    --exclude=".git" \\
    --exclude="__pycache__" \\
    --exclude="*.pyc" \\
    --exclude="logs/*.log" \\
    -C "$BOT_DIR" .

echo "✅ Backup completed: $BACKUP_DIR/vzoelfess_backup_$DATE.tar.gz"

# Keep only last 7 backups
find "$BACKUP_DIR" -name "vzoelfess_backup_*.tar.gz" -mtime +7 -delete
"""

    try:
        with open('backup.sh', 'w') as f:
            f.write(backup_script)
        os.chmod('backup.sh', 0o755)
        print("✅ Backup script created: backup.sh")
        print("Run: ./backup.sh to create backup")

    except Exception as e:
        print(f"⚠️  Could not create backup script: {e}")

async def main():
    """Main deployment function"""
    print("🚀 VzoelFess Bot Deployment Setup")
    print("=" * 50)

    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed!")
        return

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed!")
        return

    # Setup directories
    setup_directories()

    # Test database
    if not await test_database():
        print("\n❌ Database test failed!")
        return

    # Create deployment files
    create_service_file()
    create_docker_files()
    create_backup_script()

    print("\n" + "=" * 50)
    print("🎉 Deployment setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Configure your .env file with real values")
    print("2. Set up Telegram channel and admin group")
    print("3. Choose deployment method:")
    print("   • Direct: python main.py")
    print("   • Systemd: Use the .service file")
    print("   • Docker: docker-compose up -d")
    print("\n🔧 Maintenance:")
    print("• Run ./backup.sh for backups")
    print("• Check logs/ directory for debugging")
    print("• Monitor database growth in data/")
    print("\n🎭 Bot is ready for production!")

if __name__ == "__main__":
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Deployment interrupted by user")
    except Exception as e:
        print(f"\n❌ Deployment error: {e}")
        import traceback
        traceback.print_exc()