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

# Reboot function for the bot
def reboot_bot():
    global bot
    logger.info("Rebooting bot...")
    if bot:
        bot.stop()
    bot = TelegramBot()
    bot.start()
    logger.info("Bot rebooted successfully")

if __name__ == "__main__":
    run_bot()