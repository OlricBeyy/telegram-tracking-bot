"""
This module contains a Flask server to keep the Replit environment alive
using UptimeRobot or a similar service.
"""

import logging
import threading
from flask import Flask, render_template_string

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    """Render the home page showing the bot is alive"""
    html = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ürün Takip Botu</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f5f5f5;
                text-align: center;
                padding: 40px 20px;
                max-width: 800px;
                margin: 0 auto;
                color: #333;
            }
            .container {
                background-color: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                margin-top: 20px;
            }
            h1 {
                color: #2c3e50;
            }
            .status {
                font-size: 18px;
                padding: 10px;
                margin: 20px 0;
                border-radius: 5px;
                background-color: #e8f5e9;
                color: #2e7d32;
            }
            .info {
                text-align: left;
                margin: 20px 0;
                line-height: 1.6;
            }
            .footer {
                margin-top: 40px;
                font-size: 14px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Ürün Takip Botu</h1>
            <div class="status">
                ✅ Bot çalışıyor ve aktif
            </div>
            <div class="info">
                <p>Bu bot, çevrimiçi mağazalardaki ürünleri takip etmenizi sağlar. Fiyat değişikliklerini ve stok durumunu kontrol eder, değişiklik olduğunda sizi bilgilendirir.</p>
                
                <p><strong>Kullanmak için:</strong> Telegram'da <code>@your_bot_username</code> ile botu bulun ve <code>/start</code> komutunu gönderin.</p>
                
                <p><strong>Özellikler:</strong></p>
                <ul>
                    <li>Ürün fiyat değişikliklerini takip etme</li>
                    <li>Stok durumu bildirimleri</li>
                    <li>Birden fazla mağaza desteği</li>
                    <li>Kolay ürün ekleme ve yönetme</li>
                </ul>
            </div>
            <div class="footer">
                &copy; 2023 Ürün Takip Botu
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

def run():
    """Run the Flask server in a separate thread"""
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    """Start the Flask server in a separate thread to keep the Replit alive"""
    logger.info("Starting keep-alive server on port 5000")
    server = threading.Thread(target=run)
    server.daemon = True  # Daemon threads are killed when the main program exits
    server.start()
    logger.info("Keep-alive server started")
