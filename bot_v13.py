#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import traceback
from datetime import datetime, timedelta
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, CallbackQueryHandler,
    CallbackContext, Filters, ConversationHandler
)

from database import Database
from scraper import ProductScraper
from config import STORES, HEADERS, PRODUCT_CHECK_INTERVAL_MINUTES, ADMIN_USER_ID, MSG_UNAUTHORIZED, MSG_ADMIN_ONLY, GENERIC_STORE_ID

# Configure logger for this module
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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
        
        # Create updater and dispatcher
        self.updater = Updater(token=self.token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Add handlers
        self._add_handlers()
        
        logger.info("Bot initialized successfully")
    
    def _add_handlers(self):
        """Add all command and callback handlers to the dispatcher"""
        # Command handlers
        self.dispatcher.add_handler(CommandHandler("start", self._start_command))
        self.dispatcher.add_handler(CommandHandler("help", self._help_command))
        self.dispatcher.add_handler(CommandHandler("list", self._list_command))
        self.dispatcher.add_handler(CommandHandler("reboot", self._reboot_command))
        self.dispatcher.add_handler(CommandHandler("authorize", self._authorize_command))
        
        # Direct URL handler - must be before the conversation handler
        # This handles URLs directly sent to the bot to track products
        url_pattern = r'^https?://[^\s]+$'
        self.dispatcher.add_handler(
            MessageHandler(
                Filters.text & ~Filters.command & Filters.regex(url_pattern),
                self._direct_url_handler
            )
        )
        
        # Track product conversation flow
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("track", self._track_command)],
            states={
                SELECTING_STORE: [
                    CallbackQueryHandler(self._store_selected, pattern=r'^store_\w+$')
                ],
                ENTERING_URL: [
                    MessageHandler(Filters.text & ~Filters.command, self._url_received)
                ],
                CONFIRMING_PRODUCT: [
                    CallbackQueryHandler(self._confirm_product, pattern=r'^confirm_(yes|no)$')
                ]
            },
            fallbacks=[CommandHandler("cancel", self._cancel_tracking)],
        )
        self.dispatcher.add_handler(conv_handler)
        
        # Product action handlers
        self.dispatcher.add_handler(CallbackQueryHandler(self._remove_product, pattern=r'^remove_\d+$'))
        self.dispatcher.add_handler(CallbackQueryHandler(self._check_product, pattern=r'^check_\d+$'))
        self.dispatcher.add_handler(CallbackQueryHandler(self._confirm_direct_product, pattern=r'^confirm_direct_(yes|no)$'))
        
        # Error handler
        self.dispatcher.add_error_handler(self._error_handler)

    def _start_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /start command - introduce the bot and its functions"""
        user = update.effective_user
        
        # Ensure user exists in database - check for authorization
        self.db.add_user(update.effective_user.id)
        
        # Check if user is authorized to use the bot
        if not self.db.is_authorized(user.id) and not self.db.is_admin(user.id):
            update.message.reply_text(MSG_UNAUTHORIZED)
            logger.warning(f"Unauthorized access attempt by user {user.id}")
            return
            
        # User is authorized or admin
        is_admin = self.db.is_admin(user.id)
        
        admin_commands = ""
        if is_admin:
            admin_commands = f"👑 *Admin Komutları:*\n" \
                            f"/reboot - Botu yeniden başlat\n" \
                            f"/authorize - Yeni kullanıcı ekle/yetkisi değiştir\n\n"
        
        # Customize message for girlfriend
        if not is_admin:
            update.message.reply_markdown(
                f"💖 İyi günler aşkım, ne yapmak istersin?\n\n"
                f"🛠 *Komutlar:*\n"
                f"/track - Yeni bir ürün takibi başlat\n"
                f"/list - Takip ettiğin ürünleri listele\n"
                f"/help - Yardım menüsü\n\n"
                f"Takip etmek istediğin bir ürün için doğrudan link gönderebilir veya /track komutunu kullanabilirsin."
            )
        else:
            update.message.reply_markdown(
                f"👋 Merhaba {user.first_name}!\n\n"
                f"🛠 *Komutlar:*\n"
                f"/track - Yeni bir ürün takibi başlat\n"
                f"/list - Takip ettiğin ürünleri listele\n"
                f"/help - Yardım menüsü\n"
                f"{admin_commands}"
                f"Takip etmek istediğin bir ürün için doğrudan link gönderebilir veya /track komutunu kullanabilirsin."
            )
        
    def _reboot_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /reboot command - restart the bot when there are issues"""
        user = update.effective_user
        
        # Check if user is admin
        if not self.db.is_admin(user.id):
            update.message.reply_text(MSG_ADMIN_ONLY)
            logger.warning(f"Unauthorized reboot attempt by user {user.id}")
            return
        
        # User is admin, proceed with reboot
        update.message.reply_text(
            "🔄 Bot yeniden başlatılıyor...\n\n"
            "Bu işlem birkaç saniye sürebilir. Lütfen bekleyin."
        )
        
        logger.info(f"Bot reboot requested by admin user {user.id}")
        
        # Schedule the reboot to occur after sending the message
        def _do_reboot():
            try:
                self.reboot()
                logger.info("Bot rebooted successfully")
            except Exception as e:
                logger.error(f"Error during reboot: {e}", exc_info=True)
        
        # Run the reboot in a separate thread to avoid blocking
        import threading
        reboot_thread = threading.Thread(target=_do_reboot)
        reboot_thread.daemon = True
        reboot_thread.start()

    def _help_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /help command - display help information"""
        user = update.effective_user
        is_admin = self.db.is_admin(user.id)
        
        admin_commands = ""
        if is_admin:
            admin_commands = "*Admin Komutları:*\n" \
                           "/reboot - Botu yeniden başlat\n" \
                           "/authorize - Yeni kullanıcı ekle/yetkisi değiştir\n\n"
        
        update.message.reply_markdown(
            "📘 *Bot Kullanım Rehberi*\n\n"
            "*Komutlar:*\n"
            "/start - Botu başlat\n"
            "/track - Yeni bir ürün takibi başlat\n"
            "/list - Takip ettiğiniz ürünleri listele\n"
            "/help - Bu yardım mesajını göster\n"
            f"{admin_commands}"
            "*Ürün Takibi Nasıl Çalışır:*\n"
            "1. Herhangi bir e-ticaret sitesinden ürün linkini doğrudan sohbete gönderin\n"
            "   *VEYA*\n"
            "1. /track komutunu kullanın\n"
            "2. Listeden bir mağaza seçin\n"
            "3. Takip etmek istediğiniz ürünün URL'sini gönderin\n"
            "4. Bilgileri onaylayın\n\n"
            "*Desteklenen Özel Mağaza Özellikleri:*\n" + 
            "\n".join(f"• {store['name']}" for store in [s for s in STORES if s['id'] != GENERIC_STORE_ID]) + 
            "\n\n*Not:* Diğer tüm e-ticaret sitelerinden de ürün takibi yapabilirsiniz!"
        )

    def _track_command(self, update: Update, context: CallbackContext) -> int:
        """Start the product tracking conversation flow"""
        user = update.effective_user
        
        # Check if user is authorized
        if not self.db.is_authorized(user.id) and not self.db.is_admin(user.id):
            update.message.reply_text(MSG_UNAUTHORIZED)
            logger.warning(f"Unauthorized tracking attempt by user {user.id}")
            return ConversationHandler.END
            
        # Create keyboard with store options
        keyboard = []
        for store in STORES:
            keyboard.append([InlineKeyboardButton(
                text=store['name'], 
                callback_data=f"store_{store['id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "Hangi mağazadan ürün takip etmek istiyorsunuz?",
            reply_markup=reply_markup
        )
        
        return SELECTING_STORE

    def _store_selected(self, update: Update, context: CallbackContext) -> int:
        """Handle store selection for product tracking"""
        query = update.callback_query
        query.answer()
        
        store_id = query.data.split('_')[1]
        context.user_data['selected_store'] = store_id
        
        # Find store name
        store_name = next((s['name'] for s in STORES if s['id'] == store_id), "Seçilen mağaza")
        
        query.edit_message_text(
            f"{store_name} mağazasından bir ürün takip edeceksiniz.\n\n"
            f"Lütfen ürün sayfasının tam URL'sini girin:"
        )
        
        return ENTERING_URL

    def _url_received(self, update: Update, context: CallbackContext) -> int:
        """Process the product URL entered by the user"""
        url = update.message.text.strip()
        store_id = context.user_data.get('selected_store')
        
        # Save URL to context
        context.user_data['product_url'] = url
        
        update.message.reply_text("Ürün bilgileri alınıyor, lütfen bekleyin...")
        
        try:
            # Check if we need to use generic scraper for unsupported sites
            if store_id == GENERIC_STORE_ID:
                # Use generic scraper
                product_info = self.scraper.get_product_info(GENERIC_STORE_ID, url)
            else:
                # Verify URL matches store domain
                store = next((s for s in STORES if s['id'] == store_id), None)
                if store and store['domain']:
                    parsed_url = urlparse(url)
                    if store['domain'] not in parsed_url.netloc:
                        update.message.reply_text(
                            f"⚠️ Girdiğiniz URL {store['name']} mağazasına ait değil gibi görünüyor.\n\n"
                            f"Lütfen {store['domain']} adresinden bir ürün URL'si girin veya 'Diğer Site' seçeneğiyle herhangi bir siteyi deneyebilirsiniz."
                        )
                        return ConversationHandler.END
                
                # Get product info using scraper
                product_info = self.scraper.get_product_info(store_id, url)
            
            if not product_info:
                update.message.reply_text(
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
            
            update.message.reply_text(
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
            update.message.reply_text(
                "⚠️ Ürün bilgilerini alırken bir hata oluştu. Lütfen geçerli bir URL girdiğinizden emin olun ve tekrar deneyin."
            )
            return ConversationHandler.END

    def _confirm_product(self, update: Update, context: CallbackContext) -> int:
        """Handle product confirmation for tracking"""
        query = update.callback_query
        query.answer()
        
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
                
                query.edit_message_text(
                    f"✅ *{product_info['title']}* ürünü başarıyla takip listesine eklendi.\n\n"
                    f"Fiyat veya stok durumu değiştiğinde sizi bilgilendireceğim!\n\n"
                    f"Takip ettiğiniz tüm ürünleri görmek için /list komutunu kullanabilirsiniz.",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Error adding product: {e}", exc_info=True)
                query.edit_message_text(
                    "⚠️ Ürün eklenirken bir hata oluştu. Lütfen tekrar deneyin."
                )
        else:
            query.edit_message_text(
                "İşlem iptal edildi. Başka bir ürün eklemek için /track komutunu kullanabilirsiniz."
            )
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END

    def _cancel_tracking(self, update: Update, context: CallbackContext) -> int:
        """Cancel the product tracking conversation"""
        update.message.reply_text(
            "Ürün takip işlemi iptal edildi. Ana menüye dönmek için /start komutunu kullanabilirsiniz."
        )
        context.user_data.clear()
        return ConversationHandler.END

    def _list_command(self, update: Update, context: CallbackContext) -> None:
        """List all tracked products for the user"""
        user = update.effective_user
        
        # Check if user is authorized
        if not self.db.is_authorized(user.id) and not self.db.is_admin(user.id):
            update.message.reply_text(MSG_UNAUTHORIZED)
            logger.warning(f"Unauthorized list attempt by user {user.id}")
            return
            
        # Get user's products
        user_id = user.id
        products = self.db.get_user_products(user_id)
        
        if not products:
            update.message.reply_text(
                "📝 Henüz takip ettiğiniz bir ürün bulunmuyor.\n\n"
                "Ürün eklemek için /track komutunu kullanabilirsiniz."
            )
            return
        
        update.message.reply_text(
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
            
            update.message.reply_text(
                f"📌 *{product['title']}*\n"
                f"💰 *Fiyat:* {price_text}\n"
                f"🏪 *Stok Durumu:* {'✅ Stokta' if product['in_stock'] else '❌ Stokta değil'}\n"
                f"🛒 *Mağaza:* {store_name}\n"
                f"📅 *Eklenme:* {product['created_at']}\n"
                f"📅 *Son Güncelleme:* {product['updated_at']}\n",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    def _remove_product(self, update: Update, context: CallbackContext) -> None:
        """Remove a product from tracking list"""
        query = update.callback_query
        query.answer()
        
        product_id = int(query.data.split('_')[1])
        user_id = update.effective_user.id
        
        # Check product ownership
        if not self.db.is_product_owner(user_id, product_id):
            query.edit_message_text("⚠️ Bu ürünü silme yetkiniz yok.")
            return
        
        product = self.db.get_product(product_id)
        success = self.db.remove_product(product_id)
        
        if success and product:
            query.edit_message_text(
                f"✅ *{product['title']}* ürünü takip listenizden kaldırıldı.",
                parse_mode='Markdown'
            )
        else:
            query.edit_message_text(
                "⚠️ Ürün kaldırılırken bir hata oluştu. Lütfen tekrar deneyin."
            )

    def _direct_url_handler(self, update: Update, context: CallbackContext) -> None:
        """Handle direct URL messages sent to the bot for product tracking"""
        user = update.effective_user
        url = update.message.text.strip()
        
        # Check if user is authorized
        if not self.db.is_authorized(user.id) and not self.db.is_admin(user.id):
            update.message.reply_text(MSG_UNAUTHORIZED)
            logger.warning(f"Unauthorized direct URL tracking attempt by user {user.id}")
            return
        
        update.message.reply_text("Ürün bilgileri alınıyor, lütfen bekleyin...")
        
        try:
            # Always use generic scraper for direct URLs
            product_info = self.scraper.get_product_info(GENERIC_STORE_ID, url)
            
            if not product_info:
                update.message.reply_text(
                    "⚠️ Bu URL'den ürün bilgilerini alamadım. Lütfen URL'i kontrol edip tekrar deneyin."
                )
                return
            
            # Show product info and ask for confirmation
            keyboard = [
                [
                    InlineKeyboardButton("✓ Evet", callback_data="confirm_direct_yes"),
                    InlineKeyboardButton("✗ Hayır", callback_data="confirm_direct_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Format price with currency
            price_formatted = f"{product_info['price']} TL" if product_info['price'] else "Fiyat bilgisi alınamadı"
            
            # Store the information in user_data for later use
            context.user_data['direct_url'] = url
            context.user_data['direct_product_info'] = product_info
            
            update.message.reply_text(
                f"*Ürün Bilgileri:*\n\n"
                f"📌 *İsim:* {product_info['title']}\n"
                f"💰 *Fiyat:* {price_formatted}\n"
                f"🏪 *Stok Durumu:* {'✅ Stokta' if product_info['in_stock'] else '❌ Stokta değil'}\n\n"
                f"Bu ürünü takip listesine eklemek istiyor musunuz?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error processing direct URL: {e}", exc_info=True)
            update.message.reply_text(
                "⚠️ Ürün bilgilerini alırken bir hata oluştu. Lütfen geçerli bir URL girdiğinizden emin olun ve tekrar deneyin."
            )
            
    def _confirm_direct_product(self, update: Update, context: CallbackContext) -> None:
        """Handle confirmation for direct URL product tracking"""
        query = update.callback_query
        query.answer()
        
        user_choice = query.data.split('_')[2]  # confirm_direct_yes/no -> yes/no
        
        if user_choice == 'yes':
            try:
                # Get data from context
                url = context.user_data.get('direct_url')
                product_info = context.user_data.get('direct_product_info')
                
                if not url or not product_info:
                    query.edit_message_text(
                        "⚠️ İşlem zaman aşımına uğradı. Lütfen linki tekrar gönderin."
                    )
                    context.user_data.clear()
                    return
                
                # Add product to database using generic store
                product_id = self.db.add_product(
                    user_id=update.effective_user.id,
                    store_id=GENERIC_STORE_ID,
                    url=url,
                    title=product_info['title'],
                    price=product_info['price'],
                    in_stock=product_info['in_stock']
                )
                
                query.edit_message_text(
                    f"✅ *{product_info['title']}* ürünü başarıyla takip listesine eklendi.\n\n"
                    f"Fiyat veya stok durumu değiştiğinde sizi bilgilendireceğim!\n\n"
                    f"Takip ettiğiniz tüm ürünleri görmek için /list komutunu kullanabilirsiniz.",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Error adding direct product: {e}", exc_info=True)
                query.edit_message_text(
                    "⚠️ Ürün eklenirken bir hata oluştu. Lütfen tekrar deneyin."
                )
        else:
            query.edit_message_text(
                "İşlem iptal edildi. Başka bir ürün eklemek istediğinizde doğrudan linki gönderebilir veya /track komutunu kullanabilirsiniz."
            )
        
        # Clear user data
        context.user_data.clear()
    
    def _authorize_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /authorize command - add or modify user authorization"""
        user = update.effective_user
        
        # Check if user is admin
        if not self.db.is_admin(user.id):
            update.message.reply_text(MSG_ADMIN_ONLY)
            logger.warning(f"Unauthorized authorize attempt by user {user.id}")
            return
        
        # Check if command has required arguments
        if not context.args or len(context.args) < 2:
            update.message.reply_text(
                "⚠️ Eksik parametreler.\n\n"
                "Kullanım: /authorize <user_id> <durum>\n"
                "Örnek: /authorize 123456789 true"
            )
            return
        
        # Parse arguments
        try:
            target_user_id = int(context.args[0])
            is_authorized = context.args[1].lower() in ["true", "1", "yes", "evet"]
            
            # Update user authorization
            success = self.db.set_user_authorization(target_user_id, is_authorized)
            
            if success:
                status_text = "yetkilendirildi" if is_authorized else "yetkisi kaldırıldı"
                update.message.reply_text(
                    f"✅ Kullanıcı {target_user_id} başarıyla {status_text}."
                )
                logger.info(f"Admin {user.id} authorized user {target_user_id} as {is_authorized}")
            else:
                update.message.reply_text(
                    f"⚠️ Kullanıcı {target_user_id} yetkilendirilemedi. Kullanıcının önce botu başlatması gerekebilir."
                )
        except ValueError:
            update.message.reply_text("⚠️ Geçersiz kullanıcı ID'si. Lütfen sayısal bir değer girin.")
        except Exception as e:
            logger.error(f"Error authorizing user: {e}", exc_info=True)
            update.message.reply_text(f"⚠️ İşlem sırasında bir hata oluştu: {str(e)}")
            
    def _check_product(self, update: Update, context: CallbackContext) -> None:
        """Check current status of a product"""
        query = update.callback_query
        query.answer()
        
        product_id = int(query.data.split('_')[1])
        user_id = update.effective_user.id
        
        # Check product ownership
        if not self.db.is_product_owner(user_id, product_id):
            query.edit_message_text("⚠️ Bu ürünü kontrol etme yetkiniz yok.")
            return
        
        # Get product from database
        product = self.db.get_product(product_id)
        
        if not product:
            query.edit_message_text("⚠️ Ürün bulunamadı.")
            return
            
        query.edit_message_text(
            "Ürün bilgileri güncelleniyor, lütfen bekleyin..."
        )
        
        try:
            # Get current product info
            product_info = self.scraper.get_product_info(product['store_id'], product['url'])
            
            if not product_info:
                query.edit_message_text(
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
            
            query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error checking product {product_id}: {e}", exc_info=True)
            query.edit_message_text(
                "⚠️ Ürün güncellenirken bir hata oluştu. Lütfen tekrar deneyin."
            )

    def _error_handler(self, update: object, context: CallbackContext) -> None:
        """Handle errors in bot updates"""
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
        
        try:
            # Get the error message
            tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
            tb_string = ''.join(tb_list)
            
            # Construct error message
            error_message = f"❌ *Bir hata oluştu*\n\n"
            error_message += f"Hata detayları:\n`{context.error}`\n\n"
            
            # Send error message to user if it's a critical error and there's an update
            if update and update.effective_message:
                update.effective_message.reply_text(
                    "⚠️ Üzgünüm, bir hata oluştu. Lütfen daha sonra tekrar deneyin."
                )
                
            # Log detailed error
            logger.error(f"Update: {update}\nError: {tb_string}")
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    def _scheduled_check_products(self, context: CallbackContext) -> None:
        """Callback for scheduled product check job"""
        logger.info("Running scheduled product check")
        self._check_all_products()

    def _check_all_products(self) -> None:
        """Check all products for updates and notify users"""
        logger.info("Checking all products for updates")
        
        # Get all products
        products = self.db.get_all_products()
        
        # Check each product
        for product in products:
            try:
                # Get current product info
                product_info = self.scraper.get_product_info(product['store_id'], product['url'])
                
                if not product_info:
                    logger.warning(f"Could not get info for product {product['id']}")
                    continue
                
                # Check if price or stock changed
                price_changed = product_info['price'] != product['price']
                stock_changed = product_info['in_stock'] != product['in_stock']
                
                # If something changed, update DB and notify user
                if price_changed or stock_changed:
                    # Update in database
                    self.db.update_product(
                        product_id=product['id'],
                        title=product_info['title'],
                        price=product_info['price'],
                        in_stock=product_info['in_stock']
                    )
                    
                    # Create notification message
                    message = f"📢 *Ürün Güncellemesi*\n\n"
                    message += f"📌 *{product_info['title']}*\n\n"
                    
                    # Add price information if changed
                    if price_changed and product_info['price'] and product['price']:
                        old_price = float(product['price'])
                        new_price = float(product_info['price'])
                        price_diff = new_price - old_price
                        
                        if price_diff < 0:
                            message += f"💰 *Fiyat Düştü!*\n"
                            message += f"{old_price:.2f} TL ➡️ {new_price:.2f} TL\n"
                            message += f"({abs(price_diff):.2f} TL indirim! 🎉)\n\n"
                        else:
                            message += f"💰 *Fiyat Arttı!*\n"
                            message += f"{old_price:.2f} TL ➡️ {new_price:.2f} TL\n"
                            message += f"({price_diff:.2f} TL artış 📈)\n\n"
                    
                    # Add stock information if changed
                    if stock_changed:
                        if product_info['in_stock']:
                            message += f"🏪 *Stok Durumu:* Stoka Girdi! ✅\n\n"
                        else:
                            message += f"🏪 *Stok Durumu:* Tükendi! ❌\n\n"
                    
                    # Add store information and link
                    store_name = next((s['name'] for s in STORES if s['id'] == product['store_id']), "Bilinmeyen Mağaza")
                    message += f"🛒 *Mağaza:* {store_name}\n"
                    message += f"🔗 [Ürüne Git]({product['url']})"
                    
                    # TODO: Send the notification to the user - needs bot instance
                    # We'll handle this in actual notification code
                    logger.info(f"Would notify user {product['user_id']} about product {product['id']}")
                    
            except Exception as e:
                logger.error(f"Error checking product {product['id']}: {e}", exc_info=True)
        
        logger.info("Completed periodic check of all products")

    def start(self):
        """Start the bot"""
        logger.info("Starting the Telegram bot")
        
        # Set up the periodic product check job
        job_queue = self.updater.job_queue
        job_queue.run_repeating(
            self._scheduled_check_products, 
            interval=PRODUCT_CHECK_INTERVAL_MINUTES * 60,  # Convert to seconds
            first=60  # Start first check after 1 minute (in seconds)
        )
        logger.info(f"Scheduled product checks every {PRODUCT_CHECK_INTERVAL_MINUTES} minutes")
        
        # Start the bot with polling
        self.updater.start_polling()
    
    def stop(self):
        """Stop the bot"""
        logger.info("Stopping the Telegram bot")
        
        # Stop the bot
        if self.updater:
            self.updater.stop()
            
    def reboot(self):
        """Reboot the bot by stopping and starting again"""
        logger.info("Rebooting the Telegram bot")
        self.stop()
        self.start()
        logger.info("Telegram bot rebooted successfully")