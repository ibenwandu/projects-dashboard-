# Plan: Add DeepSeek as an LLM for Trade Alerts Analysis

This plan adds **DeepSeek** as a fourth base LLM (alongside ChatGPT, Gemini, Claude) in Trade-Alerts and Scalp-Engine **without breaking** existing behavior. DeepSeek’s API is **OpenAI-compatible** (`base_url="https://api.deepseek.com"`), so integration reuses the same client pattern as ChatGPT.

---

## 1. Overview of Current Flow

| System | Role |
|--------|------|
| **Trade-Alerts** | Runs LLM analysis (ChatGPT, Gemini, Claude), synthesizes with Gemini, parses opportunities, exports `market_state.json` (opportunities + `llm_weights`). Logs recommendations to RL DB. |
| **Scalp-Engine** | Reads `market_state` (file or API), shows opportunities and Required LLMs in UI, executes trades when consensus and required_llms are met. Has its own RL DB (`scalping_rl.db`) for daily learning. |

**LLM keys used everywhere:** `chatgpt`, `gemini`, `claude`, `synthesis` (synthesis = Gemini final). Adding **`deepseek`** as a new key keeps the same patterns.

---

## 2. Trade-Alerts Changes

### 2.1 `src/llm_analyzer.py`

- **Add DeepSeek client** (OpenAI-compatible):
  - Env: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` (e.g. `deepseek-chat`).
  - `OpenAI(api_key=..., base_url="https://api.deepseek.com")`.
- **Add** `_get_deepseek_prompt(...)` (reuse same structure as ChatGPT/Claude; same data summary).
- **Add** `analyze_with_deepseek(data_summary, current_datetime)` (same pattern as `analyze_with_chatgpt`).
- **Update** `analyze_all()`:
  - Set `results['deepseek'] = self.analyze_with_deepseek(...)`.
  - Log "Completed X/4 LLM analyses" when DeepSeek is enabled (or keep "X/3" for backward compatibility and log "X base LLMs").
- **Optional:** Only call DeepSeek if `DEEPSEEK_API_KEY` is set (same as other LLMs). No code paths should assume DeepSeek is present.

**Risk:** None. New code path; existing LLMs unchanged.

---

### 2.2 `main.py`

- **Step 7 (Log recommendations):** In the loop over base LLMs, add `'deepseek'`:
  - Change `for llm_name in ['chatgpt', 'gemini', 'claude']` to include `'deepseek'`.
  - Same parse + log flow as other LLMs.
- **Step 8 (all_opportunities):** In the loop that parses from individual LLMs, add `'deepseek'`:
  - Change `for llm_name in ['chatgpt', 'gemini', 'claude']` to include `'deepseek'`.
  - So `all_opportunities['deepseek']` is populated when DeepSeek returns recommendations.

**Risk:** Low. Only adds another key; parsing and export already support arbitrary LLM keys.

---

### 2.3 `src/market_bridge.py`

- **`_analyze_consensus_for_pair()`:** Add `'deepseek'` to `base_llms`:
  - `base_llms = ['chatgpt', 'gemini', 'claude', 'deepseek']`.
- **Consensus level:** Keep as `len(base_llm_sources)` (can be 1–4). No change to `min_consensus_level` semantics (e.g. 2 = at least 2 agree).
- **Log message:** Change "X/3" to "X/4" or "X base LLMs" where it logs consensus.
- **Default `llm_weights` in `export_market_state()`:** Add `'deepseek': 0.25` and normalize so weights sum to 1.0 (e.g. 5 × 0.2 or keep 4 × 0.25 and add deepseek 0.25 with renormalization).

**Risk:** Low. Consensus logic is key-agnostic; only the list of base LLMs and default weights change.

---

### 2.4 `src/trade_alerts_rl.py`

- **RecommendationDatabase:**
  - **`learning_checkpoints` table:** Add column `deepseek_weight REAL`. Use a one-time migration: `ALTER TABLE learning_checkpoints ADD COLUMN deepseek_weight REAL;` (run on first load or separate migration script). Existing rows get NULL; when reading, treat NULL as 0.25.
  - **`save_learning_checkpoint()`:** Include `weights.get('deepseek', 0.25)` in INSERT (add column to INSERT list and value tuple).
- **LLMLearningEngine:**
  - **`calculate_llm_weights()`:** Add `'deepseek'` to `llm_sources`.
  - **`generate_performance_report()`:** Add `'deepseek'` to the list of LLMs.
- **RecommendationParser / `_json_to_recommendation()`:** In the "Normalize LLM source name" block, add:
  - `elif 'DEEPSEEK' in llm_source_upper:` → `llm_source = 'deepseek'`.
- **Parsing from `llm_recommendations` (Structure 4):** No change; keys are iterated. Once `llm_recommendations['deepseek']` exists, it will be parsed.

**Risk:** Low. DB migration is additive; old checkpoints without `deepseek_weight` can default to 0.25.

---

### 2.5 `src/email_sender.py`

- **Log / body text:** Replace "3 LLM recommendations" with "N LLM recommendations" (e.g. `sum(1 for v in llm_recommendations.values() if v)`).

**Risk:** None.

---

### 2.6 Other Trade-Alerts Files

- **`src/gemini_synthesizer.py`:** No change. It iterates `llm_recommendations.items()`; DeepSeek will be included automatically.
- **`run_analysis_now.py`:** No change. Uses `analyze_all()` which will return `deepseek` when implemented.
- **`requirements.txt`:** No new dependency (DeepSeek uses `openai` with a different base URL).

---

## 3. Scalp-Engine Changes

### 3.1 `scalp_ui.py`

- **Required LLMs (Configuration tab):** Add DeepSeek to `llm_options`:
  - `('deepseek', 'DeepSeek', llm_weights.get('deepseek', 0.25))`.
- **Consensus level help text:** Update "3: All 3 LLMs agree" to something like "3: At least 3 LLMs agree" (or "4: All 4 LLMs agree" if you add level 4 later). Keep `min_consensus_level` 1/2/3 (and optionally 4) as now.
- **Performance / LLM tables:** Ensure any hardcoded list of LLMs includes `deepseek` (e.g. from `market_state['llm_weights']`); usually this is key-agnostic.

**Risk:** None. UI just shows whatever is in `llm_weights` and `required_llms`; adding deepseek to the options list is sufficient.

---

### 3.2 `config_api_server.py` (if used)

- Default `required_llms` can stay `['gemini']` (or whatever). No need to add deepseek to default unless desired.

---

### 3.3 Scalp-Engine RL (`src/scalping_rl_enhanced.py`, `src/daily_learning.py`)

- **`scalping_rl_enhanced.py` – LLMLearningEngine.calculate_llm_weights():** Add `'deepseek'` to `llm_sources`.
- **`learning_checkpoints` table (Scalp-Engine):** Add `deepseek_weight REAL` (migration: `ALTER TABLE learning_checkpoints ADD COLUMN deepseek_weight REAL`).
- **`daily_learning.py` – INSERT into learning_checkpoints:** Add `deepseek_weight` column and `weights.get('deepseek', 0.25)` to the INSERT.

**Risk:** Low. Same additive pattern as Trade-Alerts RL.

---

### 3.4 `auto_trader_core.py` / `scalp_engine.py`

- No code changes. They use `required_llms` and consensus level from config; deepseek will appear in `llm_sources` from market_state once Trade-Alerts includes it.

---

## 4. Environment / Deployment

- **Trade-Alerts (e.g. Render):** Set `DEEPSEEK_API_KEY` (and optionally `DEEPSEEK_MODEL`, e.g. `deepseek-chat`). If not set, DeepSeek is simply disabled like a missing ChatGPT key.
- **Scalp-Engine:** No new env vars. It only consumes market_state and config.

---

## 5. Implementation Order (Safe Sequence)

1. **Trade-Alerts – LLM only**
   - `llm_analyzer.py`: Add DeepSeek client, prompt, `analyze_with_deepseek`, and `analyze_all()` update.
   - Test locally with `DEEPSEEK_API_KEY` set; run one analysis and confirm `results['deepseek']` is present when enabled.
2. **Trade-Alerts – Pipeline**
   - `main.py`: Add `deepseek` to logging and `all_opportunities` loops.
   - `market_bridge.py`: Add `deepseek` to `base_llms`, default `llm_weights`, and log text.
   - `trade_alerts_rl.py`: DB migration for `deepseek_weight`, `save_learning_checkpoint`, `calculate_llm_weights`, parser normalization, `generate_performance_report`.
   - `email_sender.py`: Dynamic N in "N LLM recommendations".
3. **Scalp-Engine**
   - `scalp_ui.py`: Add DeepSeek to Required LLMs and any LLM list; adjust consensus help text if desired.
   - `scalping_rl_enhanced.py`: Add `deepseek` to `llm_sources`; add `deepseek_weight` to schema (migration) and any INSERT/SELECT that uses checkpoint weights.
   - `daily_learning.py`: Add `deepseek_weight` to checkpoint INSERT.
4. **Deploy**
   - Deploy Trade-Alerts first (without setting `DEEPSEEK_API_KEY` to verify nothing breaks).
   - Set `DEEPSEEK_API_KEY` and run one full analysis; confirm market_state and emails include DeepSeek when it returns content.
   - Deploy Scalp-Engine; confirm Configuration tab shows DeepSeek and that consensus/required_llms still work.

---

## 6. Rollback

- **Disable DeepSeek:** Unset `DEEPSEEK_API_KEY`. Analysis will run with 3 base LLMs; all_opportunities and consensus will have no deepseek key; existing behavior is unchanged.
- **Code rollback:** Revert commits. DB migrations (new column) are harmless; old code can ignore `deepseek_weight`.

---

## 7. Summary Table

| Component | Change |
|-----------|--------|
| **Trade-Alerts** | |
| `llm_analyzer.py` | DeepSeek client + `analyze_with_deepseek` + `analyze_all()` |
| `main.py` | Include `deepseek` in log and all_opportunities loops |
| `market_bridge.py` | `base_llms` + default `llm_weights` + log text |
| `trade_alerts_rl.py` | `deepseek_weight` in checkpoints; deepseek in weights/report/parser |
| `email_sender.py` | "N LLM recommendations" |
| **Scalp-Engine** | |
| `scalp_ui.py` | DeepSeek in Required LLMs (and Performance if applicable) |
| `scalping_rl_enhanced.py` | `deepseek` in `llm_sources`; `deepseek_weight` in schema |
| `daily_learning.py` | `deepseek_weight` in checkpoint INSERT |
| **Config / Env** | `DEEPSEEK_API_KEY` (optional `DEEPSEEK_MODEL`) for Trade-Alerts |

This keeps all existing behavior intact and adds DeepSeek as an optional fourth base LLM end-to-end.
