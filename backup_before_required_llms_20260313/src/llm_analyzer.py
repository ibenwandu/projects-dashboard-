"""LLM analysis: ChatGPT, Gemini, Claude, DeepSeek"""

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
# Note: google-genai has different API, stick with google-generativeai for now
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

# Claude
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ChatGPT
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class LLMAnalyzer:
    """Analyze forex data using multiple LLMs"""
    
    def __init__(self):
        """Initialize LLM analyzers"""
        # Price monitor for current prices
        try:
            from src.price_monitor import PriceMonitor
            self.price_monitor = PriceMonitor()
        except ImportError:
            self.price_monitor = None
            logger.warning("PriceMonitor not available - cannot include current prices in prompts")
        
        # ChatGPT
        self.chatgpt_api_key = os.getenv('OPENAI_API_KEY')
        self.chatgpt_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.chatgpt_enabled = OPENAI_AVAILABLE and bool(self.chatgpt_api_key)
        if self.chatgpt_enabled:
            self.chatgpt_client = OpenAI(api_key=self.chatgpt_api_key)
            logger.info(f"✅ ChatGPT enabled (model: {self.chatgpt_model})")
        
        # Gemini
        self.gemini_api_key = os.getenv('GOOGLE_API_KEY')
        self.gemini_enabled = GEMINI_AVAILABLE and bool(self.gemini_api_key)
        if self.gemini_enabled:
            genai.configure(api_key=self.gemini_api_key)
            logger.info("✅ Gemini enabled")
        
        # Claude
        self.claude_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.claude_model = os.getenv('ANTHROPIC_MODEL', 'claude-haiku-4-5-20251001')
        self.claude_enabled = ANTHROPIC_AVAILABLE and bool(self.claude_api_key)
        if self.claude_enabled:
            self.claude_client = Anthropic(api_key=self.claude_api_key)
            logger.info("✅ Claude enabled")
        
        # DeepSeek (OpenAI-compatible API)
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.deepseek_model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        self.deepseek_enabled = OPENAI_AVAILABLE and bool(self.deepseek_api_key)
        if self.deepseek_enabled:
            self.deepseek_client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
            logger.info(f"✅ DeepSeek enabled (model: {self.deepseek_model})")
        else:
            self.deepseek_client = None
    
    def _get_current_prices_section(self) -> str:
        """Get current market prices section for prompts"""
        if not self.price_monitor:
            return ""
        
        # Major currency pairs to track
        pairs = [
            'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD',
            'NZD/USD', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'EUR/AUD',
            'EUR/CAD', 'GBP/AUD', 'GBP/CAD', 'AUD/NZD', 'CAD/CHF', 'EUR/CHF',
            'GBP/CHF', 'AUD/CHF', 'NZD/CHF', 'CAD/JPY', 'CHF/JPY', 'NZD/JPY',
            'USD/ZAR', 'USD/MXN'
        ]
        
        prices = []
        for pair in pairs:
            try:
                rate = self.price_monitor.get_rate(pair)
                if rate:
                    prices.append(f"  - {pair}: {rate:.5f}")
            except Exception:
                pass
        
        if prices:
            return f"""
3. CURRENT MARKET PRICES (LIVE - as of now):
{chr(10).join(prices)}

CRITICAL: You MUST use these LIVE prices above for the "Current Price" field in each recommendation. 
DO NOT use prices from Google Drive historical data - those are snapshots from when reports were generated.
The Google Drive data contains historical prices that may be hours or days old - these are NOT current prices.

IMPORTANT: When recommending entry prices, they MUST be close to the current prices above. For example:
- For INTRADAY trades: Entry should be within 50 pips (0.5%) of current price
- For SWING trades: Entry should be within 200 pips (2%) of current price

If you recommend an entry price that is far from the current price (e.g., GBP/JPY at 160 when current is 210), the trade will never trigger and will be marked as MISSED.

"""
        return ""
    
    def _get_chatgpt_prompt(self, data_summary: str, current_datetime: datetime = None) -> str:
        """Get prompt for ChatGPT"""
        # Get current date/time if not provided
        if current_datetime is None:
            current_datetime = datetime.now(pytz.UTC)
        
        # Ensure timezone-aware
        if current_datetime.tzinfo is None:
            current_datetime = pytz.UTC.localize(current_datetime)
        
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

