"""
Configuration settings for the Telegram bot
"""
import os

# List of supported stores
STORES = [
    {
        'id': 'trendyol',
        'name': 'Trendyol',
        'domain': 'trendyol.com'
    },
    {
        'id': 'hepsiburada',
        'name': 'Hepsiburada',
        'domain': 'hepsiburada.com'
    },
    {
        'id': 'n11',
        'name': 'N11',
        'domain': 'n11.com'
    },
    {
        'id': 'amazon',
        'name': 'Amazon',
        'domain': 'amazon.com.tr'
    },
    {
        'id': 'teknosa',
        'name': 'Teknosa',
        'domain': 'teknosa.com'
    },
    {
        'id': 'mediamarkt',
        'name': 'Media Markt',
        'domain': 'mediamarkt.com.tr'
    },
    {
        'id': 'generic',
        'name': 'Diğer Site',
        'domain': ''  # Boş domain, herhangi bir site için kullanılacak
    }
]

# HTTP headers for web requests
HEADERS = {
    'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept':
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1'
}

# Notification settings
PRODUCT_CHECK_INTERVAL_MINUTES = 30  # Time in minutes between product updates

# Admin settings
# Bu değeri kendi Telegram ID'niz ile değiştirin
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '5444269025'))

# Bot messages
MSG_UNAUTHORIZED = "Üzgünüm, bu botu kullanma yetkiniz yok. Admin ile iletişime geçiniz."
MSG_ADMIN_ONLY = "Üzgünüm, bu komut sadece admin kullanıcılar tarafından kullanılabilir."

# Product scraping
GENERIC_STORE_ID = "generic"  # Store ID for generic product tracking
