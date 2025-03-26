import logging
import re
from typing import Dict, Optional, Any
import traceback
import time
import random

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
                        response = self.session.get(url, timeout=15)
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
        
        # Look for price - common patterns in e-commerce sites
        price_candidates = [
            soup.select_one('[class*="price" i]:not([class*="old" i]):not([class*="regular" i])'),  # Classes containing "price" but not "old" or "regular"
            soup.select_one('[id*="price" i]'),  # IDs containing "price"
            soup.select_one('[class*="current" i][class*="price" i]'),  # Classes containing both "current" and "price"
            soup.select_one('meta[property="product:price:amount"]')  # Open Graph price meta tag
        ]
        
        for candidate in price_candidates:
            if candidate:
                # If it's a meta tag, use the content attribute
                if candidate.name == 'meta' and candidate.get('content'):
                    price_text = candidate.get('content')
                else:
                    price_text = candidate.text
                
                if price_text:
                    # Ensure price_text is a string
                    if isinstance(price_text, str):
                        result['price'] = self._clean_price(price_text)
                        if result['price'] is not None:
                            break
        
        # Look for stock status
        # Method 1: Look for out of stock indicators
        out_of_stock_indicators = [
            'out of stock',
            'tükendi',
            'sold out',
            'stokta yok',
            'stokta bulunmamaktadır',
            'ürün geçici olarak temin edilemiyor'
        ]
        
        page_text = soup.get_text().lower()
        out_of_stock = any(indicator in page_text for indicator in out_of_stock_indicators)
        
        # Method 2: Look for add to cart buttons
        add_to_cart_candidates = [
            soup.select_one('[class*="add-to-cart" i]'),
            soup.select_one('[class*="addtocart" i]'),
            soup.select_one('[class*="add-to-basket" i]'),
            soup.select_one('[class*="addtobasket" i]'),
            soup.select_one('[id*="add-to-cart" i]'),
            soup.select_one('[id*="addtocart" i]')
        ]
        
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
        
        return result