You MUST use the date above ({current_est.strftime('%Y-%m-%d')}) as the current date for your analysis. Do NOT assume or hallucinate dates. All references to "today", "this date", or upcoming events should be based on {current_est.strftime('%Y-%m-%d')}.

"""
        
        current_prices = self._get_current_prices_section()
        return f"""{date_time_info}As an expert forex trader with over 20 years of experience in forex trading, please analyze trading opportunities using BOTH of the following sources:

1. INFORMATION FROM GOOGLE DRIVE (Forex tracker folder):
The following data contains hourly reports on trending currencies retrieved from the Google Drive folder called "Forex tracker":
{data_summary}

2. YOUR OWN RESEARCH:
You have access to current forex market information, global events, news, and real-time currency trends. Use your knowledge and research capabilities to:
- Research current market trends and currency movements
- Identify relevant news events and economic indicators
- Analyze technical and fundamental factors
- Fact-check and validate information from the Google Drive data
- Identify any discrepancies or additional opportunities not in the provided data

{current_prices}ANALYSIS REQUIREMENTS:
Based on BOTH the Google Drive information AND your own research of current news and currency trends, provide your recommendations regarding any available trading opportunities currently in the market. Also provide updated risk-managed entry/exit price levels and position sizing guidance based on current price action. As part of the analysis, check if there are any upcoming high-impact news events today that might cause a sudden reversal in this trend.

Please provide your analysis and recommendations in a clear format with:
- Currency pairs to trade
- **Current Price:** For EACH recommendation, you MUST include the current market price from the "CURRENT MARKET PRICES (LIVE)" section above. Use the exact price shown there, NOT prices from Google Drive historical data.
- **TIMEFRAME CLASSIFICATION**: For EACH trade, classify as either 'INTRADAY' or 'SWING':
  * **INTRADAY**: Quick profits, close same day (by 5 PM NY time). Entry must be within 50 pips (0.5%) of current price. Target < 40 pips.
  * **SWING**: Capture larger moves, hold for 2-5 days. Entry must be within 200 pips (2%) of current price. Target > 80 pips.
- Entry prices (exact levels) - MUST be close to current market prices shown above
- Exit/target prices (exact levels)
- Stop loss levels (exact levels)
- Position sizing recommendations
- Rationale for each recommendation (indicating which insights came from Google Drive data vs. your own research)
- Upcoming high-impact news events that might affect the trend

CRITICAL: 
1. For each trade recommendation, you MUST explicitly state the "Current Price" using the LIVE prices from the section above, NOT from Google Drive historical data.
2. For each trade recommendation, you MUST explicitly state whether it is an INTRADAY or SWING trade.
3. Entry prices MUST be realistic and close to the current market prices shown above. If you recommend GBP/JPY and current price is 210.50, do NOT recommend entry at 160 or 190 - that is too far and the trade will never trigger.
4. Use the current prices as reference - your entry should be within 0.5% for INTRADAY or 2% for SWING trades.

