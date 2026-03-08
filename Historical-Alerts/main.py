"""
Forex News-Price Correlation Prediction System
Main entry point for the application
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from src.predictor import ForexNewsPricePredictor
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

def main():
    """
    Main execution function demonstrating the system.
    """
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   FOREX NEWS-PRICE CORRELATION PREDICTION SYSTEM                 ║
║                                                                  ║
║   Analyzes 5 years of historical data + news events             ║
║   to predict future currency movements                           ║
║   (Using Gemini AI for news analysis)                            ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Check for API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.warning("\n⚠️  WARNING: GOOGLE_API_KEY not found in environment")
        logger.warning("   News analysis will use rule-based fallback")
        logger.warning("   Get API key from: https://aistudio.google.com/")
        logger.warning("   Set it with: export GOOGLE_API_KEY='your-key-here'")
        response = input("\nContinue without API key? (y/n): ")
        if response.lower() != 'y':
            logger.info("Exiting...")
            return
    
    # Initialize system
    predictor = ForexNewsPricePredictor(api_key=api_key)
    
    # Step 1: Fetch historical data
    predictor.fetch_historical_data(years=5)
    
    if not predictor.price_data:
        logger.error("\n❌ No price data available. Exiting...")
        return
    
    # Step 2: Generate/simulate news events
    predictor.simulate_news_events()
    
    # Step 3: Build features
    predictor.build_features()
    
    # Step 4: Train model
    predictor.train_model()
    
    # Step 5: Generate current predictions
    logger.info(f"\n{'='*60}")
    logger.info("CURRENT MARKET PREDICTIONS")
    logger.info(f"{'='*60}")
    
    # Example: Predict EUR/USD with recent news
    recent_news = [
        "Federal Reserve signals potential rate cuts in 2026",
        "European Central Bank maintains steady policy stance",
        "US inflation data comes in higher than expected"
    ]
    
    try:
        eurusd_prediction = predictor.predict_future_movement(
            'EURUSD',
            predictor.price_data['EURUSD']['Close'].iloc[-1],
            recent_news=recent_news if api_key else None
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"EUR/USD PREDICTION")
        logger.info(f"{'='*60}")
        logger.info(f"Current Price: {eurusd_prediction['current_price']:.5f}")
        logger.info(f"Prediction: {eurusd_prediction['prediction']}")
        logger.info(f"Confidence: {eurusd_prediction['confidence']:.1%}")
        logger.info(f"\nProbabilities:")
        logger.info(f"  Down:    {eurusd_prediction['probabilities']['down']:.1%}")
        logger.info(f"  Neutral: {eurusd_prediction['probabilities']['neutral']:.1%}")
        logger.info(f"  Up:      {eurusd_prediction['probabilities']['up']:.1%}")
        logger.info(f"\nTechnical Indicators:")
        logger.info(f"  RSI: {eurusd_prediction['technical_indicators']['rsi']:.2f}")
        logger.info(f"  Volatility: {eurusd_prediction['technical_indicators']['volatility']:.4f}")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Error generating prediction: {str(e)}")
    
    # Step 6: Generate trading signals
    signals = predictor.generate_trading_signals(confidence_threshold=0.6)
    
    logger.info(f"\n{'='*60}")
    logger.info("SYSTEM READY")
    logger.info(f"{'='*60}")
    logger.info(f"""
The prediction system is now trained and ready to use.

Key Features:
• {len(predictor.price_data)} currency pairs analyzed
• {len(predictor.news_events)} historical news events processed
• {len(predictor.features)} training samples
• Model accuracy: Check performance report above

Usage:
1. Call predictor.predict_future_movement(pair, price, news_list)
2. Call predictor.generate_trading_signals() for all pairs
3. Model can be retrained with new data periodically

Next Steps:
• Integrate with real news APIs (NewsAPI, Bloomberg, etc.)
• Add more sophisticated AI news analysis
• Implement backtesting framework
• Add risk management and position sizing
• Deploy as web service or trading bot
    """)

if __name__ == "__main__":
    main()







