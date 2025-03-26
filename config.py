"""
Configuration settings for the Telegram bot
"""

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
    }
]

# HTTP headers for web requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1'
}

# Notification settings
PRODUCT_CHECK_INTERVAL_MINUTES = 30  # Time in minutes between product updates
