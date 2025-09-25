"""
Utility functions for VzoelFess Bot
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional
import hashlib

def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from message text"""
    hashtag_pattern = r'#[\w\u00c0-\u024f\u1e00-\u1eff]+'
    hashtags = re.findall(hashtag_pattern, text, re.IGNORECASE)
    # Remove duplicates and convert to lowercase
    unique_hashtags = list(set([tag.lower() for tag in hashtags]))
    return unique_hashtags

def clean_message_text(text: str) -> str:
    """Clean message text by removing extra whitespace and formatting"""
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text

def format_hashtags(hashtags: List[str]) -> str:
    """Format hashtags for display"""
    if not hashtags:
        return ""
    return " ".join(hashtags)

def generate_message_id() -> str:
    """Generate unique message ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    hash_part = hashlib.md5(str(datetime.now().microsecond).encode()).hexdigest()[:6]
    return f"{timestamp}{hash_part}"

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def time_until_reset() -> str:
    """Calculate time until daily reset"""
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    time_diff = tomorrow - now
    hours, remainder = divmod(time_diff.total_seconds(), 3600)
    minutes = remainder // 60
    return f"{int(hours)}j {int(minutes)}m"

def validate_message(text: str, min_length: int = 10, max_length: int = 4000) -> tuple[bool, Optional[str]]:
    """Validate message content"""
    if not text or not text.strip():
        return False, "Pesan tidak boleh kosong"

    text = text.strip()

    if len(text) < min_length:
        return False, f"Pesan minimal {min_length} karakter"

    if len(text) > max_length:
        return False, f"Pesan maksimal {max_length} karakter"

    # Check for spam patterns
    spam_patterns = [
        r'(.)\1{10,}',  # Repeated characters
        r'(..)\1{5,}',  # Repeated patterns
    ]

    for pattern in spam_patterns:
        if re.search(pattern, text):
            return False, "Pesan terdeteksi sebagai spam"

    return True, None

def is_admin(user_id: int, admin_ids: List[int]) -> bool:
    """Check if user is admin"""
    return user_id in admin_ids

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_user_mention(user_id: int, first_name: str, username: str = None) -> str:
    """Format user mention"""
    if username:
        return f"@{username}"
    return f"[{first_name}](tg://user?id={user_id})"

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        import os
        return os.path.getsize(file_path)
    except:
        return 0

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"

def create_pagination_keyboard(page: int, total_pages: int, callback_data: str):
    """Create pagination keyboard for inline results"""
    keyboard = []

    if total_pages <= 1:
        return keyboard

    row = []

    # Previous page
    if page > 1:
        row.append({
            'text': '⬅️ Prev',
            'callback_data': f"{callback_data}:{page-1}"
        })

    # Page indicator
    row.append({
        'text': f"{page}/{total_pages}",
        'callback_data': "page_info"
    })

    # Next page
    if page < total_pages:
        row.append({
            'text': 'Next ➡️',
            'callback_data': f"{callback_data}:{page+1}"
        })

    keyboard.append(row)
    return keyboard