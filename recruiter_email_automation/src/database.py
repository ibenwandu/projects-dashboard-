"""Database for tracking processed emails"""

import sqlite3
import os
from datetime import datetime
from typing import Optional

class EmailDatabase:
    """SQLite database to track processed emails"""
    
    def __init__(self, db_path='data/processed_emails.db'):
        """Initialize database connection"""
        # Get project root directory (parent of src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Make path absolute if relative
        if not os.path.isabs(db_path):
            db_path = os.path.join(project_root, db_path)
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_table()
    
    def _create_table(self):
        """Create processed_emails table if it doesn't exist"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_emails (
                email_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_summary TEXT,
                sender_email TEXT,
                subject TEXT
            )
        ''')
        self.conn.commit()
    
    def is_email_processed(self, email_id: str) -> bool:
        """Check if an email has already been processed"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT email_id FROM processed_emails WHERE email_id = ?', (email_id,))
        return cursor.fetchone() is not None
    
    def mark_email_processed(self, email_id: str, category: str, 
                            response_summary: str = '', sender_email: str = '', 
                            subject: str = ''):
        """Mark an email as processed"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO processed_emails 
            (email_id, category, response_summary, sender_email, subject)
            VALUES (?, ?, ?, ?, ?)
        ''', (email_id, category, response_summary, sender_email, subject))
        self.conn.commit()
    
    def get_processed_count(self, category: Optional[str] = None) -> int:
        """Get count of processed emails, optionally filtered by category"""
        cursor = self.conn.cursor()
        if category:
            cursor.execute('SELECT COUNT(*) FROM processed_emails WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT COUNT(*) FROM processed_emails')
        return cursor.fetchone()[0]
    
    def close(self):
        """Close database connection"""
        self.conn.close()