OPTIONAL (recommended for reliable parsing): At the end of your response, add a line "MACHINE_READABLE:" followed by a JSON array of your recommendations. Each object must have: "pair" (e.g. "USD/JPY"), "direction" ("BUY" or "SELL"), "entry", "exit" (or "target"), "stop_loss". Example:
MACHINE_READABLE: [{{"pair":"USD/JPY","direction":"SELL","entry":152.6,"exit":151.9,"stop_loss":153.05}},{{"pair":"GBP/JPY","direction":"SELL","entry":208.0,"exit":207.2,"stop_loss":208.5}}]
"""

    def _get_gemini_prompt(self, data_summary: str, current_datetime: datetime = None) -> str:
        """Get prompt for Gemini"""
        # Get current date/time if not provided
        if current_datetime is None:
            current_datetime = datetime.now(pytz.UTC)
        
        # Ensure timezone-aware
        if current_datetime.tzinfo is None:
            current_datetime = pytz.UTC.localize(current_datetime)
        
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

You MUST use the date above ({current_est.strftime('%Y-%m-%d')}) as the current date for your analysis. Do NOT assume or hallucinate dates. All references to "today", "this date", or upcoming events should be based on {current_est.strftime('%Y-%m-%d')}.

"""
        
        current_prices = self._get_current_prices_section()
        return f"""{date_time_info}As an expert forex trader with over 20 years of experience in forex trading, please analyze trading opportunities using BOTH of the following sources:

1. INFORMATION FROM GOOGLE DRIVE (Forex tracker folder):
The following data contains hourly reports on trending currencies retrieved from the Google Drive folder called "Forex tracker":
{data_summary}

2. YOUR OWN RESEARCH:
You have access to current forex market information, global events, news, and real-time currency trends. Use your knowledge and research capabilities to:
- Research current market trends and currency movements
- Identify relevant news events and economic indicators
- Analyze technical and fundamental factors
- Fact-check and validate information from the Google Drive data
- Identify any discrepancies or additional opportunities not in the provided data

{current_prices}ANALYSIS REQUIREMENTS:
Based on BOTH the Google Drive information AND your own research of current news and currency trends, provide your recommendations regarding any available trading opportunities currently in the market. Also provide updated risk-managed entry/exit price levels and position sizing guidance based on current price action. As part of the analysis, check if there are any upcoming high-impact news events today that might cause a sudden reversal in this trend.

Please provide your analysis and recommendations in a clear format with:
- Currency pairs to trade
- **Current Price:** For EACH recommendation, you MUST include the current market price from the "CURRENT MARKET PRICES (LIVE)" section above. Use the exact price shown there, NOT prices from Google Drive historical data.
- **TIMEFRAME CLASSIFICATION**: For EACH trade, classify as either 'INTRADAY' or 'SWING':
  * **INTRADAY**: Quick profits, close same day (by 5 PM NY time). Entry must be within 50 pips (0.5%) of current price. Target < 40 pips.
  * **SWING**: Capture larger moves, hold for 2-5 days. Entry must be within 200 pips (2%) of current price. Target > 80 pips.
- Entry prices (exact levels) - MUST be close to current market prices shown above
- Exit/target prices (exact levels)
- Stop loss levels (exact levels)
- Position sizing recommendations
- Rationale for each recommendation (indicating which insights came from Google Drive data vs. your own research)
- Upcoming high-impact news events that might affect the trend

CRITICAL: 
1. For each trade recommendation, you MUST explicitly state the "Current Price" using the LIVE prices from the section above, NOT from Google Drive historical data.
2. For each trade recommendation, you MUST explicitly state whether it is an INTRADAY or SWING trade.
3. Entry prices MUST be realistic and close to the current market prices shown above. If you recommend GBP/JPY and current price is 210.50, do NOT recommend entry at 160 or 190 - that is too far and the trade will never trigger.
4. Use the current prices as reference - your entry should be within 0.5% for INTRADAY or 2% for SWING trades.

OPTIONAL (recommended for reliable parsing): At the end of your response, add a line "MACHINE_READABLE:" followed by a JSON array of your recommendations. Each object must have: "pair" (e.g. "USD/JPY"), "direction" ("BUY" or "SELL"), "entry", "exit" (or "target"), "stop_loss". Example:
MACHINE_READABLE: [{{"pair":"USD/JPY","direction":"SELL","entry":152.6,"exit":151.9,"stop_loss":153.05}},{{"pair":"GBP/JPY","direction":"SELL","entry":208.0,"exit":207.2,"stop_loss":208.5}}]
"""

    def _get_claude_prompt(self, data_summary: str, current_datetime: datetime = None) -> str:
        """Get prompt for Claude"""
        # Get current date/time if not provided
        if current_datetime is None:
            current_datetime = datetime.now(pytz.UTC)
        
        # Ensure timezone-aware
        if current_datetime.tzinfo is None:
            current_datetime = pytz.UTC.localize(current_datetime)
        
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

