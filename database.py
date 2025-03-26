import logging
import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Configure logger for this module
logger = logging.getLogger(__name__)

class Database:
    """SQLite database manager for the Telegram bot"""
    
    def __init__(self, db_path: str = "products_db.sqlite"):
        """
        Initialize the database connection and create tables if they don't exist
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._create_tables()
    
    def _get_connection(self) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        """
        Get a database connection and cursor
        
        Returns:
            Tuple of (connection, cursor)
        """
        # Open connection
        conn = sqlite3.connect(self.db_path)
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Return dictionary rows
        conn.row_factory = sqlite3.Row
        # Create cursor
        cursor = conn.cursor()
        
        return conn, cursor
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist"""
        conn, cursor = self._get_connection()
        
        try:
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create products table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                store_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL,
                in_stock INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
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
    
    def add_user(self, user_id: int) -> bool:
        """
        Add a new user to the database if not exists
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        conn, cursor = self._get_connection()
        
        try:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if cursor.fetchone():
                # User already exists
                return True
            
            # Add new user
            cursor.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
            conn.commit()
            logger.info(f"Added new user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            conn.rollback()
            return False
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
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            INSERT INTO products 
            (user_id, store_id, url, title, price, in_stock, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, store_id, url, title, price, int(in_stock), now, now))
            
            conn.commit()
            product_id = cursor.lastrowid
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
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            UPDATE products 
            SET title = ?, price = ?, in_stock = ?, updated_at = ? 
            WHERE id = ?
            ''', (title, price, int(in_stock), now, product_id))
            
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
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
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
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            product = cursor.fetchone()
            
            if not product:
                return None
            
            # Convert to dictionary
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
            cursor.execute("SELECT * FROM products WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            products = cursor.fetchall()
            
            # Convert to list of dictionaries
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
            
            # Convert to list of dictionaries
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
            cursor.execute("SELECT 1 FROM products WHERE id = ? AND user_id = ?", (product_id, user_id))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking product ownership for user {user_id}, product {product_id}: {e}")
            return False
        finally:
            conn.close()
