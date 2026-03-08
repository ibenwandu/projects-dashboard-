"""LLM-based sentiment analysis"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class SentimentAnalyzer:
    """Analyze market sentiment using LLM"""
    
    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini"):
        """
        Initialize sentiment analyzer
        
        Args:
            provider: LLM provider ("openai", "anthropic", "gemini")
            model: Model name
        """
        self.provider = provider
        self.model = model
        self.client = None
        
        if provider == "openai":
            self._init_openai()
        elif provider == "anthropic":
            self._init_anthropic()
        elif provider == "gemini":
            self._init_gemini()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")
    
    def _init_anthropic(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")
    
    def _init_gemini(self):
        """Initialize Gemini client"""
        try:
            import google.generativeai as genai
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)
        except ImportError:
            raise ImportError("google-generativeai package not installed. Install with: pip install google-generativeai")
    
    def analyze_sentiment(self, currency: str, news_text: str, trade_direction: str, bias_expectation: str) -> Dict:
        """
        Analyze sentiment for a currency
        
        Args:
            currency: Currency code (e.g., "USD")
            news_text: Formatted news text
            trade_direction: Trade direction ("long" or "short")
            bias_expectation: Expected bias (e.g., "Weak USD")
            
        Returns:
            Dictionary with sentiment analysis results
        """
        prompt = self._build_prompt(currency, news_text, trade_direction, bias_expectation)
        
        try:
            if self.provider == "openai":
                response = self._analyze_openai(prompt)
            elif self.provider == "anthropic":
                response = self._analyze_anthropic(prompt)
            elif self.provider == "gemini":
                response = self._analyze_gemini(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            return self._parse_response(response)
            
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'direction': 'neutral',
                'drivers': [],
                'conflicts_with_trade': False,
                'analysis': f"Error: {str(e)}"
            }
    
    def _build_prompt(self, currency: str, news_text: str, trade_direction: str, bias_expectation: str) -> str:
        """Build LLM prompt for sentiment analysis"""
        
        prompt = f"""You are a senior forex market analyst. Analyze the following news to determine market sentiment toward {currency}.

TRADE CONTEXT:
- Trade Direction: {trade_direction}
- Expected Bias: {bias_expectation}

{news_text}

Analyze the news and provide:

1. SENTIMENT: Determine if market sentiment toward {currency} is:
   - "bullish" (strengthening/positive)
   - "bearish" (weakening/negative)  
   - "neutral" (no clear direction)

2. CONFIDENCE: Rate confidence 0.0 to 1.0 (1.0 = very confident)

3. DIRECTION: Which way is sentiment shifting?
   - "strengthening" if {currency} sentiment is becoming more positive
   - "weakening" if {currency} sentiment is becoming more negative
   - "stable" if no significant shift

4. KEY DRIVERS: List 2-5 specific fundamental drivers (e.g., "Hawkish Fed commentary", "Strong US PMI data", "Risk-off sentiment")

5. TRADE CONFLICT: Does the sentiment shift CONFLICT with the trade direction?
   - If trade is LONG {currency} and sentiment is BEARISH → CONFLICT = True
   - If trade is SHORT {currency} and sentiment is BULLISH → CONFLICT = True
   - Otherwise → CONFLICT = False

Respond in this exact JSON format:
{{
    "sentiment": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "direction": "strengthening|weakening|stable",
    "drivers": ["driver1", "driver2", ...],
    "conflicts_with_trade": true|false,
    "analysis": "Brief 2-3 sentence summary"
}}"""

        return prompt
    
    def _analyze_openai(self, prompt: str) -> str:
        """Analyze using OpenAI"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a forex market analyst. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content
    
    def _analyze_anthropic(self, prompt: str) -> str:
        """Analyze using Anthropic"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            temperature=0.3,
            system="You are a forex market analyst. Respond only with valid JSON.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    
    def _analyze_gemini(self, prompt: str) -> str:
        """Analyze using Gemini"""
        response = self.client.generate_content(prompt)
        return response.text
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse LLM response"""
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return {
                    'sentiment': parsed.get('sentiment', 'neutral'),
                    'confidence': float(parsed.get('confidence', 0.5)),
                    'direction': parsed.get('direction', 'stable'),
                    'drivers': parsed.get('drivers', []),
                    'conflicts_with_trade': bool(parsed.get('conflicts_with_trade', False)),
                    'analysis': parsed.get('analysis', '')
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback if JSON parsing fails
        return {
            'sentiment': 'neutral',
            'confidence': 0.0,
            'direction': 'stable',
            'drivers': [],
            'conflicts_with_trade': False,
            'analysis': response_text[:200]
        }






