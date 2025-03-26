#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import signal
import sys
import threading
from flask import Flask, render_template

from bot_v13 import TelegramBot

# Create Flask app for keep alive server
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global bot variable
bot = None

# Flask routes
@app.route('/')
def home():
    """Render the home page showing that the bot is alive"""
    return render_template('index.html') if os.path.exists('templates/index.html') else "Bot is running!"

# Graceful shutdown handler
def signal_handler(sig, frame):
    logger.info("Shutting down the bot...")
    global bot
    if bot:
        bot.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Function to run the Telegram bot in a separate thread
def run_bot_thread():
    global bot
    try:
        logger.info("Initializing bot...")
        bot = TelegramBot()
        logger.info("Starting bot...")
        bot.start()
        
        # Keep the thread alive
        import time
        while True:
            time.sleep(60)
    except Exception as e:
        logger.error(f"Fatal error in bot: {e}", exc_info=True)

# Create a minimal HTML template
def create_template():
    os.makedirs('templates', exist_ok=True)
    with open('templates/index.html', 'w') as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ürün Takip Botu</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    background-color: white;
                    border-radius: 10px;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }
                h1 { color: #4285f4; }
                .status { 
                    display: inline-block;
                    background-color: #0f9d58;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                .info { margin: 20px 0; line-height: 1.5; }
                .footer { margin-top: 40px; font-size: 0.8em; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Ürün Takip Botu</h1>
                <div class="status">Aktif</div>
                <div class="info">
                    <p>Telegram ürün takip botu şu anda çalışıyor ve kullanıma hazır.</p>
                    <p>Botu kullanmak için Telegram'da <a href="https://t.me/your_bot_username">@your_bot_username</a> hesabına mesaj gönderin.</p>
                    <p>Desteklenen komutlar:</p>
                    <ul>
                        <li><strong>/start</strong> - Botu başlat</li>
                        <li><strong>/help</strong> - Yardım menüsünü göster</li>
                        <li><strong>/track</strong> - Ürün takibi başlat</li>
                        <li><strong>/list</strong> - Takip edilen ürünleri listele</li>
                        <li><strong>/reboot</strong> - Botu yeniden başlat</li>
                    </ul>
                </div>
                <div class="footer">
                    Son güncelleme: %s
                </div>
            </div>
        </body>
        </html>
        """ % (datetime.now().strftime("%d.%m.%Y %H:%M:%S")))

if __name__ == "__main__":
    # Check if Telegram token is set
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set.")
        sys.exit(1)
    
    # Create template file
    try:
        from datetime import datetime
        create_template()
    except Exception as e:
        logger.warning(f"Could not create template: {e}")
    
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run the Flask server for keep-alive
    app.run(host='0.0.0.0', port=5000)