You MUST use the date above ({current_est.strftime('%Y-%m-%d')}) as the current date for your analysis. Do NOT assume or hallucinate dates. All references to "today", "this date", or upcoming events should be based on {current_est.strftime('%Y-%m-%d')}.

"""
        
        current_prices = self._get_current_prices_section()
        return f"""{date_time_info}As an expert forex trader with over 20 years of experience in forex trading, please analyze trading opportunities using BOTH of the following sources:

1. INFORMATION FROM GOOGLE DRIVE (Forex tracker folder):
The following data contains hourly reports on trending currencies retrieved from the Google Drive folder called "Forex tracker":
{data_summary}

2. YOUR OWN RESEARCH:
You have access to current forex market information, global events, news, and real-time currency trends. Use your knowledge and research capabilities to:
- Research current market trends and currency movements
- Identify relevant news events and economic indicators
- Analyze technical and fundamental factors
- Fact-check and validate information from the Google Drive data
- Identify any discrepancies or additional opportunities not in the provided data

{current_prices}ANALYSIS REQUIREMENTS:
Based on BOTH the Google Drive information AND your own research of current news and currency trends, provide your recommendations regarding any available trading opportunities currently in the market. Also provide updated risk-managed entry/exit price levels and position sizing guidance based on current price action. As part of the analysis, check if there are any upcoming high-impact news events today that might cause a sudden reversal in this trend.

Please provide your analysis and recommendations in a clear format with:
- Currency pairs to trade
- **Current Price:** For EACH recommendation, you MUST include the current market price from the "CURRENT MARKET PRICES (LIVE)" section above. Use the exact price shown there, NOT prices from Google Drive historical data.
- **TIMEFRAME CLASSIFICATION**: For EACH trade, classify as either 'INTRADAY' or 'SWING':
  * **INTRADAY**: Quick profits, close same day (by 5 PM NY time). Entry must be within 50 pips (0.5%) of current price. Target < 40 pips.
  * **SWING**: Capture larger moves, hold for 2-5 days. Entry must be within 200 pips (2%) of current price. Target > 80 pips.
- Entry prices (exact levels) - MUST be close to current market prices shown above
- Exit/target prices (exact levels)
- Stop loss levels (exact levels)
- Position sizing recommendations
- Rationale for each recommendation (indicating which insights came from Google Drive data vs. your own research)
- Upcoming high-impact news events that might affect the trend

CRITICAL: 
1. For each trade recommendation, you MUST explicitly state the "Current Price" using the LIVE prices from the section above, NOT from Google Drive historical data.
2. For each trade recommendation, you MUST explicitly state whether it is an INTRADAY or SWING trade.
3. Entry prices MUST be realistic and close to the current market prices shown above. If you recommend GBP/JPY and current price is 210.50, do NOT recommend entry at 160 or 190 - that is too far and the trade will never trigger.
4. Use the current prices as reference - your entry should be within 0.5% for INTRADAY or 2% for SWING trades.

OPTIONAL (recommended for reliable parsing): At the end of your response, add a line "MACHINE_READABLE:" followed by a JSON array of your recommendations. Each object must have: "pair" (e.g. "USD/JPY"), "direction" ("BUY" or "SELL"), "entry", "exit" (or "target"), "stop_loss". Example:
MACHINE_READABLE: [{{"pair":"USD/JPY","direction":"SELL","entry":152.6,"exit":151.9,"stop_loss":153.05}},{{"pair":"GBP/JPY","direction":"SELL","entry":208.0,"exit":207.2,"stop_loss":208.5}}]
"""

    def _get_deepseek_prompt(self, data_summary: str, current_datetime: datetime = None) -> str:
        """Get prompt for DeepSeek (same structure as ChatGPT, with explicit JSON request)."""
        base_prompt = self._get_chatgpt_prompt(data_summary, current_datetime)
        
        # Add explicit request for MACHINE_READABLE JSON format at the end
        # DeepSeek sometimes uses narrative format, so we emphasize JSON
        json_request = """

