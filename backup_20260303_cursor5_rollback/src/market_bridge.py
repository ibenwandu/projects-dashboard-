"""
Market Bridge: Exports market state for Scalp-Engine
Bridges the slow 'Trade-Alerts' analysis with the fast 'Scalp-Engine'
Supports Render shared disk for seamless integration
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from src.logger import setup_logger

logger = setup_logger()

# Try to import requests for API communication
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("⚠️ requests library not available - API communication disabled")

class MarketBridge:
    """Bridges Trade-Alerts analysis to Scalp-Engine"""
    
    def __init__(self, filename: str = "market_state.json"):
        """
        Initialize market bridge
        
        Args:
            filename: Name of the state file (default: market_state.json)
        """
        self.filename = filename  # Store filename for fallback path
        # Check for Render shared disk path (for Scalp-Engine integration)
        render_shared_path = os.getenv('MARKET_STATE_FILE_PATH')
        if render_shared_path:
            # Use the shared disk path if configured
            self.filepath = Path(render_shared_path)
            logger.info(f"MarketBridge initialized with shared disk path: {self.filepath}")
        else:
            # Default: Save in the root directory so Scalp Engine can find it easily
            current_dir = Path(__file__).parent.parent
            self.filepath = current_dir / filename
            logger.info(f"MarketBridge initialized with local path: {self.filepath}")
        
        # API configuration (for Scalp-Engine integration)
        self.api_url = os.getenv('MARKET_STATE_API_URL')
        self.api_key = os.getenv('MARKET_STATE_API_KEY')
        if self.api_url:
            logger.info(f"MarketBridge API configured: {self.api_url}")
        else:
            logger.info("MarketBridge API not configured (MARKET_STATE_API_URL not set)")
    
    def _calculate_usd_exposure(self, pair: str, direction: str) -> Optional[str]:
        """
        Calculate whether a trade opportunity is bullish or bearish on USD
        
        This properly handles USD as base currency (USD/JPY) vs quote currency (EUR/USD):
        - USD as base (USD/JPY): LONG = buying USD = bullish USD
        - USD as quote (EUR/USD): LONG = buying base, selling USD = bearish USD
        
        Args:
            pair: Currency pair (e.g., "EUR/USD", "USD/JPY", "EURUSD")
            direction: Trade direction ("LONG", "SHORT", "BUY", "SELL")
        
        Returns:
            "BULLISH" if trade is bullish on USD
            "BEARISH" if trade is bearish on USD
            None if USD not in pair
        """
        # Normalize pair format (handle EUR/USD, EURUSD, EUR-USD)
        pair_normalized = pair.replace('/', '').replace('-', '').upper()
        
        # Check if USD is in pair
        if 'USD' not in pair_normalized:
            return None  # Non-USD pair (e.g., EUR/GBP)
        
        # Normalize direction
        direction_upper = direction.upper()
        
        # Determine if USD is base or quote currency
        if pair_normalized.startswith('USD'):
            # USD is base currency (e.g., USDJPY, USDCAD, USDCHF)
            # LONG = buying USD = bullish USD
            # SHORT = selling USD = bearish USD
            if direction_upper in ['LONG', 'BUY']:
                return "BULLISH"
            elif direction_upper in ['SHORT', 'SELL']:
                return "BEARISH"
        else:
            # USD is quote currency (e.g., EURUSD, GBPUSD, NZDUSD)
            # LONG = buying base currency, selling USD = bearish USD
            # SHORT = selling base currency, buying USD = bullish USD
            if direction_upper in ['LONG', 'BUY']:
                return "BEARISH"
            elif direction_upper in ['SHORT', 'SELL']:
                return "BULLISH"
        
        return None
    
    def export_market_state(
        self,
        opportunities: List[Dict],
        synthesized_text: str,
        llm_weights: Optional[Dict[str, float]] = None,
        llm_recommendations: Optional[Dict] = None,
        all_opportunities: Optional[Dict[str, List[Dict]]] = None
    ) -> Dict:
        """
        Converts complex LLM analysis into a simple 'Battle Plan' for the scalper.
        
        Args:
            opportunities: List of trading opportunities from parser
            synthesized_text: Final synthesized text from Gemini
            
        Returns:
            Market state dictionary
        """
        
        # 1. Determine Global Bias (USD-Normalized)
        # Convert all opportunities to USD exposure before calculating bias
        # This properly handles USD as base currency (USD/JPY) vs quote currency (EUR/USD)
        
        # Calculate USD-normalized bias
        usd_bullish_count = 0
        usd_bearish_count = 0
        non_usd_count = 0
        long_count = 0  # Keep for backward compatibility
        short_count = 0  # Keep for backward compatibility
        
        for op in opportunities:
            try:
                pair = op.get('pair', '')
                direction = op.get('direction', '').upper()
                
                # Skip if missing required fields
                if not pair or not direction:
                    non_usd_count += 1
                    continue
                
                # Track old counts for backward compatibility
                if direction in ['BUY', 'LONG']:
                    long_count += 1
                elif direction in ['SELL', 'SHORT']:
                    short_count += 1
                
                # Calculate USD exposure (with error handling)
                try:
                    usd_exposure = self._calculate_usd_exposure(pair, direction)
                    
                    if usd_exposure == "BULLISH":
                        usd_bullish_count += 1
                    elif usd_exposure == "BEARISH":
                        usd_bearish_count += 1
                    else:
                        non_usd_count += 1  # Non-USD pair (e.g., EUR/GBP)
                except Exception as e:
                    # If USD exposure calculation fails, treat as non-USD
                    logger.warning(f"Error calculating USD exposure for {pair} {direction}: {e}")
                    non_usd_count += 1
            except Exception as e:
                # Skip this opportunity if processing fails
                logger.warning(f"Error processing opportunity: {e}")
                continue
        
        # Calculate bias based on USD exposure
        if usd_bullish_count > usd_bearish_count:
            global_bias = "BULLISH"
        elif usd_bearish_count > usd_bullish_count:
            global_bias = "BEARISH"
        else:
            global_bias = "NEUTRAL"
        
        # Log USD-normalized bias calculation
        logger.info(
            f"📊 Global Bias (USD-Normalized): {global_bias} "
            f"(USD Bullish: {usd_bullish_count}, USD Bearish: {usd_bearish_count}, "
            f"Non-USD: {non_usd_count}, Total: {len(opportunities)})"
        )
        
        # 2. Extract Approved Pairs
        approved_pairs = list(set([op.get('pair', '') for op in opportunities if op.get('pair')]))
        
        # 3. Determine Volatility Regime (Heuristic based on keywords in Gemini text)
        regime = "NORMAL"
        if synthesized_text:
            text_upper = synthesized_text.upper()
            if "VOLATILITY" in text_upper or "CAUTION" in text_upper or "RISK OFF" in text_upper or "HIGH VOLATILITY" in text_upper:
                regime = "HIGH_VOL"
            elif "RANGING" in text_upper or "CHOPPY" in text_upper or "SIDEWAYS" in text_upper:
                regime = "RANGING"
            elif "TREND" in text_upper or "BREAKOUT" in text_upper or "MOMENTUM" in text_upper:
                regime = "TRENDING"
        
        # 3.5. Enhance opportunities with consensus information
        enhanced_opportunities = self._enhance_opportunities_with_consensus(
            opportunities, synthesized_text, llm_recommendations, all_opportunities
        )
        
        # 4. Construct the Battle Plan
        # consol-recommend4 Phase 2.1: global denominator for consensus display (LLMs that contributed this run)
        available_llm_count = (
            enhanced_opportunities[0].get('available_llm_count', 4) if enhanced_opportunities else 4
        )
        state = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "global_bias": global_bias,
            "regime": regime,
            "approved_pairs": approved_pairs,
            "opportunities": enhanced_opportunities,  # Use enhanced opportunities with consensus
            "available_llm_count": available_llm_count,
            # USD-normalized bias counts (new)
            "usd_bullish_count": usd_bullish_count,
            "usd_bearish_count": usd_bearish_count,
            "non_usd_pairs_count": non_usd_count,
            # Legacy counts (deprecated, kept for backward compatibility)
            "long_count": long_count,
            "short_count": short_count,
            "total_opportunities": len(opportunities),
            "llm_weights": llm_weights if llm_weights else {
                'chatgpt': 0.2,
                'gemini': 0.2,
                'claude': 0.2,
                'deepseek': 0.2,
                'synthesis': 0.2
            }  # Default weights (5-way: chatgpt, gemini, claude, deepseek, synthesis)
        }
        
        # DEBUG: Log what's being written to market state
        logger.info(f"🔍 [MARKET-STATE-DEBUG] Writing {len(enhanced_opportunities)} opportunities to market state:")
        for idx, opp in enumerate(enhanced_opportunities):
            logger.info(f"   Opp #{idx}: {opp.get('pair')} {opp.get('direction')} - consensus_level={opp.get('consensus_level')}, llm_sources={opp.get('llm_sources')}")
        
        # 5. Write to file, then push to API
        self._write_to_file(state)
        self._send_to_api(state)
        return state
    
    def _write_to_file(self, state: Dict) -> bool:
        """
        Write market state to JSON file on disk using atomic writes (temp file + rename).

        Returns True on success, False on failure (fallback attempted if on shared disk).
        """
        import tempfile
        import shutil

        try:
            # Validate JSON serializability before attempting write
            try:
                json_str = json.dumps(state, indent=4)
            except (ValueError, TypeError) as e:
                logger.error(f"❌ State contains non-serializable data: {e}")
                # Try to sanitize the state
                state = self._sanitize_state(state)
                json_str = json.dumps(state, indent=4)

            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Attempting to export market state to {self.filepath}")

            # Atomic write: write to temp file first, then rename
            # This prevents file corruption if write is interrupted
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json',
                prefix='market_state_',
                dir=str(self.filepath.parent),
                text=True
            )

            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(json_str)

                # Atomic rename (on same filesystem, this is atomic)
                shutil.move(temp_path, str(self.filepath))

                logger.info(f"✅ Market State exported to {self.filepath}")
                logger.info(f"   Bias: {state.get('global_bias')}, Regime: {state.get('regime')}, Pairs: {state.get('approved_pairs')}")
                return True
            except Exception as e:
                # Clean up temp file if rename failed
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise

        except (PermissionError, OSError) as e:
            logger.error(f"❌ Failed to write market state to {self.filepath}: {e}")
            if str(self.filepath).startswith('/var/data'):
                logger.error("   Check disk mount permissions and MARKET_STATE_FILE_PATH environment variable")
                try:
                    fallback_path = Path(__file__).parent.parent / self.filename
                    logger.info(f"Attempting fallback export to {fallback_path}")
                    fallback_path.parent.mkdir(parents=True, exist_ok=True)

                    # Also use atomic writes for fallback
                    temp_fd, temp_path = tempfile.mkstemp(
                        suffix='.json',
                        prefix='market_state_',
                        dir=str(fallback_path.parent),
                        text=True
                    )
                    try:
                        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                            f.write(json_str)
                        shutil.move(temp_path, str(fallback_path))
                        logger.warning(f"⚠️ Market State exported to fallback location: {fallback_path}")
                        logger.warning("   This file may not be accessible to Scalp-Engine. Check disk mounting.")
                        return True
                    except Exception as e2:
                        try:
                            os.unlink(temp_path)
                        except Exception:
                            pass
                        raise e2
                except Exception as e2:
                    logger.error(f"❌ Fallback export also failed: {e2}", exc_info=True)
            return False

    def _sanitize_state(self, state: Dict) -> Dict:
        """
        Sanitize state to remove non-serializable values (NaN, Infinity, etc.)

        Args:
            state: State dictionary potentially containing invalid JSON values

        Returns:
            Sanitized state dictionary
        """
        import math

        def sanitize_value(value):
            """Recursively sanitize a value"""
            if isinstance(value, float):
                # Replace NaN and Infinity with None (null in JSON)
                if math.isnan(value) or math.isinf(value):
                    logger.warning(f"Sanitizing invalid float value: {value}")
                    return None
                return value
            elif isinstance(value, dict):
                return {k: sanitize_value(v) for k, v in value.items()}
            elif isinstance(value, (list, tuple)):
                return [sanitize_value(v) for v in value]
            return value

        return sanitize_value(state)

    def _send_to_api(self, state: Dict) -> bool:
        """
        Send market state to Scalp-Engine API
        
        Args:
            state: Market state dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.api_url:
            # API not configured - this is OK, just log it
            return False
        
        if not REQUESTS_AVAILABLE:
            logger.warning("⚠️ requests library not available - cannot send to API")
            return False
        
        try:
            # Prepare headers
            headers = {'Content-Type': 'application/json'}
            if self.api_key and self.api_key != 'change-me-in-production':
                headers['X-API-Key'] = self.api_key
            
            # Send POST request
            logger.info(f"Sending market state to API: {self.api_url}")
            response = requests.post(
                self.api_url,
                json=state,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Market state sent to API successfully")
                logger.info(f"   API response: {response.json().get('message', 'OK')}")
                return True
            else:
                logger.warning(f"⚠️ API returned status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ API request timeout (service may be unavailable)")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"⚠️ API connection error: {e} (service may be unavailable)")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Error sending to API: {e}", exc_info=True)
            return False
    
    def merge_opportunities_from_all_llms(
        self,
        all_opportunities: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """
        Merge opportunities from all LLMs, keeping unique pairs and selecting best entry price
        
        Args:
            all_opportunities: Dict mapping LLM name to list of opportunities
                e.g., {'chatgpt': [...], 'gemini': [...], 'claude': [...], 'synthesis': [...]}
        
        Returns:
            Merged list of unique opportunities with best entry prices
        """
        # Create a map: (pair, direction) -> best opportunity
        opportunity_map = {}
        
        for llm_name, opps in all_opportunities.items():
            if not opps:
                continue
            
            for opp in opps:
                pair = opp.get('pair', '').upper()
                direction = opp.get('direction', '').upper()
                entry = opp.get('entry')  # May be None if fill step missed this pair
                if entry is None:
                    entry = 0.0
                else:
                    try:
                        entry = float(entry)
                    except (TypeError, ValueError):
                        entry = 0.0
                
                if not pair or not direction or entry <= 0:
                    continue
                
                # Create key: (pair, direction)
                key = (pair, direction)
                
                # Determine if this entry price is "better"
                # For LONG/BUY: lower entry is better (buy cheaper)
                # For SHORT/SELL: higher entry is better (sell higher)
                is_better = False
                if key not in opportunity_map:
                    is_better = True
                else:
                    existing_entry = opportunity_map[key].get('entry', 0.0)
                    if direction in ['LONG', 'BUY']:
                        # Lower entry is better for long
                        is_better = entry < existing_entry
                    else:  # SHORT or SELL
                        # Higher entry is better for short
                        is_better = entry > existing_entry
                
                if is_better:
                    # Create a copy and add LLM source
                    new_opp = opp.copy()
                    new_opp['source_llm'] = llm_name
                    opportunity_map[key] = new_opp
        
        # Convert map to list
        merged_opportunities = list(opportunity_map.values())
        
        # Per-LLM contribution (how many merged opps came from each source)
        source_counts = {}
        for opp in merged_opportunities:
            src = opp.get('source_llm', 'unknown')
            source_counts[src] = source_counts.get(src, 0) + 1
        contrib = ", ".join(f"{k}: {v}" for k, v in sorted(source_counts.items()))
        
        logger.info(
            f"📊 Merged opportunities: {len(merged_opportunities)} unique pairs "
            f"(from {sum(len(opps) for opps in all_opportunities.values())} total recommendations). "
            f"Per-LLM: {contrib}"
        )
        
        return merged_opportunities
    
    def _enhance_opportunities_with_consensus(
        self, 
        opportunities: List[Dict],
        synthesis_text: str,
        llm_recommendations: Optional[Dict] = None,
        all_opportunities: Optional[Dict[str, List[Dict]]] = None
    ) -> List[Dict]:
        """
        Enhance opportunities with consensus information
        
        This analyzes which LLMs agree on each opportunity
        """
        # Log what we have for debugging
        if all_opportunities:
            logger.info(f"📊 Consensus calculation: {len(opportunities)} merged opportunities to analyze")
            for llm_name, opps in all_opportunities.items():
                logger.info(f"   {llm_name}: {len(opps)} parsed opportunities")
        else:
            logger.warning("⚠️ No all_opportunities provided - consensus will use fallback methods")
        
        # consol-recommend4 Phase 2.1: available_llm_count = LLMs that contributed this run (display denominator)
        base_llms = ['chatgpt', 'gemini', 'claude', 'deepseek']
        available_llm_count = sum(
            1 for llm in base_llms
            if all_opportunities and all_opportunities.get(llm)
        ) if all_opportunities else 4
        if available_llm_count == 0:
            available_llm_count = 4
        
        enhanced = []
        
        for opp in opportunities:
            # Create enhanced copy
            enhanced_opp = opp.copy()
            
            # Determine consensus level by analyzing actual LLM recommendations
            consensus_info = self._analyze_consensus_for_pair(
                opp['pair'], 
                opp['direction'],
                synthesis_text,
                llm_recommendations,
                all_opportunities
            )
            
            enhanced_opp['consensus_level'] = consensus_info['level']
            enhanced_opp['llm_sources'] = consensus_info['sources']
            enhanced_opp['available_llm_count'] = available_llm_count  # display denominator (consol-recommend4 Phase 2.1)
            enhanced_opp['id'] = f"{opp['pair']}_{opp['direction']}_{opp['entry']}"
            
            # DEBUG: Log what was set
            logger.info(f"🔍 [CONSENSUS-DEBUG] Enhanced opportunity for {opp['pair']} {opp['direction']}:")
            logger.info(f"   consensus_level: {enhanced_opp['consensus_level']}")
            logger.info(f"   llm_sources: {enhanced_opp['llm_sources']}")
            logger.info(f"   llm_sources count: {len(enhanced_opp['llm_sources'])}")
            logger.info(f"   base LLMs in sources (excluding synthesis): {[s for s in enhanced_opp['llm_sources'] if s.lower() != 'synthesis']}")
            
            enhanced.append(enhanced_opp)
        
        return enhanced
    
    def _analyze_consensus_for_pair(
        self, 
        pair: str, 
        direction: str, 
        synthesis_text: str,
        llm_recommendations: Optional[Dict] = None,
        all_opportunities: Optional[Dict[str, List[Dict]]] = None
    ) -> Dict:
        """
        Analyze which LLMs agree on a specific pair/direction
        
        Priority:
        1. Use already-parsed opportunities (most reliable)
        2. Use actual LLM recommendations text (fallback)
        3. Use synthesis text parsing (last resort)
        """
        logger.info(f"🔍 [CONSENSUS-DEBUG] Starting consensus analysis for {pair} {direction}")
        logger.info(f"   Input: pair='{pair}', direction='{direction}'")
        logger.info(f"   all_opportunities keys: {list(all_opportunities.keys()) if all_opportunities else 'None'}")
        
        base_llms = ['chatgpt', 'gemini', 'claude', 'deepseek']
        sources = []
        base_llm_sources = []
        
        # Method 1: Use already-parsed opportunities (MOST RELIABLE)
        if all_opportunities:
            pair_clean = pair.replace('/', '').upper()
            pair_with_slash = pair.upper()
            direction_upper = direction.upper()
            
            logger.info(f"   Normalized: pair_clean='{pair_clean}', pair_with_slash='{pair_with_slash}', direction_upper='{direction_upper}'")
            
            # Normalize direction
            if direction_upper in ['BUY', 'LONG']:
                target_directions = ['BUY', 'LONG']
            else:  # SELL or SHORT
                target_directions = ['SELL', 'SHORT']
            
            logger.info(f"   Target directions for matching: {target_directions}")
            
            # Check each base LLM's parsed opportunities
            for llm_name in base_llms:
                if llm_name not in all_opportunities or not all_opportunities[llm_name]:
                    logger.info(f"   ❌ {llm_name}: No opportunities found (parser may have failed)")
                    continue
                
                logger.info(f"   🔎 {llm_name}: Checking {len(all_opportunities[llm_name])} opportunities")
                
                llm_matched = False
                # Check if this LLM has a matching opportunity
                for idx, opp in enumerate(all_opportunities[llm_name]):
                    opp_pair_raw = opp.get('pair', '')
                    opp_pair = opp_pair_raw.upper().replace('/', '').replace('-', '')
                    opp_direction = opp.get('direction', '').upper()
                    
                    logger.debug(f"      [{llm_name}] Opp #{idx}: pair='{opp_pair_raw}' -> '{opp_pair}', direction='{opp_direction}'")
                    
                    # Normalize pair for comparison (remove slashes, dashes, spaces)
                    pair_clean_normalized = pair_clean.replace('-', '')
                    pair_with_slash_normalized = pair_with_slash.replace('/', '').replace('-', '').upper()
                    
                    # Check if pair matches (handle multiple formats)
                    pair_matches = (
                        opp_pair == pair_clean_normalized or
                        opp_pair == pair_with_slash_normalized or
                        opp_pair_raw.upper().replace('/', '').replace('-', '') == pair_clean_normalized or
                        opp_pair_raw.upper().replace('/', '').replace('-', '') == pair_with_slash_normalized
                    )
                    
                    # Check if direction matches (more flexible)
                    direction_matches = (
                        opp_direction in target_directions or
                        (direction_upper in ['BUY', 'LONG'] and opp_direction in ['BUY', 'LONG']) or
                        (direction_upper in ['SELL', 'SHORT'] and opp_direction in ['SELL', 'SHORT']) or
                        (direction_upper == 'BUY' and opp_direction == 'LONG') or
                        (direction_upper == 'LONG' and opp_direction == 'BUY') or
                        (direction_upper == 'SELL' and opp_direction == 'SHORT') or
                        (direction_upper == 'SHORT' and opp_direction == 'SELL')
                    )
                    
                    logger.debug(f"      [{llm_name}] Opp #{idx}: pair_matches={pair_matches}, direction_matches={direction_matches}")
                    logger.debug(f"         Comparing: '{opp_pair}' vs '{pair_clean_normalized}' or '{pair_with_slash_normalized}'")
                    logger.debug(f"         Comparing: '{opp_direction}' vs {target_directions}")
                    
                    if pair_matches and direction_matches:
                        if llm_name not in base_llm_sources:
                            base_llm_sources.append(llm_name)
                            logger.info(f"   ✅ [{llm_name}] MATCHED! Added to base_llm_sources. Current: {base_llm_sources}")
                        if llm_name not in sources:
                            sources.append(llm_name)
                            logger.info(f"   ✅ [{llm_name}] Added to sources. Current: {sources}")
                        logger.info(f"✅ Consensus: {llm_name} agrees on {pair} {direction} (matched: {opp_pair_raw} {opp_direction})")
                        llm_matched = True
                        break  # Found match for this LLM, move to next
                    else:
                        if not pair_matches:
                            logger.debug(f"      [{llm_name}] Opp #{idx}: PAIR MISMATCH - '{opp_pair}' != '{pair_clean_normalized}' and != '{pair_with_slash_normalized}'")
                        if not direction_matches:
                            logger.debug(f"      [{llm_name}] Opp #{idx}: DIRECTION MISMATCH - '{opp_direction}' not in {target_directions}")
                
                if not llm_matched:
                    logger.info(f"   ❌ {llm_name}: NO MATCH found after checking {len(all_opportunities[llm_name])} opportunities")
            
            # Check synthesis opportunities
            if 'synthesis' in all_opportunities and all_opportunities['synthesis']:
                for opp in all_opportunities['synthesis']:
                    opp_pair_raw = opp.get('pair', '')
                    opp_pair = opp_pair_raw.upper().replace('/', '').replace('-', '')
                    opp_direction = opp.get('direction', '').upper()
                    
                    # Normalize pair for comparison
                    pair_clean_normalized = pair_clean.replace('-', '')
                    pair_with_slash_normalized = pair_with_slash.replace('/', '').replace('-', '').upper()
                    
                    pair_matches = (
                        opp_pair == pair_clean_normalized or
                        opp_pair == pair_with_slash_normalized or
                        opp_pair_raw.upper().replace('/', '').replace('-', '') == pair_clean_normalized or
                        opp_pair_raw.upper().replace('/', '').replace('-', '') == pair_with_slash_normalized
                    )
                    
                    direction_matches = (
                        opp_direction in target_directions or
                        (direction_upper in ['BUY', 'LONG'] and opp_direction in ['BUY', 'LONG']) or
                        (direction_upper in ['SELL', 'SHORT'] and opp_direction in ['SELL', 'SHORT']) or
                        (direction_upper == 'BUY' and opp_direction == 'LONG') or
                        (direction_upper == 'LONG' and opp_direction == 'BUY') or
                        (direction_upper == 'SELL' and opp_direction == 'SHORT') or
                        (direction_upper == 'SHORT' and opp_direction == 'SELL')
                    )
                    
                    if pair_matches and direction_matches:
                        if 'synthesis' not in sources:
                            sources.append('synthesis')
                        break
        
        # Method 2: Use actual LLM recommendations text (fallback if parsed opportunities not available)
        if not base_llm_sources and llm_recommendations:
            pair_clean = pair.replace('/', '').replace('-', '').replace(' ', '').upper()
            pair_with_slash = pair.upper().replace('-', '/')
            # Ensure we have slash form for text search (LLM text usually has "EUR/USD")
            if '/' not in pair_with_slash and len(pair_clean) == 6:
                pair_with_slash = f"{pair_clean[:3]}/{pair_clean[3:]}"
            direction_upper = direction.upper()
            
            # Normalize direction keywords (include common variants)
            if direction_upper in ['BUY', 'LONG']:
                buy_keywords = ['BUY', 'LONG', 'GO LONG', 'LONG POSITION', 'ENTRY PRICE (BUY LIMIT)', 'ENTRY PRICE (BUY)', 'BUY (LONG)', 'TRADE: BUY', 'LONG TRADE']
                sell_keywords = []  # Exclude sell keywords
            else:  # SELL or SHORT
                buy_keywords = []  # Exclude buy keywords
                sell_keywords = ['SELL', 'SHORT', 'GO SHORT', 'SHORT POSITION', 'ENTRY PRICE (SELL LIMIT)', 'ENTRY PRICE (SELL)', 'SELL (SHORT)', 'TRADE: SELL', 'SHORT TRADE']
            
            # Check each base LLM's recommendations
            for llm_name in base_llms:
                if llm_name not in llm_recommendations or not llm_recommendations[llm_name]:
                    continue
                
                llm_text = llm_recommendations[llm_name]
                llm_text_upper = llm_text.upper()
                
                # Look for the pair in various formats (must include slash form; LLM text often has "EUR/USD")
                pair_patterns = [pair_with_slash, pair_clean]
                pair_found = False
                for pattern in pair_patterns:
                    if pattern and pattern in llm_text_upper:
                        pair_found = True
                        break
                
                if pair_found:
                    # Find position using whichever form appears in text (critical: text often has "EUR/USD" not "EURUSD")
                    pair_pos = -1
                    for pattern in [pair_with_slash, pair_clean]:
                        if pattern in llm_text_upper:
                            pair_pos = llm_text_upper.find(pattern)
                            break
                    
                    # Check if direction matches
                    direction_match = False
                    if pair_pos >= 0:
                        context_start = max(0, pair_pos - 300)
                        context_end = min(len(llm_text_upper), pair_pos + 300)
                        context = llm_text_upper[context_start:context_end]
                        if direction_upper in ['BUY', 'LONG']:
                            has_buy = any(kw in context for kw in buy_keywords)
                            has_sell = any(kw in context for kw in sell_keywords) if sell_keywords else False
                            if has_buy and not has_sell:
                                direction_match = True
                        else:  # SELL or SHORT
                            has_sell = any(kw in context for kw in sell_keywords)
                            has_buy = any(kw in context for kw in buy_keywords) if buy_keywords else False
                            if has_sell and not has_buy:
                                direction_match = True
                    
                    if direction_match:
                        if llm_name not in base_llm_sources:
                            base_llm_sources.append(llm_name)
                        if llm_name not in sources:
                            sources.append(llm_name)
            
            # Always include synthesis if it made it to final recommendations
            if synthesis_text:
                synthesis_upper = synthesis_text.upper()
                pair_in_synthesis = pair_clean in synthesis_upper or pair_with_slash in synthesis_upper
                if pair_in_synthesis:
                    # Check direction in synthesis
                    if direction_upper in ['BUY', 'LONG']:
                        has_buy = any(kw in synthesis_upper for kw in ['BUY', 'LONG', 'ENTRY PRICE (BUY LIMIT)'])
                        if has_buy and 'synthesis' not in sources:
                            sources.append('synthesis')
                    else:
                        has_sell = any(kw in synthesis_upper for kw in ['SELL', 'SHORT', 'ENTRY PRICE (SELL LIMIT)'])
                        if has_sell and 'synthesis' not in sources:
                            sources.append('synthesis')
        
        # Method 3: Fallback to text parsing if no parsed opportunities or LLM recommendations available
        if not base_llm_sources and synthesis_text:
            text_lower = synthesis_text.lower()
            pair_clean_lower = pair.replace('/', '').lower()
            
            # Check if this is in final synthesis (highest confidence)
            if pair_clean_lower in text_lower:
                # If it made it to synthesis, at least Gemini agrees
                base_llm_sources.append('gemini')
                sources.append('gemini')
                
                # Check for explicit mentions of agreement
                if 'all' in text_lower and ('agree' in text_lower or 'three' in text_lower or 'unanimous' in text_lower):
                    base_llm_sources = ['chatgpt', 'gemini', 'claude', 'deepseek']
                    sources = ['chatgpt', 'gemini', 'claude', 'deepseek']
                elif 'consensus' in text_lower or 'both' in text_lower or 'two' in text_lower:
                    # At least 2 agree - try to identify which ones
                    if 'chatgpt' in text_lower:
                        if 'chatgpt' not in base_llm_sources:
                            base_llm_sources.append('chatgpt')
                            sources.append('chatgpt')
                    if 'claude' in text_lower:
                        if 'claude' not in base_llm_sources:
                            base_llm_sources.append('claude')
                            sources.append('claude')
                    if 'deepseek' in text_lower:
                        if 'deepseek' not in base_llm_sources:
                            base_llm_sources.append('deepseek')
                            sources.append('deepseek')
                
                # Always add synthesis
                if 'synthesis' not in sources:
                    sources.append('synthesis')
        
        # Ensure sources is not empty
        if not sources:
            sources = ['synthesis']
        
        # Calculate consensus level: count of base LLMs only (1, 2, 3, or 4)
        # Don't count synthesis toward consensus level
        consensus_level = len(base_llm_sources)
        
        # Log consensus detection results with detailed debug info
        logger.info(f"📊 [CONSENSUS-DEBUG] Consensus calculation complete for {pair} {direction}:")
        logger.info(f"   base_llm_sources: {base_llm_sources} (count: {len(base_llm_sources)})")
        logger.info(f"   all sources: {sources} (count: {len(sources)})")
        logger.info(f"   consensus_level: {consensus_level}/4")
        logger.info(f"📊 Consensus for {pair} {direction}: {consensus_level}/4 (sources: {base_llm_sources}, all sources: {sources})")
        
        # Ensure consensus_level is between 1 and 4
        if consensus_level == 0:
            # If no base LLMs found but synthesis exists, check synthesis text for consensus hints
            if synthesis_text and 'synthesis' in sources:
                synthesis_lower = synthesis_text.lower()
                pair_lower = pair.lower().replace('/', '').replace('-', '')
                
                # Check if synthesis mentions this pair and multiple LLMs agreeing
                if pair_lower in synthesis_lower:
                    # Look for consensus indicators in synthesis text
                    # Check for "all three", "all agree", "unanimous" near the pair mention
                    pair_context_start = max(0, synthesis_lower.find(pair_lower) - 200)
                    pair_context_end = min(len(synthesis_lower), synthesis_lower.find(pair_lower) + 200)
                    pair_context = synthesis_lower[pair_context_start:pair_context_end]
                    
                    # Check for explicit mentions of LLM names agreeing
                    llm_mentions = []
                    if 'chatgpt' in pair_context or 'gpt' in pair_context:
                        llm_mentions.append('chatgpt')
                    if 'gemini' in pair_context:
                        llm_mentions.append('gemini')
                    if 'claude' in pair_context:
                        llm_mentions.append('claude')
                    if 'deepseek' in pair_context:
                        llm_mentions.append('deepseek')
                    
                    # Count how many LLMs are mentioned
                    if len(llm_mentions) >= 3 or any(keyword in pair_context for keyword in ['all agree', 'unanimous', 'all three', 'all 3', 'all four', 'all 4', 'consensus', 'converge', 'all analysts', 'all ai']):
                        # If synthesis mentions 3+ LLMs or consensus keywords, cap at 4
                        consensus_level = min(4, max(3, len(llm_mentions)))
                        logger.info(f"   💡 Synthesis text suggests LLMs agree - setting to {consensus_level}/4 (mentioned: {llm_mentions})")
                    elif len(llm_mentions) >= 2 or any(keyword in pair_context for keyword in ['both', 'two', '2 llm', 'chatgpt and gemini', 'gemini and claude', 'chatgpt and claude', 'two agree', 'both recommend']):
                        consensus_level = 2
                        logger.info(f"   💡 Synthesis text suggests 2 LLMs agree - setting to 2/4 (mentioned: {llm_mentions})")
                    else:
                        # Default to 1 if synthesis exists but no consensus indicators
                        consensus_level = 1
                        logger.info(f"   ⚠️ No base LLM matches found, defaulting to 1/4 (synthesis only)")
                else:
                    # Synthesis exists but doesn't mention this pair - still count as 1
                    consensus_level = 1
                    logger.info(f"   ⚠️ Synthesis exists but doesn't mention {pair}, defaulting to 1/4")
            elif 'synthesis' in sources:
                # Synthesis is in sources but no text available - default to 1
                consensus_level = 1
                logger.info(f"   ⚠️ Synthesis in sources but no text, defaulting to 1/4")
            else:
                consensus_level = 1
                logger.warning(f"   ⚠️ No consensus detected - defaulting to 1/4")
        elif consensus_level > 4:
            consensus_level = 4
        
        return {
            'level': consensus_level,
            'sources': sources
        }
