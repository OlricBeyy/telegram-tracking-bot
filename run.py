#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import signal
import sys

from bot_v13 import TelegramBot

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
        # Keep the main thread alive
        import time
        while True:
            time.sleep(60)
    except Exception as e:
        logger.error(f"Fatal error in bot: {e}", exc_info=True)

if __name__ == "__main__":
    # Check if Telegram token is set
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set.")
        sys.exit(1)
    else:
        logger.info(f"TELEGRAM_TOKEN is set, length: {len(os.environ.get('TELEGRAM_TOKEN'))}")
    
    # Log the environment variables
    logger.info("Starting bot application...")
    run_bot()