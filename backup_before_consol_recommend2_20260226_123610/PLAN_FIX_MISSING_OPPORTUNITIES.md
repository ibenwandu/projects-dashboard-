# Comprehensive Plan: Fix Missing Trading Opportunities

**Goal:** Ensure every LLM-recommended pair that appears in the email (ChatGPT, Gemini, Claude, DeepSeek, Synthesis) can appear in the Scalp-Engine opportunities list. No piecemeal fixes—a single, coherent solution.

**Root cause (recap):** Opportunities are dropped in two places: (1) **Parser**—pair/section regex doesn’t match the LLM’s exact format, or entry/exit/stop extraction fails so the opportunity is skipped; (2) **Merge**—opportunities with missing or zero `entry` are discarded. The result is that only synthesis (and sometimes Gemini) contributions make it through, so pairs from ChatGPT (e.g. GBP/USD, EUR/JPY), Claude (EUR/USD), and DeepSeek (EUR/CHF) are missing.

---

## 1. Parser: Format coverage and section boundaries

**Owner:** `src/recommendation_parser.py`

### 1.1 Add patterns for actual LLM formats (not just “expected” ones)

- **ChatGPT “Currency Pair:” (pair only in bold)**  
  Current pattern_1b expects `### 1. **Currency Pair: USD/JPY**`.  
  Actual ChatGPT: `### 1. Currency Pair: **USD/JPY**`.  
  **Action:** Add a new pattern (e.g. pattern_1c) that matches:
  - `(?:####|###)\s+\d+\.\s+Currency\s+Pair:\s+\*\*([A-Z]{3})[/\s-]([A-Z]{3})\*\*`
  - Reuse the same section-boundary logic as 1b so the block includes the following lines (Entry, Exit, Stop Loss).

- **Claude simple list**  
  Actual: `1. USD/JPY SHORT (SWING Trade)` then block with `- Entry:`, `- Take Profit Target:`, `- Stop Loss:`.  
  **Action:** Verify pattern_9a and the section capture include the full recommendation block (multi-line). If the lookahead stops at the next `1. XXX/YYY`, ensure “Entry”/“Take Profit”/“Stop Loss” appear in the captured section. Add or adjust patterns so Claude’s bullet format is matched.

