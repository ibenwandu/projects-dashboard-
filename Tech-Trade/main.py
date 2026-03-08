"""
Tech-Trade: Main Entry Point
Technical Correlation Analysis System
"""

import argparse
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import logging

from src.logger import setup_logger
from src.data_fetcher import DukascopyDataFetcher, fetch_using_dukascopy_library
from src.correlation_analyzer import CorrelationAnalyzer
from src.pattern_validator import PatternValidator
from src.data_manager import DataManager

logger = setup_logger()


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def download_data(config: dict):
    """Download historical data for all configured pairs"""
    logger.info("="*80)
    logger.info("DOWNLOADING HISTORICAL DATA")
    logger.info("="*80)
    
    # Get configuration
    pairs = []
    pairs.extend(config.get('currency_pairs', {}).get('major', []))
    pairs.extend(config.get('currency_pairs', {}).get('minor', []))
    pairs.extend(config.get('currency_pairs', {}).get('exotic', []))
    
    timeframes = config.get('timeframes', ['1DAY', '1WEEK'])
    years = config.get('historical_period', {}).get('years', 5)
    
    data_storage = config.get('data_storage', {})
    data_dir = data_storage.get('raw_data_dir', 'data/raw')
    
    # Initialize components
    data_manager = DataManager(
        raw_data_dir=data_dir,
        cache_duration_hours=data_storage.get('cache_duration_hours', 24)
    )
    fetcher = DukascopyDataFetcher(data_dir=data_dir)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    
    logger.info(f"Downloading {len(pairs)} pairs across {len(timeframes)} timeframes")
    logger.info(f"Period: {start_date.date()} to {end_date.date()}")
    logger.info("")
    
    all_data = {}
    
    for timeframe in timeframes:
        logger.info(f"--- {timeframe} Timeframe ---")
        timeframe_data = {}
        
        # Count how many pairs need downloading vs using cache
        cached_count = 0
        download_count = 0
        
        # IMPORTANT: Add initial delay to reset any rate limits from previous attempts
        # If IP was rate-limited from previous failed attempts, we need to wait for it to reset
        import time
        initial_delay = 60  # Wait 60 seconds before first request to reset rate limits
        logger.info(f"⏳ Waiting {initial_delay} seconds before first download to reset any rate limits...")
        logger.info(f"   (Your IP may have been rate-limited from previous attempts)")
        time.sleep(initial_delay)
        logger.info(f"✅ Wait complete, starting downloads...")
        
        for pair in pairs:
            # Check cache first - if valid and covers range, skip download
            cached_df = data_manager.load_raw_data(pair, timeframe)
            if cached_df is not None and data_manager.is_cache_valid(pair, timeframe):
                # Check if cached data covers our date range
                if len(cached_df) > 0:
                    cached_start = cached_df.index.min()
                    cached_end = cached_df.index.max()
                    
                    if cached_start <= start_date and cached_end >= end_date:
                        logger.info(f"⏭️  Using cached data for {pair} ({timeframe}) - {len(cached_df)} records")
                        timeframe_data[pair] = cached_df
                        cached_count += 1
                        continue
            
            # Need to download
            download_count += 1
            logger.info(f"Downloading {pair} ({timeframe})...")
            
            # Skip Dukascopy entirely (blocked by Cloudflare) and use yfinance directly
            # This saves time - Dukascopy would take hours to fail, yfinance takes seconds
            # Add delay between pairs to avoid yfinance rate limiting
            # yfinance is VERY sensitive to rate limiting - need much longer delays
            if download_count > 1:  # Don't delay again for first pair (already waited initially)
                delay_between_pairs = 30  # 30 second delay between pairs (very conservative)
                logger.info(f"⏳ Waiting {delay_between_pairs} seconds before downloading {pair} to avoid rate limits...")
                time.sleep(delay_between_pairs)
            
            df = fetcher.fetch_pair_data(
                pair, 
                timeframe, 
                start_date, 
                end_date, 
                years,
                use_yfinance_fallback=True,
                skip_dukascopy=True  # Skip Dukascopy entirely - use yfinance directly
            )
            
            if df is not None:
                # Ensure no duplicates before saving
                initial_len = len(df)
                df = df[~df.index.duplicated(keep='first')]
                if len(df) < initial_len:
                    logger.info(f"Removed {initial_len - len(df)} duplicates")
                
                timeframe_data[pair] = df
                data_manager.save_raw_data(pair, timeframe, df)
            else:
                logger.warning(f"⚠️  Failed to download {pair}")
        
        all_data[timeframe] = timeframe_data
        logger.info(f"✅ {timeframe}: {cached_count} from cache, {download_count} downloaded, {len(timeframe_data)}/{len(pairs)} total")
        logger.info("")
    
    logger.info("="*80)
    logger.info("✅ DATA DOWNLOAD COMPLETE")
    logger.info("="*80)
    logger.info("")
    
    return all_data


