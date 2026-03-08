"""
Data Manager
Handles data storage, caching, and retrieval
"""

import os
import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataManager:
    """Manages data storage and retrieval"""
    
    def __init__(
        self,
        raw_data_dir: str = "data/raw",
        processed_data_dir: str = "data/processed",
        patterns_dir: str = "data/patterns",
        cache_duration_hours: int = 24
    ):
        """
        Initialize data manager
        
        Args:
            raw_data_dir: Directory for raw CSV files
            processed_data_dir: Directory for processed data
            patterns_dir: Directory for pattern results
            cache_duration_hours: How long to cache data before re-downloading
        """
        self.raw_data_dir = Path(raw_data_dir)
        self.processed_data_dir = Path(processed_data_dir)
        self.patterns_dir = Path(patterns_dir)
        
        # Create directories
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_duration = timedelta(hours=cache_duration_hours)
    
    def save_raw_data(self, pair: str, timeframe: str, df: pd.DataFrame):
        """Save raw data to CSV"""
        pair_clean = pair.replace('/', '')
        filename = f"{pair_clean}_{timeframe}.csv"
        filepath = self.raw_data_dir / filename
        
        df.to_csv(filepath)
        logger.debug(f"Saved raw data: {filepath}")
    
    def load_raw_data(self, pair: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Load raw data from CSV"""
        pair_clean = pair.replace('/', '')
        filename = f"{pair_clean}_{timeframe}.csv"
        filepath = self.raw_data_dir / filename
        
        if not filepath.exists():
            return None
        
        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            logger.debug(f"Loaded raw data: {filepath}")
            return df
        except Exception as e:
            logger.warning(f"Error loading {filepath}: {e}")
            return None
    
    def is_cache_valid(self, pair: str, timeframe: str) -> bool:
        """Check if cached data is still valid"""
        pair_clean = pair.replace('/', '')
        filename = f"{pair_clean}_{timeframe}.csv"
        filepath = self.raw_data_dir / filename
        
        if not filepath.exists():
            return False
        
        # Check file modification time
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        age = datetime.now() - mtime
        
        return age < self.cache_duration
    
    def save_patterns(self, patterns: List[Dict], filename: str = None):
        """Save detected patterns to JSON"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"patterns_{timestamp}.json"
        
        filepath = self.patterns_dir / filename
        
        # Convert numpy types to native Python types for JSON
        patterns_serializable = []
        for pattern in patterns:
            pattern_copy = {}
            for key, value in pattern.items():
                if isinstance(value, (np.integer, np.floating)):
                    pattern_copy[key] = float(value)
                elif isinstance(value, np.ndarray):
                    pattern_copy[key] = value.tolist()
                else:
                    pattern_copy[key] = value
            patterns_serializable.append(pattern_copy)
        
        with open(filepath, 'w') as f:
            json.dump(patterns_serializable, f, indent=2, default=str)
        
        logger.info(f"💾 Saved {len(patterns)} patterns to: {filepath}")
    
    def load_patterns(self, filename: str) -> List[Dict]:
        """Load patterns from JSON"""
        filepath = self.patterns_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Pattern file not found: {filepath}")
            return []
        
        try:
            with open(filepath, 'r') as f:
                patterns = json.load(f)
            logger.info(f"📂 Loaded {len(patterns)} patterns from: {filepath}")
            return patterns
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
            return []
    
    def list_available_data(self) -> Dict[str, List[str]]:
        """List all available data files"""
        available = {
            'daily': [],
            'weekly': []
        }
        
        for filepath in self.raw_data_dir.glob("*.csv"):
            filename = filepath.stem
            if '_1DAY' in filename or '_daily' in filename.lower():
                pair = filename.replace('_1DAY', '').replace('_daily', '')
                available['daily'].append(pair)
            elif '_1WEEK' in filename or '_weekly' in filename.lower():
                pair = filename.replace('_1WEEK', '').replace('_weekly', '')
                available['weekly'].append(pair)
        
        return available