- **DeepSeek “Trade N:” and bullets**  
  Document the exact DeepSeek header and bullet format from a real run; add a dedicated pattern set if it differs from Gemini/ChatGPT (e.g. “### **Trade 1: GBP/JPY (Sell on Rally)**” and “*   **Entry Price:** …”).

- **Single source of truth for formats**  
  Add a short comment block at the top of `_parse_text` (or a separate `PARSER_FORMATS.md`) listing each LLM and the exact sample line(s) we support (e.g. “ChatGPT: ### N. Currency Pair: **XXX/YYY**”, “Claude: 1. XXX/YYY SHORT …”). When a new format appears in production, add a pattern and update this list.

### 1.2 Section boundaries

- Some patterns use a lookahead that ends the section too early (e.g. at the next `###` or `*   **Currency Pair:**`), so “Entry Price” or “Entry:” lines are excluded.  
- **Action:** For each pattern set (1a, 1b, 1c, 2, 6, 7, 9a–9d, etc.), define the section as “from the match start to the next same-level header” (e.g. next `### N.` or next `1. XXX/YYY` or next `*   **Currency Pair:**`). Ensure that:
  - The “Entry” / “Entry Price” / “Take Profit” / “Stop Loss” lines for that recommendation are inside the captured `section_text`.
  - If a pattern’s lookahead is too greedy (e.g. `.*?` stops at a newline), relax it so the section is full block (e.g. use `(?=\n(?:###|\d+\.\s+[A-Z]))` with DOTALL).

### 1.3 Entry/exit/stop extraction

- **Action:** In `_extract_opportunity_from_text`, add entry/exit/stop patterns that mirror the exact phrasing from each LLM (e.g. ChatGPT “**Entry Price:** 1.36000”, Claude “- Entry: 153.80”, “- Take Profit Target: 149.50”). Prefer one pattern per observed format over a single generic pattern.
- Add a fallback: if “current price” or “Current Price:” appears in the section, use that number as a last-resort entry when no “Entry”/“Entry Price” line is found (and log “Used current price as entry for {pair}”).

---

## 2. Parser: Don’t drop opportunities when entry is missing

**Owner:** `src/recommendation_parser.py`

- **Current behavior:** `if opp and opp.get('entry'): ... opportunities.append(opp)` — any recommendation without a parsed entry is discarded.
- **New behavior:**
  - When we have a valid (pair, direction) and a known pair (from `_normalize_pair`) but `_extract_opportunity_from_text` returns an opp with `entry is None` (or 0):
    - Still append the opportunity with `entry=None` (or a sentinel like `0`), and set a flag e.g. `needs_entry_fill: True`.
  - Alternatively (preferred): parser does not add `needs_entry_fill`; instead, a dedicated pipeline step (see §4) fills missing entry before merge. So parser returns opportunities even when entry is None; downstream “fill missing entry” step adds entry from current_prices or synthesis.
- **Action:** In `_parse_text`, when `_extract_opportunity_from_text` returns an opp with valid pair and direction but missing entry:
  - Append that opp to `opportunities` (with `entry: None` or `0`), and ensure the pipeline step in §4 fills it before merge. Optionally log: “Including {pair} {direction} with missing entry for downstream fill.”

---

## 3. Merge: Keep opportunities with missing entry and fill them

**Owner:** `src/market_bridge.py` and `main.py`

- **Current behavior:** `merge_opportunities_from_all_llms` does `if not pair or not direction or entry <= 0: continue`, so any opportunity without a valid entry is dropped.
- **New behavior:**
  - **Pre-merge step (in main or bridge):** “Fill missing entry.” For every opportunity in `all_opportunities` (each LLM list) where `entry` is None or <= 0:
    - If `current_prices` is provided and has the pair, set `entry = current_prices[pair]` and log “Filled missing entry for {pair} from current price.”
    - Else if we have synthesis opportunities and one of them is same (pair, direction), use that synthesis entry for this opp.
    - If still no entry, only then drop the opportunity (and log “Dropped {pair} {direction}: no entry and no current price/synthesis fallback”).
  - **Merge:** Change `merge_opportunities_from_all_llms` so it does **not** skip an opportunity solely because `entry <= 0`. Instead:
    - When building `opportunity_map`, if an opp has no valid entry, apply the same “fill missing entry” rule (using `current_prices` or synthesis) inside the merge loop if you prefer, or rely on the pre-merge fill so every opp passed to merge already has a valid entry.
  - **Preferred:** Do “fill missing entry” once in `main.py` after parsing all LLMs and before calling `merge_opportunities_from_all_llms`. Then merge can keep the current `entry <= 0` skip as a safety net (since nothing should reach it after the fill step).

### 3.1 API contract

- **Action:** `merge_opportunities_from_all_llms(all_opportunities, current_prices=None, synthesis_opportunities=None)`.
  - If `current_prices` and/or `synthesis_opportunities` are provided, the merge (or a helper used by main) fills missing entry before comparing “best” entry. Main will pass `current_prices` and `all_opportunities['synthesis']` when calling merge so that any opportunity that has pair/direction but no entry gets an entry and is not dropped.

---

## 4. Pipeline: Single “parse → fill → merge → export” flow

**Owner:** `main.py`

- **Current flow:** Parse each LLM → merge → export. Opportunities without entry never enter the merge.
- **New flow:**
  1. Parse each LLM (and synthesis) as today; collect `all_opportunities`.
  2. **Fill missing entry (new step):** For every opp in `all_opportunities` (all keys) where `entry` is None or <= 0:
     - Set `entry` from `current_prices[pair]` if available;
     - Else from synthesis opp with same (pair, direction) if available;
     - Else remove this opp from the list (or skip it in merge) and log.
  3. Merge as today (`merge_opportunities_from_all_llms`).
  4. Export as today.

- **Action:** In `main.py`, after the loop that builds `all_opportunities` and before `merge_opportunities_from_all_llms`:
  - Call a new helper, e.g. `_fill_missing_entry_prices(all_opportunities, current_prices)` that:
    - Takes `current_prices` and optionally `all_opportunities['synthesis']`;
    - Iterates over every list in `all_opportunities` and for each opp with missing/invalid entry fills it as above;
    - Removes opps that still have no entry after fill (and logs them).
  - Then call `merge_opportunities_from_all_llms(all_opportunities)` as today (merge can keep the `entry <= 0` check as a safeguard).

---

## 5. Observability and regression prevention

### 5.1 Logging

- **Per-LLM parse result:** After parsing each LLM, log: `Parsed {llm_name}: {len(opps)} opportunities, pairs: [A, B, ...]`. If `len(opps) == 0` but we know that LLM’s block had recommendations in the email, log a short snippet of the raw text (e.g. first 300 chars) at DEBUG so we can add patterns.
- **Fill step:** Log how many opportunities had missing entry and how many were filled from current_prices vs synthesis vs dropped.
- **Merge:** Keep existing “Merged N unique opportunities from all LLMs” and add “Per-LLM contribution: chatgpt M, gemini N, …” (count how many merged opps have source_llm = X).

### 5.2 Tests

- **Parser:** Add unit tests in `tests/` (or under `src/`) that:
  - Feed **real** snippets from the email (ChatGPT “### 1. Currency Pair: **USD/JPY**” + block with Entry/Exit/Stop; Claude “1. USD/JPY SHORT …”; DeepSeek “Trade 1: …”; Gemini Final “*   **Currency Pair:** GBP/JPY”).
  - Assert: expected pair count (e.g. ChatGPT 3, Claude 3, Synthesis 2), and that expected pairs (e.g. GBP/USD, EUR/JPY, EUR/USD, EUR/CHF) appear in the parsed list with valid entry when the snippet includes entry.
- **Fill + merge:** Test that when `all_opportunities['chatgpt']` has one opp with pair/direction but entry=None, and `current_prices` has that pair, the fill step sets entry and the merged list contains that pair.
- **End-to-end:** Optional: a test that runs the full analysis pipeline on a saved fixture (full LLM + synthesis text) and asserts minimum number of unique pairs and that specific pairs from each LLM are present in the exported opportunities.

### 5.3 Documentation

- Add `PARSER_FORMATS.md` (or a section in an existing doc) that lists each LLM and the exact line formats we support, with one sample line each. Update it whenever a new pattern is added.
- In `PLAN_FIX_MISSING_OPPORTUNITIES.md` (this file), add a “Verification” section: after deployment, run one analysis and confirm in logs that “Parsed chatgpt: ≥1 opportunities”, “Parsed claude: ≥1 opportunities”, and “Merged N unique opportunities” with N ≥ 3 when the email has recommendations from multiple LLMs.

---

## 6. Optional: Structured output from LLMs

- **Idea:** In the LLM analyzer prompts (e.g. in `src/llm_analyzer.py` or the synthesizer), add an instruction: “At the end of your response, include a MACHINE_READABLE block in this exact format: …” with a small JSON array, e.g. `[{"pair":"USD/JPY","direction":"SELL","entry":152.6,"exit":151.9,"stop_loss":153.05}, ...]`.
- **Parser:** In `recommendation_parser.py`, before running regex patterns, try to extract and parse this block (e.g. regex to find `MACHINE_READABLE` or ```json … ``` and then `json.loads`). If valid, use it as the list of opportunities for that LLM (and optionally still run text parsing to cross-check or fill missing fields).
- **Benefit:** Reduces dependence on regex for every format change; LLM output becomes the contract. Can be Phase 2 after the parser and fill/merge changes are in place.

---

## 7. Implementation order (no piecemeal behavior)

Implement in one coherent pass so that “missing opportunities” is fixed end-to-end:

1. **Parser**
   - Add pattern_1c for ChatGPT “Currency Pair: **XXX/YYY**”.
   - Review and fix section boundaries for all patterns so Entry/Exit/Stop lines are inside the captured section.
   - Add entry/exit/stop patterns and “current price as entry” fallback in `_extract_opportunity_from_text`.
   - Allow appending opportunities with missing entry (entry=None) and document that downstream fill will add entry.

2. **Pipeline**
   - Add `_fill_missing_entry_prices(all_opportunities, current_prices, synthesis_opportunities)` in main (or in market_bridge and call from main). Implement fill from current_prices then from synthesis; drop only if still missing and log.
   - Call fill after parsing and before merge. Ensure merge receives only opportunities with valid entry (or update merge to accept and fill as in §3).

3. **Merge**
   - Either keep merge as-is and ensure fill step removes any opp that still has no entry, or extend merge to accept optional `current_prices`/synthesis and fill inside merge when entry is missing. Prefer doing fill in main so merge logic stays simple.

4. **Observability**
   - Add per-LLM parse logging (count + pair list); add fill-step logging; add optional per-LLM contribution in merge log.
   - Add parser unit tests with real email snippets; add fill+merge test.
   - Add `PARSER_FORMATS.md` and update this plan’s “Verification” section.

5. **Optional (Phase 2)**
   - Structured MACHINE_READABLE block in prompts and parser.

---

## 8. Success criteria

- For a run where the email contains recommendations from ChatGPT (e.g. USD/JPY, GBP/USD, EUR/JPY), Gemini (GBP/JPY, USD/JPY), Claude (USD/JPY, EUR/USD, GBP/JPY), DeepSeek (GBP/JPY, USD/JPY, EUR/CHF), and Synthesis (GBP/JPY, USD/JPY):
  - Parsed opportunities: chatgpt ≥ 1, claude ≥ 1, deepseek ≥ 1, synthesis ≥ 1.
  - Merged unique opportunities include at least: GBP/JPY, USD/JPY, and as many of GBP/USD, EUR/JPY, EUR/USD, EUR/CHF as were recommended and parseable.
  - Exported market state `opportunities` and `approved_pairs` reflect the merged list (no unintended drops).
- Logs make it clear when an opportunity was filled from current price or synthesis and when one was dropped (no entry, no fallback).

---

## 9. Files to touch

| File | Changes |
|------|--------|
| `src/recommendation_parser.py` | New pattern(s) for ChatGPT/Claude/DeepSeek; section boundaries; entry/exit/stop patterns and current-price fallback; allow opps with entry=None to be returned. |
| `main.py` | New step: `_fill_missing_entry_prices(...)` after parse, before merge; pass `current_prices` and synthesis into fill; per-LLM parse logging. |
| `src/market_bridge.py` | Optional: `merge_opportunities_from_all_llms(..., current_prices=None, synthesis_opportunities=None)` and fill inside merge; or keep merge as-is and rely on main’s fill. |
| Tests | New tests for parser (real snippets), fill step, and merge. |
| `PARSER_FORMATS.md` (new) | Document supported formats per LLM. |
| `PLAN_FIX_MISSING_OPPORTUNITIES.md` (this file) | Verification subsection and any updates after implementation. |

This plan is a single, comprehensive fix: parser coverage + fill missing entry + merge behavior + observability + tests, so that we stop missing trading opportunities due to format or missing-entry drops.
