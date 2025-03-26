import logging
import re
from typing import Dict, Optional, Any, List
import traceback
import time
import random
import json
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import STORES, GENERIC_STORE_ID

# Configure logger for this module
logger = logging.getLogger(__name__)

class ProductScraper:
    """Class to handle product scraping from various e-commerce websites"""
    
    def __init__(self, headers: Dict[str, str]):
        """Initialize the scraper with request headers"""
        self.headers = headers
        self.session = requests.Session()
        self.session.headers.update(headers)
        
        # Add more realistic browser fingerprint to avoid bot detection
        self.session.headers.update({
            'sec-ch-ua': '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        })
        
        # Random user agents to rotate and avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.54',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/111.0.5563.101 Mobile/15E148 Safari/604.1'
        ]
    
    def get_product_info(self, store_id: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Get product information from a store using the appropriate scraper
        
        Args:
            store_id: ID of the store to scrape from
            url: URL of the product page
            
        Returns:
            Dictionary with product information or None if scraping failed
        """
        # Initialize response variable to None to avoid "possibly unbound" errors
        response = None
        
        # Define fallback result here at the top level
        fallback_result = {
            'title': f"Ürün ({url.split('/')[-1]})",
            'price': None,
            'in_stock': True
        }
        
        try:
            # Find store configuration
            store = next((s for s in STORES if s['id'] == store_id), None)
            if not store:
                logger.error(f"Store with ID {store_id} not found")
                return None
            
            # Add random delay to avoid being blocked (0.5-2s)
            time.sleep(random.uniform(0.5, 2.0))
            
            try:
                # Get the product page with increased timeout and retries
                for attempt in range(3):  # Try up to 3 times
                    try:
                        # Rotate user agents to avoid detection
                        self.session.headers['User-Agent'] = random.choice(self.user_agents)
                        
                        # Add randomized delay to seem more human-like
                        time.sleep(random.uniform(1.0, 3.0))
                        
                        # Add referer for some sites that check this
                        parsed_url = urlparse(url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        referer = f"{base_url}/"
                        self.session.headers['Referer'] = referer
                        
                        # Set cookies and handle cloudflare if needed
                        response = self.session.get(url, timeout=20, allow_redirects=True)
                        
                        # Check for anti-bot challenges and adapt
                        if "captcha" in response.text.lower() or "robot" in response.text.lower():
                            logger.warning(f"Anti-bot measures detected on {url}")
                            # Use different headers and wait longer
                            time.sleep(random.uniform(3.0, 5.0))
                            self.session.headers['User-Agent'] = random.choice(self.user_agents)
                            response = self.session.get(url, timeout=20)
                        
                        response.raise_for_status()
                        break  # If successful, break out of retry loop
                    except (requests.RequestException, requests.Timeout) as e:
                        if attempt < 2:  # Only retry if we haven't reached max attempts
                            logger.warning(f"Retry {attempt+1} for URL {url}: {e}")
                            time.sleep(2 * (attempt + 1))  # Exponential backoff
                        else:
                            # On last attempt failure, raise to outer try block
                            raise
                
                # Check if we got a valid response
                if not response:
                    logger.error(f"Failed to get response from {url} after 3 attempts")
                    return fallback_result if store_id == GENERIC_STORE_ID else None
                
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Call the appropriate scraper method based on store ID
                if store_id == 'trendyol':
                    return self._scrape_trendyol(soup, url)
                elif store_id == 'hepsiburada':
                    return self._scrape_hepsiburada(soup, url)
                elif store_id == 'n11':
                    return self._scrape_n11(soup, url)
                elif store_id == 'amazon':
                    return self._scrape_amazon(soup, url)
                elif store_id == 'teknosa':
                    return self._scrape_teknosa(soup, url)
                elif store_id == 'mediamarkt':
                    return self._scrape_mediamarkt(soup, url)
                elif store_id == GENERIC_STORE_ID:
                    # For generic store, if scraping fails, at least return a basic result
                    result = self._scrape_generic(soup, url)
                    # Check if result has a valid title
                    if not result['title'] or len(result['title']) < 3:
                        # Try to extract basic info from HTML title
                        title_tag = soup.find('title')
                        if title_tag and title_tag.text:
                            result['title'] = title_tag.text.strip()
                    return result
                else:
                    logger.warning(f"No scraper implemented for store ID {store_id}")
                    return None
                    
            except requests.RequestException as e:
                logger.error(f"Request error while scraping {url}: {e}")
                # For generic store, return basic fallback result instead of None
                if store_id == GENERIC_STORE_ID:
                    logger.info(f"Using fallback result for {url}")
                    return fallback_result
                raise  # Re-raise for other stores to be caught by outer try-except
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            logger.error(traceback.format_exc())
            
            # If generic store scraping completely failed, return basic info
            if store_id == GENERIC_STORE_ID:
                return fallback_result
        
        return None
    
    def _clean_price(self, price_str: str) -> Optional[float]:
        """
        Clean price string and convert to float
        
        Args:
            price_str: String containing the price
            
        Returns:
            Price as float or None if conversion failed
        """
        if not price_str:
            return None
        
        # Remove non-numeric characters except dot/comma
        price_str = re.sub(r'[^\d.,]', '', price_str)
        
        # Replace comma with dot for decimal conversion
        price_str = price_str.replace('.', '').replace(',', '.')
        
        # Extract the first valid number
        match = re.search(r'\d+(?:\.\d+)?', price_str)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        
        return None
    
    def _scrape_trendyol(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Scrape product information from Trendyol
        
        Args:
            soup: BeautifulSoup object of the product page
            url: URL of the product page
            
        Returns:
            Dictionary with product information
        """
        # Initialize result
        result = {
            'title': None,
            'price': None,
            'in_stock': False
        }
        
        # Extract title
        title_tag = soup.select_one('h1.pr-new-br') or soup.select_one('h1.product-name')
        if title_tag:
            result['title'] = title_tag.text.strip()
        
        # Extract price
        price_tag = soup.select_one('.prc-dsc') or soup.select_one('.product-price')
        if price_tag:
            result['price'] = self._clean_price(price_tag.text)
        
        # Check stock status
        sold_out = soup.select_one('.pr-in-cn') or soup.select_one('.soldOutProductCt')
        add_to_cart = soup.select_one('.add-to-basket') or soup.select_one('.add-to-cart')
        
        # If there's no sold out message and add to cart button exists, product is in stock
        result['in_stock'] = sold_out is None and add_to_cart is not None
        
        return result
    
    def _scrape_hepsiburada(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Scrape product information from Hepsiburada
        
        Args:
            soup: BeautifulSoup object of the product page
            url: URL of the product page
            
        Returns:
            Dictionary with product information
        """
        # Initialize result
        result = {
            'title': None,
            'price': None,
            'in_stock': False
        }
        
        # Extract title
        title_tag = soup.select_one('h1.product-name') or soup.select_one('h1[data-bind="markupText: product.name"]')
        if title_tag:
            result['title'] = title_tag.text.strip()
        
        # Extract price
        price_tag = soup.select_one('[data-bind="markupText: product.price.currentPrice"]') or soup.select_one('.product-price')
        if price_tag:
            result['price'] = self._clean_price(price_tag.text)
        
        # Check stock status
        sold_out = soup.select_one('.product-status-text') or soup.select_one('.out-of-stock-text')
        add_to_cart = soup.select_one('#addToCart') or soup.select_one('.add-to-cart')
        
        # If there's no sold out message and add to cart button exists, product is in stock
        result['in_stock'] = (sold_out is None or 'tükendi' not in sold_out.text.lower()) and add_to_cart is not None
        
        return result
    
    def _scrape_n11(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Scrape product information from N11
        
        Args:
            soup: BeautifulSoup object of the product page
            url: URL of the product page
            
        Returns:
            Dictionary with product information
        """
        # Initialize result
        result = {
            'title': None,
            'price': None,
            'in_stock': False
        }
        
        # Extract title
        title_tag = soup.select_one('h1.proName') or soup.select_one('h1.productName')
        if title_tag:
            result['title'] = title_tag.text.strip()
        
        # Extract price
        price_tag = soup.select_one('.newPrice') or soup.select_one('.price')
        if price_tag:
            # Try to find the actual price span
            price_span = price_tag.select_one('ins') or price_tag
            result['price'] = self._clean_price(price_span.text)
        
        # Check stock status
        sold_out = soup.select_one('.unf-p-summary-out-of-stock') or soup.select_one('.outOfStock')
        add_to_cart = soup.select_one('#addBasket') or soup.select_one('.btnAddBasket')
        
        # If there's no sold out message and add to cart button exists, product is in stock
        result['in_stock'] = sold_out is None and add_to_cart is not None
        
        return result
    
    def _scrape_amazon(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Scrape product information from Amazon
        
        Args:
            soup: BeautifulSoup object of the product page
            url: URL of the product page
            
        Returns:
            Dictionary with product information
        """
        # Initialize result
        result = {
            'title': None,
            'price': None,
            'in_stock': False
        }
        
        # Extract title
        title_tag = soup.select_one('#productTitle')
        if title_tag:
            result['title'] = title_tag.text.strip()
        
        # Extract price
        price_tag = soup.select_one('.a-price .a-offscreen') or soup.select_one('#priceblock_ourprice')
        if price_tag:
            result['price'] = self._clean_price(price_tag.text)
        
        # Check stock status
        availability = soup.select_one('#availability')
        if availability:
            result['in_stock'] = 'stokta' in availability.text.lower() or 'in stock' in availability.text.lower()
        else:
            add_to_cart = soup.select_one('#add-to-cart-button')
            result['in_stock'] = add_to_cart is not None
        
        return result
    
    def _scrape_teknosa(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Scrape product information from Teknosa
        
        Args:
            soup: BeautifulSoup object of the product page
            url: URL of the product page
            
        Returns:
            Dictionary with product information
        """
        # Initialize result
        result = {
            'title': None,
            'price': None,
            'in_stock': False
        }
        
        # Extract title
        title_tag = soup.select_one('h1.pdp-title')
        if title_tag:
            result['title'] = title_tag.text.strip()
        
        # Extract price
        price_tag = soup.select_one('.product-price')
        if price_tag:
            result['price'] = self._clean_price(price_tag.text)
        
        # Check stock status
        sold_out = soup.select_one('.add-to-cart--out-of-stock')
        add_to_cart = soup.select_one('.add-to-cart:not(.add-to-cart--out-of-stock)')
        
        # If there's no sold out message and add to cart button exists, product is in stock
        result['in_stock'] = sold_out is None and add_to_cart is not None
        
        return result
    
    def _scrape_mediamarkt(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Scrape product information from MediaMarkt
        
        Args:
            soup: BeautifulSoup object of the product page
            url: URL of the product page
            
        Returns:
            Dictionary with product information
        """
        # Initialize result
        result = {
            'title': None,
            'price': None,
            'in_stock': False
        }
        
        # Extract title
        title_tag = soup.select_one('h1.product-title')
        if title_tag:
            result['title'] = title_tag.text.strip()
        
        # Extract price
        price_tag = soup.select_one('.price')
        if price_tag:
            result['price'] = self._clean_price(price_tag.text)
        
        # Check stock status
        availability = soup.select_one('.availability')
        if availability:
            result['in_stock'] = 'stokta' in availability.text.lower() or 'in stock' in availability.text.lower()
        else:
            add_to_cart = soup.select_one('.add-to-cart')
            result['in_stock'] = add_to_cart is not None
        
        return result
        
    def _scrape_generic(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Generic scraper that works with most e-commerce websites
        
        Args:
            soup: BeautifulSoup object of the product page
            url: URL of the product page
            
        Returns:
            Dictionary with product information
        """
        # Initialize result
        result = {
            'title': None,
            'price': None,
            'in_stock': False
        }
        
        # First try JSON-LD data which is more reliable and structured
        json_ld_data = None
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                json_data = json.loads(script.string)
                # Check if it's product data
                if isinstance(json_data, dict) and (json_data.get('@type') == 'Product' or 
                                                   (isinstance(json_data.get('@graph'), list) and 
                                                    any(item.get('@type') == 'Product' for item in json_data.get('@graph', [])))):
                    json_ld_data = json_data
                    break
                elif isinstance(json_data, list):
                    for item in json_data:
                        if isinstance(item, dict) and item.get('@type') == 'Product':
                            json_ld_data = item
                            break
            except (json.JSONDecodeError, AttributeError):
                continue
                
        # If JSON-LD data was found, extract product info
        if json_ld_data:
            logger.info(f"Found JSON-LD product data for {url}")
            
            # Extract from @graph if needed
            if isinstance(json_ld_data, dict) and '@graph' in json_ld_data:
                for item in json_ld_data.get('@graph', []):
                    if isinstance(item, dict) and item.get('@type') == 'Product':
                        json_ld_data = item
                        break
            
            # Extract title
            if json_ld_data.get('name'):
                result['title'] = json_ld_data.get('name')
                
            # Extract price
            if isinstance(json_ld_data.get('offers'), dict):
                offers = json_ld_data.get('offers')
                # Check price and availability
                price = offers.get('price')
                if price:
                    try:
                        result['price'] = float(price)
                    except (ValueError, TypeError):
                        # Try cleaning the price
                        result['price'] = self._clean_price(str(price))
                
                # Check availability
                availability = offers.get('availability', '').lower()
                if availability:
                    result['in_stock'] = 'instock' in availability or 'in stock' in availability
            
            # Handle multiple offers
            elif isinstance(json_ld_data.get('offers'), list) and json_ld_data.get('offers'):
                # Use the first offer
                offers = json_ld_data.get('offers')[0]
                if isinstance(offers, dict):
                    price = offers.get('price')
                    if price:
                        try:
                            result['price'] = float(price)
                        except (ValueError, TypeError):
                            result['price'] = self._clean_price(str(price))
                    
                    availability = offers.get('availability', '').lower()
                    if availability:
                        result['in_stock'] = 'instock' in availability or 'in stock' in availability
        
        # If we didn't get all the information from JSON-LD, use the HTML parsing approach
        if not result['title']:
            # Try to find a title - look for common patterns in e-commerce sites
            title_candidates = [
                soup.select_one('h1'),  # Most sites use h1 for product title
                soup.select_one('[class*="title" i]'),  # Classes containing "title"
                soup.select_one('[class*="product-name" i]'),  # Classes containing "product-name"
                soup.select_one('[class*="product" i]'),  # Classes containing "product"
                soup.select_one('title')  # Last resort: use page title
            ]
            
            for candidate in title_candidates:
                if candidate and candidate.text.strip():
                    result['title'] = candidate.text.strip()
                    break
            
            # If no title found, use URL as fallback
            if not result['title']:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.split('/')
                # Try to get the last meaningful part of the path
                for part in reversed(path_parts):
                    if part and part not in ['', '.html', '.htm']:
                        result['title'] = part.replace('-', ' ').replace('_', ' ').capitalize()
                        break
        
        # Look for price in HTML if not found in JSON-LD
        if result['price'] is None:
            # Try to find meta tags with price information first (more reliable)
            meta_price_tags = [
                soup.select_one('meta[property="product:price:amount"]'),
                soup.select_one('meta[property="og:price:amount"]'),
                soup.select_one('meta[itemprop="price"]')
            ]
            
            for tag in meta_price_tags:
                if tag and tag.get('content'):
                    price_text = tag.get('content')
                    price = self._clean_price(price_text)
                    if price is not None:
                        result['price'] = price
                        break
            
            # If still no price, look in the HTML
            if result['price'] is None:
                price_candidates = [
                    soup.select_one('[class*="price" i]:not([class*="old" i]):not([class*="regular" i])'),
                    soup.select_one('[id*="price" i]'),
                    soup.select_one('[class*="current" i][class*="price" i]'),
                    soup.select_one('[itemprop="price"]')
                ]
                
                for candidate in price_candidates:
                    if candidate:
                        # If it has a content attribute, use that
                        if candidate.get('content'):
                            price_text = candidate.get('content')
                        else:
                            price_text = candidate.text
                        
                        if price_text:
                            # Ensure price_text is a string
                            if isinstance(price_text, str):
                                result['price'] = self._clean_price(price_text)
                                if result['price'] is not None:
                                    break
        
        # Determine in-stock status if not already found
        if 'in_stock' not in result or result['in_stock'] is None:
            # Method 1: Look for out of stock indicators
            out_of_stock_indicators = [
                'out of stock',
                'tükendi',
                'sold out',
                'stokta yok',
                'stokta bulunmamaktadır',
                'ürün geçici olarak temin edilemiyor',
                'şu an için temin edilemiyor'
            ]
            
            page_text = soup.get_text().lower()
            out_of_stock = any(indicator in page_text for indicator in out_of_stock_indicators)
            
            # Method 2: Look for availability meta tags
            availability_meta = soup.select_one('meta[property="product:availability"]') or soup.select_one('meta[itemprop="availability"]')
            if availability_meta and availability_meta.get('content'):
                availability_text = availability_meta.get('content').lower()
                out_of_stock = out_of_stock or 'outofstock' in availability_text or 'out of stock' in availability_text
            
            # Method 3: Look for add to cart buttons
            add_to_cart_candidates = [
                soup.select_one('[class*="add-to-cart" i]'),
                soup.select_one('[class*="addtocart" i]'),
                soup.select_one('[class*="add-to-basket" i]'),
                soup.select_one('[class*="addtobasket" i]'),
                soup.select_one('[id*="add-to-cart" i]'),
                soup.select_one('[id*="addtocart" i]')
            ]
            
            # Also look for buttons/links with Turkish "Sepete Ekle" text
            sepete_ekle_buttons = []
            for button in soup.find_all(['button', 'a']):
                if button.text and 'sepete ekle' in button.text.lower():
                    sepete_ekle_buttons.append(button)
            
            add_to_cart_candidates.extend(sepete_ekle_buttons)
            
            has_add_to_cart = any(candidate is not None for candidate in add_to_cart_candidates)
            
            # If there's no clear out-of-stock message and there's an add to cart button, assume in stock
            # If we see an out-of-stock message, definitely out of stock
            # Otherwise, assume in stock if we found price information
            if out_of_stock:
                result['in_stock'] = False
            elif has_add_to_cart:
                result['in_stock'] = True
            else:
                # Fallback: if we found a price, assume it's in stock
                result['in_stock'] = result['price'] is not None
        
        # Clean up title if needed
        if result['title']:
            # Remove excessive whitespace and newlines
            result['title'] = ' '.join(result['title'].split())
            
            # If the title is too long, truncate it
            if len(result['title']) > 200:
                result['title'] = result['title'][:197] + '...'
                
        return result
