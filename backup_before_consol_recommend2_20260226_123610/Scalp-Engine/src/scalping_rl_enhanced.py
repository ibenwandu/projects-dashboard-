"""
Enhanced Scalping RL System
Replicates Trade-Alerts RL functionality for Scalp-Engine
Tracks both executed trades and simulated opportunities for continuous learning
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf


class ScalpingRLEnhanced:
    """
    Enhanced RL system for Scalp-Engine that:
    1. Tracks executed trades (real outcomes from OANDA)
    2. Simulates non-executed opportunities (market simulation)
    3. Calculates LLM weights based on performance
    4. Provides consensus analysis
    """
    
    def __init__(self, db_path="scalping_rl.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize enhanced database schema"""
        db_file = Path(self.db_path)
        parent_dir = db_file.parent
        
        if str(parent_dir) not in ['.', '/', ''] and not parent_dir.exists():
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                print(f"⚠️  Warning: Could not create directory {parent_dir}: {e}")
        
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            c = conn.cursor()
            
            # Enhanced signals table with LLM tracking
            c.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    pair TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL,
                    
                    -- LLM Intelligence Context
                    llm_sources TEXT,  -- JSON array of LLM sources (e.g., ["gemini", "synthesis"])
                    consensus_level INTEGER DEFAULT 1,  -- Number of LLMs that agreed
                    rationale TEXT,
                    confidence REAL DEFAULT 0.5,
                    
                    -- Market Context
                    regime TEXT,
                    strength REAL,
                    ema_spread REAL,
                    hour INTEGER,  -- Hour of day (0-23)
                    
                    -- Trade Execution Info
                    executed INTEGER DEFAULT 0,  -- 1 if actually executed, 0 if simulated
                    trade_id TEXT,  -- OANDA trade ID if executed
                    position_size REAL,
                    
                    -- Outcome Tracking
                    outcome TEXT DEFAULT 'PENDING',  -- WIN, LOSS, MISSED, PENDING
                    exit_price REAL,
                    pnl_pips REAL,
                    bars_held INTEGER,
                    max_favorable_pips REAL,
                    max_adverse_pips REAL,
                    outcome_timestamp DATETIME,
                    evaluated INTEGER DEFAULT 0,
                    -- Fisher Transform tracking (Semi-Auto/Manual only)
                    fisher_signal INTEGER DEFAULT 0
                )
            ''')
            
            # LLM performance tracking table
            c.execute('''
                CREATE TABLE IF NOT EXISTS llm_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    llm_source TEXT NOT NULL,
                    total_signals INTEGER,
                    total_evaluated INTEGER,
                    executed_count INTEGER,
                    simulated_count INTEGER,
                    win_rate REAL,
                    avg_pnl_pips REAL,
                    profit_factor REAL,
                    missed_rate REAL,
                    accuracy_weight REAL
                )
            ''')
            
            # Learning checkpoints
            c.execute('''
                CREATE TABLE IF NOT EXISTS learning_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_signals INTEGER,
                    total_evaluated INTEGER,
                    gemini_weight REAL,
                    synthesis_weight REAL,
                    chatgpt_weight REAL,
                    claude_weight REAL,
                    overall_win_rate REAL,
                    notes TEXT
                )
            ''')
            
            # Migration: Add fisher_signal column if not present (for Fisher Transform tracking)
            try:
                c.execute("SELECT fisher_signal FROM signals LIMIT 1")
            except sqlite3.OperationalError:
                c.execute("ALTER TABLE signals ADD COLUMN fisher_signal INTEGER DEFAULT 0")
                conn.commit()
            
            # Consensus analysis
            c.execute('''
                CREATE TABLE IF NOT EXISTS consensus_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    consensus_type TEXT,  -- 'ALL_AGREE', '2_AGREE', 'ALL_DISAGREE'
                    win_rate REAL,
                    sample_size INTEGER,
                    avg_pnl_pips REAL
                )
            ''')
            
            # Add new columns to existing signals table if they don't exist
            new_columns = [
                ('llm_sources', 'TEXT'),
                ('consensus_level', 'INTEGER DEFAULT 1'),
                ('rationale', 'TEXT'),
                ('confidence', 'REAL DEFAULT 0.5'),
                ('executed', 'INTEGER DEFAULT 0'),
                ('trade_id', 'TEXT'),
                ('exit_price', 'REAL'),
                ('bars_held', 'INTEGER'),
                ('max_favorable_pips', 'REAL'),
                ('max_adverse_pips', 'REAL'),
                ('outcome_timestamp', 'DATETIME'),
                ('evaluated', 'INTEGER DEFAULT 0'),
                ('fisher_signal', 'INTEGER DEFAULT 0')
            ]
            
            for col_name, col_type in new_columns:
                try:
                    c.execute(f'ALTER TABLE signals ADD COLUMN {col_name} {col_type}')
                except sqlite3.OperationalError:
                    pass  # Column already exists
            
            conn.commit()
            conn.close()
            print(f"✅ Enhanced RL database initialized: {self.db_path}")
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize database: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def log_signal(
        self,
        pair: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None,
        llm_sources: List[str] = None,
        consensus_level: int = 1,
        rationale: str = "",
        confidence: float = 0.5,
        executed: bool = False,
        trade_id: Optional[str] = None,
        position_size: float = 0.0,
        regime: Optional[str] = None,
        strength: float = 0.5,
        ema_spread: float = 0.0,
        fisher_signal: bool = False
    ) -> int:
        """
        Log a trading signal (executed or opportunity)
        
        Args:
            pair: Currency pair
            direction: LONG or SHORT
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price (optional)
            llm_sources: List of LLM sources that recommended this
            consensus_level: Number of LLMs that agreed
            rationale: Trade rationale
            confidence: Confidence level (0.0-1.0)
            executed: True if trade was actually executed, False if just an opportunity
            trade_id: OANDA trade ID if executed
            position_size: Position size in units
            regime: Market regime
            strength: Signal strength
            ema_spread: EMA spread in pips
            
        Returns:
            signal_id
        """
        now = datetime.utcnow()
        hour = now.hour
        
        # Convert llm_sources list to JSON string
        import json
        llm_sources_json = json.dumps(llm_sources) if llm_sources else "[]"
        
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            INSERT INTO signals (
                timestamp, pair, direction, entry_price, stop_loss, take_profit,
                llm_sources, consensus_level, rationale, confidence,
                executed, trade_id, position_size,
                regime, strength, ema_spread, hour,
                outcome, evaluated, fisher_signal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            now.isoformat(), pair, direction, entry_price, stop_loss, take_profit,
            llm_sources_json, consensus_level, rationale, confidence,
            1 if executed else 0, trade_id, position_size,
            regime, strength, ema_spread, hour,
            'PENDING', 0, 1 if fisher_signal else 0
        ))
        signal_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return signal_id
    
    def update_outcome_real_trade(
        self,
        signal_id: int,
        exit_price: float,
        pnl_pips: float,
        bars_held: Optional[int] = None,
        max_favorable_pips: Optional[float] = None,
        max_adverse_pips: Optional[float] = None
    ):
        """
        Update signal with outcome from real executed trade
        
        Args:
            signal_id: Signal ID
            exit_price: Exit price
            pnl_pips: P&L in pips
            bars_held: Number of bars held (optional)
            max_favorable_pips: Maximum favorable excursion in pips (optional)
            max_adverse_pips: Maximum adverse excursion in pips (optional)
        """
        outcome = "WIN" if pnl_pips > 0 else "LOSS"
        
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            UPDATE signals SET
                outcome = ?,
                exit_price = ?,
                pnl_pips = ?,
                bars_held = ?,
                max_favorable_pips = ?,
                max_adverse_pips = ?,
                outcome_timestamp = ?,
                evaluated = 1
            WHERE id = ?
        ''', (
            outcome, exit_price, pnl_pips,
            bars_held, max_favorable_pips, max_adverse_pips,
            datetime.utcnow().isoformat(), signal_id
        ))
        conn.commit()
        conn.close()
    
    def update_outcome_simulated(
        self,
        signal_id: int,
        outcome: str,
        exit_price: float,
        pnl_pips: float,
        bars_held: Optional[int] = None,
        max_favorable_pips: Optional[float] = None,
        max_adverse_pips: Optional[float] = None
    ):
        """
        Update signal with simulated outcome
        
        Args:
            signal_id: Signal ID
            outcome: 'WIN', 'LOSS', or 'MISSED'
            exit_price: Exit price
            pnl_pips: P&L in pips
            bars_held: Number of bars held (optional)
            max_favorable_pips: Maximum favorable excursion in pips (optional)
            max_adverse_pips: Maximum adverse excursion in pips (optional)
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            UPDATE signals SET
                outcome = ?,
                exit_price = ?,
                pnl_pips = ?,
                bars_held = ?,
                max_favorable_pips = ?,
                max_adverse_pips = ?,
                outcome_timestamp = ?,
                evaluated = 1
            WHERE id = ?
        ''', (
            outcome, exit_price, pnl_pips,
            bars_held, max_favorable_pips, max_adverse_pips,
            datetime.utcnow().isoformat(), signal_id
        ))
        conn.commit()
        conn.close()
    
    def get_pending_signals(self, min_age_minutes: int = 15) -> List[Dict]:
        """
        Get signals that need evaluation (for market simulation)
        
        Args:
            min_age_minutes: Minimum age in minutes before evaluating
            
        Returns:
            List of signal dictionaries
        """
        cutoff = (datetime.utcnow() - timedelta(minutes=min_age_minutes)).isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            SELECT id, timestamp, pair, direction, entry_price, stop_loss, take_profit, executed
            FROM signals
            WHERE outcome = 'PENDING'
            AND timestamp < ?
            AND evaluated = 0
            AND entry_price IS NOT NULL
            AND stop_loss IS NOT NULL
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
                'take_profit': row[6],
                'executed': bool(row[7])
            })
        return signals
    
    def get_llm_performance(self, llm_source: Optional[str] = None) -> pd.DataFrame:
        """
        Get performance statistics for LLM(s)
        
        Args:
            llm_source: Specific LLM source to filter by (optional)
            
        Returns:
            DataFrame with performance metrics
        """
        conn = sqlite3.connect(str(self.db_path))
        
        query = '''
            SELECT 
                s.*,
                json_extract(s.llm_sources, '$') as llm_sources_array
            FROM signals s
            WHERE s.evaluated = 1
        '''
        
        if llm_source:
            # Filter by LLM source (check if it's in the JSON array)
            query += f" AND json_extract(s.llm_sources, '$') LIKE '%\"{llm_source}\"%'"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_fisher_performance(self) -> Dict:
        """
        Get performance statistics for Fisher Transform signals only.
        Used by ML/RL to incorporate Fisher opportunity outcomes.
        
        Returns:
            Dict with total, wins, losses, win_rate, avg_pnl_pips, profit_factor
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        try:
            c.execute('''
                SELECT outcome, pnl_pips FROM signals
                WHERE fisher_signal = 1 AND evaluated = 1
            ''')
            rows = c.fetchall()
        except sqlite3.OperationalError:
            rows = []  # Column may not exist yet
        conn.close()
        
        wins = sum(1 for r in rows if r[0] == 'WIN')
        losses = sum(1 for r in rows if r[0] == 'LOSS')
        total = len(rows)
        pnls = [r[1] or 0 for r in rows]
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss else (gross_profit or 0)
        
        return {
            'total': total,
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / total) if total else 0.0,
            'avg_pnl_pips': (sum(pnls) / total) if total else 0.0,
            'profit_factor': profit_factor
        }
    
    def get_historical_performance(
        self,
        llm_source: Optional[str] = None,
        pair: Optional[str] = None,
        regime: Optional[str] = None
    ) -> Dict:
        """
        Get historical performance statistics
        
        Args:
            llm_source: Filter by LLM source (optional)
            pair: Filter by pair (optional)
            regime: Filter by regime (optional)
            
        Returns:
            Dictionary with win_rate, avg_pnl, total_trades
        """
        df = self.get_llm_performance(llm_source=llm_source)
        
        if len(df) == 0:
            return {"win_rate": 0.0, "avg_pnl": 0.0, "total_trades": 0}
        
        # Apply filters
        if pair:
            df = df[df['pair'] == pair]
        if regime:
            df = df[df['regime'] == regime]
        
        if len(df) == 0:
            return {"win_rate": 0.0, "avg_pnl": 0.0, "total_trades": 0}
        
        wins = df[df['outcome'] == 'WIN']
        total = len(df[df['outcome'].isin(['WIN', 'LOSS'])])
        avg_pnl = df['pnl_pips'].mean() if 'pnl_pips' in df.columns else 0.0
        
        return {
            "win_rate": len(wins) / total if total > 0 else 0.0,
            "avg_pnl": avg_pnl,
            "total_trades": total
        }


