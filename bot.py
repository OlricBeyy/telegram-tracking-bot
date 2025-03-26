import logging
import os
from typing import Dict, List, Optional, Tuple
import traceback
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

from database import Database
from scraper import ProductScraper
from config import STORES, HEADERS, PRODUCT_CHECK_INTERVAL_MINUTES

# Configure logger for this module
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_STORE, ENTERING_URL, CONFIRMING_PRODUCT, MONITORING = range(4)

class TelegramBot:
    def __init__(self):
        """Initialize the Telegram bot with required components"""
        # Get token from environment variable
        self.token = os.environ.get("TELEGRAM_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN environment variable not set")
        
        # Initialize database
        self.db = Database()
        
        # Initialize product scraper
        self.scraper = ProductScraper(HEADERS)
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self._add_handlers()
        
        logger.info("Bot initialized successfully")
    
    def _add_handlers(self):
        """Add all command and callback handlers to the application"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("list", self._list_command))
        
        # Track product conversation flow
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("track", self._track_command)],
            states={
                SELECTING_STORE: [
                    CallbackQueryHandler(self._store_selected, pattern=r'^store_\w+$')
                ],
                ENTERING_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._url_received)
                ],
                CONFIRMING_PRODUCT: [
                    CallbackQueryHandler(self._confirm_product, pattern=r'^confirm_(yes|no)$')
                ]
            },
            fallbacks=[CommandHandler("cancel", self._cancel_tracking)],
        )
        self.application.add_handler(conv_handler)
        
        # Product action handlers
        self.application.add_handler(CallbackQueryHandler(self._remove_product, pattern=r'^remove_\d+$'))
        self.application.add_handler(CallbackQueryHandler(self._check_product, pattern=r'^check_\d+$'))
        
        # Error handler
        self.application.add_error_handler(self._error_handler)

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command - introduce the bot and its functions"""
        user = update.effective_user
        await update.message.reply_html(
            f"👋 Merhaba {user.mention_html()}!\n\n"
            f"🔍 Ben bir ürün takip botuyum. Favori mağazalarınızdaki ürünlerin "
            f"fiyat değişimlerini ve stok durumlarını takip edebilirsiniz.\n\n"
            f"🛠 Komutlar:\n"
            f"/track - Yeni bir ürün takibi başlat\n"
            f"/list - Takip ettiğiniz ürünleri listele\n"
            f"/help - Yardım menüsü\n\n"
            f"Hadi başlayalım! Takip etmek istediğiniz bir ürün için /track komutunu kullanın."
        )
        
        # Ensure user exists in database
        self.db.add_user(update.effective_user.id)

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command - display help information"""
        await update.message.reply_text(
            "📘 *Bot Kullanım Rehberi*\n\n"
            "*Komutlar:*\n"
            "/start - Botu başlat\n"
            "/track - Yeni bir ürün takibi başlat\n"
            "/list - Takip ettiğiniz ürünleri listele\n"
            "/help - Bu yardım mesajını göster\n\n"
            "*Ürün Takibi Nasıl Çalışır:*\n"
            "1. /track komutunu kullanın\n"
            "2. Listeden bir mağaza seçin\n"
            "3. Takip etmek istediğiniz ürünün URL'sini gönderin\n"
            "4. Bilgileri onaylayın\n\n"
            "*Desteklenen Mağazalar:*\n" + 
            "\n".join(f"• {store['name']}" for store in STORES),
            parse_mode='Markdown'
        )

    async def _track_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the product tracking conversation flow"""
        # Create keyboard with store options
        keyboard = []
        for store in STORES:
            keyboard.append([InlineKeyboardButton(
                text=store['name'], 
                callback_data=f"store_{store['id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Hangi mağazadan ürün takip etmek istiyorsunuz?",
            reply_markup=reply_markup
        )
        
        return SELECTING_STORE

    async def _store_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle store selection for product tracking"""
        query = update.callback_query
        await query.answer()
        
        store_id = query.data.split('_')[1]
        context.user_data['selected_store'] = store_id
        
        # Find store name
        store_name = next((s['name'] for s in STORES if s['id'] == store_id), "Seçilen mağaza")
        
        await query.edit_message_text(
            f"{store_name} mağazasından bir ürün takip edeceksiniz.\n\n"
            f"Lütfen ürün sayfasının tam URL'sini girin:"
        )
        
        return ENTERING_URL

    async def _url_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process the product URL entered by the user"""
        url = update.message.text.strip()
        store_id = context.user_data.get('selected_store')
        
        # Save URL to context
        context.user_data['product_url'] = url
        
        await update.message.reply_text("Ürün bilgileri alınıyor, lütfen bekleyin...")
        
        try:
            # Get product info using scraper
            product_info = self.scraper.get_product_info(store_id, url)
            
            if not product_info:
                await update.message.reply_text(
                    "⚠️ Bu URL'den ürün bilgilerini alamadım. Lütfen URL'i kontrol edip tekrar deneyin."
                )
                return ConversationHandler.END
            
            # Save product info to context
            context.user_data['product_info'] = product_info
            
            # Show product info and ask for confirmation
            keyboard = [
                [
                    InlineKeyboardButton("✓ Evet", callback_data="confirm_yes"),
                    InlineKeyboardButton("✗ Hayır", callback_data="confirm_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Format price with currency
            price_formatted = f"{product_info['price']} TL" if product_info['price'] else "Fiyat bilgisi alınamadı"
            
            await update.message.reply_text(
                f"*Ürün Bilgileri:*\n\n"
                f"📌 *İsim:* {product_info['title']}\n"
                f"💰 *Fiyat:* {price_formatted}\n"
                f"🏪 *Stok Durumu:* {'✅ Stokta' if product_info['in_stock'] else '❌ Stokta değil'}\n\n"
                f"Bu ürünü takip listesine eklemek istiyor musunuz?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return CONFIRMING_PRODUCT
            
        except Exception as e:
            logger.error(f"Error processing URL: {e}", exc_info=True)
            await update.message.reply_text(
                "⚠️ Ürün bilgilerini alırken bir hata oluştu. Lütfen geçerli bir URL girdiğinizden emin olun ve tekrar deneyin."
            )
            return ConversationHandler.END

    async def _confirm_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle product confirmation for tracking"""
        query = update.callback_query
        await query.answer()
        
        user_choice = query.data.split('_')[1]
        
        if user_choice == 'yes':
            try:
                # Get data from context
                store_id = context.user_data.get('selected_store')
                url = context.user_data.get('product_url')
                product_info = context.user_data.get('product_info')
                
                # Add product to database
                product_id = self.db.add_product(
                    user_id=update.effective_user.id,
                    store_id=store_id,
                    url=url,
                    title=product_info['title'],
                    price=product_info['price'],
                    in_stock=product_info['in_stock']
                )
                
                await query.edit_message_text(
                    f"✅ *{product_info['title']}* ürünü başarıyla takip listesine eklendi.\n\n"
                    f"Fiyat veya stok durumu değiştiğinde sizi bilgilendireceğim!\n\n"
                    f"Takip ettiğiniz tüm ürünleri görmek için /list komutunu kullanabilirsiniz.",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Error adding product: {e}", exc_info=True)
                await query.edit_message_text(
                    "⚠️ Ürün eklenirken bir hata oluştu. Lütfen tekrar deneyin."
                )
        else:
            await query.edit_message_text(
                "İşlem iptal edildi. Başka bir ürün eklemek için /track komutunu kullanabilirsiniz."
            )
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END

    async def _cancel_tracking(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the product tracking conversation"""
        await update.message.reply_text(
            "Ürün takip işlemi iptal edildi. Ana menüye dönmek için /start komutunu kullanabilirsiniz."
        )
        context.user_data.clear()
        return ConversationHandler.END

    async def _list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List all tracked products for the user"""
        user_id = update.effective_user.id
        products = self.db.get_user_products(user_id)
        
        if not products:
            await update.message.reply_text(
                "📝 Henüz takip ettiğiniz bir ürün bulunmuyor.\n\n"
                "Ürün eklemek için /track komutunu kullanabilirsiniz."
            )
            return
        
        await update.message.reply_text(
            f"🛒 *Takip Ettiğiniz Ürünler ({len(products)})*\n\n"
            f"Her ürün için güncel durumu kontrol edebilir veya takibi sonlandırabilirsiniz:",
            parse_mode='Markdown'
        )
        
        # Send each product as a separate message with action buttons
        for product in products:
            # Format price
            price_text = f"{product['price']} TL" if product['price'] else "Fiyat bilgisi yok"
            
            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Güncelle", callback_data=f"check_{product['id']}"),
                    InlineKeyboardButton("❌ Takibi Bırak", callback_data=f"remove_{product['id']}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Get store name
            store_name = next((s['name'] for s in STORES if s['id'] == product['store_id']), "Bilinmeyen Mağaza")
            
            await update.message.reply_text(
                f"📌 *{product['title']}*\n"
                f"💰 *Fiyat:* {price_text}\n"
                f"🏪 *Stok Durumu:* {'✅ Stokta' if product['in_stock'] else '❌ Stokta değil'}\n"
                f"🛒 *Mağaza:* {store_name}\n"
                f"📅 *Eklenme:* {product['created_at']}\n"
                f"📅 *Son Güncelleme:* {product['updated_at']}\n",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def _remove_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove a product from tracking list"""
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split('_')[1])
        user_id = update.effective_user.id
        
        # Check product ownership
        if not self.db.is_product_owner(user_id, product_id):
            await query.edit_message_text("⚠️ Bu ürünü silme yetkiniz yok.")
            return
        
        product = self.db.get_product(product_id)
        success = self.db.remove_product(product_id)
        
        if success:
            await query.edit_message_text(
                f"✅ *{product['title']}* ürünü takip listenizden kaldırıldı.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "⚠️ Ürün kaldırılırken bir hata oluştu. Lütfen tekrar deneyin."
            )

    async def _check_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check current status of a product"""
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split('_')[1])
        user_id = update.effective_user.id
        
        # Check product ownership
        if not self.db.is_product_owner(user_id, product_id):
            await query.edit_message_text("⚠️ Bu ürünü kontrol etme yetkiniz yok.")
            return
        
        # Get product from database
        product = self.db.get_product(product_id)
        
        await query.edit_message_text(
            "Ürün bilgileri güncelleniyor, lütfen bekleyin..."
        )
        
        try:
            # Get current product info
            product_info = self.scraper.get_product_info(product['store_id'], product['url'])
            
            if not product_info:
                await query.edit_message_text(
                    "⚠️ Ürün bilgileri alınamadı. Lütfen daha sonra tekrar deneyin."
                )
                return
            
            # Format prices
            old_price_text = f"{product['price']} TL" if product['price'] else "Fiyat bilgisi yok"
            new_price_text = f"{product_info['price']} TL" if product_info['price'] else "Fiyat bilgisi yok"
            
            # Create status message
            message = f"🔄 *{product_info['title']}* güncel durumu:\n\n"
            
            # Check price difference
            if product_info['price'] != product['price']:
                if product_info['price'] and product['price']:
                    price_diff = float(product_info['price']) - float(product['price'])
                    if price_diff < 0:
                        message += f"💰 *Fiyat:* {old_price_text} ➡️ {new_price_text} (🎉 {abs(price_diff):.2f} TL indirim!)\n"
                    else:
                        message += f"💰 *Fiyat:* {old_price_text} ➡️ {new_price_text} (📈 {price_diff:.2f} TL artış)\n"
                else:
                    message += f"💰 *Fiyat:* {old_price_text} ➡️ {new_price_text}\n"
            else:
                message += f"💰 *Fiyat:* {new_price_text} (değişmedi)\n"
            
            # Check stock difference
            if product_info['in_stock'] != product['in_stock']:
                if product_info['in_stock']:
                    message += f"🏪 *Stok Durumu:* ❌ Stokta değil ➡️ ✅ Stokta (Stoka girdi!)\n"
                else:
                    message += f"🏪 *Stok Durumu:* ✅ Stokta ➡️ ❌ Stokta değil (Tükendi!)\n"
            else:
                message += f"🏪 *Stok Durumu:* {'✅ Stokta' if product_info['in_stock'] else '❌ Stokta değil'} (değişmedi)\n"
            
            # Get store name
            store_name = next((s['name'] for s in STORES if s['id'] == product['store_id']), "Bilinmeyen Mağaza")
            message += f"🛒 *Mağaza:* {store_name}\n"
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Tekrar Güncelle", callback_data=f"check_{product_id}"),
                    InlineKeyboardButton("❌ Takibi Bırak", callback_data=f"remove_{product_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Update product in database
            self.db.update_product(
                product_id=product_id,
                title=product_info['title'],
                price=product_info['price'],
                in_stock=product_info['in_stock']
            )
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error checking product: {e}", exc_info=True)
            await query.edit_message_text(
                "⚠️ Ürün kontrolü sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin."
            )

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in bot updates"""
        # Log the error
        logger.error(f"Update caused error: {context.error}", exc_info=context.error)
        
        # Get traceback info
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)
        
        # Log detailed error info
        logger.error(f"Traceback: {tb_string}")
        
        # Inform user of the error if possible
        if update and hasattr(update, 'effective_message') and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Bot işlem sırasında bir hatayla karşılaştı. Lütfen daha sonra tekrar deneyin.\n"
                "Sorun devam ederse, botun yeniden başlatılması gerekebilir."
            )

    async def _scheduled_check_products(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Callback for scheduled product check job"""
        await self._check_all_products()
        
    async def _check_all_products(self) -> None:
        """Check all products for updates and notify users"""
        logger.info("Starting periodic check of all products")
        
        products = self.db.get_all_products()
        for product in products:
            try:
                # Get current product info
                product_info = self.scraper.get_product_info(product['store_id'], product['url'])
                
                if not product_info:
                    logger.warning(f"Could not get info for product {product['id']}")
                    continue
                
                # Check for changes
                price_changed = product_info['price'] != product['price']
                stock_changed = product_info['in_stock'] != product['in_stock']
                
                # Notify user if needed
                if price_changed or stock_changed:
                    # Format prices
                    old_price_text = f"{product['price']} TL" if product['price'] else "Fiyat bilgisi yok"
                    new_price_text = f"{product_info['price']} TL" if product_info['price'] else "Fiyat bilgisi yok"
                    
                    # Create notification message
                    message = f"🔔 *Takip Ettiğiniz Ürün Güncellendi!*\n\n"
                    message += f"📌 *{product_info['title']}*\n\n"
                    
                    # Price change message
                    if price_changed and product_info['price'] and product['price']:
                        price_diff = float(product_info['price']) - float(product['price'])
                        if price_diff < 0:
                            message += f"💰 *Fiyat:* {old_price_text} ➡️ {new_price_text} (🎉 {abs(price_diff):.2f} TL indirim!)\n"
                        else:
                            message += f"💰 *Fiyat:* {old_price_text} ➡️ {new_price_text} (📈 {price_diff:.2f} TL artış)\n"
                    elif price_changed:
                        message += f"💰 *Fiyat:* {old_price_text} ➡️ {new_price_text}\n"
                    
                    # Stock change message
                    if stock_changed:
                        if product_info['in_stock']:
                            message += f"🏪 *Stok Durumu:* ❌ Stokta değil ➡️ ✅ Stokta (Stoka girdi!)\n"
                        else:
                            message += f"🏪 *Stok Durumu:* ✅ Stokta ➡️ ❌ Stokta değil (Tükendi!)\n"
                    
                    # Add URL
                    message += f"\n[Ürün Sayfasını Ziyaret Et]({product['url']})"
                    
                    # Add action buttons
                    keyboard = [
                        [
                            InlineKeyboardButton("🔄 Güncelle", callback_data=f"check_{product['id']}"),
                            InlineKeyboardButton("❌ Takibi Bırak", callback_data=f"remove_{product['id']}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Notify user
                    await self.application.bot.send_message(
                        chat_id=product['user_id'],
                        text=message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                    
                    # Update product in database
                    self.db.update_product(
                        product_id=product['id'],
                        title=product_info['title'],
                        price=product_info['price'],
                        in_stock=product_info['in_stock']
                    )
                    
                    logger.info(f"Notified user {product['user_id']} about changes to product {product['id']}")
                
            except Exception as e:
                logger.error(f"Error checking product {product['id']}: {e}", exc_info=True)
        
        logger.info("Completed periodic check of all products")

    def start(self):
        """Start the bot"""
        logger.info("Starting the Telegram bot")
        
        # Set up the periodic product check job
        job_queue = self.application.job_queue
        job_queue.run_repeating(
            self._scheduled_check_products, 
            interval=timedelta(minutes=PRODUCT_CHECK_INTERVAL_MINUTES),
            first=timedelta(minutes=1)  # Start first check after 1 minute
        )
        logger.info(f"Scheduled product checks every {PRODUCT_CHECK_INTERVAL_MINUTES} minutes")
        
        # Start the bot with polling
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    def stop(self):
        """Stop the bot"""
        logger.info("Stopping the Telegram bot")
        
        # Stop the bot
        if self.application:
            self.application.stop()
