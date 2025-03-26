import os
import logging
from flask import Flask, request, render_template_string
from threading import Thread
import signal
import sys

from bot_v13 import TelegramBot
from keep_alive import keep_alive

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)

logger = logging.getLogger(__name__)

# Flask application
app = Flask(__name__)

# Global bot variable
bot = None

# Home page route
@app.route('/')
def home():
    """Render the home page showing that the bot is alive"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Product Tracking Bot</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <style>
            body {
                padding: 40px 20px;
            }
            .status-badge {
                font-size: 1.2rem;
                padding: 0.5rem 1rem;
            }
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <div class="card shadow mt-5">
                        <div class="card-header bg-primary text-white">
                            <h2 class="card-title mb-0">Telegram Product Tracking Bot</h2>
                        </div>
                        <div class="card-body">
                            <div class="d-flex justify-content-center mb-4">
                                <span class="badge bg-success status-badge">Bot is Active and Running</span>
                            </div>
                            
                            <h4 class="card-subtitle mb-3">Features</h4>
                            <ul class="list-group mb-4">
                                <li class="list-group-item">Track product prices from multiple Turkish e-commerce websites</li>
                                <li class="list-group-item">Get notifications when prices change or products come back in stock</li>
                                <li class="list-group-item">Easily manage your tracked products</li>
                                <li class="list-group-item">Fast and reliable notifications</li>
                            </ul>
                            
                            <h4 class="card-subtitle mb-3">Supported Stores</h4>
                            <div class="row row-cols-2 row-cols-md-3 g-3 mb-4">
                                <div class="col"><div class="card h-100"><div class="card-body">Trendyol</div></div></div>
                                <div class="col"><div class="card h-100"><div class="card-body">Hepsiburada</div></div></div>
                                <div class="col"><div class="card h-100"><div class="card-body">N11</div></div></div>
                                <div class="col"><div class="card h-100"><div class="card-body">Amazon</div></div></div>
                                <div class="col"><div class="card h-100"><div class="card-body">Teknosa</div></div></div>
                                <div class="col"><div class="card h-100"><div class="card-body">Media Markt</div></div></div>
                            </div>
                            
                            <div class="alert alert-info" role="alert">
                                <h5 class="alert-heading">How to Use</h5>
                                <p>Search for <code>@YourBotUsername</code> on Telegram and send <code>/start</code> to begin!</p>
                            </div>
                        </div>
                        <div class="card-footer text-muted">
                            <div class="d-flex justify-content-between align-items-center">
                                <span>© 2025 Product Tracking Bot</span>
                                <span>Running 24/7 on Replit</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

# Graceful shutdown handler
def signal_handler(sig, frame):
    logger.info("Shutting down the bot...")
    global bot
    if bot:
        bot.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Function to run the Telegram bot
def run_bot():
    global bot
    try:
        logger.info("Initializing bot...")
        bot = TelegramBot()
        logger.info("Starting bot...")
        bot.start()
    except Exception as e:
        logger.error(f"Fatal error in bot: {e}", exc_info=True)

if __name__ == "__main__":
    # Start the bot in a separate thread
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Start Flask app
    logger.info("Starting Flask server on port 5000")
    app.run(host='0.0.0.0', port=5000)
