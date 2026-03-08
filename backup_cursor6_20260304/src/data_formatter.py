"""Format raw forex data for LLM analysis"""

import os
import json
from typing import Dict, List, Optional
from src.logger import setup_logger

logger = setup_logger()

class DataFormatter:
    """Format raw forex data from Google Drive for LLM analysis"""
    
    def format_file(self, file_path: str) -> Optional[str]:
        """
        Format a single file's content for LLM analysis
        
        Args:
            file_path: Path to file (JSON or text)
            
        Returns:
            Formatted string ready for LLM prompt
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try JSON first
            try:
                data = json.loads(content)
                return self._format_json(data)
            except json.JSONDecodeError:
                # Assume text format
                return self._format_text(content)
        except Exception as e:
            logger.error(f"Error formatting file {file_path}: {e}")
            return None
    
    def format_files(self, file_paths: List[str]) -> str:
        """
        Format multiple files into a single summary
        
        Args:
            file_paths: List of file paths to format
            
        Returns:
            Combined formatted string
        """
        # Add disclaimer about historical prices
        disclaimer = """
⚠️ IMPORTANT: PRICE DATA DISCLAIMER ⚠️
The data below comes from Google Drive "Forex tracker" folder reports. 
Any prices mentioned in these reports are HISTORICAL SNAPSHOTS from when the reports were generated.
These prices are NOT current market prices - they may be hours or days old.
DO NOT use prices from this data as "Current Price" in recommendations.
Always use the live market prices provided separately in the prompt.

"""
        
        formatted_parts = [disclaimer]
        
        for file_path in file_paths:
            formatted = self.format_file(file_path)
            if formatted:
                file_name = os.path.basename(file_path)
                formatted_parts.append(f"\n=== {file_name} ===\n{formatted}\n")
        
        return "\n".join(formatted_parts)
    
    def _format_json(self, data: Dict) -> str:
        """Format JSON data"""
        # Handle different JSON structures from Forex tracker
        formatted = []
        
        if 'trends' in data:
            trends = data['trends']
            formatted.append("TRENDING CURRENCIES (Historical Data):")
            for trend in trends[:20]:  # Top 20
                pair = trend.get('pair', 'N/A')
                change = trend.get('change_pct', 0)
                direction = trend.get('direction', 'neutral')
                # Note: Prices in trends are historical snapshots
                formatted.append(f"  {pair}: {change:.2f}% ({direction}) [Historical]")
        
        if 'news' in data:
            news = data['news']
            formatted.append("\nRELATED NEWS:")
            for item in news[:20]:  # Top 20
                title = item.get('title', 'N/A')
                source = item.get('source', 'N/A')
                formatted.append(f"  - {title} (Source: {source})")
        
        if 'correlations' in data:
            correlations = data['correlations']
            formatted.append("\nNEWS-CURRENCY CORRELATIONS:")
            for corr in correlations[:15]:  # Top 15
                pair = corr.get('currency_pair', 'N/A')
                news_title = corr.get('news_title', 'N/A')[:60]
                score = corr.get('correlation_score', 0)
                formatted.append(f"  {pair}: {news_title}... (Score: {score:.2f})")
        
        return "\n".join(formatted) if formatted else str(data)
    
    def _format_text(self, text: str) -> str:
        """Format text data"""
        # Clean up text, limit length
        cleaned = text.strip()
        # Limit to first 5000 characters to avoid token limits
        if len(cleaned) > 5000:
            cleaned = cleaned[:5000] + "... (truncated)"
        return cleaned







