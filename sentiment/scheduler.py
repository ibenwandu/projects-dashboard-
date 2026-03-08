"""Scheduler for running monitoring checks"""

import schedule
import time
from datetime import datetime
from src.monitor import SentimentMonitor

def run_check():
    """Run a single monitoring check"""
    print(f"\n{'='*60}")
    print(f"Running sentiment check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        monitor = SentimentMonitor()
        monitor.check_watchlist()
        print(f"\n{'='*60}")
        print("Check completed successfully")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n❌ Error in monitoring check: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main scheduler loop"""
    import yaml
    import os
    
    # Load settings
    settings_file = 'config/settings.yaml'
    if not os.path.exists(settings_file):
        settings_file = 'config/settings.yaml.example'
        print(f"⚠️  Using example settings file. Copy to settings.yaml and customize.")
    
    with open(settings_file, 'r') as f:
        settings = yaml.safe_load(f)
    
    interval_minutes = settings.get('check_interval_minutes', 15)
    
    print(f"📊 Sentiment-Aware Forex Monitor")
    print(f"⏰ Scheduled to run every {interval_minutes} minutes")
    print(f"🔄 Starting scheduler... (Press Ctrl+C to stop)\n")
    
    # Schedule the job
    schedule.every(interval_minutes).minutes.do(run_check)
    
    # Run immediately
    run_check()
    
    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\n👋 Scheduler stopped by user")
        print("Goodbye!")

if __name__ == "__main__":
    main()






