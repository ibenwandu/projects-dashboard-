"""Parse Gemini final recommendations to extract entry/exit points"""

import os
import re
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
from src.logger import setup_logger

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

logger = setup_logger()

class RecommendationParser:
    """Parse Gemini final synthesis to extract trading recommendations"""
    
    def __init__(self):
        """Initialize parser"""
        # Major, minor, and exotic currency pairs
        # Expanded to include emerging market pairs (USD/MXN, USD/ZAR, etc.)
        self.currency_pairs = [
            # Major pairs
            'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD', 'NZD/USD',
            # Minor pairs
            'EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'EUR/AUD', 'EUR/CAD', 'GBP/AUD',
            'GBP/CAD', 'AUD/NZD', 'CAD/CHF', 'EUR/CHF', 'GBP/CHF', 'AUD/CHF', 'NZD/CHF',
            'CAD/JPY', 'CHF/JPY', 'NZD/JPY',
            # Exotic/emerging market pairs
            'USD/MXN', 'USD/ZAR', 'USD/TRY', 'USD/BRL', 'USD/CNH', 'USD/HKD', 'USD/SGD',
            'EUR/TRY', 'GBP/ZAR', 'AUD/MXN', 'NZD/ZAR'
        ]
    
    def parse_file(self, file_path: str) -> List[Dict]:
        """
        Parse analysis file to extract trading opportunities
        
        Args:
            file_path: Path to analysis file (text or JSON)
            
        Returns:
            List of trading opportunity dictionaries
        """
        try:
            # Validate path is within expected working directories (prevent path traversal)
            abs_path = Path(file_path).resolve()
            allowed_roots = [Path(os.getcwd()).resolve(), Path('/var/data').resolve()]
            # Include temp directory for testing
            temp_root = Path(tempfile.gettempdir()).resolve()
            allowed_roots.append(temp_root)

            if not any(str(abs_path).startswith(str(root)) for root in allowed_roots):
                logger.error(f"Refusing to read file outside allowed directories: {file_path}")
                return []

            # Enforce file size limit before reading
            try:
                file_size = os.path.getsize(abs_path)
                if file_size > MAX_FILE_SIZE_BYTES:
                    logger.error(f"File too large ({file_size} bytes, limit {MAX_FILE_SIZE_BYTES}), skipping: {file_path}")
                    return []
            except OSError as e:
                logger.warning(f"Could not stat file {file_path}: {e}")

            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read(MAX_FILE_SIZE_BYTES)

            # Try JSON first
            try:
                data = json.loads(content)
                return self._parse_json(data)
            except (json.JSONDecodeError, ValueError):
                # Fallback to text parsing
                return self._parse_text(content)
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return []
    
    def parse_text(self, text: str) -> List[Dict]:
        """
        Parse text to extract trading opportunities (public method).
        Tries MACHINE_READABLE JSON block first, then falls back to regex parsing.
        
        Args:
            text: Text content to parse
            
        Returns:
            List of trading opportunity dictionaries (may include opps with entry=None for downstream fill)
        """
        return self._parse_text(text)
    
    def _parse_json(self, data: Dict) -> List[Dict]:
        """Parse JSON format analysis"""
        opportunities = []
        
        # Handle different JSON structures
        if isinstance(data, list):
            for item in data:
                opp = self._extract_opportunity_from_dict(item)
                if opp:
                    opportunities.append(opp)
        elif isinstance(data, dict):
            # Look for recommendations or opportunities key
            if 'recommendations' in data:
                for item in data['recommendations']:
                    opp = self._extract_opportunity_from_dict(item)
                    if opp:
                        opportunities.append(opp)
            elif 'opportunities' in data:
                for item in data['opportunities']:
                    opp = self._extract_opportunity_from_dict(item)
                    if opp:
                        opportunities.append(opp)
            else:
                opp = self._extract_opportunity_from_dict(data)
                if opp:
                    opportunities.append(opp)
        
        return opportunities
    
    def _try_extract_machine_readable_json(self, text: str) -> Optional[List[Dict]]:
        """
        Try to extract and parse a MACHINE_READABLE JSON block from LLM text.
        Block format: MACHINE_READABLE: [...] or ```json [...] ```
        Returns list of opportunities or None if not found/invalid.
        """
        if not text or not text.strip():
            return None
        # Look for MACHINE_READABLE: [...] (single line or multi-line array)
        mr_match = re.search(
            r'MACHINE_READABLE\s*:\s*(\[[\s\S]*?\])\s*(?:\n|$)',
            text,
            re.IGNORECASE
        )
        if mr_match:
            try:
                raw = mr_match.group(1).strip()
                data = json.loads(raw)
                if isinstance(data, list) and len(data) > 0:
                    opps = []
                    for item in data:
                        opp = self._extract_opportunity_from_dict(item)
                        if opp and opp.get('pair'):
                            opps.append(opp)
                    if opps:
                        logger.info(f"📋 Parsed {len(opps)} opportunities from MACHINE_READABLE JSON block")
                        return opps
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"MACHINE_READABLE block parse failed: {e}")
        # Look for ```json [...] ```
        code_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
        if code_match:
            try:
                raw = code_match.group(1).strip()
                data = json.loads(raw)
                if isinstance(data, list) and len(data) > 0:
                    opps = []
                    for item in data:
                        opp = self._extract_opportunity_from_dict(item)
                        if opp and opp.get('pair'):
                            opps.append(opp)
                    if opps:
                        logger.info(f"📋 Parsed {len(opps)} opportunities from JSON code block")
                        return opps
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"JSON code block parse failed: {e}")
        return None

    def _parse_text(self, text: str) -> List[Dict]:
        """Parse text format analysis - ENHANCED for all LLM formats. Returns opportunities (entry may be None for downstream fill)."""
        opportunities = []
        
        if not text or len(text.strip()) == 0:
            logger.warning("⚠️ Parser received empty text")
            return opportunities

        # Optional: try MACHINE_READABLE JSON block first
        mr_opps = self._try_extract_machine_readable_json(text)
        if mr_opps:
            return mr_opps
        
        # ========================================================================
        # PATTERN SET 1a: "Trade Recommendation:" format (ChatGPT - ACTUAL FORMAT!)
        # Actual format: "### 1. Trade Recommendation: **EUR/USD**"
        # ========================================================================
        pattern_1a = r'(?:####|###)\s+\d+\.\s+Trade\s+Recommendation:\s+\*\*([A-Z]{3})[/\s-]([A-Z]{3})\*\*'
        
        matches_1a = list(re.finditer(
            rf'{pattern_1a}(.*?)(?=\n(?:####|###)\s+\d+\.|\n\*\s*\*\*Currency\s+Pair|Trade\s+Recommendation\s+\d+|\d+\.\s+[A-Z]{{3}}[/\s-]|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 1b: "Currency Pair:" format (ChatGPT - bold label + pair)
        # Actual format: "### 1. **Currency Pair: USD/JPY**" (3 hashes, not 4!)
        # ========================================================================
        pattern_1b = r'(?:####|###)\s+\d+\.\s+\*\*Currency\s+Pair:\s+([A-Z]{3})[/\s-]([A-Z]{3})\*\*'
        
        matches_1b = list(re.finditer(
            rf'{pattern_1b}(.*?)(?=\n(?:####|###)\s+\d+\.|\n\*\s*\*\*Currency\s+Pair|Trade\s+Recommendation\s+\d+|\d+\.\s+[A-Z]{{3}}[/\s-]|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 1c: ChatGPT actual format - "Currency Pair: **XXX/YYY**" (pair only in bold)
        # Actual format from email: "### 1. Currency Pair: **USD/JPY**"
        # ========================================================================
        pattern_1c = r'(?:####|###)\s+\d+\.\s+Currency\s+Pair:\s+\*\*([A-Z]{3})[/\s-]([A-Z]{3})\*\*'
        
        matches_1c = list(re.finditer(
            rf'{pattern_1c}(.*?)(?=\n(?:####|###)\s+\d+\.|\n\*\s*\*\*Currency\s+Pair|\n\*\s+\*\*Entry|\d+\.\s+[A-Z]{{3}}[/\s-]|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        matches_1 = matches_1a + matches_1b + matches_1c
        
        # ========================================================================
        # PATTERN SET 2: "Trade Recommendation X:" format (Gemini)
        # Format: "### **Trade Recommendation 1: Short GBP/USD**"
        # ========================================================================
        pattern_2 = r'###\s+\*\*Trade\s+Recommendation\s+\d+:\s+(?:Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})\*\*'
        
        matches_2 = list(re.finditer(
            rf'{pattern_2}(.*?)(?=\n###\s+\*\*Trade\s+Recommendation|\n###\s+\*\*Trade\s+\d+:|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 3: "Trade X:" format (Gemini Final Synthesis)
        # Format: "### **Trade 1: Long GBP/JPY (High Conviction)**"
        # ========================================================================
        pattern_3 = r'###\s+\*\*Trade\s+\d+:\s+(?:Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})'
        
        matches_3 = list(re.finditer(
            rf'{pattern_3}(.*?)(?=\n###\s+\*\*Trade\s+\d+:|\n---\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 4: Numbered list "1. GBP/USD" (Claude)
        # Format: "1. GBP/USD"
        # ========================================================================
        pattern_4 = r'^\d+\.\s+([A-Z]{3})[/\s]([A-Z]{3})\s*\n'
        
        matches_4 = list(re.finditer(
            rf'{pattern_4}(.*?)(?=^\d+\.\s+[A-Z]{{3}}[/\s]|^[A-Z]+\s+[A-Z]+:|$)',
            text,
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        ))
        
        # ========================================================================
        # PATTERN SET 5: "Trade Recommendation X:" format (Gemini Final - ACTUAL FORMAT)
        # Format: "### **Trade Recommendation 1: Short GBP/USD (High Conviction)**"
        # ========================================================================
        pattern_5 = r'###\s+\*\*Trade\s+Recommendation\s+\d+:\s+(?:Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})'
        
        matches_5 = list(re.finditer(
            rf'{pattern_5}(.*?)(?=\n###\s+\*\*Trade\s+Recommendation|\n---\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 6: "#### **Trade X:" format (Gemini Final - ACTUAL OUTPUT FORMAT)
        # Format: "#### **Trade 1: High Conviction - Sell USD/JPY**"
        # OR: "#### **Trade 1: Confirmed Setup - Sell GBP/JPY**"
        # This is the EXACT format from the 4 PM email that worked!
        # ========================================================================
        pattern_6 = r'####\s+\*\*Trade\s+\d+:\s+[^-]+-\s+(?:Sell|Buy|Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})\*\*'
        
        matches_6 = list(re.finditer(
            rf'{pattern_6}(.*?)(?=\n####\s+\*\*Trade\s+\d+|\n###\s+\*\*Trade|\n---\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 7: "Currency Pair:" with markdown bullets (Gemini Final format)
        # Format: "*   **Currency Pair:** USD/JPY" followed by price info
        # This is the ACTUAL format from the 4 PM email that worked!
        # ========================================================================
        pattern_7 = r'\*\s+\*\*Currency\s+Pair:\*\*\s+([A-Z]{3})[/\s]([A-Z]{3})'
        
        matches_7 = list(re.finditer(
            rf'{pattern_7}(.*?)(?=\n\*\s+\*\*Currency\s+Pair:\*\*|\n####\s+\*\*Trade|\n###\s+\*\*Trade|\n---\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 8: ChatGPT format "### 1. **Trade Recommendation: EUR/USD**"
        # Format: "### 1. **Trade Recommendation: EUR/USD**" followed by fields
        # More flexible: handles variations in spacing and formatting
        # ========================================================================
        pattern_8 = r'###\s+\d+\.\s+\*\*Trade\s+Recommendation:?\s+([A-Z]{3})[/\s-]([A-Z]{3})\*\*'
        
        matches_8 = list(re.finditer(
            rf'{pattern_8}(.*?)(?=\n###\s+\d+\.\s+\*\*Trade\s+Recommendation:|\n###\s+\d+\.\s+[A-Z]|\n\n\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        ))
        
        # ========================================================================
        # PATTERN SET 9: Claude format variations
        # Actual format from email: "1. USD/JPY SHORT (SWING Trade)" (simple format!)
        # Also handles: "🔶 TRADE 1: USD/JPY Short" and "1. SHORT USD/JPY"
        # ========================================================================
        # Pattern 9a: "1. USD/JPY SHORT (SWING Trade)" (Claude's actual simple format)
        pattern_9a = r'^\d+\.\s+([A-Z]{3})[/\s-]([A-Z]{3})\s+(?:SHORT|LONG|SELL|BUY)(?:\s*\([^)]+\))?'
        
        matches_9a = list(re.finditer(
            rf'{pattern_9a}(.*?)(?=^\d+\.\s+[A-Z]{{3}}[/\s-]|^\d+\.\s+(?:SHORT|LONG|SELL|BUY)|^[A-Z]+\s+[A-Z]+:|$)',
            text,
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        ))
        
        # Pattern 9b: "🔶 TRADE 1: USD/JPY Short" (emoji format)
        pattern_9b = r'(?:🔶\s+)?TRADE\s+\d+:\s+([A-Z]{3})[/\s-]([A-Z]{3})\s+(?:Short|Long|SELL|BUY)'
        
        matches_9b = list(re.finditer(
            rf'{pattern_9b}(.*?)(?=(?:🔶\s+)?TRADE\s+\d+:|^\d+\.\s+[A-Z]{{3}}[/\s-]|^[A-Z]+\s+[A-Z]+:|$)',
            text,
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        ))
        
        # Pattern 9c: "1. USD/JPY SHORT TRADE" (with TRADE keyword)
        pattern_9c = r'^\d+\.\s+([A-Z]{3})[/\s-]([A-Z]{3})\s+(?:SHORT|LONG|SELL|BUY)\s+TRADE'
        
        matches_9c = list(re.finditer(
            rf'{pattern_9c}(.*?)(?=^\d+\.\s+[A-Z]{{3}}[/\s-]|^\d+\.\s+(?:SHORT|LONG|SELL|BUY)|^[A-Z]+\s+[A-Z]+:|$)',
            text,
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        ))
        
        # Pattern 9d: "1. SHORT USD/JPY (SWING TRADE)" (direction first)
        pattern_9d = r'^\d+\.\s+(?:SHORT|LONG|SELL|BUY)\s+([A-Z]{3})[/\s-]([A-Z]{3})(?:\s*\([^)]+\))?'
        
        matches_9d = list(re.finditer(
            rf'{pattern_9d}(.*?)(?=^\d+\.\s+(?:SHORT|LONG|SELL|BUY)\s+[A-Z]{{3}}[/\s-]|^\d+\.\s+[A-Z]|^[A-Z]+\s+[A-Z]+:|$)',
            text,
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        ))
        
        matches_9 = matches_9a + matches_9b + matches_9c + matches_9d
        
        # Combine all matches
        all_matches = matches_1 + matches_2 + matches_3 + matches_4 + matches_5 + matches_6 + matches_7 + matches_8 + matches_9
        
        # Debug: Log if no matches found
        if len(all_matches) == 0:
            # Log a preview of the text to help diagnose why no patterns matched
            text_preview = text[:500] if len(text) > 500 else text
            logger.warning(f"⚠️ Parser found 0 pattern matches. Text preview (first 500 chars): {text_preview}")
            logger.debug(f"   Pattern matches: P1={len(matches_1)}, P2={len(matches_2)}, P3={len(matches_3)}, P4={len(matches_4)}, P5={len(matches_5)}, P6={len(matches_6)}, P7={len(matches_7)}, P8={len(matches_8)}, P9={len(matches_9)}")
            # Also log lines that might contain trade recommendations
            lines = text.split('\n')[:20]  # First 20 lines
            for i, line in enumerate(lines):
                if any(keyword in line.upper() for keyword in ['TRADE', 'RECOMMENDATION', 'EUR', 'USD', 'GBP', 'JPY', 'SHORT', 'LONG']):
                    logger.debug(f"   Line {i+1}: {line[:100]}")
        
        # Track seen opportunities to prevent duplicates
        seen_opportunities = set()
        
        # Process matches
        for match in all_matches:
            try:
                base = match.group(1).upper()
                quote = match.group(2).upper()
                pair = f"{base}/{quote}"
                section_text = match.group(3) if len(match.groups()) >= 3 else ''
                
                normalized_pair = self._normalize_pair(pair)
                if normalized_pair:
                    opp = self._extract_opportunity_from_text(normalized_pair, section_text)
                    if opp:
                        # Include even when entry is None (downstream fill will add entry from current_prices/synthesis)
                        entry_rounded = round(opp['entry'], 4) if opp.get('entry') else None
                        unique_key = (opp['pair'], opp['direction'], entry_rounded)
                        if unique_key not in seen_opportunities:
                            seen_opportunities.add(unique_key)
                            opportunities.append(opp)
                            if not opp.get('entry'):
                                logger.debug(f"Including {opp['pair']} {opp['direction']} with missing entry for downstream fill")
                        else:
                            logger.debug(f"⚠️ Skipping duplicate opportunity: {opp['pair']} {opp['direction']} @ {opp.get('entry')}")
            except Exception as e:
                logger.debug(f"Error processing match (skipping): {e}", exc_info=True)
        
        # Log deduplication summary
        if len(all_matches) > len(opportunities):
            duplicates_removed = len(all_matches) - len(opportunities)
            logger.info(f"🔍 Deduplication: Removed {duplicates_removed} duplicate(s) from {len(all_matches)} matches → {len(opportunities)} unique opportunities")

        # Post-parse validation: log opportunities with missing critical fields
        for opp in opportunities:
            missing = [f for f in ('entry', 'stop_loss', 'exit') if not opp.get(f)]
            if missing:
                logger.debug(
                    f"Opportunity {opp.get('pair')} {opp.get('direction')} is missing fields: "
                    f"{', '.join(missing)} (may be filled downstream)"
                )

        return opportunities
    
    def _extract_opportunity_from_dict(self, data: Dict) -> Optional[Dict]:
        """Extract opportunity from dictionary"""
        try:
            pair = data.get('pair') or data.get('currency_pair') or data.get('symbol')
            entry = data.get('entry') or data.get('entry_price') or data.get('entryPrice')
            exit_long = data.get('exit') or data.get('exit_price') or data.get('exitPrice') or data.get('target')
            stop_loss = data.get('stop_loss') or data.get('stopLoss') or data.get('stop')
            direction = data.get('direction') or data.get('type') or data.get('action', 'BUY').upper()
            position_size = data.get('position_size') or data.get('positionSize') or data.get('size')
            recommendation = data.get('recommendation') or data.get('reason') or data.get('analysis', '')
            
            # Extract timeframe classification
            timeframe = data.get('timeframe', 'INTRADAY')
            if isinstance(timeframe, str):
                timeframe = timeframe.upper()
                if timeframe not in ['INTRADAY', 'SWING']:
                    # Try to infer from context or default to INTRADAY
                    timeframe = 'INTRADAY'
            else:
                timeframe = 'INTRADAY'
            
            if pair and entry:
                # Normalize pair format
                pair = self._normalize_pair(pair)
                if pair:
                    return {
                        'pair': pair,
                        'entry': float(entry),
                        'exit': float(exit_long) if exit_long else None,
                        'stop_loss': float(stop_loss) if stop_loss else None,
                        'direction': 'BUY' if direction in ['BUY', 'LONG', 'GO LONG'] else 'SELL',
                        'position_size': position_size,
                        'recommendation': str(recommendation),
                        'timeframe': timeframe,
                        'source': 'structured_data'
                    }
        except Exception as e:
            logger.debug(f"Error extracting from dict: {e}")
        
        return None
    
    def _extract_opportunity_from_text(self, pair: str, text: str) -> Optional[Dict]:
        """Extract opportunity from text section"""
        try:
            # ====================================================================
            # ENHANCED ENTRY PRICE EXTRACTION
            # ====================================================================
            entry_patterns = [
                # Gemini format: "*   **Entry Price (Buy Limit):** **193.80**"
                r'(?:\*\s+)?\*\*Entry\s+Price\s*\([^)]+\):\*\*\s+\*\*([0-9]+\.?[0-9]*)\*\*',
                # Gemini format: "*   **Entry Price (Buy Limit):** 193.80"
                r'(?:\*\s+)?\*\*Entry\s+Price\s*\([^)]+\):\*\*\s+([0-9]+\.?[0-9]*)',
                # Standard: "**Entry Price:** **1.3450**"
                r'(?:\*\s+)?\*\*Entry\s+Price:\*\*\s+\*\*([0-9]+\.?[0-9]*)\*\*',
                # Standard: "**Entry Price:** 1.3450"
                r'(?:\*\s+)?\*\*Entry\s+Price:\*\*\s+([0-9]+\.?[0-9]*)',
                # ChatGPT: "- **Entry Price**: 1.18650"
                r'-\s+\*\*Entry\s+Price\*\*:\s+([0-9]+\.?[0-9]*)',
                # ChatGPT with parentheses: "- **Entry Price:** 1.18650 (approximately 10 pips below current price)"
                r'-\s+\*\*Entry\s+Price\*\*:\s+([0-9]+\.?[0-9]*)\s*\([^)]*\)',
                # Claude: "- Entry: 153.80"
                r'-\s+Entry:\s+([0-9]+\.?[0-9]*)',
                # Claude with context: "- Entry: 153.80 (within 2% of current price)"
                r'-\s+Entry:\s+([0-9]+\.?[0-9]*)\s*\([^)]*\)',
                # No markdown: "Entry Price: 1.3400"
                r'Entry\s+Price:\s+([0-9]+\.?[0-9]*)',
                # Claude approximate: "Entry: Approximately 1.3440"
                r'Entry:\s+Approximately\s+([0-9]+\.?[0-9]*)',
                # Short form: "Entry: 1.3400"
                r'Entry:\s+([0-9]+\.?[0-9]*)',
                # ChatGPT/LLM: "**Current Price:** 152.60800" or "Current Price: 1.36289" (fallback when no Entry line)
                r'(?:\*\s+)?\*\*?Current\s+Price\*\*?:\s+\*\*?([0-9]+\.?[0-9]*)\*\*?',
                r'Current\s+Price:\s+([0-9]+\.?[0-9]*)',
            ]
            
            entry = None
            for pattern in entry_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entry = float(match.group(1))
                    break
            
            # ====================================================================
            # ENHANCED EXIT/TARGET PRICE EXTRACTION
            # ====================================================================
            exit_patterns = [
                # Standard: "**Exit/Target Price:** **195.60**"
                r'(?:\*\s+)?\*\*Exit[/-]Target\s+Price:\*\*\s+\*\*([0-9]+\.?[0-9]*)\*\*',
                # Standard: "**Exit/Target Price:** 195.60"
                r'(?:\*\s+)?\*\*Exit[/-]Target\s+Price:\*\*\s+([0-9]+\.?[0-9]*)',
                # ChatGPT: "- **Exit/Target Price**: 1.19000"
                r'-\s+\*\*Exit[/-]Target\s+Price\*\*:\s+([0-9]+\.?[0-9]*)',
                # ChatGPT with context: "- **Exit/Target Price**: 1.19000 (targeting a gain of about 25 pips)"
                r'-\s+\*\*Exit[/-]Target\s+Price\*\*:\s+([0-9]+\.?[0-9]*)\s*\([^)]*\)',
                # Standard: "**Target Price:** **1.3550**"
                r'(?:\*\s+)?\*\*Target\s+Price:\*\*\s+\*\*([0-9]+\.?[0-9]*)\*\*',
                # Standard: "**Target Price:** 1.3550"
                r'(?:\*\s+)?\*\*Target\s+Price:\*\*\s+([0-9]+\.?[0-9]*)',
                # Claude: "- Take Profit Target: 149.50"
                r'-\s+Take\s+Profit\s+Target:\s+([0-9]+\.?[0-9]*)',
                # Claude with context: "- Take Profit Target: 149.50 (+430 pips potential gain)"
                r'-\s+Take\s+Profit\s+Target:\s+([0-9]+\.?[0-9]*)\s*\([^)]*\)',
                # No markdown: "Exit/Target Price: 1.3550"
                r'Exit[/-]Target\s+Price:\s+([0-9]+\.?[0-9]*)',
                # Short form: "Target: 1.3550"
                r'Target:\s+([0-9]+\.?[0-9]*)',
                # Take Profit: "Take Profit: 1.3550"
                r'Take\s+Profit:\s+([0-9]+\.?[0-9]*)',
            ]
            
            exit_price = None
            for pattern in exit_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    exit_price = float(match.group(1))
                    break
            
            # ====================================================================
            # ENHANCED STOP LOSS EXTRACTION
            # ====================================================================
            stop_patterns = [
                # Standard: "**Stop Loss:** **192.90**"
                r'(?:\*\s+)?\*\*?Stop\s+Loss\*\*?:\s+\*\*?([0-9]+\.?[0-9]*)\*\*?',
                # Standard: "**Stop Loss:** 192.90"
                r'(?:\*\s+)?\*\*?Stop\s+Loss\*\*?:\s+([0-9]+\.?[0-9]*)',
                # Claude/ChatGPT: "- **Stop Loss:** 156.20" (markdown bullet, no Level keyword)
                r'-\s+\*\*Stop\s+Loss:\*\*\s+([0-9]+\.?[0-9]*)',
                # Claude/ChatGPT with context: "- **Stop Loss:** 156.20 (+240 pips risk management)"
                r'-\s+\*\*Stop\s+Loss:\*\*\s+([0-9]+\.?[0-9]*)\s*\([^)]*\)',
                # ChatGPT: "- **Stop Loss Level**: 1.18400"
                r'-\s+\*\*Stop\s+Loss\s+Level\*\*:\s+([0-9]+\.?[0-9]*)',
                # ChatGPT with context: "- **Stop Loss Level**: 1.18400 (risk of about 25 pips)"
                r'-\s+\*\*Stop\s+Loss\s+Level\*\*:\s+([0-9]+\.?[0-9]*)\s*\([^)]*\)',
                # Claude: "- Stop Loss: 156.20"
                r'-\s+Stop\s+Loss:\s+([0-9]+\.?[0-9]*)',
                # Claude with context: "- Stop Loss: 156.20 (+240 pips risk management)"
                r'-\s+Stop\s+Loss:\s+([0-9]+\.?[0-9]*)\s*\([^)]*\)',
                # No markdown: "Stop Loss: 1.3320"
                r'Stop\s+Loss:\s+([0-9]+\.?[0-9]*)',
                # Stop Loss Level (no markdown): "Stop Loss Level: 1.18400"
                r'Stop\s+Loss\s+Level:\s+([0-9]+\.?[0-9]*)',
                # Short form: "SL: 1.3320"
                r'SL:\s+([0-9]+\.?[0-9]*)',
            ]
            
            stop_loss = None
            for pattern in stop_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    stop_loss = float(match.group(1))
                    break
            
            # ====================================================================
            # TIMEFRAME EXTRACTION (enhanced)
            # ====================================================================
            timeframe = 'INTRADAY'
            timeframe_patterns = [
                # ChatGPT: "**TIMEFRAME CLASSIFICATION:** INTRADAY"
                r'(?:\*\s+)?\*\*TIMEFRAME\s+CLASSIFICATION\*\*:\s+(intraday|swing)',
                # ChatGPT: "**Trade Classification:** INTRADAY"
                r'(?:\*\s+)?\*\*Trade\s+Classification:\*\*\s+(intraday|swing)',
                # Claude: "1. SHORT USD/JPY (SWING TRADE)"
                r'\(SWING\s+TRADE\)',
                r'\(INTRADAY\s+TRADE\)',
                # Standard formats
                r'timeframe[-\s]?classification:\s+(intraday|swing)',
                r'trade[-\s]?classification:\s+(intraday|swing)',
                r'CLASSIFICATION:\s+(SWING\s+TRADE|INTRADAY\s+TRADE)',
                r'(intraday|swing)\s+trade',
            ]
            
            for pattern in timeframe_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Handle patterns with groups vs patterns without groups
                    if match.groups():
                        tf = match.group(1).upper()
                    else:
                        # Pattern matched but no group (e.g., "(SWING TRADE)")
                        tf = match.group(0).upper()
                    
                    if 'SWING' in tf:
                        timeframe = 'SWING'
                    elif 'INTRADAY' in tf:
                        timeframe = 'INTRADAY'
                    break
            
            # ====================================================================
            # DIRECTION EXTRACTION (enhanced)
            # ====================================================================
            direction = 'BUY'
            
            # Check header for direction (enhanced for ChatGPT and Claude formats)
            # Claude format: "1. USD/JPY SHORT (SWING Trade)" (simple format, pair first)
            if re.search(r'^\d+\.\s+[A-Z]{3}[/\s-][A-Z]{3}\s+(?:SHORT|SELL)', text, re.IGNORECASE | re.MULTILINE):
                direction = 'SELL'
            elif re.search(r'^\d+\.\s+[A-Z]{3}[/\s-][A-Z]{3}\s+(?:LONG|BUY)', text, re.IGNORECASE | re.MULTILINE):
                direction = 'BUY'
            # Claude format: "🔶 TRADE 1: USD/JPY Short" (emoji format)
            elif re.search(r'(?:🔶\s+)?TRADE\s+\d+:\s+[A-Z]{3}[/\s-][A-Z]{3}\s+(?:Short|SELL)', text, re.IGNORECASE | re.MULTILINE):
                direction = 'SELL'
            elif re.search(r'(?:🔶\s+)?TRADE\s+\d+:\s+[A-Z]{3}[/\s-][A-Z]{3}\s+(?:Long|BUY)', text, re.IGNORECASE | re.MULTILINE):
                direction = 'BUY'
            # Claude format: "1. USD/JPY SHORT TRADE" (with TRADE keyword)
            elif re.search(r'^\d+\.\s+[A-Z]{3}[/\s-][A-Z]{3}\s+(?:SHORT|SELL)\s+TRADE', text, re.IGNORECASE | re.MULTILINE):
                direction = 'SELL'
            elif re.search(r'^\d+\.\s+[A-Z]{3}[/\s-][A-Z]{3}\s+(?:LONG|BUY)\s+TRADE', text, re.IGNORECASE | re.MULTILINE):
                direction = 'BUY'
            # Standard format: "1. SHORT USD/JPY" (direction first)
            elif re.search(r'(?:Trade\s+Recommendation:\s+[A-Z]{3}[/\s-][A-Z]{3}|Trade\s+\d+:|\*\*|^\d+\.\s+)\s*(?:Short|SELL)\s+', text, re.IGNORECASE | re.MULTILINE):
                direction = 'SELL'
            elif re.search(r'(?:Trade\s+Recommendation:\s+[A-Z]{3}[/\s-][A-Z]{3}|Trade\s+\d+:|\*\*|^\d+\.\s+)\s*(?:Long|BUY)\s+', text, re.IGNORECASE | re.MULTILINE):
                direction = 'BUY'
            # Check for explicit direction keywords in the header line
            elif re.search(r'^\d+\.\s+(?:SHORT|SELL)\s+[A-Z]{3}[/\s-][A-Z]{3}', text, re.IGNORECASE | re.MULTILINE):
                direction = 'SELL'
            elif re.search(r'^\d+\.\s+(?:LONG|BUY)\s+[A-Z]{3}[/\s-][A-Z]{3}', text, re.IGNORECASE | re.MULTILINE):
                direction = 'BUY'
            # Check entry format
            elif re.search(r'Entry\s+Price\s*\(\s*(?:sell|short)\s+limit\s*\)', text, re.IGNORECASE):
                direction = 'SELL'
            elif re.search(r'Entry\s+Price\s*\(\s*(?:buy|long)\s+limit\s*\)', text, re.IGNORECASE):
                direction = 'BUY'
            # Check general keywords
            elif re.search(r'\b(?:sell|short|bearish)\b', text, re.IGNORECASE):
                direction = 'SELL'
            elif re.search(r'\b(?:buy|long|bullish)\b', text, re.IGNORECASE):
                direction = 'BUY'
            
            # ====================================================================
            # POSITION SIZE (same as before)
            # ====================================================================
            size_patterns = [
                r'position[-\s]?size[:\s]+([0-9]+\.?[0-9]*)%?',
                r'risk[:\s]+([0-9]+\.?[0-9]*)%',
            ]
            
            position_size = None
            for pattern in size_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    position_size = match.group(1)
                    break
            
            # Return opportunity if we have at least pair and direction (entry may be None for downstream fill)
            if pair and direction:
                return {
                    'pair': pair,
                    'entry': float(entry) if entry else None,
                    'exit': float(exit_price) if exit_price else None,
                    'stop_loss': float(stop_loss) if stop_loss else None,
                    'direction': direction,
                    'position_size': position_size,
                    'timeframe': timeframe,
                    'recommendation': text[:500],
                    'source': 'text_parsing'
                }
        except Exception as e:
            logger.debug(f"Error extracting from text: {e}")
        
        return None
    
    def _normalize_pair(self, pair: str) -> Optional[str]:
        """Normalize currency pair format (e.g., EURUSD -> EUR/USD)"""
        # Remove spaces and convert to uppercase
        pair = pair.replace(' ', '').replace('_', '/').upper()
        
        # If no slash, try to insert one (assuming 6 chars: EURUSD)
        if '/' not in pair and len(pair) == 6:
            pair = f"{pair[:3]}/{pair[3:]}"
        
        # Validate format: should be like "EUR/USD" or "USD/MXN"
        if '/' not in pair:
            return None
        
        parts = pair.split('/')
        if len(parts) != 2 or len(parts[0]) != 3 or len(parts[1]) != 3:
            return None
        
        # Check if it's a known pair (preferred)
        if pair in self.currency_pairs:
            return pair
        
        # Try to match partial (e.g., EURUSD matches EUR/USD)
        for known_pair in self.currency_pairs:
            if pair.replace('/', '') == known_pair.replace('/', ''):
                return known_pair
        
        # If not in known list but has valid format, accept it anyway
        # This allows exotic pairs like USD/MXN, USD/ZAR that aren't in the hardcoded list
        # Validate it's a real currency code format (3 letters)
        if parts[0].isalpha() and parts[1].isalpha() and len(parts[0]) == 3 and len(parts[1]) == 3:
            logger.debug(f"📊 Accepting currency pair not in hardcoded list: {pair}")
            return pair
        
        return None

