"""Database models and operations"""

import os
from typing import List, Dict, Optional
from datetime import datetime

# Try to import Google Sheets, fallback to PostgreSQL/SQLite
try:
    from src.google_sheets_db import GoogleSheetsDatabase
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

# Try to import PostgreSQL, fallback to SQLite
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    import sqlite3
    # Define RealDictCursor for SQLite compatibility
    class RealDictCursor:
        pass

class Database:
    """Database manager for watchlist and state - supports Google Sheets, PostgreSQL, and SQLite"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database
        
        Priority: Google Sheets > PostgreSQL > SQLite
        
        Args:
            db_path: Path to SQLite database file (only used if other options not available)
        """
        # Check for Google Sheets first (simplest option)
        self.gsheets_id = os.getenv('GOOGLE_SHEETS_ID')
        self.use_gsheets = bool(self.gsheets_id) and GSHEETS_AVAILABLE
        
        if self.use_gsheets:
            try:
                self.gsheets_db = GoogleSheetsDatabase()
                print("✅ Using Google Sheets database")
                return
            except Exception as e:
                print(f"⚠️  Google Sheets not available: {e}, falling back to PostgreSQL/SQLite")
                self.use_gsheets = False
        
        # Check for PostgreSQL connection string
        self.postgres_url = os.getenv('DATABASE_URL')
        self.use_postgres = bool(self.postgres_url)
        
        if self.use_postgres:
            if not POSTGRES_AVAILABLE:
                raise ImportError("PostgreSQL URL provided but psycopg2 not installed. Install with: pip install psycopg2-binary")
            print("✅ Using PostgreSQL database")
            self._init_database()
        else:
            # Fallback to SQLite
            self.db_path = db_path or "data/sentiment_monitor.db"
            self.db_dir = os.path.dirname(self.db_path)
            
            # Create directory if it doesn't exist
            if self.db_dir and not os.path.exists(self.db_dir):
                os.makedirs(self.db_dir, exist_ok=True)
            print(f"✅ Using SQLite database: {self.db_path}")
            self._init_database()
    
    def _get_connection(self):
        """Get database connection (PostgreSQL or SQLite)"""
        if self.use_postgres:
            conn = psycopg2.connect(self.postgres_url)
            return conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
    
    def _init_database(self):
        """Initialize database tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Determine SQL syntax based on database type
        if self.use_postgres:
            # PostgreSQL syntax
            auto_increment = "SERIAL PRIMARY KEY"
            text_type = "TEXT"
            int_type = "INTEGER"
            real_type = "REAL"
            timestamp_default = "DEFAULT CURRENT_TIMESTAMP"
        else:
            # SQLite syntax
            auto_increment = "INTEGER PRIMARY KEY AUTOINCREMENT"
            text_type = "TEXT"
            int_type = "INTEGER"
            real_type = "REAL"
            timestamp_default = "DEFAULT CURRENT_TIMESTAMP"
        
        # Watchlist table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS watchlist (
                id {auto_increment},
                asset {text_type} NOT NULL UNIQUE,
                trade_direction {text_type} NOT NULL,
                bias_expectation {text_type},
                sensitivity {text_type} DEFAULT 'medium',
                notes {text_type},
                active {int_type} DEFAULT 1,
                created_at TIMESTAMP {timestamp_default},
                updated_at TIMESTAMP {timestamp_default}
            )
        """)
        
        # Alert history table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS alert_history (
                id {auto_increment},
                asset {text_type} NOT NULL,
                sentiment {text_type} NOT NULL,
                sentiment_direction {text_type},
                confidence {real_type},
                alert_data {text_type},
                created_at TIMESTAMP {timestamp_default}
            )
        """)
        
        # Asset state table (for tracking per-asset state)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS asset_state (
                asset {text_type} PRIMARY KEY,
                last_alert_time TIMESTAMP,
                last_sentiment {text_type},
                last_sentiment_direction {text_type},
                last_confidence {real_type},
                last_check_time TIMESTAMP,
                active_high_impact_events {text_type}
            )
        """)
        
        # High-impact events table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS high_impact_events (
                id {auto_increment},
                asset {text_type} NOT NULL,
                event_type {text_type} NOT NULL,
                event_description {text_type},
                event_date TIMESTAMP,
                is_active {int_type} DEFAULT 1,
                created_at TIMESTAMP {timestamp_default}
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        return self._get_connection()
    
    def _get_param_placeholder(self):
        """Get parameter placeholder for current database"""
        return "%s" if self.use_postgres else "?"
    
    def _row_to_dict(self, row):
        """Convert database row to dictionary"""
        if self.use_postgres:
            return dict(row)
        else:
            return dict(row)
    
    # Watchlist operations
    def add_trade(self, asset: str, trade_direction: str, bias_expectation: str = "",
                  sensitivity: str = "medium", notes: str = "") -> bool:
        """Add a trade to watchlist"""
        if self.use_gsheets:
            return self.gsheets_db.add_trade(asset, trade_direction, bias_expectation, sensitivity, notes)
        """
        Add a trade to watchlist
        
        Args:
            asset: Forex pair (e.g., "USD/CAD")
            trade_direction: "long" or "short"
            bias_expectation: Expected bias description
            sensitivity: "high", "medium", or "low"
            notes: Additional notes
            
        Returns:
            True if successful, False if asset already exists
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        param = self._get_param_placeholder()
        
        try:
            cursor.execute(f"""
                INSERT INTO watchlist (asset, trade_direction, bias_expectation, sensitivity, notes)
                VALUES ({param}, {param}, {param}, {param}, {param})
            """, (asset, trade_direction, bias_expectation, sensitivity, notes))
            conn.commit()
            return True
        except Exception as e:
            # Check if it's an integrity error (duplicate key)
            error_str = str(e).lower()
            if 'unique' in error_str or 'duplicate' in error_str or 'already exists' in error_str:
                # Asset already exists, update instead
                cursor.execute(f"""
                    UPDATE watchlist 
                    SET trade_direction = {param}, bias_expectation = {param}, sensitivity = {param}, notes = {param},
                        updated_at = CURRENT_TIMESTAMP
                    WHERE asset = {param}
                """, (trade_direction, bias_expectation, sensitivity, notes, asset))
                conn.commit()
                return True
            else:
                print(f"Error adding trade: {e}")
                return False
        finally:
            conn.close()
    
    def get_all_trades(self, active_only: bool = True) -> List[Dict]:
        """Get all trades from watchlist"""
        conn = self.get_connection()
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        param = self._get_param_placeholder()
        
        if active_only:
            cursor.execute(f"SELECT * FROM watchlist WHERE active = 1 ORDER BY asset")
        else:
            cursor.execute("SELECT * FROM watchlist ORDER BY asset")
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_trade(self, asset: str) -> Optional[Dict]:
        """Get a specific trade"""
        conn = self.get_connection()
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        param = self._get_param_placeholder()
        cursor.execute(f"SELECT * FROM watchlist WHERE asset = {param}", (asset,))
        row = cursor.fetchone()
        conn.close()
        
        return self._row_to_dict(row) if row else None
    
    def update_trade(self, asset: str, trade_direction: str = None, bias_expectation: str = None,
                    sensitivity: str = None, notes: str = None) -> bool:
        """Update a trade"""
        conn = self.get_connection()
        cursor = conn.cursor()
        param = self._get_param_placeholder()
        
        updates = []
        params = []
        
        if trade_direction is not None:
            updates.append(f"trade_direction = {param}")
            params.append(trade_direction)
        if bias_expectation is not None:
            updates.append(f"bias_expectation = {param}")
            params.append(bias_expectation)
        if sensitivity is not None:
            updates.append(f"sensitivity = {param}")
            params.append(sensitivity)
        if notes is not None:
            updates.append(f"notes = {param}")
            params.append(notes)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(asset)
        
        try:
            cursor.execute(f"""
                UPDATE watchlist 
                SET {', '.join(updates)}
                WHERE asset = {param}
            """, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating trade: {e}")
            return False
        finally:
            conn.close()
    
    def delete_trade(self, asset: str) -> bool:
        """Delete (deactivate) a trade"""
        conn = self.get_connection()
        cursor = conn.cursor()
        param = self._get_param_placeholder()
        
        try:
            cursor.execute(f"UPDATE watchlist SET active = 0 WHERE asset = {param}", (asset,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting trade: {e}")
            return False
        finally:
            conn.close()
    
    # Alert history operations
    def add_alert(self, asset: str, sentiment: str, sentiment_direction: str = None,
                  confidence: float = None, alert_data: Dict = None):
        """Add alert to history"""
        if self.use_gsheets:
            return self.gsheets_db.add_alert(asset, sentiment, sentiment_direction, confidence, alert_data)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        param = self._get_param_placeholder()
        
        alert_data_str = None
        if alert_data:
            import json
            alert_data_str = json.dumps(alert_data)
        
        cursor.execute(f"""
            INSERT INTO alert_history (asset, sentiment, sentiment_direction, confidence, alert_data)
            VALUES ({param}, {param}, {param}, {param}, {param})
        """, (asset, sentiment, sentiment_direction, confidence, alert_data_str))
        
        conn.commit()
        conn.close()
    
    def get_recent_alerts(self, asset: str = None, hours: int = 24) -> List[Dict]:
        """Get recent alerts"""
        if self.use_gsheets:
            return self.gsheets_db.get_recent_alerts(asset=asset, hours=hours)
        
        conn = self.get_connection()
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            time_filter = f"created_at > NOW() - INTERVAL '{hours} hours'"
        else:
            cursor = conn.cursor()
            time_filter = f"created_at > datetime('now', '-{hours} hours')"
        
        param = self._get_param_placeholder()
        
        if asset:
            cursor.execute(f"""
                SELECT * FROM alert_history 
                WHERE asset = {param} AND {time_filter}
                ORDER BY created_at DESC
            """, (asset,))
        else:
            cursor.execute(f"""
                SELECT * FROM alert_history 
                WHERE {time_filter}
                ORDER BY created_at DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]
    
    # Asset state operations
    def update_asset_state(self, asset: str, last_sentiment: str = None,
                          last_sentiment_direction: str = None, last_confidence: float = None,
                          last_alert_time: datetime = None):
        """Update asset state"""
        if self.use_gsheets:
            return self.gsheets_db.update_asset_state(asset, last_sentiment, last_sentiment_direction, last_confidence, last_alert_time)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        param = self._get_param_placeholder()
        
        # Check if state exists
        cursor.execute(f"SELECT * FROM asset_state WHERE asset = {param}", (asset,))
        exists = cursor.fetchone()
        
        if exists:
            updates = []
            params = []
            
            if last_sentiment is not None:
                updates.append(f"last_sentiment = {param}")
                params.append(last_sentiment)
            if last_sentiment_direction is not None:
                updates.append(f"last_sentiment_direction = {param}")
                params.append(last_sentiment_direction)
            if last_confidence is not None:
                updates.append(f"last_confidence = {param}")
                params.append(last_confidence)
            if last_alert_time:
                updates.append(f"last_alert_time = {param}")
                params.append(last_alert_time.isoformat())
            
            updates.append("last_check_time = CURRENT_TIMESTAMP")
            params.append(asset)
            
            cursor.execute(f"""
                UPDATE asset_state 
                SET {', '.join(updates)}
                WHERE asset = {param}
            """, params)
        else:
            cursor.execute(f"""
                INSERT INTO asset_state 
                (asset, last_sentiment, last_sentiment_direction, last_confidence, 
                 last_alert_time, last_check_time)
                VALUES ({param}, {param}, {param}, {param}, {param}, CURRENT_TIMESTAMP)
            """, (asset, last_sentiment, last_sentiment_direction, last_confidence,
                  last_alert_time.isoformat() if last_alert_time else None))
        
        conn.commit()
        conn.close()
    
    def get_asset_state(self, asset: str) -> Optional[Dict]:
        """Get asset state"""
        if self.use_gsheets:
            return self.gsheets_db.get_asset_state(asset)
        
        conn = self.get_connection()
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        param = self._get_param_placeholder()
        cursor.execute(f"SELECT * FROM asset_state WHERE asset = {param}", (asset,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            state_dict = self._row_to_dict(row)
            # Get active events for this asset
            state_dict['active_events'] = self.get_active_events(asset=asset)
            return state_dict
        return None
    
    def was_alerted_recently(self, asset: str, minutes: int = 60) -> bool:
        """Check if alerted recently"""
        if self.use_gsheets:
            return self.gsheets_db.was_alerted_recently(asset, minutes)
        
        state = self.get_asset_state(asset)
        if not state or not state.get('last_alert_time'):
            return False
        
        try:
            last_alert = datetime.fromisoformat(state['last_alert_time'])
            cutoff = datetime.now().timestamp() - (minutes * 60)
            return last_alert.timestamp() > cutoff
        except Exception:
            return False
    
    # High-impact events operations
    def add_high_impact_event(self, asset: str, event_type: str, event_description: str,
                              event_date: datetime = None):
        """Add high-impact event"""
        if self.use_gsheets:
            return self.gsheets_db.add_high_impact_event(asset, event_type, event_description, event_date)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        param = self._get_param_placeholder()
        
        event_date_str = event_date.isoformat() if event_date else None
        
        cursor.execute(f"""
            INSERT INTO high_impact_events (asset, event_type, event_description, event_date)
            VALUES ({param}, {param}, {param}, {param})
        """, (asset, event_type, event_description, event_date_str))
        
        conn.commit()
        conn.close()
    
    def get_active_events(self, asset: str = None) -> List[Dict]:
        """Get active high-impact events"""
        if self.use_gsheets:
            return self.gsheets_db.get_active_events(asset=asset)
        
        conn = self.get_connection()
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        param = self._get_param_placeholder()
        
        if asset:
            cursor.execute(f"""
                SELECT * FROM high_impact_events 
                WHERE is_active = 1 AND asset = {param}
                ORDER BY event_date ASC
            """, (asset,))
        else:
            cursor.execute("""
                SELECT * FROM high_impact_events 
                WHERE is_active = 1
                ORDER BY event_date ASC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]
    
    def deactivate_event(self, event_id: int):
        """Deactivate an event"""
        if self.use_gsheets:
            return self.gsheets_db.deactivate_event(event_id)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        param = self._get_param_placeholder()
        cursor.execute(f"UPDATE high_impact_events SET is_active = 0 WHERE id = {param}", (event_id,))
        conn.commit()
        conn.close()