IMPORTANT FOR PARSING: Please provide your recommendations in MACHINE_READABLE JSON format at the end of your response. This is critical for the system to parse your recommendations correctly.

Format:
MACHINE_READABLE: [{"pair":"EUR/USD","direction":"SELL","entry":1.158,"exit":1.1525,"stop_loss":1.161}, {"pair":"USD/JPY","direction":"BUY","entry":152.6,"exit":153.2,"stop_loss":152.1}]

Required fields for each recommendation:
- "pair": Currency pair (e.g., "EUR/USD", "USD/JPY")
- "direction": "BUY" or "SELL"
- "entry": Entry price (number)
- "exit" or "target": Target/exit price (number)
- "stop_loss": Stop loss price (number)

You can still provide narrative analysis above, but the MACHINE_READABLE line at the end is essential."""
        
        return base_prompt + json_request

    def analyze_with_gemini(self, data_summary: str, current_datetime: datetime = None) -> Optional[str]:
        """Analyze using Gemini"""
        if not self.gemini_enabled:
            logger.warning("Gemini not enabled")
            return None
        
        try:
            # First, try to list available models to find what works
            gemini_model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            
            # Get available models and use them
            available_model_names = []
            try:
                available_models = genai.list_models()
                available_model_names = [m.name for m in available_models if 'generateContent' in m.supported_generation_methods]
                logger.info(f"Available Gemini models: {len(available_model_names)} found")
                if available_model_names:
                    logger.info(f"First 5: {available_model_names[:5]}")
            except Exception as e:
                logger.warning(f"Could not list models: {e}")
            
            # Use models directly from available_models list (they have correct format)
            models_to_try = []
            
            # Add available models first (they already have /models/ prefix if needed)
            if available_model_names:
                # Prefer newer models (2.5, 2.0) and latest versions
                preferred_patterns = [
                    'gemini-2.5-pro',
                    'gemini-2.0-flash',
                    'gemini-flash-latest',
                    'gemini-pro-latest',
                    'gemini-2.0-flash-001',
                    'gemini-1.5-pro',  # Fallback to older models
                    'gemini-1.5-flash',
                ]
                
                for pattern in preferred_patterns:
                    # Find models matching pattern (case insensitive)
                    matching = [m for m in available_model_names if pattern.lower() in m.lower()]
                    if matching:
                        # Take first match (most specific)
                        models_to_try.append(matching[0])
                        logger.debug(f"Found available model matching '{pattern}': {matching[0]}")
                
                # If no preferred models found, try first few available models
                if not models_to_try and available_model_names:
                    models_to_try = available_model_names[:5]
                    logger.info(f"No preferred models found, trying first available: {models_to_try}")
            
            # Remove duplicates while preserving order
            seen = set()
            models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]
            
            logger.info(f"Trying {len(models_to_try)} Gemini models from available list...")
            
            model = None
            working_model = None
            
            for model_name in models_to_try:
                try:
                    logger.debug(f"Trying Gemini model: {model_name}")
                    # Use model name as-is from available list (already has correct format)
                    model = genai.GenerativeModel(model_name)
                    # Test with a tiny prompt to verify it works
                    test_response = model.generate_content("Hi", generation_config={'max_output_tokens': 1})
                    working_model = model_name
                    logger.info(f"✅ Found working Gemini model: {model_name}")
                    break
                except Exception as model_error:
                    error_msg = str(model_error)[:150]
                    logger.debug(f"Model {model_name} failed: {error_msg}")
                    continue
            
            if not model:
                error_msg = f"No working Gemini model found. Tried {len(models_to_try)} models from available list."
                if available_model_names:
                    error_msg += f" Available models count: {len(available_model_names)}"
                    error_msg += f" Sample: {available_model_names[:5]}"
                raise Exception(error_msg)
            
            prompt = self._get_gemini_prompt(data_summary, current_datetime)
            
            # Retry logic for quota errors (429) with exponential backoff
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(prompt)
                    result = response.text
                    logger.info(f"✅ Gemini analysis completed (model: {working_model})")
                    return result
                except Exception as api_error:
                    error_str = str(api_error)
                    # Check if it's a quota/rate limit error (429)
                    is_quota_error = '429' in error_str or 'quota' in error_str.lower() or 'rate limit' in error_str.lower()
                    
                    if is_quota_error and attempt < max_retries - 1:
                        # Exponential backoff: 10s, 20s, 30s
                        retry_delay = (attempt + 1) * 10
                        logger.warning(f"⚠️ Gemini quota/rate limit error (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    elif is_quota_error:
                        logger.error(f"❌ Gemini quota exceeded after {max_retries} attempts. Please check your billing account or wait for quota reset.")
                        raise api_error
                    else:
                        # Not a quota error, re-raise immediately
                        raise api_error
            
            # Should not reach here, but just in case
            return None
        except Exception as e:
            logger.error(f"Error with Gemini analysis: {e}")
            return None
    
    def analyze_with_chatgpt(self, data_summary: str, current_datetime: datetime = None) -> Optional[str]:
        """Analyze using ChatGPT API"""
        if not self.chatgpt_enabled:
            logger.warning("ChatGPT not enabled")
            return None
        
        try:
            prompt = self._get_chatgpt_prompt(data_summary, current_datetime)
            response = self.chatgpt_client.chat.completions.create(
                model=self.chatgpt_model,
                messages=[
                    {"role": "system", "content": "You are an expert forex trader with decades of experience."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            result = response.choices[0].message.content
            logger.info("✅ ChatGPT analysis completed")
            return result
        except Exception as e:
            logger.error(f"Error with ChatGPT analysis: {e}")
            return None
    
    def analyze_with_claude(self, data_summary: str, current_datetime: datetime = None) -> Optional[str]:
        """Analyze using Claude"""
        if not self.claude_enabled:
            logger.warning("Claude not enabled")
            return None
        
        try:
            prompt = self._get_claude_prompt(data_summary, current_datetime)
            # Try primary model first, with fallback
            try:
                message = self.claude_client.messages.create(
                    model=self.claude_model,
                    max_tokens=4000,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
            except Exception as model_error:
                # Try alternative Claude models with correct model identifiers
                # Anthropic model names use format: claude-{version}-{model}-{YYYYMMDD}
                fallback_models = [
                    'claude-haiku-4-5-20251001',      # Latest Haiku 4.5 (fast, cost-effective)
                    'claude-sonnet-4-20250514',       # Latest Sonnet (balanced)
                    'claude-opus-4-20250805',         # Latest Opus (most capable)
                    'claude-3-5-sonnet-20241022',     # Older Sonnet 3.5 (stable fallback)
                    'claude-3-haiku-20240307',        # Older Haiku 3 (last resort)
                ]
                
                message = None
                last_error = model_error  # in case loop doesn't run or all skipped
                for fallback_model in fallback_models:
                    if fallback_model == self.claude_model:
                        continue  # Skip if it's the same as the one that just failed
                    try:
                        logger.warning(f"Trying {fallback_model}")
                        message = self.claude_client.messages.create(
                            model=fallback_model,
                            max_tokens=4000,
                            messages=[{
                                "role": "user",
                                "content": prompt
                            }]
                        )
                        logger.info(f"✅ Successfully used {fallback_model}")
                        break  # Success, exit loop
                    except Exception as fallback_error:
                        last_error = fallback_error
                        logger.warning(f"{fallback_model} failed: {fallback_error}")
                        continue
                
                if message is None:
                    # consol-recommend3 Phase 1.4: log billing/credit when all models failed
                    err_lower = str(last_error).lower()
                    if any(x in err_lower for x in ("credit", "billing", "balance", "overloaded", "rate_limit")):
                        logger.warning("Claude skipped: API credit/billing issue – check Anthropic account.")
                    logger.warning("Claude unavailable / no opportunities; using other LLMs (all Claude models failed)")
                    return None
            
            result = message.content[0].text
            if not (result and result.strip()):
                logger.warning("Claude unavailable / no opportunities; using other LLMs (empty response)")
                return None
            logger.info("✅ Claude analysis completed")
            return result
        except Exception as e:
            # consol-recommend3 Phase 1.4: one clear line when failure is billing/credit
            err_lower = str(e).lower()
            if any(x in err_lower for x in ("credit", "billing", "balance", "overloaded", "rate_limit")):
                logger.warning("Claude skipped: API credit/billing issue – check Anthropic account.")
            logger.warning(f"Claude unavailable / no opportunities; using other LLMs - Error with Claude analysis: {e}")
            return None
    
    def analyze_with_deepseek(self, data_summary: str, current_datetime: datetime = None) -> Optional[str]:
        """Analyze using DeepSeek (OpenAI-compatible API)."""
        if not self.deepseek_enabled:
            logger.warning("DeepSeek not enabled")
            return None
        try:
            prompt = self._get_deepseek_prompt(data_summary, current_datetime)
            response = self.deepseek_client.chat.completions.create(
                model=self.deepseek_model,
                messages=[
                    {"role": "system", "content": "You are an expert forex trader with decades of experience."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            result = response.choices[0].message.content
            logger.info("✅ DeepSeek analysis completed")
            return result
        except Exception as e:
            logger.error(f"Error with DeepSeek analysis: {e}")
            return None
    
    def analyze_all(self, data_summary: str, current_datetime: datetime = None) -> Dict[str, Optional[str]]:
        """
        Run analysis on all enabled LLMs (ChatGPT, Gemini, Claude, DeepSeek)
        
        Args:
            data_summary: Summary of forex data from Google Drive
            current_datetime: Current datetime (defaults to now, in UTC)
            
        Returns:
            Dictionary with LLM names as keys and analysis results as values
        """
        # Get current datetime if not provided
        if current_datetime is None:
            current_datetime = datetime.now(pytz.UTC)
        
        # Ensure timezone-aware
        if current_datetime.tzinfo is None:
            current_datetime = pytz.UTC.localize(current_datetime)
        
        # Log current date/time for debugging
        est_tz = pytz.timezone('America/New_York')
        current_est = current_datetime.astimezone(est_tz)
        logger.info(f"Starting LLM analysis at {current_est.strftime('%Y-%m-%d %H:%M:%S %Z')} (EST/EDT)")
        
        results = {}
        
        # Run analyses (ChatGPT, Gemini, Claude)
        logger.info("Running ChatGPT analysis...")
        results['chatgpt'] = self.analyze_with_chatgpt(data_summary, current_datetime)
        
        logger.info("Running Gemini analysis...")
        results['gemini'] = self.analyze_with_gemini(data_summary, current_datetime)
        
        logger.info("Running Claude analysis...")
        results['claude'] = self.analyze_with_claude(data_summary, current_datetime)
        if results.get('claude') is None and self.claude_enabled:
            logger.info("Claude unavailable or no opportunities; consensus will use remaining LLMs")
        logger.info("Running DeepSeek analysis...")
        results['deepseek'] = self.analyze_with_deepseek(data_summary, current_datetime)
        
        # Log results
        enabled_count = sum(1 for v in results.values() if v is not None)
        base_llm_count = 4  # chatgpt, gemini, claude, deepseek
        logger.info(f"Completed {enabled_count}/{base_llm_count} LLM analyses")
        
        # Log which ones succeeded/failed
        for name, result in results.items():
            if result:
                logger.info(f"✅ {name.upper()} analysis completed successfully")
            else:
                logger.warning(f"❌ {name.upper()} analysis failed or returned no result")
        
        return results

