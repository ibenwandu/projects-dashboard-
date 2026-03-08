"""
Trade Alerts Reinforcement Learning System
Tracks LLM recommendations and learns from outcomes
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional
import json
import re
from pathlib import Path
import yfinance as yf

# Import logger for error handling and diagnostics
try:
    from src.logger import setup_logger
    logger = setup_logger()
except ImportError:
    # Fallback if logger not available
    import logging
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


class CurrentPriceValidator:
    """Validates that 'Current Price' in recommendations matches live market prices"""
    
    def __init__(self):
        """Initialize validator with price monitor"""
        try:
            from src.price_monitor import PriceMonitor
            self.price_monitor = PriceMonitor()
        except ImportError:
            self.price_monitor = None
            logger.warning("PriceMonitor not available - CurrentPriceValidator will be limited")
    
    def validate_current_price(self, pair: str, current_price: Optional[float] = None) -> Dict:
        """
        Validate that current_price matches live market price
        
        Args:
            pair: Currency pair (e.g., 'EUR/USD' or 'EURUSD')
            current_price: Current price from recommendation (optional)
            
        Returns:
            Dict with:
            - is_valid: bool - True if price matches or is close
            - live_price: float or None - Current live market price
            - recommended_price: float or None - Price from recommendation
            - difference_pips: float - Difference in pips
            - difference_percent: float - Difference as percentage
            - warning: str - Warning message if mismatch detected
        """
        # Normalize pair format
        if '/' in pair:
            pair_formatted = pair
        else:
            # Convert GBPUSD -> GBP/JPY
            if len(pair) == 6:
                pair_formatted = f"{pair[:3]}/{pair[3:]}"
            else:
                return {
                    'is_valid': True,
                    'live_price': None,
                    'recommended_price': current_price,
                    'difference_pips': None,
                    'difference_percent': None,
                    'warning': f'Invalid pair format: {pair}'
                }
        
        if not self.price_monitor:
            return {
                'is_valid': True,  # Don't reject if we can't validate
                'live_price': None,
                'recommended_price': current_price,
                'difference_pips': None,
                'difference_percent': None,
                'warning': 'PriceMonitor not available - validation skipped'
            }
        
        # Get live market price
        live_price = self.price_monitor.get_rate(pair_formatted)
        
        if live_price is None:
            return {
                'is_valid': True,  # Don't reject if we can't get price
                'live_price': None,
                'recommended_price': current_price,
                'difference_pips': None,
                'difference_percent': None,
                'warning': f'Could not fetch live price for {pair_formatted}'
            }
        
        # If no current_price provided, just return live price
        if current_price is None:
            return {
                'is_valid': True,
                'live_price': live_price,
                'recommended_price': None,
                'difference_pips': None,
                'difference_percent': None,
                'warning': None
            }
        
        # Calculate difference
        difference = abs(live_price - current_price)
        difference_percent = (difference / live_price) * 100 if live_price else 0
        
        # Determine pip value
        pip_value = 0.01 if 'JPY' in pair_formatted.upper() else 0.0001
        difference_pips = difference / pip_value
        
        # Threshold: warn if difference > 0.1% or > 10 pips
        threshold_percent = 0.1
        threshold_pips = 10.0
        
        is_valid = difference_percent <= threshold_percent and difference_pips <= threshold_pips
        
        warning = None
        if not is_valid:
            warning = (
                f"Current Price mismatch detected for {pair_formatted}: "
                f"Recommended={current_price:.5f}, Live={live_price:.5f} "
                f"(diff: {difference_pips:.1f} pips, {difference_percent:.2f}%). "
                f"Recommended price appears to be from historical data, not live market."
            )
        
        return {
            'is_valid': is_valid,
            'live_price': live_price,
            'recommended_price': current_price,
            'difference_pips': difference_pips,
            'difference_percent': difference_percent,
            'warning': warning
        }


class EntryPriceValidator:
    """Validates entry prices against current market price"""
    
    def __init__(self, price_monitor=None):
        """
        Initialize validator
        
        Args:
            price_monitor: PriceMonitor instance (optional, creates new if None)
        """
        if price_monitor is None:
            try:
                from src.price_monitor import PriceMonitor
                self.price_monitor = PriceMonitor()
            except ImportError:
                self.price_monitor = None
                logger.warning("PriceMonitor not available - entry price validation disabled")
        else:
            self.price_monitor = price_monitor
    
    def validate_entry_price(self, pair: str, entry_price: float, timeframe: str = 'INTRADAY') -> Dict:
        """
        Validate entry price against current market price
        
        Args:
            pair: Currency pair (e.g., 'GBP/JPY' or 'GBPJPY')
            entry_price: Recommended entry price
            timeframe: 'INTRADAY' or 'SWING'
        
        Returns:
            Dict with:
            - is_valid: bool - True if entry price is realistic
            - current_price: float or None - Current market price
            - distance_pips: float - Distance from current price in pips
            - distance_percent: float - Distance as percentage
            - max_allowed_distance_pips: float - Maximum allowed distance
            - reason: str - Reason for validation result
        """
        # Normalize pair format (handle both GBP/JPY and GBPJPY)
        if '/' in pair:
            pair_formatted = pair
        else:
            # Convert GBPJPY -> GBP/JPY
            if len(pair) == 6:
                pair_formatted = f"{pair[:3]}/{pair[3:]}"
            else:
                pair_formatted = pair
        
        if not self.price_monitor:
            # Can't validate without price monitor
            return {
                'is_valid': True,  # Don't reject if we can't validate
                'current_price': None,
                'distance_pips': None,
                'distance_percent': None,
                'max_allowed_distance_pips': None,
                'reason': 'PriceMonitor not available - validation skipped'
            }
        
        # Get current market price
        current_price = self.price_monitor.get_rate(pair_formatted)
        
        if current_price is None:
            # Can't get current price - allow it but log warning
            return {
                'is_valid': True,  # Don't reject if we can't get price
                'current_price': None,
                'distance_pips': None,
                'distance_percent': None,
                'max_allowed_distance_pips': None,
                'reason': 'Could not fetch current price - validation skipped'
            }
        
        # Calculate distance
        distance = abs(entry_price - current_price)
        distance_percent = (distance / current_price) * 100
        
        # Determine pip value (0.0001 for most pairs, 0.01 for JPY pairs)
        pip_value = 0.01 if 'JPY' in pair_formatted.upper() else 0.0001
        distance_pips = distance / pip_value
        
        # Determine maximum allowed distance based on timeframe
        if timeframe.upper() == 'INTRADAY':
            # INTRADAY: Entry should be close to current price (within 50 pips or 0.5%)
            max_distance_pips = 50.0
            max_distance_percent = 0.5
        elif timeframe.upper() == 'SWING':
            # SWING: Entry can be further (within 200 pips or 2%)
            max_distance_pips = 200.0
            max_distance_percent = 2.0
        else:
            # Default: Moderate tolerance (100 pips or 1%)
            max_distance_pips = 100.0
            max_distance_percent = 1.0
        
        # Use the more restrictive of pips or percentage
        max_distance = max(
            max_distance_pips * pip_value,  # Convert pips to price units
            current_price * (max_distance_percent / 100.0)  # Percentage of current price
        )
        
        # Validate
        is_valid = distance <= max_distance
        
        if is_valid:
            reason = f"Entry price within acceptable range ({distance_pips:.1f} pips, {distance_percent:.2f}% from current)"
        else:
            reason = f"Entry price too far from current: {distance_pips:.1f} pips ({distance_percent:.2f}%) away. Max allowed: {max_distance_pips:.0f} pips ({max_distance_percent}%)"
        
        return {
            'is_valid': is_valid,
            'current_price': current_price,
            'distance_pips': distance_pips,
            'distance_percent': distance_percent,
            'max_allowed_distance_pips': max_distance_pips,
            'reason': reason
        }


class RecommendationDatabase:
    """Stores and manages all LLM recommendations"""
    
    def __init__(self, db_path: str = "trade_alerts_rl.db", validate_entries: bool = True):
        self.db_path = db_path
        self.validate_entries = validate_entries
        self.entry_validator = EntryPriceValidator() if validate_entries else None
        self.current_price_validator = CurrentPriceValidator()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Main recommendations table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    date_generated TEXT NOT NULL,
                    llm_source TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit_1 REAL,
                    take_profit_2 REAL,
                    position_size_pct REAL,
                    confidence TEXT,
                    rationale TEXT,
                    timeframe TEXT,  -- 'INTRADAY' or 'SWING'
                    
                    -- Market context at time
                    market_session TEXT,
                    day_of_week TEXT,
                    
                    -- Outcome tracking
                    outcome TEXT,  -- 'WIN_TP1', 'WIN_TP2', 'LOSS_SL', 'NEUTRAL', 'PENDING', 'MISSED'
                    exit_price REAL,
                    pnl_pips REAL,
                    bars_held INTEGER,
                    max_favorable_pips REAL,
                    max_adverse_pips REAL,
                    outcome_timestamp TEXT,
                    evaluated INTEGER DEFAULT 0,
                    
                    -- Link to original file
                    source_file TEXT,
                    
                    UNIQUE(timestamp, llm_source, pair, direction, entry_price)
                )
            ''')
            
            # Add timeframe column if it doesn't exist (for existing databases)
            try:
                conn.execute('ALTER TABLE recommendations ADD COLUMN timeframe TEXT')
                conn.commit()
                logger.info("✅ Added timeframe column to existing database")
            except sqlite3.OperationalError:
                # Column already exists, ignore
                pass
            
            # LLM performance tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS llm_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    llm_source TEXT NOT NULL,
                    pair TEXT,
                    timeframe TEXT,  -- 'INTRADAY' or 'SWING' for separate tracking
                    total_recommendations INTEGER,
                    total_evaluated INTEGER,
                    win_rate REAL,
                    avg_pnl_pips REAL,
                    profit_factor REAL,
                    avg_bars_to_tp REAL,
                    avg_bars_to_sl REAL,
                    accuracy_weight REAL
                )
            ''')
            
            # Learning checkpoints
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_recommendations INTEGER,
                    total_evaluated INTEGER,
                    chatgpt_weight REAL,
                    gemini_weight REAL,
                    claude_weight REAL,
                    synthesis_weight REAL,
                    overall_win_rate REAL,
                    notes TEXT
                )
            ''')
            
            # Consensus analysis
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consensus_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    consensus_type TEXT,  -- 'ALL_AGREE', '2_AGREE', 'ALL_DISAGREE'
                    win_rate REAL,
                    sample_size INTEGER,
                    avg_pnl_pips REAL
                )
            ''')
            
            # Migration: add deepseek_weight to learning_checkpoints if missing
            try:
                conn.execute("ALTER TABLE learning_checkpoints ADD COLUMN deepseek_weight REAL")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            conn.commit()
    
    def log_recommendation(self, rec: Dict) -> Optional[int]:
        """
        Log a recommendation to database
        
        Returns:
            Recommendation ID if logged successfully, None if rejected
        """
        # Validate entry price if validation is enabled
        if self.validate_entries and self.entry_validator:
            pair = rec.get('pair', '')
            entry_price = rec.get('entry_price')
            timeframe = rec.get('timeframe', 'INTRADAY')
            
            if entry_price:
                validation = self.entry_validator.validate_entry_price(pair, entry_price, timeframe)
                
                if not validation['is_valid']:
                    # Entry price is unrealistic - still log it but mark for RL learning
                    current_price_str = f"{validation['current_price']:.5f}" if validation['current_price'] is not None else "N/A"
                    distance_pips_str = f"{validation['distance_pips']:.1f}" if validation['distance_pips'] is not None else "N/A"
                    distance_percent_str = f"{validation['distance_percent']:.2f}" if validation['distance_percent'] is not None else "N/A"
                    logger.warning(
                        f"⚠️  Unrealistic entry price for {pair}: "
                        f"Entry={entry_price:.5f}, Current={current_price_str}, "
                        f"Distance={distance_pips_str} pips ({distance_percent_str}%). "
                        f"Reason: {validation['reason']}"
                    )
                    # Still log it so RL can learn which LLMs have this problem
                    # But we'll track this in the rationale
                    original_rationale = rec.get('rationale', '')
                    rec['rationale'] = f"[UNREALISTIC_ENTRY: {validation['reason']}] {original_rationale}"
                    rec['confidence'] = 'UNREALISTIC'  # Mark confidence to track this
                else:
                    # Valid entry price
                    current_price_str = f"{validation['current_price']:.5f}" if validation['current_price'] is not None else "N/A"
                    distance_pips_str = f"{validation['distance_pips']:.1f}" if validation['distance_pips'] is not None else "N/A"
                    logger.debug(
                        f"✅ Valid entry price for {pair}: "
                        f"Entry={entry_price:.5f}, Current={current_price_str}, "
                        f"Distance={distance_pips_str} pips"
                    )
        
        # Validate current price if provided in recommendation
        pair = rec.get('pair', '')
        current_price = rec.get('current_price')
        if current_price and self.current_price_validator:
            price_validation = self.current_price_validator.validate_current_price(pair, current_price)
            
            if price_validation['warning']:
                # Log warning about price mismatch
                logger.warning(
                    f"⚠️  {price_validation['warning']}"
                )
                # Add warning to rationale for tracking
                original_rationale = rec.get('rationale', '')
                rec['rationale'] = f"[PRICE_MISMATCH: {price_validation['warning']}] {original_rationale}"
            
            # Update current_price with live price if available (for accuracy)
            if price_validation['live_price']:
                rec['current_price'] = price_validation['live_price']
                if price_validation['recommended_price'] and price_validation['recommended_price'] != price_validation['live_price']:
                    logger.info(
                        f"🔧 Updated current_price for {pair}: "
                        f"{price_validation['recommended_price']:.5f} → {price_validation['live_price']:.5f} "
                        f"(corrected from historical data)"
                    )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT OR IGNORE INTO recommendations (
                    timestamp, date_generated, llm_source, pair, direction,
                    entry_price, stop_loss, take_profit_1, take_profit_2,
                    position_size_pct, confidence, rationale, timeframe,
                    market_session, day_of_week, outcome, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rec['timestamp'],
                rec.get('date_generated', rec['timestamp'].split('T')[0]),
                rec['llm_source'],
                rec['pair'],
                rec['direction'],
                rec['entry_price'],
                rec.get('stop_loss'),
                rec.get('take_profit_1'),
                rec.get('take_profit_2'),
                rec.get('position_size_pct', 2.0),
                rec.get('confidence'),
                rec.get('rationale', ''),
                rec.get('timeframe', 'INTRADAY'),  # Default to INTRADAY if not specified
                rec.get('market_session', 'UNKNOWN'),
                rec.get('day_of_week', 'UNKNOWN'),
                'PENDING',
                rec.get('source_file', '')
            ))
            conn.commit()
            rec_id = cursor.lastrowid
            
            # Check if it was a duplicate (INSERT OR IGNORE returns 0 if duplicate)
            if rec_id == 0:
                return None
            
            return rec_id
    
    def get_pending_recommendations(self, min_age_hours: int = 4) -> pd.DataFrame:
        """Get recommendations that need evaluation"""
        cutoff = (datetime.utcnow() - timedelta(hours=min_age_hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query('''
                SELECT * FROM recommendations
                WHERE outcome = 'PENDING'
                AND timestamp < ?
                AND evaluated = 0
                ORDER BY timestamp
            ''', conn, params=(cutoff,))
    
    def get_expired_recommendations(self, min_age_hours: int = 24) -> pd.DataFrame:
        """
        Get recommendations that are old enough to be considered expired
        These are candidates for MISSED evaluation if they never triggered
        """
        cutoff = (datetime.utcnow() - timedelta(hours=min_age_hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query('''
                SELECT * FROM recommendations
                WHERE outcome = 'PENDING'
                AND timestamp < ?
                AND evaluated = 0
                ORDER BY timestamp
            ''', conn, params=(cutoff,))
    
    def update_outcome(self, rec_id: int, outcome_data: Dict):
        """Update recommendation with outcome"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE recommendations
                SET outcome = ?,
                    exit_price = ?,
                    pnl_pips = ?,
                    bars_held = ?,
                    max_favorable_pips = ?,
                    max_adverse_pips = ?,
                    outcome_timestamp = ?,
                    evaluated = 1
                WHERE id = ?
            ''', (
                outcome_data['outcome'],
                outcome_data['exit_price'],
                outcome_data['pnl_pips'],
                outcome_data['bars_held'],
                outcome_data['max_favorable_pips'],
                outcome_data['max_adverse_pips'],
                outcome_data['timestamp'],
                rec_id
            ))
            conn.commit()
    
    def get_llm_performance(self, llm_source: str = None, pair: str = None) -> pd.DataFrame:
        """Get performance statistics for LLM"""
        query = 'SELECT * FROM recommendations WHERE evaluated = 1'
        params = []
        
        if llm_source:
            query += ' AND llm_source = ?'
            params.append(llm_source)
        
        if pair:
            query += ' AND pair = ?'
            params.append(pair)
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=params if params else None)
    
    def get_all_recommendations(self, llm_source: str = None) -> pd.DataFrame:
        """Get all recommendations (evaluated and unevaluated) for an LLM"""
        query = 'SELECT * FROM recommendations WHERE 1=1'
        params = []
        
        if llm_source:
            query += ' AND llm_source = ?'
            params.append(llm_source)
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=params if params else None)
    
    def save_performance_snapshot(self, llm_source: str, stats: Dict):
        """Save performance snapshot"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO llm_performance (
                    timestamp, llm_source, pair, total_recommendations,
                    total_evaluated, win_rate, avg_pnl_pips, profit_factor,
                    avg_bars_to_tp, avg_bars_to_sl, accuracy_weight
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat(),
                llm_source,
                stats.get('pair'),
                stats['total_recommendations'],
                stats['total_evaluated'],
                stats['win_rate'],
                stats['avg_pnl_pips'],
                stats['profit_factor'],
                stats.get('avg_bars_to_tp', 0),
                stats.get('avg_bars_to_sl', 0),
                stats.get('accuracy_weight', 1.0)
            ))
            conn.commit()
    
    def save_learning_checkpoint(self, weights: Dict, stats: Dict):
        """Save learning checkpoint"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO learning_checkpoints (
                    timestamp, total_recommendations, total_evaluated,
                    chatgpt_weight, gemini_weight, claude_weight,
                    synthesis_weight, overall_win_rate, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat(),
                stats['total_recommendations'],
                stats['total_evaluated'],
                weights.get('chatgpt', 0.25),
                weights.get('gemini', 0.25),
                weights.get('claude', 0.25),
                weights.get('synthesis', 0.25),
                stats['overall_win_rate'],
                stats.get('notes', '')
            ))
            conn.commit()


class RecommendationParser:
    """Parses recommendation files and extracts trade details"""
    
    def parse_text(self, text: str, llm_source: str, timestamp: str = None, filename: str = "") -> List[Dict]:
        """
        Parse recommendations from text directly
        
        Args:
            text: Text content to parse
            llm_source: LLM source name (CHATGPT, GEMINI, CLAUDE, SYNTHESIS)
            timestamp: ISO format timestamp (defaults to now)
            filename: Source filename (optional)
        
        Returns:
            List of recommendation dictionaries
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        return self._parse_recommendations(text, llm_source.upper(), timestamp, filename)
    
    def parse_file(self, file_path: str) -> List[Dict]:
        """Parse a recommendation file (supports both .txt and .json)"""
        filename = Path(file_path).name
        
        # Extract timestamp from filename
        timestamp_match = re.search(r'(\d{8})_(\d{6})', filename)
        if timestamp_match:
            date_str, time_str = timestamp_match.groups()
            timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S").isoformat()
        else:
            timestamp = datetime.utcnow().isoformat()
        
        recommendations = []
        
        # Check if it's a JSON file
        if filename.lower().endswith('.json'):
            return self._parse_json_file(file_path, timestamp, filename)
        
        # Otherwise, parse as text file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse each LLM section (try multiple section name variations)
        sections = {}
        
        # Try exact matches first
        section_patterns = {
            'CHATGPT': ['CHATGPT RECOMMENDATIONS', 'CHATGPT', 'OPENAI', 'GPT'],
            'GEMINI': ['GEMINI RECOMMENDATIONS', 'GEMINI', 'GOOGLE'],
            'CLAUDE': ['CLAUDE RECOMMENDATIONS', 'CLAUDE', 'ANTHROPIC'],
            'SYNTHESIS': ['GEMINI FINAL RECOMMENDATION', 'FINAL RECOMMENDATION', 'SYNTHESIS', 'COMBINED']
        }
        
        for llm_source, patterns in section_patterns.items():
            for pattern in patterns:
                section_text = self._extract_section(content, pattern)
                if section_text:
                    sections[llm_source] = section_text
                    break
        
        # If no structured sections found, try parsing the entire content
        if not any(sections.values()):
            # Try to find recommendations in free-form text
            recommendations.extend(self._parse_freeform_recommendations(content, timestamp, filename))
        else:
            # Parse structured sections
            for llm_source, section_text in sections.items():
                if section_text:
                    recs = self._parse_recommendations(section_text, llm_source, timestamp, filename)
                    recommendations.extend(recs)
        
        return recommendations
    
    def _parse_json_file(self, file_path: str, timestamp: str, filename: str) -> List[Dict]:
        """Parse JSON recommendation file"""
        import json
        recommendations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            # Structure 1: Direct list of recommendations
            if isinstance(data, list):
                for item in data:
                    rec = self._json_to_recommendation(item, timestamp, filename)
                    if rec:
                        recommendations.append(rec)
            
            # Structure 2: Dict with 'recommendations' key
            elif isinstance(data, dict):
                if 'recommendations' in data:
                    for item in data['recommendations']:
                        rec = self._json_to_recommendation(item, timestamp, filename)
                        if rec:
                            recommendations.append(rec)
                
                # Structure 3: Dict with LLM sources as keys (e.g., {'chatgpt': {...}, 'gemini': {...}})
                elif any(key.upper() in ['CHATGPT', 'GEMINI', 'CLAUDE', 'SYNTHESIS'] for key in data.keys()):
                    for llm_source, llm_data in data.items():
                        if isinstance(llm_data, list):
                            for item in llm_data:
                                rec = self._json_to_recommendation(item, timestamp, filename, llm_source)
                                if rec:
                                    recommendations.append(rec)
                        elif isinstance(llm_data, dict):
                            rec = self._json_to_recommendation(llm_data, timestamp, filename, llm_source)
                            if rec:
                                recommendations.append(rec)
                        elif isinstance(llm_data, str):
                            # LLM data is text - parse it
                            recs = self._parse_recommendations(llm_data, llm_source.upper(), timestamp, filename)
                            recommendations.extend(recs)
                
                # Structure 4: Dict with 'llm_recommendations' key (new Trade-Alerts format)
                elif 'llm_recommendations' in data:
                    logger.debug(f"Found Structure 4: llm_recommendations with keys: {list(data['llm_recommendations'].keys())}")
                    for llm_name, llm_text in data['llm_recommendations'].items():
                        if isinstance(llm_text, str):
                            recs = self._parse_recommendations(llm_text, llm_name.upper(), timestamp, filename)
                            logger.debug(f"Parsed {len(recs)} recommendations from {llm_name}")
                            recommendations.extend(recs)
                    # Also parse gemini_final if present
                    if 'gemini_final' in data and isinstance(data['gemini_final'], str):
                        gemini_final_len = len(data['gemini_final'])
                        logger.info(f"Parsing gemini_final (length: {gemini_final_len} chars)")
                        recs = self._parse_recommendations(data['gemini_final'], 'SYNTHESIS', timestamp, filename)
                        logger.info(f"Parsed {len(recs)} recommendations from gemini_final")
                        recommendations.extend(recs)
                    else:
                        logger.warning(f"gemini_final not found or not a string. Available keys: {list(data.keys())}")
                
                # Structure 5: Single recommendation object
                else:
                    rec = self._json_to_recommendation(data, timestamp, filename)
                    if rec:
                        recommendations.append(rec)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {filename}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error parsing JSON file {filename}: {e}", exc_info=True)
        
        return recommendations
    
    def _json_to_recommendation(self, item: Dict, timestamp: str, filename: str, llm_source: str = None) -> Optional[Dict]:
        """Convert JSON item to recommendation dict"""
        try:
            # Try to extract LLM source
            if not llm_source:
                llm_source = item.get('llm_source') or item.get('source') or item.get('llm') or 'SYNTHESIS'
            
            # Normalize LLM source name
            llm_source_upper = llm_source.upper()
            if 'CHATGPT' in llm_source_upper or 'GPT' in llm_source_upper:
                llm_source = 'chatgpt'
            elif 'GEMINI' in llm_source_upper:
                llm_source = 'gemini'
            elif 'CLAUDE' in llm_source_upper:
                llm_source = 'claude'
            elif 'DEEPSEEK' in llm_source_upper:
                llm_source = 'deepseek'
            else:
                llm_source = 'synthesis'
            
            # Extract pair (handle various formats)
            pair = item.get('pair') or item.get('currency_pair') or item.get('symbol')
            if pair:
                pair = pair.replace('/', '').replace('-', '').upper()
            
            # Extract direction
            direction = item.get('direction') or item.get('position') or item.get('side')
            if direction:
                direction = direction.upper()
                if direction in ['BUY', 'LONG']:
                    direction = 'LONG'
                elif direction in ['SELL', 'SHORT']:
                    direction = 'SHORT'
            
            # Extract prices
            entry = item.get('entry') or item.get('entry_price') or item.get('price')
            stop_loss = item.get('stop_loss') or item.get('sl') or item.get('stop')
            tp1 = item.get('take_profit_1') or item.get('tp1') or item.get('target_1') or item.get('target')
            tp2 = item.get('take_profit_2') or item.get('tp2') or item.get('target_2')
            
            # Convert to float if needed
            try:
                entry = float(entry) if entry else None
                stop_loss = float(stop_loss) if stop_loss else None
                tp1 = float(tp1) if tp1 else None
                tp2 = float(tp2) if tp2 else None
            except (ValueError, TypeError):
                pass
            
            # Extract other fields
            position_size = item.get('position_size_pct') or item.get('position_size') or item.get('size_pct') or 2.0
            confidence = item.get('confidence') or item.get('confidence_level')
            rationale = item.get('rationale') or item.get('reasoning') or item.get('analysis') or ''
            
            # Extract timeframe classification
            timeframe = item.get('timeframe', 'INTRADAY')
            if isinstance(timeframe, str):
                timeframe = timeframe.upper()
                if timeframe not in ['INTRADAY', 'SWING']:
                    timeframe = 'INTRADAY'  # Default to INTRADAY if invalid
            else:
                timeframe = 'INTRADAY'
            
            # Minimum required fields
            if pair and direction and entry and stop_loss:
                return {
                    'timestamp': timestamp,
                    'date_generated': timestamp.split('T')[0],
                    'llm_source': llm_source.lower(),
                    'pair': pair,
                    'direction': direction,
                    'entry_price': entry,
                    'stop_loss': stop_loss,
                    'take_profit_1': tp1,
                    'take_profit_2': tp2,
                    'position_size_pct': float(position_size) if position_size else 2.0,
                    'confidence': confidence,
                    'rationale': str(rationale)[:500] if rationale else '',
                    'timeframe': timeframe,
                    'source_file': filename
                }
        
        except Exception as e:
            # Use print for now since logger may not be available
            pass  # Silently skip invalid items
        
        return None
    
    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract a specific section from content"""
        pattern = f"={'{'}3,{'}'}\\s*{section_name}\\s*={'{'}3,{'}'}(.+?)(?:={'{'}3,{'}'}|$)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def _parse_recommendations(self, text: str, llm_source: str, timestamp: str, filename: str) -> List[Dict]:
        """Parse recommendations from text - ENHANCED for all LLM formats"""
        recommendations = []
        
        # ========================================================================
        # PATTERN SET 1: Original "Currency Pair:" format (ChatGPT)
        # ========================================================================
        pattern_1 = r'(?:###\s+\d+\.|\*\s+)?\*\*?Currency\s+Pair:?\*\*?\s+([A-Z]{3})[/\s]([A-Z]{3})'
        
        matches_1 = list(re.finditer(
            rf'{pattern_1}(.*?)(?=\n(?:###\s+\d+\.|\*\s+\*\*Currency\s+Pair|Trade\s+Recommendation\s+\d+|\d+\.\s+[A-Z]{{3}}[/\s]|$))',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 2: "Trade Recommendation X:" format (Gemini)
        # ========================================================================
        pattern_2 = r'###\s+\*\*Trade\s+Recommendation\s+\d+:\s+(?:Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})\*\*'
        
        matches_2 = list(re.finditer(
            rf'{pattern_2}(.*?)(?=\n###\s+\*\*Trade\s+Recommendation|\n###\s+\*\*Trade\s+\d+:|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 3: "Trade X:" format (Gemini Final)
        # ========================================================================
        pattern_3 = r'###\s+\*\*Trade\s+\d+:\s+(?:Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})'
        
        matches_3 = list(re.finditer(
            rf'{pattern_3}(.*?)(?=\n###\s+\*\*Trade\s+\d+:|\n---\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 4: Numbered list "1. GBP/USD" (Claude)
        # ========================================================================
        pattern_4 = r'^\d+\.\s+([A-Z]{3})[/\s]([A-Z]{3})\s*\n'
        
        matches_4 = list(re.finditer(
            rf'{pattern_4}(.*?)(?=^\d+\.\s+[A-Z]{{3}}[/\s]|^[A-Z]+\s+[A-Z]+:|$)',
            text,
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        ))
        
        # ========================================================================
        # PATTERN SET 5: "Trade Recommendation X:" format (Gemini Final - ACTUAL FORMAT)
        # Format: "### **Trade Recommendation 1: Short GBP/USD (High Conviction)**"
        # ========================================================================
        pattern_5 = r'###\s+\*\*Trade\s+Recommendation\s+\d+:\s+(?:Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})'
        
        matches_5 = list(re.finditer(
            rf'{pattern_5}(.*?)(?=\n###\s+\*\*Trade\s+Recommendation|\n---\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 6: "#### **Trade X:" format (Gemini Final - ACTUAL OUTPUT FORMAT)
        # Format: "#### **Trade 1: High Conviction - Sell USD/JPY**"
        # OR: "#### **Trade 1: Confirmed Setup - Sell GBP/JPY**"
        # ========================================================================
        pattern_6 = r'####\s+\*\*Trade\s+\d+:\s+[^-]+-\s+(?:Sell|Buy|Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})\*\*'
        
        matches_6 = list(re.finditer(
            rf'{pattern_6}(.*?)(?=\n####\s+\*\*Trade\s+\d+|\n###\s+\*\*Trade|\n---\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 7: "Currency Pair:" with markdown bullets (Gemini Final format)
        # Format: "*   **Currency Pair:** USD/JPY" followed by price info
        # ========================================================================
        pattern_7 = r'\*\s+\*\*Currency\s+Pair:\*\*\s+([A-Z]{3})[/\s]([A-Z]{3})'
        
        matches_7 = list(re.finditer(
            rf'{pattern_7}(.*?)(?=\n\*\s+\*\*Currency\s+Pair:\*\*|\n####\s+\*\*Trade|\n###\s+\*\*Trade|\n---\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # Combine all matches
        all_matches = matches_1 + matches_2 + matches_3 + matches_4 + matches_5 + matches_6 + matches_7
        
        logger.debug(f"Pattern matches for {llm_source}: P1={len(matches_1)}, P2={len(matches_2)}, P3={len(matches_3)}, P4={len(matches_4)}, P5={len(matches_5)}, P6={len(matches_6)}, P7={len(matches_7)}, Total={len(all_matches)}")
        
        if len(all_matches) == 0:
            # Log a snippet of the text to help diagnose why no patterns matched
            text_preview = text[:500] if len(text) > 500 else text
            logger.warning(f"No pattern matches found for {llm_source}. Text preview (first 500 chars): {text_preview}")
        
        for match in all_matches:
            try:
                base = match.group(1).upper()
                quote = match.group(2).upper()
                pair = f"{base}{quote}"
                section_text = match.group(3) if len(match.groups()) >= 3 else ''
                
                logger.debug(f"Processing match: {pair}, section_text length: {len(section_text)}")
                
                # Get full match text (includes header) for direction extraction
                full_match_text = match.group(0) + section_text
                
                # Use same enhanced extraction as recommendation_parser.py
                entry = self._extract_price(section_text, [
                    'Entry Price', 'Entry', 'Entry Range', 'Entry Price (Buy Limit)',
                    'Entry Price (Sell Limit)'
                ])
                
                stop_loss = self._extract_price(section_text, [
                    'Stop Loss', 'SL', 'Stop', 'Stop-Loss'
                ])
                
                logger.debug(f"Extracted for {pair}: entry={entry}, stop_loss={stop_loss}")
                
                tp1 = self._extract_price(section_text, [
                    'Take Profit Target 1', 'Target Price 1', 'TP1',
                    'Exit/Target Price', 'Target Price', 'Exit Price',
                    'Take Profit Target', 'Take Profit'
                ])
                
                tp2 = self._extract_price(section_text, [
                    'Take Profit Target 2', 'Target Price 2', 'TP2'
                ])
                
                # Extract direction - pass full match text to include header
                direction = self._extract_direction(full_match_text, entry is not None)
                
                # Extract timeframe
                timeframe = self._extract_timeframe(section_text)
                
                # Extract position sizing
                position_size = self._extract_position_size(section_text)
                
                # Require entry (stop_loss is optional, matching recommendation_parser.py behavior)
                if entry:
                    recommendations.append({
                        'timestamp': timestamp,
                        'date_generated': timestamp.split('T')[0],
                        'llm_source': llm_source.lower(),
                        'pair': pair,
                        'direction': direction,
                        'entry_price': entry,
                        'stop_loss': stop_loss,  # Optional
                        'take_profit_1': tp1,
                        'take_profit_2': tp2,
                        'position_size_pct': position_size,
                        'confidence': self._extract_confidence(section_text),
                        'rationale': self._extract_rationale(section_text),
                        'timeframe': timeframe,
                        'source_file': filename
                    })
                    logger.info(f"✅ Added recommendation: {pair} {direction} @ {entry} SL:{stop_loss} TP1:{tp1} TP2:{tp2}")
                else:
                    logger.warning(f"⚠️ Skipped {pair}: missing entry ({entry})")
                    # Log section text snippet to help diagnose extraction failures
                    section_preview = section_text[:200] if len(section_text) > 200 else section_text
                    logger.debug(f"Section text preview for {pair}: {section_preview}")
            
            except Exception as e:
                logger.error(f"Exception processing match for {llm_source}: {e}", exc_info=True)
                continue
        
        return recommendations
    
    def _extract_direction(self, text: str, has_entry: bool) -> str:
        """Extract direction - enhanced for headers like 'Trade Recommendation 1: Short GBP/USD'"""
        # Check header for direction (highest priority) - handle "Trade Recommendation X:" format
        if re.search(r'(?:Trade\s+(?:Recommendation\s+)?\d+:|###\s+\*\*Trade\s+Recommendation\s+\d+:|###\s+\*\*Trade\s+\d+:|\\*\\*)\s*Short\s+', text, re.IGNORECASE):
            return 'SHORT'
        elif re.search(r'(?:Trade\s+(?:Recommendation\s+)?\d+:|###\s+\*\*Trade\s+Recommendation\s+\d+:|###\s+\*\*Trade\s+\d+:|\\*\\*)\s*Long\s+', text, re.IGNORECASE):
            return 'LONG'
        
        # Check entry format
        if re.search(r'Entry\s+Price\s*\(\s*(?:sell|short)\s+limit\s*\)', text, re.IGNORECASE):
            return 'SHORT'
        elif re.search(r'Entry\s+Price\s*\(\s*(?:buy|long)\s+limit\s*\)', text, re.IGNORECASE):
            return 'LONG'
        
        # Check keywords
        if re.search(r'\b(sell|short)\b', text, re.IGNORECASE):
            return 'SHORT'
        elif re.search(r'\b(buy|long)\b', text, re.IGNORECASE):
            return 'LONG'
        
        return 'LONG' if has_entry else 'SHORT'
    
    def _extract_timeframe(self, text: str) -> str:
        """Extract timeframe - enhanced patterns"""
        patterns = [
            r'(?:\*\s+)?\*\*Trade\s+Classification:\*\*\s+(intraday|swing)',
            r'(?:\*\s+)?\*\*TIMEFRAME\s+CLASSIFICATION\*\*:\s+(intraday|swing)',
            r'timeframe[-\s]?classification:\s+(intraday|swing)',
            r'trade[-\s]?classification:\s+(intraday|swing)',
            r'CLASSIFICATION:\s+(SWING\s+TRADE|INTRADAY\s+TRADE)',
            r'(intraday|swing)\s+trade',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tf = match.group(1).upper()
                if 'SWING' in tf:
                    return 'SWING'
                elif 'INTRADAY' in tf:
                    return 'INTRADAY'
        
        # Context clues
        text_lower = text.lower()
        if 'swing' in text_lower or ('2-5 days' in text_lower):
            return 'SWING'
        elif 'intraday' in text_lower or 'same day' in text_lower:
            return 'INTRADAY'
        
        return 'INTRADAY'
    
    def _extract_price(self, text: str, keywords: List[str]) -> Optional[float]:
        """Enhanced price extraction - handles all LLM formats"""
        for keyword in keywords:
            patterns = [
                # Gemini: "*   **Entry Price (Buy Limit):** **193.80**"
                rf'(?:\*\s+)?\*\*{re.escape(keyword)}\s*\([^)]+\):\*\*\s+\*\*([0-9]+\.?[0-9]*)\*\*',
                # Gemini: "*   **Entry Price (Buy Limit):** 193.80"
                rf'(?:\*\s+)?\*\*{re.escape(keyword)}\s*\([^)]+\):\*\*\s+([0-9]+\.?[0-9]*)',
                # Standard: "**Entry Price:** **1.3450**"
                rf'(?:\*\s+)?\*\*{re.escape(keyword)}:\*\*\s+\*\*([0-9]+\.?[0-9]*)\*\*',
                # Standard: "**Entry Price:** 1.3450"
                rf'(?:\*\s+)?\*\*{re.escape(keyword)}:\*\*\s+([0-9]+\.?[0-9]*)',
                # Claude: "- Entry: 1.3400"
                rf'-\s+{re.escape(keyword)}:\s+([0-9]+\.?[0-9]*)',
                # ChatGPT: "- **Entry Price**: 1.3430"
                rf'-\s+\*\*{re.escape(keyword)}\*\*:\s+([0-9]+\.?[0-9]*)',
                # No markdown: "Entry Price: 1.3400"
                rf'{re.escape(keyword)}:\s+([0-9]+\.?[0-9]*)',
                # Approximate: "Entry: Approximately 1.3440"
                rf'{re.escape(keyword)}:\s+Approximately\s+([0-9]+\.?[0-9]*)',
                # Short form: "Entry: 1.3400"
                rf'{re.escape(keyword)}:\s+([0-9]+\.?[0-9]*)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        price = float(match.group(1))
                        if 0.5 <= price <= 1000:
                            return price
                    except:
                        pass
        
        return None
    
    def _extract_position_size(self, text: str) -> float:
        """Extract position size percentage"""
        pattern = r'([0-9.]+)%?\s*of\s+(?:trading\s+)?capital'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        return 2.0  # Default
    
    def _extract_confidence(self, text: str) -> Optional[str]:
        """Extract confidence level"""
        keywords = ['high confidence', 'medium confidence', 'low confidence', 'strong conviction']
        for keyword in keywords:
            if keyword.lower() in text.lower():
                return keyword.title()
        return None
    
    def _extract_rationale(self, text: str) -> str:
        """Extract rationale/reasoning"""
        # Look for "Rationale:" section
        pattern = r'Rationale:(.+?)(?:\n\n|Risk Management|Position Sizing|$)'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()[:500]  # Limit to 500 chars
        return ""
    
    def _parse_freeform_recommendations(self, content: str, timestamp: str, filename: str) -> List[Dict]:
        """Parse recommendations from free-form text (no structured sections)"""
        recommendations = []
        
        # Look for currency pairs with directions in the text
        # Pattern: EUR/USD, GBP/JPY, etc. followed by LONG/SHORT/BUY/SELL
        pair_direction_patterns = [
            r'([A-Z]{3}/[A-Z]{3})\s+(?:is\s+)?(LONG|SHORT|BUY|SELL)',
            r'(LONG|SHORT|BUY|SELL)\s+(?:position\s+on\s+)?([A-Z]{3}/[A-Z]{3})',
            r'([A-Z]{3}/[A-Z]{3})\s+.*?(?:recommend|suggest|trade|position).*?(LONG|SHORT|BUY|SELL)',
            r'(?:Trade|Position|Recommendation):\s*(?:.*?)?([A-Z]{3}/[A-Z]{3})\s+(LONG|SHORT|BUY|SELL)',
            r'(LONG|SHORT|BUY|SELL)\s+([A-Z]{3}/[A-Z]{3})',  # Simple: LONG EUR/USD
        ]
        
        for pattern in pair_direction_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                try:
                    # Extract pair and direction
                    if '/' in match.group(1):
                        pair = match.group(1).replace('/', '').upper()
                        direction = match.group(2).upper()
                    else:
                        direction = match.group(1).upper()
                        pair = match.group(2).replace('/', '').upper()
                    
                    # Normalize direction
                    if direction in ['BUY', 'LONG']:
                        direction = 'LONG'
                    elif direction in ['SELL', 'SHORT']:
                        direction = 'SHORT'
                    else:
                        continue
                    
                    # Get context around the match
                    start_pos = max(0, match.start() - 500)
                    end_pos = min(len(content), match.end() + 1000)
                    context = content[start_pos:end_pos]
                    
                    # Extract prices from context
                    entry = self._extract_price(context, ['Entry Price', 'Entry', 'Entry Range', 'Price', 'Current Price', 'At'])
                    stop_loss = self._extract_price(context, ['Stop Loss', 'SL', 'Stop', 'Stop-Loss'])
                    tp1 = self._extract_price(context, ['Take Profit Target 1', 'Target Price 1', 'TP1', 'Exit/Target Price', 'Target 1', 'TP 1'])
                    tp2 = self._extract_price(context, ['Take Profit Target 2', 'Target Price 2', 'TP2', 'Target 2', 'TP 2'])
                    
                    # If we have at least entry and stop loss, create recommendation
                    if entry and stop_loss:
                        # Try to determine LLM source from context
                        llm_source = 'synthesis'  # Default
                        context_upper = context.upper()
                        if 'CHATGPT' in context_upper or 'OPENAI' in context_upper or 'GPT' in context_upper:
                            llm_source = 'chatgpt'
                        elif 'GEMINI' in context_upper or 'GOOGLE' in context_upper:
                            llm_source = 'gemini'
                        elif 'CLAUDE' in context_upper or 'ANTHROPIC' in context_upper:
                            llm_source = 'claude'
                        elif 'DEEPSEEK' in context_upper:
                            llm_source = 'deepseek'
                        
                        # Extract timeframe classification
                        timeframe = 'INTRADAY'  # Default
                        if 'SWING' in context_upper or ('HOLD' in context_upper and ('DAYS' in context_upper or 'WEEKS' in context_upper)):
                            timeframe = 'SWING'
                        elif 'INTRADAY' in context_upper or 'SAME DAY' in context_upper or 'CLOSE BY 5 PM' in context_upper:
                            timeframe = 'INTRADAY'
                        
                        recommendations.append({
                            'timestamp': timestamp,
                            'date_generated': timestamp.split('T')[0],
                            'llm_source': llm_source,
                            'pair': pair,
                            'direction': direction,
                            'entry_price': entry,
                            'stop_loss': stop_loss,
                            'take_profit_1': tp1,
                            'take_profit_2': tp2,
                            'position_size_pct': self._extract_position_size(context),
                            'confidence': self._extract_confidence(context),
                            'rationale': self._extract_rationale(context),
                            'timeframe': timeframe,
                            'source_file': filename
                        })
                
                except Exception as e:
                    continue  # Skip invalid matches
        
        return recommendations


class OutcomeEvaluator:
    """Evaluates recommendation outcomes using market data"""
    
    def __init__(self):
        self.cache = {}
        # Initialize OANDA API for historical data
        self.oanda_client = None
        try:
            from oandapyV20 import API
            from oandapyV20.endpoints import instruments
            
            access_token = os.getenv('OANDA_ACCESS_TOKEN')
            environment = os.getenv('OANDA_ENV', 'practice')
            
            if access_token:
                self.oanda_client = API(access_token=access_token, environment=environment)
                self.instruments_endpoint = instruments
                logger.info("✅ OutcomeEvaluator: OANDA API initialized for historical data")
            else:
                logger.warning("⚠️ OutcomeEvaluator: OANDA credentials not available, will use yfinance fallback")
        except ImportError:
            logger.warning("⚠️ OutcomeEvaluator: oandapyV20 not available, will use yfinance fallback")
        except Exception as e:
            logger.warning(f"⚠️ OutcomeEvaluator: Failed to initialize OANDA API: {e}, will use yfinance fallback")
    
    def evaluate_recommendation(self, rec: pd.Series) -> Optional[Dict]:
        """Evaluate a single recommendation"""
        rec_id = rec.get('id', 'unknown') if hasattr(rec, 'get') else 'unknown'
        try:
            logger.debug(f"[OutcomeEvaluator] Evaluating recommendation ID={rec_id}")

            # Convert pair format: EURJPY -> EUR/JPY or EURUSD -> EUR/USD
            # Ensure we get scalar values from Series, not Series objects
            pair_value = rec['pair']
            if isinstance(pair_value, pd.Series):
                pair_value = pair_value.iloc[0] if len(pair_value) > 0 else None
            # Keep original pair format for OANDA (will be converted in _get_price_data)
            pair_formatted = pair_value
            logger.debug(f"[OutcomeEvaluator] Pair: {pair_formatted}")

            # Get price data from entry time to now
            timestamp_value = rec['timestamp']
            if isinstance(timestamp_value, pd.Series):
                timestamp_value = timestamp_value.iloc[0] if len(timestamp_value) > 0 else None

            # Parse timestamp, handling nanoseconds (9 digits) which fromisoformat doesn't support
            # Python's fromisoformat only supports microseconds (6 digits)
            # Simple and reliable approach: split on decimal, truncate, preserve timezone
            import re
            timestamp_clean = str(timestamp_value)

            # Fix nanoseconds: find decimal point, truncate to 6 digits, preserve timezone
            if '.' in timestamp_clean:
                parts = timestamp_clean.split('.', 1)
                decimal_and_tz = parts[1]

                # Find where timezone starts (+00:00, -05:00, or Z)
                tz_match = re.search(r'([+\-]\d{2}:\d{2}|Z|$)', decimal_and_tz)
                if tz_match:
                    tz_start = tz_match.start()
                    decimal_part = decimal_and_tz[:tz_start]
                    tz_part = decimal_and_tz[tz_start:]
                else:
                    decimal_part = decimal_and_tz
                    tz_part = ''

                # Truncate to 6 digits max (microseconds)
                if len(decimal_part) > 6:
                    decimal_part = decimal_part[:6]

                timestamp_clean = f"{parts[0]}.{decimal_part}{tz_part}"

            try:
                start_date = datetime.fromisoformat(timestamp_clean)
                logger.debug(f"[OutcomeEvaluator] Parsed timestamp: {start_date}")
            except ValueError as e:
                logger.warning(f"[OutcomeEvaluator] fromisoformat failed for {timestamp_value} (cleaned: {timestamp_clean}): {e}")
                return None
            # Ensure both datetimes are timezone-aware (or both naive) for subtraction
            if start_date.tzinfo is None:
                # start_date is naive, use naive datetime.utcnow()
                end_date = datetime.utcnow()
            else:
                # start_date is aware, convert to UTC-aware for comparison
                from datetime import timezone
                end_date = datetime.now(timezone.utc)
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)

            logger.debug(f"[OutcomeEvaluator] Fetching price data from {start_date} to {end_date}")
            price_data = self._get_price_data(pair_formatted, start_date, end_date)

            if price_data is None or len(price_data) < 2:
                logger.warning(f"[OutcomeEvaluator] Failed to get price data for {pair_formatted}: {len(price_data) if price_data is not None else 'None'} candles")
                return None

            logger.debug(f"[OutcomeEvaluator] Got {len(price_data)} candles from {price_data.index[0]} to {price_data.index[-1]}")

            # Evaluate outcome - ensure all values are scalars, not Series
            def get_scalar(value):
                if isinstance(value, pd.Series):
                    if len(value) > 0:
                        val = value.iloc[0]
                        return val if pd.notna(val) else None
                    return None
                return value if pd.notna(value) else None

            entry = get_scalar(rec['entry_price'])
            stop_loss = get_scalar(rec['stop_loss'])
            tp1 = get_scalar(rec['take_profit_1'])
            tp2 = get_scalar(rec['take_profit_2'])
            direction_value = get_scalar(rec['direction'])
            direction = str(direction_value).upper() if direction_value is not None else 'LONG'

            logger.debug(f"[OutcomeEvaluator] Entry={entry}, SL={stop_loss}, TP1={tp1}, TP2={tp2}, Dir={direction}")

            # Validate required fields
            if entry is None or pd.isna(entry):
                logger.warning(f"[OutcomeEvaluator] Cannot evaluate ID={rec_id}: entry_price is None/NaN")
                return None
            if stop_loss is None or pd.isna(stop_loss):
                logger.warning(f"[OutcomeEvaluator] Cannot evaluate ID={rec_id}: stop_loss is None/NaN")
                return None

            # Convert to float to ensure numeric type
            try:
                entry = float(entry)
                stop_loss = float(stop_loss)
                tp1 = float(tp1) if tp1 is not None and not pd.isna(tp1) else None
                tp2 = float(tp2) if tp2 is not None and not pd.isna(tp2) else None
            except (ValueError, TypeError) as e:
                logger.warning(f"[OutcomeEvaluator] Cannot evaluate ID={rec_id}: invalid numeric values - {e}")
                return None

            logger.debug(f"[OutcomeEvaluator] Checking outcome for {pair_formatted} {direction}...")
            outcome = self._check_outcome(
                price_data, entry, stop_loss, tp1, tp2, direction
            )

            if outcome:
                logger.debug(f"[OutcomeEvaluator] ID={rec_id}: outcome={outcome['outcome']}, pnl={outcome.get('pnl_pips', 0):.1f}pips")
            else:
                logger.warning(f"[OutcomeEvaluator] ID={rec_id}: _check_outcome returned None")

            return outcome

        except Exception as e:
            logger.error(f"[OutcomeEvaluator] Error evaluating recommendation {rec_id}: {type(e).__name__}: {e}", exc_info=True)
            return None
    
    def _format_pair_for_yfinance(self, pair: str) -> str:
        """Convert pair format for yfinance (strip whitespace; avoid 'possibly delisted' from bad symbols)."""
        pair = str(pair).strip() if pair else ''
        if not pair:
            return ''
        # EURJPY -> EURJPY=X, EUR/USD -> EURUSD=X
        if pair.endswith('=X'):
            return pair
        clean_pair = pair.replace('/', '').replace('-', '').replace(' ', '')
        return f"{clean_pair}=X" if clean_pair else ''
    
    def _get_price_data(self, pair: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """Get historical price data using OANDA API (primary) or yfinance (fallback)"""
        # Handle timezone-aware datetimes for date() method
        start_date = start.date() if start.tzinfo is None else start.replace(tzinfo=None).date()
        end_date = end.date() if end.tzinfo is None else end.replace(tzinfo=None).date()
        cache_key = f"{pair}_{start_date}_{end_date}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Try OANDA API first (more reliable for forex)
        if self.oanda_client:
            try:
                # Convert pair format: EUR/USD -> EUR_USD for OANDA, or AUDUSD -> AUD_USD
                # Handle both formats: with/without slash, and remove =X if present
                clean_pair = pair.replace('=X', '').replace('/', '_').replace('-', '_')
                # If no underscore, assume it's like AUDUSD and needs to be split (but OANDA uses AUD_USD format)
                # Actually, OANDA expects pairs like EUR_USD, AUD_USD, etc.
                # If we have AUDUSD, we need to detect where to split (3+3 chars)
                if '_' not in clean_pair and len(clean_pair) == 6:
                    # Assume first 3 chars are base, last 3 are quote
                    oanda_pair = f"{clean_pair[:3]}_{clean_pair[3:]}"
                else:
                    oanda_pair = clean_pair
                
                # Convert datetime to RFC3339 format for OANDA
                # OANDA requires format: 2026-01-26T16:00:00.000000Z (microseconds, not nanoseconds)
                def format_for_oanda(dt):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    
                    # Convert to UTC if not already
                    if dt.tzinfo != timezone.utc:
                        dt = dt.astimezone(timezone.utc)
                    
                    # Format: YYYY-MM-DDTHH:MM:SS.ffffffZ
                    # Use strftime for precise control, then add microseconds
                    # This ensures we NEVER produce nanoseconds
                    base_str = dt.strftime('%Y-%m-%dT%H:%M:%S')
                    # Get microseconds (0-999999, always 6 digits max)
                    microseconds = dt.microsecond
                    if microseconds > 0:
                        # Format microseconds to exactly 6 digits with leading zeros
                        micro_str = f"{microseconds:06d}"
                        # Remove trailing zeros to minimize string length (OANDA accepts variable precision)
                        micro_str = micro_str.rstrip('0')
                        if micro_str:
                            return f"{base_str}.{micro_str}Z"
                    return f"{base_str}Z"
                
                start_rfc3339 = format_for_oanda(start)
                end_rfc3339 = format_for_oanda(end)
                
                logger.debug(f"OANDA request: {oanda_pair} from {start_rfc3339} to {end_rfc3339}")
                
                params = {
                    "from": start_rfc3339,
                    "to": end_rfc3339,
                    "granularity": "H1"  # 1-hour candles
                }
                
                logger.debug(f"Fetching OANDA candles for {oanda_pair} from {start_rfc3339} to {end_rfc3339}")
                req = self.instruments_endpoint.InstrumentsCandles(instrument=oanda_pair, params=params)
                response = self.oanda_client.request(req)
                
                if 'candles' in response and len(response['candles']) > 0:
                    # Convert OANDA candles to DataFrame
                    data_list = []
                    timestamps = []
                    for candle in response['candles']:
                        if candle.get('complete', False):  # Only use complete candles
                            data_list.append({
                                'Open': float(candle['mid']['o']),
                                'High': float(candle['mid']['h']),
                                'Low': float(candle['mid']['l']),
                                'Close': float(candle['mid']['c']),
                                'Volume': int(candle['volume'])
                            })
                            timestamps.append(datetime.fromisoformat(_normalize_iso_timestamp(candle['time'])))
                    
                    if len(data_list) > 0:
                        # Create DataFrame with datetime index
                        df = pd.DataFrame(data_list, index=timestamps)
                        df.index.name = 'Datetime'
                        
                        if len(df) > 0:
                            self.cache[cache_key] = df
                            logger.info(f"✅ Fetched {len(df)} candles from OANDA for {pair} ({oanda_pair})")
                            return df
                    else:
                        logger.warning(f"⚠️ OANDA returned {len(response['candles'])} candles but none were complete for {pair}")
                else:
                    logger.warning(f"⚠️ OANDA returned no candles for {pair} ({oanda_pair})")
                
            except Exception as e:
                logger.warning(f"⚠️ OANDA API failed for {pair}: {e}, trying yfinance fallback")
                import traceback
                logger.debug(traceback.format_exc())
        
        # Fallback to yfinance (multiple strategies to avoid "possibly delisted; no price data found")
        start_naive = start if start.tzinfo is None else start.replace(tzinfo=None)
        end_naive = end if end.tzinfo is None else end.replace(tzinfo=None)
        yf_pair = self._format_pair_for_yfinance(pair)
        if not yf_pair:
            logger.warning(f"Invalid pair for yfinance: {pair!r}")
            return None

        def _yf_download(start_str: Optional[str], end_str: Optional[str], interval: str, period: Optional[str] = None) -> Optional[pd.DataFrame]:
            try:
                kwargs = {"progress": False, "interval": interval, "threads": False}
                if period:
                    kwargs["period"] = period
                else:
                    kwargs["start"] = start_str
                    kwargs["end"] = end_str
                df = yf.download(yf_pair, **kwargs)
                if df is not None and len(df) > 0:
                    # Single ticker can return MultiIndex columns; flatten if needed
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    return df
            except Exception as e:
                logger.debug(f"yfinance attempt failed ({interval} period={period}): {e}")
            return None

        start_str = start_naive.strftime('%Y-%m-%d')
        end_str = end_naive.strftime('%Y-%m-%d')

        # 1) Primary: start/end with 1h (same as OANDA granularity)
        data = _yf_download(start_str, end_str, '1h', period=None)
        if data is not None:
            self.cache[cache_key] = data
            logger.debug(f"✅ Fetched {len(data)} candles from yfinance for {pair} (1h)")
            return data

        # 2) Period-based 1h (Yahoo sometimes returns data for period when start/end fails)
        data = _yf_download(None, None, '1h', period="5d")
        if data is not None:
            # Trim to requested range
            try:
                data = data.loc[(data.index >= pd.Timestamp(start_naive)) & (data.index <= pd.Timestamp(end_naive))]
            except Exception:
                pass
            if len(data) > 0:
                self.cache[cache_key] = data
                logger.debug(f"✅ Fetched {len(data)} candles from yfinance for {pair} (1h period=5d)")
                return data

        # 3) Daily data: still usable for outcome (hit SL/TP within range)
        data = _yf_download(start_str, end_str, '1d', period=None)
        if data is not None:
            self.cache[cache_key] = data
            logger.debug(f"✅ Fetched {len(data)} candles from yfinance for {pair} (1d fallback)")
            return data

        logger.warning(f"All yfinance attempts failed for {pair} ({yf_pair})")
        return None
    
    def _check_outcome(
        self,
        price_data: pd.DataFrame,
        entry: float,
        stop_loss: float,
        tp1: Optional[float],
        tp2: Optional[float],
        direction: str
    ) -> Dict:
        """Check if TP or SL was hit"""
        logger.debug(f"[_check_outcome] Checking {direction}: Entry={entry}, SL={stop_loss}, TP1={tp1}, TP2={tp2}")

        max_favorable = 0
        max_adverse = 0

        for i, (timestamp, row) in enumerate(price_data.iterrows()):
            # Ensure we get scalar values, not Series
            high_val = row['High']
            low_val = row['Low']
            close_val = row['Close']

            # Convert to scalar if Series (shouldn't happen but defensive)
            high = float(high_val.iloc[0]) if isinstance(high_val, pd.Series) else float(high_val)
            low = float(low_val.iloc[0]) if isinstance(low_val, pd.Series) else float(low_val)
            close = float(close_val.iloc[0]) if isinstance(close_val, pd.Series) else float(close_val)

            if direction == 'LONG':
                # Track excursions
                favorable = high - entry
                adverse = low - entry
                max_favorable = max(max_favorable, favorable * 10000)  # pips
                max_adverse = min(max_adverse, adverse * 10000)
                
                # Check stop loss
                if low <= stop_loss:
                    pnl_pips = (stop_loss - entry) * 10000
                    logger.debug(f"[_check_outcome] LONG SL hit at {stop_loss}, pnl={pnl_pips:.1f}pips in {i+1} bars")
                    return {
                        'outcome': 'LOSS_SL',
                        'exit_price': stop_loss,
                        'pnl_pips': pnl_pips,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable,
                        'max_adverse_pips': max_adverse,
                        'timestamp': timestamp.isoformat()
                    }

                # Check TP2 first (better profit)
                if tp2 and high >= tp2:
                    pnl_pips = (tp2 - entry) * 10000
                    logger.debug(f"[_check_outcome] LONG TP2 hit at {tp2}, pnl={pnl_pips:.1f}pips in {i+1} bars")
                    return {
                        'outcome': 'WIN_TP2',
                        'exit_price': tp2,
                        'pnl_pips': pnl_pips,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable,
                        'max_adverse_pips': max_adverse,
                        'timestamp': timestamp.isoformat()
                    }

                # Check TP1
                if tp1 and high >= tp1:
                    pnl_pips = (tp1 - entry) * 10000
                    logger.debug(f"[_check_outcome] LONG TP1 hit at {tp1}, pnl={pnl_pips:.1f}pips in {i+1} bars")
                    return {
                        'outcome': 'WIN_TP1',
                        'exit_price': tp1,
                        'pnl_pips': pnl_pips,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable,
                        'max_adverse_pips': max_adverse,
                        'timestamp': timestamp.isoformat()
                    }
            
            else:  # SHORT
                # Track excursions
                favorable = entry - low
                adverse = entry - high
                max_favorable = max(max_favorable, favorable * 10000)
                max_adverse = min(max_adverse, adverse * 10000)

                # Check stop loss
                if high >= stop_loss:
                    pnl_pips = (entry - stop_loss) * 10000
                    logger.debug(f"[_check_outcome] SHORT SL hit at {stop_loss}, pnl={pnl_pips:.1f}pips in {i+1} bars")
                    return {
                        'outcome': 'LOSS_SL',
                        'exit_price': stop_loss,
                        'pnl_pips': pnl_pips,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable,
                        'max_adverse_pips': max_adverse,
                        'timestamp': timestamp.isoformat()
                    }

                # Check TP2 first
                if tp2 and low <= tp2:
                    pnl_pips = (entry - tp2) * 10000
                    logger.debug(f"[_check_outcome] SHORT TP2 hit at {tp2}, pnl={pnl_pips:.1f}pips in {i+1} bars")
                    return {
                        'outcome': 'WIN_TP2',
                        'exit_price': tp2,
                        'pnl_pips': pnl_pips,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable,
                        'max_adverse_pips': max_adverse,
                        'timestamp': timestamp.isoformat()
                    }

                # Check TP1
                if tp1 and low <= tp1:
                    pnl_pips = (entry - tp1) * 10000
                    logger.debug(f"[_check_outcome] SHORT TP1 hit at {tp1}, pnl={pnl_pips:.1f}pips in {i+1} bars")
                    return {
                        'outcome': 'WIN_TP1',
                        'exit_price': tp1,
                        'pnl_pips': pnl_pips,
                        'bars_held': i + 1,
                        'max_favorable_pips': max_favorable,
                        'max_adverse_pips': max_adverse,
                        'timestamp': timestamp.isoformat()
                    }
        
        # Timeout - check if trade was never triggered (MISSED)
        # If price never got close to entry, this is a MISSED trade
        # Check if price ever got within reasonable distance of entry (within 2x ATR equivalent)
        entry_zone_hit = False
        reasonable_distance = abs(entry * 0.002)  # ~20 pips for most pairs
        
        for _, row in price_data.iterrows():
            high = row['High']
            low = row['Low']
            if direction == 'LONG':
                # Check if price got close to entry from below
                if low <= (entry + reasonable_distance):
                    entry_zone_hit = True
                    break
            else:  # SHORT
                # Check if price got close to entry from above
                if high >= (entry - reasonable_distance):
                    entry_zone_hit = True
                    break
        
        # If price never got close to entry, mark as MISSED
        if not entry_zone_hit:
            logger.debug(f"[_check_outcome] Entry zone never hit - MISSED trade")
            return {
                'outcome': 'MISSED',
                'exit_price': None,
                'pnl_pips': 0,
                'bars_held': len(price_data),
                'max_favorable_pips': max_favorable,
                'max_adverse_pips': max_adverse,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Otherwise, check current P&L (trade was triggered but didn't hit TP/SL)
        current_price = price_data.iloc[-1]['Close']
        if direction == 'LONG':
            pnl_pips = (current_price - entry) * 10000
        else:
            pnl_pips = (entry - current_price) * 10000

        outcome = 'WIN_TP1' if pnl_pips > 0 else 'LOSS_SL' if pnl_pips < -10 else 'NEUTRAL'

        logger.debug(f"[_check_outcome] Open trade: {outcome} at {current_price}, pnl={pnl_pips:.1f}pips, {len(price_data)} bars")

        return {
            'outcome': outcome,
            'exit_price': current_price,
            'pnl_pips': pnl_pips,
            'bars_held': len(price_data),
            'max_favorable_pips': max_favorable,
            'max_adverse_pips': max_adverse,
            'timestamp': datetime.utcnow().isoformat()
        }


class LLMLearningEngine:
    """Trains and manages LLM performance models"""
    
    def __init__(self, db: RecommendationDatabase):
        self.db = db
    
    def calculate_llm_weights(self) -> Dict[str, float]:
        """Calculate performance weights for each LLM"""
        weights = {}
        
        llm_sources = ['chatgpt', 'gemini', 'claude', 'synthesis', 'deepseek']
        
        logger.info("📊 Calculating LLM weights from database...")
        
        for llm in llm_sources:
            try:
                df = self.db.get_llm_performance(llm_source=llm)
            except Exception as e:
                logger.warning(f"⚠️ Error getting performance data for {llm}: {e}")
                weights[llm] = 0.25
                continue
            
            # Log detailed info for debugging (use INFO level so it shows in logs)
            evaluated_count = len(df)
            try:
                if hasattr(self.db, 'get_all_recommendations'):
                    total_recs = len(self.db.get_all_recommendations(llm_source=llm))
                    logger.info(f"   {llm}: {evaluated_count} evaluated recommendations (total: {total_recs})")
                else:
                    logger.info(f"   {llm}: {evaluated_count} evaluated recommendations")
            except Exception as e:
                logger.info(f"   {llm}: {evaluated_count} evaluated recommendations (could not get total: {e})")
            
            if len(df) < 5:  # Need minimum samples
                logger.info(f"   {llm}: Only {evaluated_count} evaluated recommendations (need 5+) - using default 0.25")
                weights[llm] = 0.25  # Equal weight
                continue
            
            # Calculate win rate (excluding MISSED trades from denominator for win rate)
            wins = df[df['outcome'].isin(['WIN_TP1', 'WIN_TP2'])]
            evaluated_trades = df[~df['outcome'].isin(['PENDING', 'MISSED'])]
            win_rate = len(wins) / len(evaluated_trades) if len(evaluated_trades) > 0 else 0.5
            
            # Count MISSED trades (Rec 4: Penalize missed trades)
            missed_trades = df[df['outcome'] == 'MISSED']
            missed_count = len(missed_trades)
            total_recommendations = len(df)
            missed_rate = missed_count / total_recommendations if total_recommendations > 0 else 0
            
            # Calculate profit factor
            total_profit = wins['pnl_pips'].sum()
            losses = df[df['outcome'] == 'LOSS_SL']
            total_loss = abs(losses['pnl_pips'].sum())
            
            profit_factor = total_profit / total_loss if total_loss > 0 else 1.0
            
            # Rec 4: Penalize high missed rate
            # If >30% of trades are missed, reduce weight significantly
            # Treat MISSED as 0.5x loss (not as bad as real loss, but worse than silence)
            missed_penalty = 1.0 - (missed_rate * 0.5)  # Max 50% penalty if 100% missed
            
            # Combined score with missed penalty
            accuracy_score = (win_rate * 0.6) + (min(profit_factor / 2, 0.5) * 0.4)
            # Apply missed penalty to reduce weight for LLMs with high missed rates
            accuracy_score = accuracy_score * missed_penalty
            
            weights[llm] = max(accuracy_score, 0.05)  # Minimum 5% weight to avoid zero
        
        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
            logger.info(f"📊 Calculated LLM weights: {weights}")
        else:
            logger.warning("⚠️ All weights sum to zero - using defaults")
            default_weight = 1.0 / len(llm_sources) if llm_sources else 0.25
            weights = {k: default_weight for k in llm_sources}
        
        return weights
    
    def analyze_consensus(self) -> Dict:
        """Analyze performance by consensus level"""
        # Get all recommendations grouped by timestamp
        all_recs = self.db.get_llm_performance()
        
        if len(all_recs) == 0:
            return {}
        
        # Group by timestamp and pair to find consensus
        grouped = all_recs.groupby(['timestamp', 'pair', 'direction'])
        
        consensus_stats = {
            'ALL_AGREE': {'wins': 0, 'total': 0, 'pnl': []},
            '2_AGREE': {'wins': 0, 'total': 0, 'pnl': []},
            'ALL_DISAGREE': {'wins': 0, 'total': 0, 'pnl': []}
        }
        
        for (ts, pair, direction), group in grouped:
            count = len(group)
            
            if count >= 3:  # All 3 LLMs agree
                consensus_type = 'ALL_AGREE'
            elif count == 2:  # 2 agree
                consensus_type = '2_AGREE'
            else:  # Disagree or only 1
                consensus_type = 'ALL_DISAGREE'
            
            # Check outcomes
            wins = group[group['outcome'].isin(['WIN_TP1', 'WIN_TP2'])]
            
            consensus_stats[consensus_type]['total'] += 1
            consensus_stats[consensus_type]['wins'] += len(wins)
            consensus_stats[consensus_type]['pnl'].extend(group['pnl_pips'].tolist())
        
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
            'pair_analysis': {},
            'recommendations': {}
        }
        
        # LLM performance
        for llm in ['chatgpt', 'gemini', 'claude', 'synthesis', 'deepseek']:
            df = self.db.get_llm_performance(llm_source=llm)
            
            if len(df) > 0:
                wins = df[df['outcome'].isin(['WIN_TP1', 'WIN_TP2'])]
                losses = df[df['outcome'] == 'LOSS_SL']
                
                report['llm_performance'][llm] = {
                    'total_recs': len(df),
                    'win_rate': len(wins) / len(df),
                    'avg_pnl': df['pnl_pips'].mean(),
                    'profit_factor': wins['pnl_pips'].sum() / abs(losses['pnl_pips'].sum()) if len(losses) > 0 else 0,
                    'avg_bars_held': df['bars_held'].mean()
                }
        
        # Consensus analysis
        report['consensus_analysis'] = self.analyze_consensus()
        
        # Weights
        report['recommended_weights'] = self.calculate_llm_weights()
        
        return report





