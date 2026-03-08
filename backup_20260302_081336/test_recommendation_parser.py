"""
Unit tests for recommendation_parser: ChatGPT format (pattern_1c), MACHINE_READABLE JSON, and fill behavior.
Run from repo root: python test_recommendation_parser.py
"""
import sys
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.recommendation_parser import RecommendationParser


def test_chatgpt_currency_pair_pair_only_bold():
    """ChatGPT actual format: ### 1. Currency Pair: **USD/JPY** (pair only in bold)."""
    text = """
### 1. Currency Pair: **USD/JPY**
- **Current Price:** 152.60800
- **Entry Price:** 152.55000 (slightly below current price)
- **Exit/Target Price:** 152.95000
- **Stop Loss:** 152.30000
- **TIMEFRAME CLASSIFICATION:** INTRADAY

### 2. Currency Pair: **GBP/USD**
- **Current Price:** 1.36289
- **Entry Price:** 1.36000
- **Exit/Target Price:** 1.36700
- **Stop Loss:** 1.35500
- **TIMEFRAME CLASSIFICATION:** INTRADAY

### 3. Currency Pair: **EUR/JPY**
- **Current Price:** 181.10050
- **Entry Price:** 181.00000
- **Exit/Target Price:** 182.00000
- **Stop Loss:** 180.50000
- **TIMEFRAME CLASSIFICATION:** SWING
"""
    parser = RecommendationParser()
    opps = parser.parse_text(text)
    pairs = [o.get("pair") for o in opps if o.get("pair")]
    assert "USD/JPY" in pairs, f"Expected USD/JPY in {pairs}"
    assert "GBP/USD" in pairs, f"Expected GBP/USD in {pairs}"
    assert "EUR/JPY" in pairs, f"Expected EUR/JPY in {pairs}"
    assert len(opps) >= 3, f"Expected at least 3 opportunities, got {len(opps)}"
    for o in opps:
        assert o.get("entry") is not None, f"Expected entry for {o.get('pair')}"
    print("test_chatgpt_currency_pair_pair_only_bold: OK")


def test_machine_readable_json():
    """MACHINE_READABLE: [...] block is parsed first."""
    text = """
Some prose analysis here.

MACHINE_READABLE: [{"pair":"USD/JPY","direction":"SELL","entry":152.6,"exit":151.9,"stop_loss":153.05},{"pair":"GBP/JPY","direction":"SELL","entry":208.0,"exit":207.2,"stop_loss":208.5}]
"""
    parser = RecommendationParser()
    opps = parser.parse_text(text)
    pairs = [o.get("pair") for o in opps if o.get("pair")]
    assert "USD/JPY" in pairs, f"Expected USD/JPY in {pairs}"
    assert "GBP/JPY" in pairs, f"Expected GBP/JPY in {pairs}"
    assert len(opps) == 2, f"Expected 2 opportunities from JSON, got {len(opps)}"
    assert opps[0].get("entry") == 152.6
    print("test_machine_readable_json: OK")


def test_synthesis_format():
    """Gemini Final format: *   **Currency Pair:** GBP/JPY with Entry Price (Sell Limit)."""
    text = """
#### **Trade 1: High Conviction - Sell GBP/JPY**
*   **Currency Pair:** GBP/JPY
*   **Entry Price (Sell Limit):** **209.500**
*   **Exit/Target Price:** **207.500**
*   **Stop Loss:** **210.500**

#### **Trade 2: Confirmed Setup - Sell USD/JPY**
*   **Currency Pair:** USD/JPY
*   **Entry Price (Sell Limit):** **153.300**
*   **Exit/Target Price:** **152.700**
*   **Stop Loss:** **153.750**
"""
    parser = RecommendationParser()
    opps = parser.parse_text(text)
    pairs = [o.get("pair") for o in opps if o.get("pair")]
    assert "GBP/JPY" in pairs, f"Expected GBP/JPY in {pairs}"
    assert "USD/JPY" in pairs, f"Expected USD/JPY in {pairs}"
    assert len(opps) >= 2, f"Expected at least 2 opportunities, got {len(opps)}"
    print("test_synthesis_format: OK")


def test_opportunities_with_missing_entry_included():
    """Parser includes opportunities with pair/direction but missing entry (for downstream fill)."""
    # Section that has pair and direction but no Entry line (e.g. malformed)
    text = """
### 1. Currency Pair: **EUR/USD**
- **Current Price:** 1.18857
- **Exit/Target Price:** 1.1940
- **Stop Loss:** 1.1850
(no Entry line)
"""
    parser = RecommendationParser()
    opps = parser.parse_text(text)
    # Parser should still return the opportunity (entry may be None or from Current Price fallback)
    assert len(opps) >= 1, f"Expected at least 1 opportunity (with or without entry), got {len(opps)}"
    assert any(o.get("pair") == "EUR/USD" for o in opps), f"Expected EUR/USD in {[o.get('pair') for o in opps]}"
    print("test_opportunities_with_missing_entry_included: OK")


if __name__ == "__main__":
    test_chatgpt_currency_pair_pair_only_bold()
    test_machine_readable_json()
    test_synthesis_format()
    test_opportunities_with_missing_entry_included()
    print("All parser tests passed.")