def analyze_correlations(config: dict, data_dict: dict):
    """Analyze correlations between pairs"""
    logger.info("="*80)
    logger.info("ANALYZING CORRELATIONS")
    logger.info("="*80)
    
    # Get configuration
    pattern_detection = config.get('pattern_detection', {})
    correlation_threshold = pattern_detection.get('correlation_threshold', 0.7)
    max_combinations = config.get('analysis', {}).get('max_pairs_to_compare', 50)
    
    # Get daily data (primary analysis)
    daily_data = data_dict.get('1DAY', {})
    
    if not daily_data:
        logger.error("No daily data available for analysis")
        return []
    
    logger.info(f"Analyzing {len(daily_data)} pairs...")
    logger.info("")
    
    # Initialize analyzer
    analyzer = CorrelationAnalyzer(correlation_threshold=correlation_threshold)
    
    # Analyze all pairs
    patterns = analyzer.analyze_all_pairs(
        daily_data,
        max_combinations=max_combinations
    )
    
    logger.info("")
    logger.info("="*80)
    logger.info("✅ CORRELATION ANALYSIS COMPLETE")
    logger.info("="*80)
    logger.info("")
    
    return patterns


def validate_patterns(config: dict, patterns: list, data_dict: dict):
    """Validate pattern consistency"""
    logger.info("="*80)
    logger.info("VALIDATING PATTERNS")
    logger.info("="*80)
    
    pattern_detection = config.get('pattern_detection', {})
    consistency_threshold = pattern_detection.get('consistency_threshold', 0.6)
    
    # Get data for both timeframes
    daily_data = data_dict.get('1DAY', {})
    weekly_data = data_dict.get('1WEEK', {})
    
    if not daily_data:
        logger.error("No daily data available for validation")
        return []
    
    # Initialize validator
    validator = PatternValidator(consistency_threshold=consistency_threshold)
    
    # Validate all patterns
    validated = validator.validate_all_patterns(
        patterns, daily_data, weekly_data
    )
    
    # Filter to only valid patterns
    valid_patterns = [v for v in validated if v['overall_valid']]
    
    logger.info("")
    logger.info(f"✅ Found {len(valid_patterns)}/{len(patterns)} valid, consistent patterns")
    logger.info("="*80)
    logger.info("")
    
    return validated


def generate_report(config: dict, validated_patterns: list):
    """Generate analysis report"""
    logger.info("="*80)
    logger.info("GENERATING REPORT")
    logger.info("="*80)
    
    data_storage = config.get('data_storage', {})
    patterns_dir = data_storage.get('patterns_dir', 'data/patterns')
    
    data_manager = DataManager(patterns_dir=patterns_dir)
    
    # Save all patterns
    all_patterns = [v['pattern'] for v in validated_patterns]
    data_manager.save_patterns(all_patterns)
    
    # Save only valid patterns
    valid_patterns = [
        v['pattern'] for v in validated_patterns 
        if v['overall_valid']
    ]
    data_manager.save_patterns(valid_patterns, 'valid_patterns.json')
    
    # Print summary
    logger.info("")
    logger.info("📊 PATTERN SUMMARY")
    logger.info("-" * 80)
    logger.info(f"Total patterns detected: {len(all_patterns)}")
    logger.info(f"Valid & consistent patterns: {len(valid_patterns)}")
    logger.info("")
    
    if valid_patterns:
        logger.info("🏆 TOP 10 STRONGEST PATTERNS:")
        logger.info("-" * 80)
        
        # Sort by correlation
        sorted_patterns = sorted(
            valid_patterns,
            key=lambda x: abs(x['correlation']),
            reverse=True
        )
        
        for i, pattern in enumerate(sorted_patterns[:10], 1):
            logger.info(
                f"{i:2d}. {pattern['pair1']} <-> {pattern['pair2']}: "
                f"corr={pattern['correlation']:.3f}, "
                f"lag={pattern['lag']}, "
                f"significance={pattern['significance']}"
            )
    
    logger.info("")
    logger.info("="*80)
    logger.info("✅ REPORT GENERATION COMPLETE")
    logger.info("="*80)
    logger.info("")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Tech-Trade: Technical Correlation Analysis')
    parser.add_argument('--download', action='store_true', help='Download historical data')
    parser.add_argument('--analyze', action='store_true', help='Analyze correlations')
    parser.add_argument('--validate', action='store_true', help='Validate patterns')
    parser.add_argument('--report', action='store_true', help='Generate report')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--all', action='store_true', help='Run all steps')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        return
    
    # Run requested operations
    if args.all or args.download:
        data_dict = download_data(config)
    else:
        data_dict = {}
    
    if args.all or args.analyze:
        if not data_dict:
            logger.warning("No data available. Run --download first.")
        else:
            patterns = analyze_correlations(config, data_dict)
            
            if args.all or args.validate:
                validated = validate_patterns(config, patterns, data_dict)
                
                if args.all or args.report:
                    generate_report(config, validated)
    elif args.validate or args.report:
        logger.warning("Run --analyze first to generate patterns.")


if __name__ == '__main__':
    main()

