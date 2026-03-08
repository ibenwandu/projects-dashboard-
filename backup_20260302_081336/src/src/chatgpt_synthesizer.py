"""Gemini synthesis of LLM recommendations"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

try:
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
    
    def synthesize(self, llm_recommendations: Dict[str, Optional[str]]) -> Optional[str]:
        """
        Synthesize recommendations from multiple LLMs using Gemini
        
        Args:
            llm_recommendations: Dictionary with LLM names and their recommendations
            
        Returns:
            Final synthesized recommendations
        """
        if not self.enabled:
            logger.warning("Gemini not enabled")
            return None
        
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
            
            prompt = f"""You are an expert forex trader reviewing recommendations from multiple AI analysts. Review the following recommendations from ChatGPT, Gemini, and Claude. Analyze them, identify convergence points, and provide your final trading recommendations.

{recommendations_text}

Based on your review of all recommendations:
1. Identify the strongest trading opportunities (where multiple analysts agree)
2. Provide final trading recommendations with specific:
   - Currency pairs
   - Entry prices (exact levels)
   - Exit/target prices (exact levels)
   - Stop loss levels (exact levels)
   - Position sizing guidance
   - Rationale for each recommendation

Format your recommendations clearly with specific price levels that can be used for automated monitoring and alerts.
"""
            
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            result = response.text
            logger.info("✅ Gemini synthesis completed")
            return result
            
        except Exception as e:
            logger.error(f"Error with Gemini synthesis: {e}")
            return None

