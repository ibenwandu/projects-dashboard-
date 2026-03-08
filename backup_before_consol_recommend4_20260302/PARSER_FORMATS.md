# Parser formats – supported LLM output styles

The recommendation parser (`src/recommendation_parser.py`) extracts trading opportunities from LLM text. It tries a **MACHINE_READABLE** JSON block first, then falls back to regex patterns. Supported formats:

---

## MACHINE_READABLE (preferred)

At the end of the response, a line:

`MACHINE_READABLE: [{"pair":"USD/JPY","direction":"SELL","entry":152.6,"exit":151.9,"stop_loss":153.05}, ...]`

Or a fenced JSON block:

` ```json [{"pair":"USD/JPY",...}] ``` `

Fields: `pair`, `direction` (BUY/SELL), `entry`, `exit` or `target`, `stop_loss`.

---

## ChatGPT

- **Header:** `### 1. Currency Pair: **USD/JPY**` (pair only in bold) — pattern_1c  
- **Header:** `### 1. **Currency Pair: USD/JPY**` (label + pair in bold) — pattern_1b  
- **Header:** `### 1. Trade Recommendation: **EUR/USD**` — pattern_1a  
- **Fields in section:** `**Entry Price:** 1.36000`, `**Exit/Target Price:** 1.36700`, `**Stop Loss:** 1.35500` or `**Stop Loss Level:** ...`

---

## Claude

- **Header:** `1. USD/JPY SHORT (SWING Trade)` — pattern_9a  
- **Header:** `1. SHORT USD/JPY (SWING TRADE)` — pattern_9d  
- **Fields in section:** `- Entry: 152.20`, `- Take Profit Target: 149.50`, `- Stop Loss: 154.80`

---

## Gemini

- **Header:** `### **Trade Recommendation 1: Short GBP/USD**` — pattern_2 / pattern_5  
- **Fields in section:** `**Entry Price (Sell Limit):** **208.00**`, `**Exit/Target Price:** **207.20**`, `**Stop Loss:** **208.50**`

---

## Gemini Final (Synthesis)

- **Header:** `#### **Trade 1: High Conviction - Sell USD/JPY**` — pattern_6  
- **Bullets:** `*   **Currency Pair:** USD/JPY` — pattern_7  
- **Fields:** `*   **Entry Price (Sell Limit):** **153.30**`, etc.

---

## DeepSeek

- Same structure as ChatGPT (uses ChatGPT prompt).  
- Also: `### **Trade 1: GBP/JPY (Sell on Rally)**`-style headers; section with `**Entry Price:**`, `**Take Profit 1:**`, `**Stop Loss:**`.

---

## Entry fallback

If no "Entry" or "Entry Price" line is found in a section, the parser tries "**Current Price:**" or "Current Price:" in the section and uses that as entry. Opportunities with pair and direction but no entry are still returned; the pipeline fill step adds entry from live prices or synthesis before merge.

---

## Updating this doc

When adding a new regex pattern for an LLM format, add one sample line under that LLM’s section above.
