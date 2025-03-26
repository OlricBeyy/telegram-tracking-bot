# Telegram Product Tracking Bot

This bot helps users track product prices and stock availability from various Turkish e-commerce websites.

## Features

- **Multi-store Support**: Track products from Trendyol, Hepsiburada, N11, Amazon, Teknosa, and MediaMarkt
- **Price Tracking**: Get notifications when product prices change
- **Stock Alerts**: Receive alerts when products come back in stock or go out of stock
- **Easy Management**: Simple commands to add, check, and remove tracked products
- **Optimized Performance**: Fast response times and reliable operation

## Commands

- `/start` - Start the bot and see welcome message
- `/help` - Display help information
- `/track` - Start tracking a new product
- `/list` - View all tracked products

## Setup

### Prerequisites

- Python 3.7+
- A Telegram Bot token from BotFather

### Environment Variables

- `TELEGRAM_TOKEN` - Your Telegram bot token

### Running on Replit

1. Fork this Replit project
2. Set your `TELEGRAM_TOKEN` in the Secrets tab
3. Run the project
4. Set up an uptime monitor (like UptimeRobot) to ping the web server URL

## How It Works

1. User starts the bot with `/start`
2. User selects `/track` to add a product
3. User selects a store and provides product URL
4. The bot scrapes the product information and confirms with the user
5. The bot periodically checks for price and stock changes
6. User receives notifications when changes are detected

## Technical Details

- **Web Scraping**: Custom scrapers for each supported online store
- **Database**: SQLite database to store user and product information
- **Keep-Alive**: Flask web server to keep the Replit project running 24/7
- **Error Handling**: Comprehensive error handling and logging

## Optimizations

This bot uses several optimizations to ensure stable and efficient operation:

- Proper error handling with detailed logging
- Rate limiting for web requests to avoid IP blocks
- Efficient database queries
- Webhook mode for better performance
- Keep-alive mechanism for 24/7 operation

## Hosting

This bot is designed to run on Replit with a keep-alive mechanism. To ensure 24/7 operation:

1. The bot includes a simple Flask web server
2. Set up an uptime monitor service (like UptimeRobot) to ping your Replit URL every few minutes
3. This prevents Replit from putting your project to sleep due to inactivity

## License

This project is available under the MIT License.
