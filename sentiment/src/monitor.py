"""Main monitoring logic"""

import os
import yaml
from typing import List, Dict
from datetime import datetime

from src.data import PriceCollector, NewsCollector
from src.analysis import SentimentAnalyzer, DecisionEngine
from src.alerts import EmailAlerter
from src.database import Database

class SentimentMonitor:
    """Main sentiment monitoring system"""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize sentiment monitor
        
        Args:
            config_dir: Directory containing config files
        """
        self.config_dir = config_dir
        
        # Load settings
        self.settings = self._load_settings()
        
        # Initialize database
        self.db = Database()
        
        # Initialize components
        self.price_collector = PriceCollector()
        self.news_collector = NewsCollector()
        
        llm_provider = self.settings.get('llm_provider', 'openai')
        llm_model = self.settings.get('llm_model', 'gpt-4o-mini')
        self.sentiment_analyzer = SentimentAnalyzer(provider=llm_provider, model=llm_model)
        
        confidence_threshold = self.settings.get('sentiment_confidence_threshold', 0.7)
        momentum_threshold = self.settings.get('momentum_threshold_percent', 0.5)
        self.decision_engine = DecisionEngine(
            confidence_threshold=confidence_threshold,
            momentum_threshold=momentum_threshold
        )
        
        self.email_alerter = EmailAlerter()
    
    def _load_settings(self) -> Dict:
        """Load settings from YAML file"""
        settings_file = os.path.join(self.config_dir, 'settings.yaml')
        if not os.path.exists(settings_file):
            settings_file = os.path.join(self.config_dir, 'settings.yaml.example')
            print(f"⚠️  Using example settings file. Copy to settings.yaml and customize.")
        
        try:
            with open(settings_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {}
    
    def check_watchlist(self):
        """Check all assets in watchlist"""
        watchlist = self.db.get_all_trades(active_only=True)
        
        if not watchlist:
            print("⚠️  Watchlist is empty. Add trades via web UI or database")
            return
        
        print(f"📋 Checking {len(watchlist)} assets in watchlist...\n")
        
        for trade in watchlist:
            asset = trade.get('asset')
            if not asset:
                continue
            
            print(f"\n{'─'*60}")
            print(f"Analyzing: {asset}")
            print(f"Position: {trade.get('trade_direction', 'N/A').upper()}")
            print(f"{'─'*60}")
            
            try:
                self._check_asset(asset, trade)
            except Exception as e:
                print(f"❌ Error checking {asset}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Update last check time
        self.state_manager.update_last_check()
    
    def _check_asset(self, asset: str, trade_info: Dict):
        """Check a single asset"""
        # Step 1: Get price signals
        print("📊 Collecting price data...")
        trade_direction = trade_info.get('trade_direction', 'long')
        price_signals = self.price_collector.get_price_signals(asset, trade_direction)
        
        if not price_signals.get('current_price'):
            print(f"⚠️  Could not get price data for {asset} - skipping")
            return
        
        print(f"   Current Price: {price_signals['current_price']:.5f}")
        if price_signals.get('momentum_1h'):
            print(f"   1-Hour Momentum: {price_signals['momentum_1h']:+.2f}%")
        
        # Step 2: Decision - should we investigate?
        if not self.decision_engine.should_investigate(price_signals):
            print("✓ No significant price signals - skipping sentiment analysis")
            return
        
        print("⚠️  Price signals detected - investigating fundamentals...")
        
        # Step 3: Get news
        print("📰 Collecting news...")
        base_currency, quote_currency = asset.split('/')
        hours = self.settings.get('news_lookback_hours', 24)
        news_items = self.news_collector.get_currency_news(base_currency, quote_currency, hours)
        print(f"   Found {len(news_items)} relevant news items")
        
        if not news_items:
            print("⚠️  No recent news found - skipping sentiment analysis")
            return
        
        # Step 4: Sentiment analysis
        print("🤖 Analyzing sentiment...")
        news_text = self.news_collector.format_news_for_llm(news_items)
        bias_expectation = trade_info.get('bias_expectation', '')
        sentiment_analysis = self.sentiment_analyzer.analyze_sentiment(
            base_currency,
            news_text,
            trade_direction,
            bias_expectation
        )
        
        print(f"   Sentiment: {sentiment_analysis.get('sentiment', 'N/A').upper()}")
        print(f"   Confidence: {sentiment_analysis.get('confidence', 0):.0%}")
        print(f"   Direction: {sentiment_analysis.get('direction', 'N/A')}")
        print(f"   Conflicts with trade: {sentiment_analysis.get('conflicts_with_trade', False)}")
        
        # Step 5: Decision - should we alert?
        if not self.decision_engine.should_alert(price_signals, sentiment_analysis):
            print("✓ No alert trigger - sentiment not conflicting or confidence too low")
            return
        
        # Check if we already alerted recently (avoid spam)
        if self.db.was_alerted_recently(asset, minutes=60):
            print("⚠️  Alert already sent recently for this asset - skipping to avoid spam")
            return
        
        # Step 6: Generate and send alert
        print("🚨 ALERT TRIGGERED - Sending notification...")
        alert_data = self.decision_engine.generate_alert_data(
            asset, trade_info, price_signals, sentiment_analysis, news_items
        )
        
        # Send email alert
        success = self.email_alerter.send_alert(alert_data)
        
        if success:
            # Record alert in database
            self.db.add_alert(
                asset=asset,
                sentiment=sentiment_analysis.get('sentiment'),
                sentiment_direction=sentiment_analysis.get('direction'),
                confidence=sentiment_analysis.get('confidence'),
                alert_data=alert_data
            )
            
            # Update asset state
            self.db.update_asset_state(
                asset=asset,
                last_sentiment=sentiment_analysis.get('sentiment'),
                last_sentiment_direction=sentiment_analysis.get('direction'),
                last_confidence=sentiment_analysis.get('confidence'),
                last_alert_time=datetime.now()
            )
            
            print("✅ Alert sent successfully")
        else:
            print("❌ Failed to send alert")
        
        # Update asset state even if alert wasn't sent (track sentiment)
        self.db.update_asset_state(
            asset=asset,
            last_sentiment=sentiment_analysis.get('sentiment'),
            last_sentiment_direction=sentiment_analysis.get('direction'),
            last_confidence=sentiment_analysis.get('confidence')
        )