class OutcomeEvaluator:
    """Evaluates signal outcomes using market data (for simulation)"""
    
    def __init__(self):
        self.cache = {}
    
    def evaluate_signal(self, signal: Dict) -> Optional[Dict]:
        """
        Evaluate a single signal using market data
        
        Args:
            signal: Dictionary with id, timestamp, pair, direction, entry_price, stop_loss, take_profit
            
        Returns:
            Dictionary with outcome, pnl, exit_price, bars_held, max_favorable_pips, max_adverse_pips
            or None if evaluation failed
        """
        try:
            # Convert pair format for yfinance
            pair_formatted = self._format_pair_for_yfinance(signal['pair'])
            
            # Get price data from signal time to now
            start_date = datetime.fromisoformat(signal['timestamp'])
            end_date = datetime.utcnow()
            
            price_data = self._get_price_data(pair_formatted, start_date, end_date)
            
            if price_data is None or len(price_data) < 2:
                return None
            
            # Evaluate outcome
            entry = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profit = signal.get('take_profit')
            direction = signal['direction']
            
            outcome = self._check_outcome(
                price_data, entry, stop_loss, take_profit, direction
            )
            
            return outcome
            
        except Exception as e:
            print(f"Error evaluating signal {signal.get('id', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_pair_for_yfinance(self, pair: str) -> str:
        """Convert pair format for yfinance"""
        clean_pair = pair.replace('/', '').replace('-', '').upper()
        return f"{clean_pair}=X"
    
    def _get_price_data(
        self, pair: str, start: datetime, end: datetime
    ) -> Optional[pd.DataFrame]:
        """Get historical price data using yfinance"""
        cache_key = f"{pair}_{start.date()}_{end.date()}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # For scalping, use 5-minute intervals
            data = yf.download(
                pair,
                start=start.strftime('%Y-%m-%d'),
                end=(end + timedelta(days=1)).strftime('%Y-%m-%d'),  # Add 1 day to ensure we get today's data
                interval='5m',
                progress=False
            )
            
            if len(data) > 0:
                self.cache[cache_key] = data
                return data
            
        except Exception as e:
            print(f"Error fetching data for {pair}: {e}")
        
        return None
    
    def _check_outcome(
        self,
        price_data: pd.DataFrame,
        entry: float,
        stop_loss: float,
        take_profit: Optional[float],
        direction: str
    ) -> Dict:
        """
        Check if TP or SL was hit
        
        Args:
            price_data: DataFrame with High, Low, Close columns
            entry: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price (optional)
            direction: 'LONG' or 'SHORT'
            
        Returns:
            Dictionary with outcome, pnl, exit_price, bars_held, max_favorable_pips, max_adverse_pips
        """
        is_long = direction.upper() in ['LONG', 'BUY']
        
        max_favorable_pips = 0.0
        max_adverse_pips = 0.0
        pip_value = 0.0001 if 'JPY' not in str(entry) else 0.01
        
        for i, (timestamp, row) in enumerate(price_data.iterrows()):
            high = row['High']
            low = row['Low']
            
            if is_long:
                # Track max favorable/adverse
                favorable = (high - entry) / pip_value
                adverse = (entry - low) / pip_value
                max_favorable_pips = max(max_favorable_pips, favorable)
                max_adverse_pips = max(max_adverse_pips, adverse)
                
                # Check stop loss first
                if low <= stop_loss:
                    pnl_pips = (stop_loss - entry) / pip_value
                    return {
                        'outcome': 'LOSS',
                        'pnl_pips': pnl_pips,
                        'exit_price': stop_loss,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable_pips,
                        'max_adverse_pips': max_adverse_pips
                    }
                
                # Check take profit
                if take_profit and high >= take_profit:
                    pnl_pips = (take_profit - entry) / pip_value
                    return {
                        'outcome': 'WIN',
                        'pnl_pips': pnl_pips,
                        'exit_price': take_profit,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable_pips,
                        'max_adverse_pips': max_adverse_pips
                    }
            else:  # SHORT
                # Track max favorable/adverse
                favorable = (entry - low) / pip_value
                adverse = (high - entry) / pip_value
                max_favorable_pips = max(max_favorable_pips, favorable)
                max_adverse_pips = max(max_adverse_pips, adverse)
                
                # Check stop loss first
                if high >= stop_loss:
                    pnl_pips = (entry - stop_loss) / pip_value
                    return {
                        'outcome': 'LOSS',
                        'pnl_pips': pnl_pips,
                        'exit_price': stop_loss,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable_pips,
                        'max_adverse_pips': max_adverse_pips
                    }
                
                # Check take profit
                if take_profit and low <= take_profit:
                    pnl_pips = (entry - take_profit) / pip_value
                    return {
                        'outcome': 'WIN',
                        'pnl_pips': pnl_pips,
                        'exit_price': take_profit,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable_pips,
                        'max_adverse_pips': max_adverse_pips
                    }
        
        # If neither TP nor SL hit, check current P&L
        current_price = price_data.iloc[-1]['Close']
        pip_value = 0.0001 if 'JPY' not in str(entry) else 0.01
        
        if is_long:
            pnl_pips = (current_price - entry) / pip_value
        else:
            pnl_pips = (entry - current_price) / pip_value
        
        # For scalping, if trade is old enough and hasn't hit TP/SL, mark as MISSED
        # (entry price was never reached or trade expired)
        bars_held = len(price_data)
        hours_old = bars_held * 5 / 60  # 5-minute bars
        
        if hours_old >= 4:  # 4+ hours old
            outcome = 'MISSED'
            pnl_pips = 0.0  # No P&L if never triggered
        else:
            # Still pending, but return current status
            outcome = 'WIN' if pnl_pips > 0 else 'LOSS'
        
        return {
            'outcome': outcome,
            'pnl_pips': pnl_pips,
            'exit_price': current_price,
            'bars_held': bars_held,
            'max_favorable_pips': max_favorable_pips,
            'max_adverse_pips': max_adverse_pips
        }


class LLMLearningEngine:
    """Trains and manages LLM performance models for Scalp-Engine"""
    
    def __init__(self, db: ScalpingRLEnhanced):
        self.db = db
    
    def calculate_llm_weights(self) -> Dict[str, float]:
        """
        Calculate performance weights for each LLM
        
        Returns:
            Dictionary mapping LLM source to weight (0.0-1.0)
        """
        weights = {}
        
        # Scalp-Engine: gemini, synthesis, chatgpt, claude, deepseek
        llm_sources = ['gemini', 'synthesis', 'chatgpt', 'claude', 'deepseek']
        
        for llm in llm_sources:
            df = self.db.get_llm_performance(llm_source=llm)
            
            if len(df) < 5:  # Need minimum samples
                default_w = 1.0 / len(llm_sources) if llm_sources else 0.25
                weights[llm] = default_w
                continue
            
            # Calculate win rate (excluding MISSED and PENDING)
            wins = df[df['outcome'] == 'WIN']
            evaluated_trades = df[df['outcome'].isin(['WIN', 'LOSS'])]
            win_rate = len(wins) / len(evaluated_trades) if len(evaluated_trades) > 0 else 0.5
            
            # Count MISSED trades
            missed_trades = df[df['outcome'] == 'MISSED']
            missed_count = len(missed_trades)
            total_signals = len(df)
            missed_rate = missed_count / total_signals if total_signals > 0 else 0
            
            # Calculate profit factor
            total_profit = wins['pnl_pips'].sum() if len(wins) > 0 else 0
            losses = df[df['outcome'] == 'LOSS']
            total_loss = abs(losses['pnl_pips'].sum()) if len(losses) > 0 else 0
            
            profit_factor = total_profit / total_loss if total_loss > 0 else 1.0
            
            # Penalize high missed rate
            missed_penalty = 1.0 - (missed_rate * 0.5)  # Max 50% penalty
            
            # Combined score
            accuracy_score = (win_rate * 0.6) + (min(profit_factor / 2, 0.5) * 0.4)
            accuracy_score = accuracy_score * missed_penalty
            
            weights[llm] = max(accuracy_score, 0.05)  # Minimum 5% weight
        
        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        else:
            default_w = 1.0 / len(llm_sources) if llm_sources else 0.25
            weights = {k: default_w for k in llm_sources}
        
        return weights
    
    def analyze_consensus(self) -> Dict:
        """Analyze performance by consensus level"""
        df = self.db.get_llm_performance()
        
        if len(df) == 0:
            return {}
        
        consensus_stats = {
            'ALL_AGREE': {'wins': 0, 'total': 0, 'pnl': []},
            '2_AGREE': {'wins': 0, 'total': 0, 'pnl': []},
            'ALL_DISAGREE': {'wins': 0, 'total': 0, 'pnl': []}
        }
        
        # Group by timestamp and pair to find consensus
        grouped = df.groupby(['timestamp', 'pair', 'direction'])
        
        for (ts, pair, direction), group in grouped:
            count = len(group)
            
            if count >= 3:  # All 3+ LLMs agree
                consensus_type = 'ALL_AGREE'
            elif count == 2:  # 2 agree
                consensus_type = '2_AGREE'
            else:  # Disagree or only 1
                consensus_type = 'ALL_DISAGREE'
            
            # Check outcomes
            wins = group[group['outcome'] == 'WIN']
            
            consensus_stats[consensus_type]['total'] += 1
            consensus_stats[consensus_type]['wins'] += len(wins)
            if 'pnl_pips' in group.columns:
                consensus_stats[consensus_type]['pnl'].extend(
                    group['pnl_pips'].dropna().tolist()
                )
        
        # Calculate win rates
        results = {}
        for consensus_type, stats in consensus_stats.items():
            if stats['total'] > 0:
                results[consensus_type] = {
                    'win_rate': stats['wins'] / stats['total'],
                    'sample_size': stats['total'],
                    'avg_pnl': np.mean(stats['pnl']) if stats['pnl'] else 0
                }
        
        return results
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'llm_performance': {},
            'consensus_analysis': {},
            'recommended_weights': {}
        }
        
        # LLM performance
        for llm in ['gemini', 'synthesis', 'chatgpt', 'claude']:
            df = self.db.get_llm_performance(llm_source=llm)
            
            if len(df) > 0:
                wins = df[df['outcome'] == 'WIN']
                losses = df[df['outcome'] == 'LOSS']
                executed = df[df['executed'] == 1]
                simulated = df[df['executed'] == 0]
                
                report['llm_performance'][llm] = {
                    'total_signals': len(df),
                    'executed_count': len(executed),
                    'simulated_count': len(simulated),
                    'win_rate': len(wins) / len(df[df['outcome'].isin(['WIN', 'LOSS'])]) if len(df[df['outcome'].isin(['WIN', 'LOSS'])]) > 0 else 0,
                    'avg_pnl': df['pnl_pips'].mean() if 'pnl_pips' in df.columns else 0,
                    'profit_factor': wins['pnl_pips'].sum() / abs(losses['pnl_pips'].sum()) if len(losses) > 0 and losses['pnl_pips'].sum() != 0 else 0
                }
        
        # Consensus analysis
        report['consensus_analysis'] = self.analyze_consensus()
        
        # Weights
        report['recommended_weights'] = self.calculate_llm_weights()
        
        return report
