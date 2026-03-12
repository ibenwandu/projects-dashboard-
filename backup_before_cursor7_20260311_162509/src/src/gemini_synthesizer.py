"""Gemini synthesis of LLM recommendations"""

import os
import time
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import pytz
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

# Gemini - Use the working package (google-generativeai)
try:
    # Explicitly import generativeai to avoid conflict with google-genai
    from google import generativeai
    genai = generativeai
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        # Fallback to direct import
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False

class GeminiSynthesizer:
    """Synthesize recommendations from multiple LLMs using Gemini"""
    
    def __init__(self):
        """Initialize Gemini client"""
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.enabled = GEMINI_AVAILABLE and bool(self.api_key)
        
        if self.enabled:
            genai.configure(api_key=self.api_key)
            logger.info("✅ Gemini synthesizer enabled")
        else:
            logger.warning("Gemini not enabled - set GOOGLE_API_KEY")
    
    def synthesize(self, llm_recommendations: Dict[str, Optional[str]], current_datetime: datetime = None, current_prices: Optional[Dict[str, float]] = None) -> Optional[str]:
        """
        Synthesize recommendations from multiple LLMs using Gemini
        
        Args:
            llm_recommendations: Dictionary with LLM names and their recommendations
            current_datetime: Current datetime (defaults to now, in UTC)
            current_prices: Dictionary mapping currency pairs to current live prices (e.g., {'EUR/USD': 1.0850})
            
        Returns:
            Final synthesized recommendations
        """
        if not self.enabled:
            logger.warning("Gemini not enabled")
            return None
        
        # Get current datetime if not provided
        if current_datetime is None:
            current_datetime = datetime.now(pytz.UTC)
        
        # Ensure timezone-aware
        if current_datetime.tzinfo is None:
            current_datetime = pytz.UTC.localize(current_datetime)
        
        # Filter out None values
        valid_recommendations = {
            name: rec for name, rec in llm_recommendations.items() if rec
        }
        
        if not valid_recommendations:
            logger.warning("No valid LLM recommendations to synthesize")
            return None
        
        try:
            # Build prompt with all recommendations
            recommendations_text = ""
            for name, rec in valid_recommendations.items():
                recommendations_text += f"\n\n=== {name.upper()} RECOMMENDATIONS ===\n{rec}\n"
            
            # Format in both UTC and EST/EDT
            est_tz = pytz.timezone('America/New_York')
            current_est = current_datetime.astimezone(est_tz)
            current_utc = current_datetime.astimezone(pytz.UTC)
            
            date_time_info = f"""
IMPORTANT: CURRENT DATE AND TIME
- Current Date (EST/EDT): {current_est.strftime('%Y-%m-%d')}
- Current Time (EST/EDT): {current_est.strftime('%H:%M:%S %Z')}
- Current Date (UTC): {current_utc.strftime('%Y-%m-%d')}
- Current Time (UTC): {current_utc.strftime('%H:%M:%S %Z')}

You MUST use the date above ({current_est.strftime('%Y-%m-%d')}) as the current date for your synthesis. Do NOT assume or hallucinate dates. All references to "today", "this date", or upcoming events should be based on {current_est.strftime('%Y-%m-%d')}.

"""
            
            # Build current prices section if provided
            current_prices_section = ""
            if current_prices:
                prices_list = []
                for pair, price in sorted(current_prices.items()):
                    prices_list.append(f"  - {pair}: {price:.5f}")
                
                if prices_list:
                    current_prices_section = f"""
3. CURRENT MARKET PRICES (LIVE - as of now):
{chr(10).join(prices_list)}

CRITICAL: You MUST use these LIVE prices above for the "Current Price" field in each recommendation. 
DO NOT use prices from Google Drive historical data - those are snapshots from when reports were generated.
The Google Drive data contains historical prices that may be hours or days old - these are NOT current prices.
"""
            
            prompt = f"""{date_time_info}You are an expert forex trader with over 20 years of experience reviewing recommendations from multiple AI analysts. Each analyst has provided recommendations based on BOTH:
1. Data from the Google Drive "Forex tracker" folder (hourly reports on trending currencies)
2. Their own research of current news, market trends, and currency movements

Review the following recommendations from ChatGPT, Gemini, and Claude. Analyze them, identify convergence points, and provide your final trading recommendations.

{recommendations_text}
{current_prices_section}
Based on your review of all recommendations:
1. Identify the strongest trading opportunities (where multiple analysts agree)
2. Consider upcoming high-impact news events that might cause sudden reversals
3. Cross-reference findings from Google Drive data with current market research
4. Provide final trading recommendations with specific:
   - Currency pairs
   - Entry prices (exact levels)
   - Exit/target prices (exact levels)
   - Stop loss levels (exact levels)
   - Position sizing guidance
   - Rationale for each recommendation (synthesizing insights from both data sources)
   - Risk assessment including news event impact

CRITICAL FORMATTING REQUIREMENTS:
You MUST format each recommendation using this EXACT structure:

### **Trade Recommendation 1: [Long/Short] [PAIR]**

*   **Currency Pair:** [PAIR]
*   **Current Price:** **[PRICE]**  (MUST be from the LIVE prices section above, NOT from Google Drive historical data)
*   **Entry Price (Buy Limit):** **[PRICE]**  (for LONG trades)
   OR
*   **Entry Price (Sell Limit):** **[PRICE]**  (for SHORT trades)
*   **Exit/Target Price:** **[PRICE]**
*   **Stop Loss:** **[PRICE]**
*   **Trade Classification:** [INTRADAY or SWING]
*   **Rationale:** [Your analysis]

### **Trade Recommendation 2: [Long/Short] [PAIR]**
[Same format...]

IMPORTANT:
- Use EXACTLY "### **Trade Recommendation [NUMBER]:" as the header
- Include "Currency Pair:", "Current Price:", "Entry Price (Buy/Sell Limit):", "Exit/Target Price:", "Stop Loss:" labels
- The "Current Price" MUST be taken from the "CURRENT MARKET PRICES (LIVE)" section above - use the exact price shown there for the currency pair
- DO NOT use prices from Google Drive historical data for "Current Price" - those are outdated snapshots
- Use markdown bold (**text**) for price values
- Format all price levels as exact numbers (e.g., 1.3450, not "around 1.34")

This specific format is required for automated parsing and alerting.
"""
            
            # Try to get available models first, then use them
            models_to_try = []
            
            try:
                available_models = genai.list_models()
                available_model_names = [m.name for m in available_models if 'generateContent' in m.supported_generation_methods]
                
                if available_model_names:
                    # Prefer newer models (2.5, 2.0) and latest versions
                    preferred_patterns = [
                        'gemini-2.5-pro',
                        'gemini-2.0-flash',
                        'gemini-flash-latest',
                        'gemini-pro-latest',
                        'gemini-2.0-flash-001',
                        'gemini-1.5-pro',
                        'gemini-1.5-flash',
                    ]
                    
                    for pattern in preferred_patterns:
                        matching = [m for m in available_model_names if pattern.lower() in m.lower()]
                        if matching:
                            # Add all matches for this pattern (up to 2)
                            models_to_try.extend(matching[:2])
                    
                    # Remove duplicates while preserving order
                    seen = set()
                    models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]
                    
                    # If no preferred found, use first available
                    if not models_to_try:
                        models_to_try = available_model_names[:5]
            except Exception:
                # Fallback if listing fails
                models_to_try = [
                    'models/gemini-2.0-flash',
                    'models/gemini-2.5-pro',
                    'models/gemini-flash-latest',
                ]
            
            model = None
            working_model = None
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    # Test with a tiny prompt to verify it works
                    test_response = model.generate_content("Hi", generation_config={'max_output_tokens': 1})
                    working_model = model_name
                    logger.info(f"✅ Found working Gemini model for synthesis: {model_name}")
                    break
                except Exception as model_error:
                    logger.debug(f"Model {model_name} failed: {str(model_error)[:100]}")
                    continue
            
            if not model:
                raise Exception("No working Gemini model found after trying all options")
            
            # Retry logic for quota errors (429) with exponential backoff
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(prompt)
                    result = response.text
                    logger.info(f"✅ Gemini synthesis completed (model: {working_model})")
                    return result
                except Exception as api_error:
                    error_str = str(api_error)
                    # Check if it's a quota/rate limit error (429)
                    is_quota_error = '429' in error_str or 'quota' in error_str.lower() or 'rate limit' in error_str.lower()
                    
                    if is_quota_error and attempt < max_retries - 1:
                        # Exponential backoff: 10s, 20s, 30s
                        retry_delay = (attempt + 1) * 10
                        logger.warning(f"⚠️ Gemini synthesis quota/rate limit error (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    elif is_quota_error:
                        logger.error(f"❌ Gemini synthesis quota exceeded after {max_retries} attempts. Please check your billing account or wait for quota reset.")
                        raise api_error
                    else:
                        # Not a quota error, re-raise immediately
                        raise api_error
            
            # Should not reach here, but just in case
            return None
            
        except Exception as e:
            logger.error(f"Error with Gemini synthesis: {e}")
            return None

