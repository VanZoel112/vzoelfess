# VzoelFess Bot 🎭

Bot menfess (mention and confess) anonymous Telegram yang lengkap dengan fitur hashtag, rate limiting, dan panel admin.

## ✨ Fitur Utama

### 👥 User Features
- **Anonymous Confession**: Kirim pesan anonim ke channel
- **Hashtag System**: Wajib menggunakan hashtag untuk kategorisasi
- **Rate Limiting**: Sistem pembatasan spam otomatis
- **User Statistics**: Tracking personal statistik
- **Real-time Status**: Cek status dan kuota harian

### 🛡️ Admin Features
- **Review System**: Approve/reject menfess sebelum publish
- **User Management**: Ban/unban user dengan alasan
- **Real-time Moderation**: Inline button untuk aksi cepat
- **Analytics**: Statistik lengkap bot dan user activity
- **Multi-Admin Support**: Support multiple admin dengan permission

### 🗄️ Database Features
- **SQLite**: Database utama (wajib)
- **Redis**: Caching dan rate limiting (opsional)
- **MongoDB**: Permanent logging dan analytics (opsional)
- **Auto Failover**: Fallback jika Redis/MongoDB tidak tersedia

## 🚀 Installation

### 1. Clone Repository
```bash
git clone <repository_url>
cd vzoelfess
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Environment
```bash
cp .env.example .env
```

Edit `.env` dengan konfigurasi Anda:
```env
# Telegram API (Wajib)
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token

# Bot Configuration (Wajib)
MENFESS_CHANNEL_ID=-1001234567890
ADMIN_GROUP_ID=-1001234567890
OWNER_ID=123456789

# Rate Limiting
MESSAGES_PER_HOUR=5
MESSAGES_PER_DAY=20
COOLDOWN_MINUTES=10

# Redis (Opsional - untuk performa optimal)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# MongoDB (Opsional - untuk logging permanent)
MONGODB_URI=mongodb://localhost:27017/vzoelfess
MONGODB_DB=vzoelfess
```

### 4. Setup Channel & Group

1. **Buat Channel Menfess**:
   - Buat channel public/private
   - Add bot sebagai admin
   - Copy channel ID ke `MENFESS_CHANNEL_ID`

2. **Buat Group Admin**:
   - Buat group untuk admin review
   - Add bot sebagai admin
   - Copy group ID ke `ADMIN_GROUP_ID`

3. **Get Owner ID**:
   - Chat bot @userinfobot
   - Copy user ID ke `OWNER_ID`

### 5. Run Bot
```bash
python main.py
```

## 📖 User Commands

### Basic Commands
- `/start` - Mulai bot dan lihat status
- `/help` - Panduan penggunaan
- `/stats` - Statistik personal
- `/hashtags` - Lihat hashtag populer

### Mengirim Menfess
Kirim pesan langsung ke bot dengan format:
```
Isi pesan menfess...

#hashtag1 #hashtag2 #hashtag3
```

**Aturan Hashtag**:
- ✅ Minimal 1 hashtag wajib
- ✅ Maksimal 10 hashtag per pesan
- ✅ Format: `#hashtag` (tanpa spasi)
- ✅ Bisa bahasa Indonesia/Inggris

## 🛡️ Admin Commands

### Moderation Commands
- `/approve <menfess_id>` - Setujui menfess
- `/reject <menfess_id> [alasan]` - Tolak menfess
- `/pending` - Lihat menfess pending
- `/adminstats` - Statistik admin

### User Management
- `/ban <user_id> [alasan]` - Ban user
- `/unban <user_id>` - Unban user
- `/user <user_id>` - Info detail user

### Quick Actions (Inline Buttons)
- ✅ Approve - Setujui langsung
- ❌ Reject - Tolak langsung
- 👤 User Info - Lihat info user
- 🚫 Ban User - Ban user langsung

## 🎯 Rate Limiting System

### Default Limits
- **Per Jam**: 5 pesan
- **Per Hari**: 20 pesan
- **Cooldown**: 10 menit antar pesan

### Smart Rate Limiting
- Menggunakan Redis untuk real-time tracking
- Sliding window algorithm
- Automatic reset pada tengah malam
- Fallback ke SQLite jika Redis tidak tersedia

## 🏷️ Hashtag System

### Aturan Hashtag
- **Wajib**: Setiap menfess harus ada hashtag
- **Format**: `#hashtag` (mulai dengan #)
- **Jumlah**: 1-10 hashtag per pesan
- **Karakter**: A-Z, 0-9, underscore

### Tracking
- Statistik penggunaan hashtag
- Top hashtag populer
- First/last used tracking
- Auto-complete suggestions

## 📊 Analytics & Monitoring

### Real-time Analytics
- Daily message counts
- User activity tracking
- Approval/rejection rates
- Hashtag trending

### Data Export
- User data backup (GDPR compliant)
- Analytics export
- Admin activity logs
- System health monitoring

## 🔧 Architecture

### Database Layer
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   SQLite    │    │    Redis    │    │  MongoDB    │
│  (Primary)  │    │  (Caching)  │    │ (Logging)   │
│             │    │             │    │             │
│ • Users     │    │ • Rate Lmt  │    │ • Analytics │
│ • Messages  │    │ • Sessions  │    │ • Audit Log │
│ • Settings  │    │ • Cache     │    │ • Backups   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Handler Structure
```
📁 handlers/
├── user_handler.py    # User interactions
├── admin_handler.py   # Admin operations
└── callback_handler.py # Inline callbacks
```

## 🔐 Security Features

### User Protection
- Anonymous messaging (no user data exposed)
- Rate limiting anti-spam
- Content validation
- Ban/unban system

### Admin Security
- Admin-only commands
- Action logging
- Audit trails
- Permission checking

### Data Privacy
- GDPR-compliant data deletion
- User data backup before deletion
- Encrypted sensitive data
- Minimal data collection

## 🚦 Error Handling

### Graceful Degradation
- Redis offline → SQLite fallback
- MongoDB offline → Local logging
- Channel unavailable → Error notification
- Network issues → Retry mechanism

### Logging
- Comprehensive error logging
- User action tracking
- Admin operation logs
- System health monitoring

## 📋 Development

### Project Structure
```
vzoelfess/
├── config/
│   └── settings.py         # Configuration
├── database/
│   ├── __init__.py        # Database manager
│   ├── models.py          # SQLite models
│   ├── redis_manager.py   # Redis operations
│   └── mongodb_manager.py # MongoDB operations
├── handlers/
│   ├── user_handler.py    # User commands
│   └── admin_handler.py   # Admin commands
├── utils/
│   └── helpers.py         # Utility functions
├── main.py               # Bot entry point
├── requirements.txt      # Dependencies
└── .env.example         # Environment template
```

### Testing
```bash
# Test database connections
python -c "from database import DatabaseManager; import asyncio; asyncio.run(DatabaseManager('test.db').initialize())"

# Test bot startup (dry run)
python main.py --test
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Make changes dengan testing
4. Submit pull request

## 📄 License

MIT License - Feel free to use and modify

## 🆘 Support

Jika ada issues atau questions:
1. Check dokumentasi ini dulu
2. Lihat logs di `logs/bot.log`
3. Test koneksi database
4. Create GitHub issue

---

**VzoelFess Bot** - Anonymous confession made easy! 🎭