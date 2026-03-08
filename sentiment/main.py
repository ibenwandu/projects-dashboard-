#!/usr/bin/env python3
"""
Sentiment-Aware Forex Monitor
Main entry point
"""

import sys
import argparse
from src.monitor import SentimentMonitor

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Sentiment-Aware Forex Monitor')
    parser.add_argument('--once', action='store_true',
                       help='Run check once and exit')
    parser.add_argument('--config', type=str, default='config',
                       help='Config directory (default: config)')
    args = parser.parse_args()
    
    print("="*60)
    print("🚨 Sentiment-Aware Forex Monitor")
    print("="*60)
    print()
    
    try:
        monitor = SentimentMonitor(config_dir=args.config)
        
        if args.once:
            print("🧪 Running single check...\n")
            monitor.check_watchlist()
            print("\n✅ Check complete. Exiting.")
        else:
            # Import scheduler for continuous operation
            from scheduler import main as scheduler_main
            scheduler_main()
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()






