# RL Parser Enhancements

## Summary

Enhanced the recommendation parser to extract trade recommendations from various text formats, including free-form text that doesn't follow the structured section format.

## Changes Made

### 1. Enhanced Text Parser (`_parse_freeform_recommendations`)
- Now extracts recommendations from free-form text without requiring structured sections
- Looks for currency pairs (e.g., EUR/USD, GBP/JPY) followed by direction keywords (LONG, SHORT, BUY, SELL)
- Automatically detects LLM source from context (ChatGPT, Gemini, Claude)
- Extracts entry prices, stop loss, and take profit levels from surrounding text

### 2. Improved Price Extraction (`_extract_price`)
- Enhanced to handle multiple price formats:
  - "Entry Price: 1.0850"
  - "EUR/USD at 1.0850"
  - "EUR/USD 1.0850"
- Validates prices are in reasonable forex range (0.5-1000)

### 3. Flexible Section Detection
- Parser now tries multiple section name variations:
  - "CHATGPT RECOMMENDATIONS", "CHATGPT", "OPENAI", "GPT"
  - "GEMINI RECOMMENDATIONS", "GEMINI", "GOOGLE"
  - "CLAUDE RECOMMENDATIONS", "CLAUDE", "ANTHROPIC"
  - "GEMINI FINAL RECOMMENDATION", "FINAL RECOMMENDATION", "SYNTHESIS"

### 4. Dual Format Saving (`_save_recommendations_to_file`)
- Trade-Alerts now saves recommendations in **both** formats:
  - `.txt` file: Human-readable format (backward compatible)
  - `.json` file: Structured format for easier parsing
- JSON format includes:
  - `timestamp`: ISO format timestamp
  - `llm_recommendations`: Dict with each LLM's text
  - `gemini_final`: Final synthesis text
  - `recommendations`: Array (populated by parser)

### 5. Enhanced JSON Parser
- Now handles the new Trade-Alerts JSON format
- Parses `llm_recommendations` dict structure
- Extracts recommendations from text fields in JSON

## Usage

The parser will automatically:
1. Try structured sections first (if present)
2. Fall back to free-form text parsing if no sections found
3. Extract recommendations from both `.txt` and `.json` files

## Example

The parser can now extract recommendations from text like:

```
I recommend a LONG position on EUR/USD at 1.0850 with a stop loss at 1.0800 
and take profit at 1.0900.
```

Or from structured format:

```
=== CHATGPT RECOMMENDATIONS ===
Trade Recommendation: **Short EUR/JPY**
Entry Price: 165.50
Stop Loss: 166.00
Take Profit Target 1: 165.00
```

## Next Steps

1. Run `historical_backfill.py` again to extract recommendations from historical files
2. Future recommendations from Trade-Alerts will be automatically saved in both formats
3. The RL system will learn from all extracted recommendations

