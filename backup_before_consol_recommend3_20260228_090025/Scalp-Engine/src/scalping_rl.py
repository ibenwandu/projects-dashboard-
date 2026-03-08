"""
src/scalping_rl.py
Tracks scalping outcomes to build a learning dataset.
"""
import sqlite3
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
import pandas as pd
import yfinance as yf

class ScalpingRL:
    def __init__(self, db_path="scalping_rl.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Create the learning database if it doesn't exist"""
        # Ensure directory exists (important for shared disk on Render)
        db_file = Path(self.db_path)
        parent_dir = db_file.parent
        
        # Only create parent directory if it's not root, not current directory, and doesn't exist
        if str(parent_dir) not in ['.', '/', ''] and not parent_dir.exists():
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
                print(f"✅ Created database directory: {parent_dir}")
            except (OSError, PermissionError) as e:
                # Log but don't fail - disk mount point might already exist
                print(f"⚠️  Warning: Could not create directory {parent_dir}: {e}")
        
        # Check if database file already exists
        db_exists = os.path.exists(str(self.db_path))
        if db_exists:
            db_size = os.path.getsize(str(self.db_path))
            print(f"📦 Opening existing database: {self.db_path} ({db_size} bytes)")
        else:
            print(f"📦 Creating new database: {self.db_path}")
        
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            c = conn.cursor()
            
            # Table 1: Signals (The "Input")
            c.execute('''CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                pair TEXT,
                direction TEXT,
                regime TEXT,
                strength REAL,
                ema_spread REAL,
                outcome TEXT, -- WIN/LOSS/PENDING
                pnl REAL,
                position_size REAL,
                hour INTEGER
            )''')
            
            # Add new columns if they don't exist (for existing databases)
            try:
                c.execute('ALTER TABLE signals ADD COLUMN position_size REAL')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                c.execute('ALTER TABLE signals ADD COLUMN hour INTEGER')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Add columns for market simulation (entry_price, stop_loss, take_profit)
            try:
                c.execute('ALTER TABLE signals ADD COLUMN entry_price REAL')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                c.execute('ALTER TABLE signals ADD COLUMN stop_loss REAL')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                c.execute('ALTER TABLE signals ADD COLUMN take_profit REAL')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                c.execute('ALTER TABLE signals ADD COLUMN evaluated INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            conn.commit()
            conn.close()
            print(f"✅ Database initialized successfully: {self.db_path}")
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize database: {e}")
            import traceback
            traceback.print_exc()
            raise
            print(f"✅ Database initialized successfully: {self.db_path}")
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize database: {e}")
            import traceback
            traceback.print_exc()
            raise

    def log_signal(self, pair, direction, regime, strength, ema_spread=0.0, position_size=0.0, entry_price=None, stop_loss=None, take_profit=None):
        """
        Log a new signal before execution
        
        Args:
            pair: Currency pair
            direction: BUY or SELL
            regime: Market regime
            strength: Signal strength (0.0-1.0)
            ema_spread: EMA spread in pips
            position_size: Position size in units (optional)
            entry_price: Entry price for market simulation (optional)
            stop_loss: Stop loss price for market simulation (optional)
            take_profit: Take profit price for market simulation (optional)
            
        Returns:
            signal_id
        """
        now = datetime.now()
        hour = now.hour  # 0-23
        
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''INSERT INTO signals 
                     (timestamp, pair, direction, regime, strength, ema_spread, outcome, pnl, position_size, hour, entry_price, stop_loss, take_profit, evaluated)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                  (now.isoformat(), pair, direction, regime, strength, ema_spread, "PENDING", 0.0, position_size, hour, entry_price, stop_loss, take_profit, 0))
        signal_id = c.lastrowid
        conn.commit()
        conn.close()
        return signal_id

    def update_outcome(self, signal_id, pnl):
        """Update the signal with the trade result"""
        outcome = "WIN" if pnl > 0 else "LOSS"
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''UPDATE signals SET outcome = ?, pnl = ? WHERE id = ?''', 
                  (outcome, pnl, signal_id))
        conn.commit()
        conn.close()
        print(f"✅ RL Update: Trade {signal_id} closed as {outcome} ({pnl:.2f})")

    def get_historical_performance(self, regime=None, min_strength=None):
        """
        Query historical performance to inform trading decisions
        
        Args:
            regime: Filter by regime (optional)
            min_strength: Filter by minimum strength (optional)
            
        Returns:
            Dictionary with win_rate, avg_pnl, total_trades
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        query = "SELECT outcome, pnl FROM signals WHERE outcome != 'PENDING'"
        params = []
        
        if regime:
            query += " AND regime = ?"
            params.append(regime)
        
        if min_strength:
            query += " AND strength >= ?"
            params.append(min_strength)
        
        c.execute(query, params)
        results = c.fetchall()
        conn.close()
        
        if not results:
            return {"win_rate": 0.0, "avg_pnl": 0.0, "total_trades": 0}
        
        wins = sum(1 for r in results if r[0] == "WIN")
        total = len(results)
        avg_pnl = sum(r[1] for r in results) / total if total > 0 else 0.0
        
        return {
            "win_rate": wins / total if total > 0 else 0.0,
            "avg_pnl": avg_pnl,
            "total_trades": total
        }
    
    def get_historical_performance_by_pair(self, pair: str, regime=None, min_strength=None):
        """
        Query historical performance for a specific pair
        
        Args:
            pair: Currency pair (e.g., "EUR/USD")
            regime: Filter by regime (optional)
            min_strength: Filter by minimum strength (optional)
            
        Returns:
            Dictionary with win_rate, avg_pnl, total_trades
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        query = "SELECT outcome, pnl FROM signals WHERE outcome != 'PENDING' AND pair = ?"
        params = [pair]
        
        if regime:
            query += " AND regime = ?"
            params.append(regime)
        
        if min_strength:
            query += " AND strength >= ?"
            params.append(min_strength)
        
        c.execute(query, params)
        results = c.fetchall()
        conn.close()
        
        if not results:
            return {"win_rate": 0.0, "avg_pnl": 0.0, "total_trades": 0}
        
        wins = sum(1 for r in results if r[0] == "WIN")
        total = len(results)
        avg_pnl = sum(r[1] for r in results) / total if total > 0 else 0.0
        
        return {
            "win_rate": wins / total if total > 0 else 0.0,
            "avg_pnl": avg_pnl,
            "total_trades": total
        }
    
    def get_historical_performance_by_hour(self, hour: int, regime=None, min_strength=None):
        """
        Query historical performance for a specific hour of day
        
        Args:
            hour: Hour of day (0-23)
            regime: Filter by regime (optional)
            min_strength: Filter by minimum strength (optional)
            
        Returns:
            Dictionary with win_rate, avg_pnl, total_trades
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        query = "SELECT outcome, pnl FROM signals WHERE outcome != 'PENDING' AND hour = ?"
        params = [hour]
        
        if regime:
            query += " AND regime = ?"
            params.append(regime)
        
        if min_strength:
            query += " AND strength >= ?"
            params.append(min_strength)
        
        c.execute(query, params)
        results = c.fetchall()
        conn.close()
        
        if not results:
            return {"win_rate": 0.0, "avg_pnl": 0.0, "total_trades": 0}
        
        wins = sum(1 for r in results if r[0] == "WIN")
        total = len(results)
        avg_pnl = sum(r[1] for r in results) / total if total > 0 else 0.0
        
        return {
            "win_rate": wins / total if total > 0 else 0.0,
            "avg_pnl": avg_pnl,
            "total_trades": total
        }
    
    def get_all_hourly_performance(self, regime=None):
        """
        Get performance statistics for all hours of the day
        
        Args:
            regime: Filter by regime (optional)
            
        Returns:
            Dictionary mapping hour (0-23) to performance stats
        """
        hourly_stats = {}
        
        for hour in range(24):
            perf = self.get_historical_performance_by_hour(hour, regime=regime)
            if perf['total_trades'] > 0:
                hourly_stats[hour] = perf
        
        return hourly_stats
    
    def get_pending_signals(self, min_age_minutes: int = 15) -> list:
        """
        Get signals that need evaluation (for market simulation)
        
        Args:
            min_age_minutes: Minimum age in minutes before evaluating (default: 15 minutes for scalping)
            
        Returns:
            List of signal dictionaries
        """
        cutoff = (datetime.now() - timedelta(minutes=min_age_minutes)).isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            SELECT id, timestamp, pair, direction, entry_price, stop_loss, take_profit
            FROM signals
            WHERE outcome = 'PENDING'
            AND timestamp < ?
            AND evaluated = 0
            AND entry_price IS NOT NULL
            AND stop_loss IS NOT NULL
            AND take_profit IS NOT NULL
            ORDER BY timestamp
        ''', (cutoff,))
        results = c.fetchall()
        conn.close()
        
        signals = []
        for row in results:
            signals.append({
                'id': row[0],
                'timestamp': row[1],
                'pair': row[2],
                'direction': row[3],
                'entry_price': row[4],
                'stop_loss': row[5],
                'take_profit': row[6]
            })
        return signals
    
    def update_outcome_simulated(self, signal_id: int, outcome: str, pnl: float):
        """
        Update signal outcome based on market simulation
        
        Args:
            signal_id: Signal ID
            outcome: 'WIN' or 'LOSS'
            pnl: PnL value (positive for WIN, negative for LOSS)
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''UPDATE signals SET outcome = ?, pnl = ?, evaluated = 1 WHERE id = ?''', 
                  (outcome, pnl, signal_id))
        conn.commit()
        conn.close()
        print(f"✅ RL Simulation Update: Signal {signal_id} evaluated as {outcome} (PnL: {pnl:.2f})")


class SignalOutcomeEvaluator:
    """Evaluates signal outcomes using market data (similar to Trade-Alerts OutcomeEvaluator)"""
    
    def __init__(self):
        self.cache = {}
    
    def evaluate_signal(self, signal: Dict) -> Optional[Dict]:
        """
        Evaluate a single signal using market data
        
        Args:
            signal: Dictionary with id, timestamp, pair, direction, entry_price, stop_loss, take_profit
            
        Returns:
            Dictionary with outcome, pnl, or None if evaluation failed
        """
        try:
            # Convert pair format for yfinance
            pair_formatted = self._format_pair_for_yfinance(signal['pair'])
            
            # Get price data from signal time to now
            start_date = datetime.fromisoformat(signal['timestamp'])
            end_date = datetime.now()
            
            price_data = self._get_price_data(pair_formatted, start_date, end_date)
            
            if price_data is None or len(price_data) < 2:
                return None
            
            # Evaluate outcome
            entry = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']
            direction = signal['direction']
            
            outcome = self._check_outcome(price_data, entry, stop_loss, take_profit, direction)
            
            return outcome
            
        except Exception as e:
            print(f"Error evaluating signal {signal.get('id', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_pair_for_yfinance(self, pair: str) -> str:
        """Convert pair format for yfinance"""
        # EUR/USD -> EURUSD=X, USD/JPY -> USDJPY=X
        clean_pair = pair.replace('/', '').replace('-', '')
        return f"{clean_pair}=X"
    
    def _get_price_data(self, pair: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """Get historical price data using yfinance"""
        cache_key = f"{pair}_{start.date()}_{end.date()}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # For scalping, use 5-minute intervals (more granular than Trade-Alerts hourly)
            data = yf.download(
                pair,
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d'),
                interval='5m',  # 5-minute intervals for scalping
                progress=False
            )
            
            if len(data) > 0:
                self.cache[cache_key] = data
                return data
            
        except Exception as e:
            print(f"Error fetching data for {pair}: {e}")
        
        return None
    
    def _check_outcome(self, price_data: pd.DataFrame, entry: float, stop_loss: float, take_profit: float, direction: str) -> Dict:
        """
        Check if TP or SL was hit (simplified for scalping - just WIN/LOSS, not TP1/TP2)
        
        Args:
            price_data: DataFrame with High, Low, Close columns
            entry: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            direction: 'BUY' or 'SELL'
            
        Returns:
            Dictionary with outcome, pnl
        """
        # Normalize direction
        if direction.upper() in ['BUY', 'LONG']:
            is_long = True
        else:
            is_long = False
        
        for i, (timestamp, row) in enumerate(price_data.iterrows()):
            high = row['High']
            low = row['Low']
            
            if is_long:
                # Check stop loss first
                if low <= stop_loss:
                    pnl = stop_loss - entry  # Negative
                    return {
                        'outcome': 'LOSS',
                        'pnl': pnl
                    }
                
                # Check take profit
                if high >= take_profit:
                    pnl = take_profit - entry  # Positive
                    return {
                        'outcome': 'WIN',
                        'pnl': pnl
                    }
            else:  # SHORT
                # Check stop loss first
                if high >= stop_loss:
                    pnl = entry - stop_loss  # Negative
                    return {
                        'outcome': 'LOSS',
                        'pnl': pnl
                    }
                
                # Check take profit
                if low <= take_profit:
                    pnl = entry - take_profit  # Positive
                    return {
                        'outcome': 'WIN',
                        'pnl': pnl
                    }
        
        # If neither TP nor SL hit, check current P&L (mark as WIN if positive, LOSS if negative)
        current_price = price_data.iloc[-1]['Close']
        if is_long:
            pnl = current_price - entry
        else:
            pnl = entry - current_price
        
        # For scalping, if we've waited long enough and price moved significantly, mark outcome
        # Otherwise, return None to indicate it's still pending
        outcome = 'WIN' if pnl > 0 else 'LOSS'
        return {
            'outcome': outcome,
            'pnl': pnl
        }