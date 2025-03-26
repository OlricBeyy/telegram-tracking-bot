import logging
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Configure logger for this module
logger = logging.getLogger(__name__)

class Database:
    """PostgreSQL database manager for the Telegram bot"""
    
    def __init__(self):
        """
        Initialize the database connection and create tables if they don't exist
        
        Uses environment variables for connection settings
        """
        self.db_url = os.environ.get("DATABASE_URL")
        if not self.db_url:
            logger.error("DATABASE_URL environment variable not set")
            raise ValueError("DATABASE_URL environment variable not set")
        
        self._create_tables()
    
    def _get_connection(self) -> Tuple[psycopg2.extensions.connection, psycopg2.extensions.cursor]:
        """
        Get a database connection and cursor
        
        Returns:
            Tuple of (connection, cursor)
        """
        # Open connection
        conn = psycopg2.connect(self.db_url)
        # Create cursor that returns dictionary rows
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        return conn, cursor
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist"""
        conn, cursor = self._get_connection()
        
        try:
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                is_authorized BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create products table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                store_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL,
                in_stock BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            ''')
            
            conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def add_user(self, user_id: int, is_admin: bool = False, is_authorized: bool = False) -> bool:
        """
        Add a new user to the database if not exists
        
        Args:
            user_id: Telegram user ID
            is_admin: Whether the user is an admin (default: False)
            is_authorized: Whether the user is authorized to use the bot (default: False)
            
        Returns:
            True if successful, False otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if cursor.fetchone():
                # User already exists
                return True
            
            # Add new user
            cursor.execute(
                "INSERT INTO users (id, is_admin, is_authorized) VALUES (%s, %s, %s)",
                (user_id, is_admin, is_authorized)
            )
            conn.commit()
            logger.info(f"Added new user: {user_id}, admin: {is_admin}, authorized: {is_authorized}")
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
            
    def set_user_authorization(self, user_id: int, is_authorized: bool) -> bool:
        """
        Set a user's authorization status
        
        Args:
            user_id: Telegram user ID
            is_authorized: Whether the user is authorized to use the bot
            
        Returns:
            True if successful, False otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                # User doesn't exist
                return False
            
            # Update user
            cursor.execute(
                "UPDATE users SET is_authorized = %s WHERE id = %s",
                (is_authorized, user_id)
            )
            conn.commit()
            status = "authorized" if is_authorized else "unauthorized"
            logger.info(f"User {user_id} is now {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id} authorization: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
            
    def is_admin(self, user_id: int) -> bool:
        """
        Check if a user is an admin
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if the user is an admin, False otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
                
            return result["is_admin"]
        except Exception as e:
            logger.error(f"Error checking if user {user_id} is admin: {e}")
            return False
        finally:
            conn.close()
            
    def is_authorized(self, user_id: int) -> bool:
        """
        Check if a user is authorized to use the bot
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if the user is authorized, False otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute("SELECT is_admin, is_authorized FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
                
            # Admins are always authorized
            if result["is_admin"]:
                return True
                
            return result["is_authorized"]
        except Exception as e:
            logger.error(f"Error checking if user {user_id} is authorized: {e}")
            return False
        finally:
            conn.close()
            
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user information
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User dictionary or None if not found
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return None
            
            return dict(user)
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
        finally:
            conn.close()
    
    def add_product(self, user_id: int, store_id: str, url: str, title: str, 
                    price: Optional[float], in_stock: bool) -> Optional[int]:
        """
        Add a new product to track
        
        Args:
            user_id: Telegram user ID
            store_id: Store identifier
            url: Product URL
            title: Product title
            price: Product price (can be None)
            in_stock: Whether the product is in stock
            
        Returns:
            Product ID if successful, None otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            # Add product
            now = datetime.now()
            cursor.execute('''
            INSERT INTO products 
            (user_id, store_id, url, title, price, in_stock, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (user_id, store_id, url, title, price, in_stock, now, now))
            
            product_id = cursor.fetchone()['id']
            conn.commit()
            logger.info(f"Added new product: {product_id}, user: {user_id}")
            return product_id
        except Exception as e:
            logger.error(f"Error adding product for user {user_id}: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def update_product(self, product_id: int, title: str, price: Optional[float], 
                      in_stock: bool) -> bool:
        """
        Update product information
        
        Args:
            product_id: Product ID
            title: Updated product title
            price: Updated product price
            in_stock: Updated stock status
            
        Returns:
            True if successful, False otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            # Update product
            now = datetime.now()
            cursor.execute('''
            UPDATE products 
            SET title = %s, price = %s, in_stock = %s, updated_at = %s 
            WHERE id = %s
            ''', (title, price, in_stock, now, product_id))
            
            conn.commit()
            logger.info(f"Updated product: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def remove_product(self, product_id: int) -> bool:
        """
        Remove a product from tracking
        
        Args:
            product_id: Product ID
            
        Returns:
            True if successful, False otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            # Remove product
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()
            logger.info(f"Removed product: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing product {product_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Get product information by ID
        
        Args:
            product_id: Product ID
            
        Returns:
            Product info dictionary or None if not found
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            
            if not product:
                return None
            
            # Already a dictionary from RealDictCursor
            return dict(product)
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_products(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all products tracked by a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of product dictionaries
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute("SELECT * FROM products WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            products = cursor.fetchall()
            
            # Already dictionaries from RealDictCursor
            return [dict(product) for product in products]
        except Exception as e:
            logger.error(f"Error getting products for user {user_id}: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """
        Get all products in the database
        
        Returns:
            List of product dictionaries
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute("SELECT * FROM products")
            products = cursor.fetchall()
            
            # Already dictionaries from RealDictCursor
            return [dict(product) for product in products]
        except Exception as e:
            logger.error(f"Error getting all products: {e}")
            return []
        finally:
            conn.close()
    
    def is_product_owner(self, user_id: int, product_id: int) -> bool:
        """
        Check if a user owns a product
        
        Args:
            user_id: Telegram user ID
            product_id: Product ID
            
        Returns:
            True if the user owns the product, False otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            cursor.execute("SELECT 1 FROM products WHERE id = %s AND user_id = %s", (product_id, user_id))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking product ownership for user {user_id}, product {product_id}: {e}")
            return False
        finally:
            conn.close()