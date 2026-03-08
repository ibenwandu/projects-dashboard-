"""
Forex News-Price Correlation Prediction System
==============================================
This system analyzes 5 years of historical currency data correlated with
high-impact news events to predict future currency movements.

Uses Gemini AI for news analysis instead of Claude.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import json
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings('ignore')

# Gemini imports
try:
    from google import generativeai
    genai = generativeai
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Using environment variables directly.")

from src.logger import setup_logger

logger = setup_logger()


class ForexNewsPricePredictor:
    """
    Main class for analyzing forex price movements correlated with news events
    and predicting future movements.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the predictor with Gemini API for news analysis.
        
        Args:
            api_key: Google API key for Gemini (if None, reads from GOOGLE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            logger.warning("WARNING: No API key provided. News analysis will be limited.")
            logger.warning("Get your API key from: https://aistudio.google.com/")
            self.client_enabled = False
        else:
            if GEMINI_AVAILABLE:
                genai.configure(api_key=self.api_key)
                self.client_enabled = True
                logger.info("✅ Gemini AI enabled for news analysis")
            else:
                logger.warning("google-generativeai package not installed. News analysis will be limited.")
                self.client_enabled = False
        
        self.price_data = {}
        self.news_events = []
        self.features = None
        self.model = None
        self.scaler = StandardScaler()
        
        # Major currency pairs (Yahoo Finance format)
        self.currency_pairs = {
            'EURUSD': 'EURUSD=X',
            'GBPUSD': 'GBPUSD=X',
            'USDJPY': 'USDJPY=X',
            'AUDUSD': 'AUDUSD=X',
            'NZDUSD': 'NZDUSD=X',
            'USDCAD': 'USDCAD=X',
            'USDCHF': 'USDCHF=X'
        }
        
    def fetch_historical_data(self, years=5):
        """
        Fetch historical price data for major currency pairs.
        
        Args:
            years: Number of years of historical data to fetch
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"FETCHING {years} YEARS OF HISTORICAL DATA")
        logger.info(f"{'='*60}")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years*365)
        
        for pair_name, ticker in self.currency_pairs.items():
            try:
                logger.info(f"\nDownloading {pair_name}...")
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                
                if not data.empty:
                    # Calculate technical indicators
                    data['Returns'] = data['Close'].pct_change()
                    data['MA_20'] = data['Close'].rolling(window=20).mean()
                    data['MA_50'] = data['Close'].rolling(window=50).mean()
                    data['Volatility'] = data['Returns'].rolling(window=20).std()
                    data['RSI'] = self._calculate_rsi(data['Close'])
                    
                    # Price movement classification
                    data['Movement'] = 0  # No significant move
                    data.loc[data['Returns'] > 0.005, 'Movement'] = 1  # Up
                    data.loc[data['Returns'] < -0.005, 'Movement'] = -1  # Down
                    
                    self.price_data[pair_name] = data
                    logger.info(f"✓ {pair_name}: {len(data)} days of data")
                else:
                    logger.warning(f"✗ {pair_name}: No data available")
                    
            except Exception as e:
                logger.error(f"✗ Error fetching {pair_name}: {str(e)}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"DATA DOWNLOAD COMPLETE: {len(self.price_data)} pairs loaded")
        logger.info(f"{'='*60}")
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def simulate_news_events(self):
        """
        Simulate high-impact news events over the past 5 years.
        In production, this would integrate with real news APIs.
        """
        logger.info(f"\n{'='*60}")
        logger.info("SIMULATING HIGH-IMPACT NEWS EVENTS")
        logger.info(f"{'='*60}")
        
        # Real historical events (simplified simulation)
        news_templates = [
            {
                'type': 'interest_rate',
                'impact': 'high',
                'affected_currencies': ['USD', 'EUR', 'GBP'],
                'direction': [1, -1],  # Can be bullish or bearish
                'description': 'Central bank interest rate decision'
            },
            {
                'type': 'employment',
                'impact': 'high',
                'affected_currencies': ['USD'],
                'direction': [1, -1],
                'description': 'Non-farm payrolls (NFP) report'
            },
            {
                'type': 'inflation',
                'impact': 'high',
                'affected_currencies': ['USD', 'EUR', 'GBP'],
                'direction': [1, -1],
                'description': 'CPI/Inflation data release'
            },
            {
                'type': 'gdp',
                'impact': 'medium',
                'affected_currencies': ['USD', 'EUR', 'GBP', 'JPY'],
                'direction': [1, -1],
                'description': 'GDP growth figures'
            },
            {
                'type': 'geopolitical',
                'impact': 'high',
                'affected_currencies': ['USD', 'JPY', 'CHF'],  # Safe havens
                'direction': [1],  # Usually positive for safe havens
                'description': 'Geopolitical crisis/tensions'
            }
        ]
        
        # Generate events across 5 years
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5*365)
        
        current_date = start_date
        while current_date < end_date:
            # Add events at realistic intervals
            if np.random.random() < 0.15:  # ~15% chance of event on any day
                template = np.random.choice(news_templates)
                
                event = {
                    'date': current_date,
                    'type': template['type'],
                    'impact': template['impact'],
                    'affected_currencies': template['affected_currencies'],
                    'direction': np.random.choice(template['direction']),
                    'description': template['description'],
                    'sentiment': np.random.choice(['positive', 'negative', 'neutral']),
                    'magnitude': np.random.uniform(0.5, 1.0)
                }
                
                self.news_events.append(event)
            
            current_date += timedelta(days=1)
        
        logger.info(f"\n✓ Generated {len(self.news_events)} high-impact news events")
        logger.info(f"  Event types: {set([e['type'] for e in self.news_events])}")
        logger.info(f"{'='*60}")
    
    def analyze_news_with_ai(self, event_description, date):
        """
        Use Gemini AI to analyze news impact on currencies.
        
        Args:
            event_description: Description of the news event
            date: Date of the event
            
        Returns:
            AI analysis with predicted impact
        """
        if not self.client_enabled:
            # Fallback to rule-based if no API key
            return self._rule_based_analysis(event_description)
        
        try:
            prompt = f"""Analyze this forex market news event from {date.strftime('%Y-%m-%d')}:

Event: {event_description}

Provide a brief analysis covering:
1. Which currencies will likely be affected (USD, EUR, GBP, JPY, etc.)
2. Expected direction (strengthen/weaken)
3. Magnitude of impact (low/medium/high)

Format your response as JSON:
{{
    "affected_currencies": ["USD", "EUR"],
    "expected_direction": {{"USD": "strengthen", "EUR": "weaken"}},
    "impact_magnitude": "high",
    "reasoning": "Brief explanation"
}}"""

            # Use Gemini model
            model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            
            # Try to get available models first
            try:
                available_models = genai.list_models()
                available_model_names = [m.name for m in available_models if 'generateContent' in m.supported_generation_methods]
                
                # Prefer newer models
                preferred_patterns = ['gemini-2.5-pro', 'gemini-2.0-flash', 'gemini-flash-latest', 'gemini-pro-latest', 'gemini-1.5-pro']
                model_name = model_name
                for pattern in preferred_patterns:
                    matching = [m for m in available_model_names if pattern.lower() in m.lower()]
                    if matching:
                        model_name = matching[0]
                        break
            except Exception:
                pass  # Use default model
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return self._rule_based_analysis(event_description)
                
        except Exception as e:
            logger.warning(f"AI analysis error: {str(e)}")
            return self._rule_based_analysis(event_description)
    
    def _rule_based_analysis(self, description):
        """Fallback rule-based analysis when AI is not available"""
        analysis = {
            "affected_currencies": ["USD"],
            "expected_direction": {"USD": "neutral"},
            "impact_magnitude": "medium",
            "reasoning": "Rule-based analysis (API key needed for AI analysis)"
        }
        
        # Simple keyword matching
        if 'rate' in description.lower() or 'fed' in description.lower():
            analysis['impact_magnitude'] = 'high'
            analysis['affected_currencies'] = ['USD', 'EUR']
        elif 'employment' in description.lower() or 'nfp' in description.lower():
            analysis['impact_magnitude'] = 'high'
            analysis['affected_currencies'] = ['USD']
        elif 'inflation' in description.lower() or 'cpi' in description.lower():
            analysis['impact_magnitude'] = 'high'
            analysis['affected_currencies'] = ['USD', 'EUR', 'GBP']
        
        return analysis
    
    def build_features(self):
        """
        Build feature matrix combining price data and news events.
        """
        logger.info(f"\n{'='*60}")
        logger.info("BUILDING FEATURE MATRIX")
        logger.info(f"{'='*60}")
        
        # Optimize: Create date-indexed dictionary for faster news lookup
        news_by_date = {}
        for event in self.news_events:
            try:
                event_date = event['date']
                if hasattr(event_date, 'date'):
                    event_date = event_date.date()
                elif isinstance(event_date, datetime):
                    event_date = event_date.date()
                else:
                    event_date = pd.Timestamp(event_date).date()
                
                if event_date not in news_by_date:
                    news_by_date[event_date] = []
                news_by_date[event_date].append(event)
            except Exception:
                continue  # Skip events with invalid dates
        
        features_list = []
        total_pairs = len(self.price_data)
        pair_num = 0
        
        for pair_name, price_data in self.price_data.items():
            pair_num += 1
            total_rows = len(price_data)
            logger.info(f"\nProcessing {pair_name} ({pair_num}/{total_pairs}) - {total_rows} rows...")
            
            row_count = 0
            for idx, row in price_data.iterrows():
                row_count += 1
                if row_count % 500 == 0:
                    logger.info(f"  Processed {row_count}/{total_rows} rows...")
                
                # Check if Returns is NaN - ensure we're working with scalar value
                try:
                    returns_value = row['Returns']
                    # Convert to scalar if it's a Series (shouldn't happen with iterrows, but safety check)
                    if isinstance(returns_value, pd.Series):
                        returns_value = returns_value.iloc[0] if len(returns_value) > 0 else None
                    if pd.isna(returns_value):
                        continue
                except (KeyError, IndexError):
                    continue
                
                # Find news events for this date (optimized lookup - check current, prev, and next day)
                try:
                    if hasattr(idx, 'date'):
                        price_date = idx.date()
                    elif isinstance(idx, datetime):
                        price_date = idx.date()
                    else:
                        price_date = pd.Timestamp(idx).date()
                    
                    # Get news for current day, previous day, and next day (±1 day window)
                    news_on_day = []
                    for day_offset in [-1, 0, 1]:
                        check_date = price_date + timedelta(days=day_offset)
                        if check_date in news_by_date:
                            news_on_day.extend(news_by_date[check_date])
                except Exception:
                    # Fallback to empty list if date conversion fails
                    news_on_day = []
                
                # Base currency from pair (e.g., EUR from EURUSD)
                base_currency = pair_name[:3]
                quote_currency = pair_name[3:]
                
                # Aggregate news impact
                news_sentiment = 0
                news_count = 0
                news_impact = 0
                
                for event in news_on_day:
                    if base_currency in event['affected_currencies']:
                        news_count += 1
                        news_sentiment += event['direction'] * event['magnitude']
                        news_impact = max(news_impact, event['magnitude'])
                
                # Create feature vector
                feature = {
                    'pair': pair_name,
                    'date': idx,
                    'close': row['Close'],
                    'returns': row['Returns'],
                    'ma_20': row['MA_20'],
                    'ma_50': row['MA_50'],
                    'volatility': row['Volatility'],
                    'rsi': row['RSI'],
                    'news_count': news_count,
                    'news_sentiment': news_sentiment,
                    'news_impact': news_impact,
                    'movement': row['Movement']  # Target variable
                }
                
                features_list.append(feature)
        
        self.features = pd.DataFrame(features_list)
        self.features = self.features.dropna()
        
        logger.info(f"\n✓ Feature matrix built: {len(self.features)} samples")
        logger.info(f"  Features: {len(self.features.columns) - 2} (excluding pair, date)")
        logger.info(f"  Movement distribution:")
        logger.info(self.features['movement'].value_counts())
        logger.info(f"{'='*60}")
    
    def train_model(self):
        """
        Train machine learning model to predict price movements.
        """
        logger.info(f"\n{'='*60}")
        logger.info("TRAINING PREDICTION MODEL")
        logger.info(f"{'='*60}")
        
        # Prepare features and target
        feature_cols = ['returns', 'ma_20', 'ma_50', 'volatility', 'rsi', 
                       'news_count', 'news_sentiment', 'news_impact']
        
        X = self.features[feature_cols]
        y = self.features['movement']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train ensemble model
        logger.info("\nTraining Random Forest...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        y_pred = self.model.predict(X_test_scaled)
        
        logger.info(f"\n{'='*60}")
        logger.info("MODEL PERFORMANCE")
        logger.info(f"{'='*60}")
        logger.info(f"Training Accuracy: {train_score:.2%}")
        logger.info(f"Testing Accuracy: {test_score:.2%}")
        logger.info(f"\nClassification Report:")
        logger.info(classification_report(y_test, y_pred, 
                                   target_names=['Down', 'Neutral', 'Up']))
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info(f"\nFeature Importance:")
        for idx, row in feature_importance.iterrows():
            logger.info(f"  {row['feature']:20s}: {row['importance']:.4f}")
        
        logger.info(f"{'='*60}")
    
    def predict_future_movement(self, pair_name, current_price, recent_news=None):
        """
        Predict future price movement for a currency pair.
        
        Args:
            pair_name: Currency pair (e.g., 'EURUSD')
            current_price: Current price level
            recent_news: Optional list of recent news descriptions
            
        Returns:
            Prediction dictionary with probabilities and recommendation
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        
        if pair_name not in self.price_data:
            raise ValueError(f"No data available for {pair_name}")
        
        # Get recent price data
        price_data = self.price_data[pair_name]
        latest = price_data.iloc[-1]
        
        # Analyze recent news if provided
        news_count = 0
        news_sentiment = 0
        news_impact = 0
        
        if recent_news and self.client_enabled:
            logger.info(f"\nAnalyzing recent news with Gemini AI...")
            for news_item in recent_news:
                analysis = self.analyze_news_with_ai(news_item, datetime.now())
                
                base_currency = pair_name[:3]
                if base_currency in analysis['affected_currencies']:
                    news_count += 1
                    direction = 1 if 'strengthen' in str(analysis['expected_direction'].get(base_currency, '')).lower() else -1
                    magnitude = {'high': 1.0, 'medium': 0.6, 'low': 0.3}.get(analysis['impact_magnitude'], 0.5)
                    news_sentiment += direction * magnitude
                    news_impact = max(news_impact, magnitude)
                    
                    logger.info(f"  • {news_item[:60]}...")
                    logger.info(f"    Impact: {analysis['impact_magnitude']}, Direction: {direction}")
        
        # Create feature vector
        features = np.array([[
            latest['Returns'],
            latest['MA_20'],
            latest['MA_50'],
            latest['Volatility'],
            latest['RSI'],
            news_count,
            news_sentiment,
            news_impact
        ]])
        
        # Scale and predict
        features_scaled = self.scaler.transform(features)
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]
        
        # Create result
        movement_map = {-1: 'DOWN', 0: 'NEUTRAL', 1: 'UP'}
        prob_map = {-1: probabilities[0], 0: probabilities[1], 1: probabilities[2]}
        
        result = {
            'pair': pair_name,
            'current_price': current_price,
            'prediction': movement_map[prediction],
            'confidence': prob_map[prediction],
            'probabilities': {
                'down': probabilities[0],
                'neutral': probabilities[1],
                'up': probabilities[2]
            },
            'news_impact': {
                'count': news_count,
                'sentiment': news_sentiment,
                'magnitude': news_impact
            },
            'technical_indicators': {
                'rsi': latest['RSI'],
                'volatility': latest['Volatility'],
                'ma_20': latest['MA_20'],
                'ma_50': latest['MA_50']
            }
        }
        
        return result
    
    def generate_trading_signals(self, confidence_threshold=0.6):
        """
        Generate trading signals for all currency pairs.
        
        Args:
            confidence_threshold: Minimum confidence to generate signal
            
        Returns:
            List of trading signals
        """
        logger.info(f"\n{'='*60}")
        logger.info("GENERATING TRADING SIGNALS")
        logger.info(f"{'='*60}")
        
        signals = []
        
        for pair_name in self.price_data.keys():
            current_price = self.price_data[pair_name]['Close'].iloc[-1]
            prediction = self.predict_future_movement(pair_name, current_price)
            
            if prediction['confidence'] >= confidence_threshold:
                signal = {
                    'pair': pair_name,
                    'action': prediction['prediction'],
                    'confidence': prediction['confidence'],
                    'current_price': current_price,
                    'timestamp': datetime.now()
                }
                signals.append(signal)
                
                logger.info(f"\n{pair_name}: {prediction['prediction']}")
                logger.info(f"  Confidence: {prediction['confidence']:.1%}")
                logger.info(f"  Current Price: {current_price:.4f}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Generated {len(signals)} signals (confidence ≥ {confidence_threshold:.0%})")
        logger.info(f"{'='*60}")
        
        return signals

