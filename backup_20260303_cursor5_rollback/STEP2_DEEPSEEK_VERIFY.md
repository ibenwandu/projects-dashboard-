# Step 2: Deploy & Verify DeepSeek (Trade-Alerts)

Changes are committed and pushed to `main`. Follow this checklist.

---

## 2a. Deploy **without** DeepSeek key (verify nothing breaks)

1. **Deploy Trade-Alerts** to Render (or your host) from `main`.
   - Do **not** set `DEEPSEEK_API_KEY` yet.
2. **Verify after deploy:**
   - Service starts and stays up.
   - On the next scheduled run (or a manual trigger), check logs for:
     - `Completed X/4 LLM analyses` (X will be 3 when DeepSeek is disabled).
     - No errors from the new code paths (e.g. no crashes in market_bridge or RL when `deepseek` is missing from results).
   - Market state still exports (e.g. `market_state.json` or API) with opportunities.
   - Email still sends with 3 LLM sections (ChatGPT, Gemini, Claude).

If anything fails, fix before enabling DeepSeek.

---

## 2b. Enable DeepSeek and run one full analysis

1. **Set environment variables** on Trade-Alerts (e.g. Render Dashboard → Service → Environment):
   - `DEEPSEEK_API_KEY` = your DeepSeek API key
   - (Optional) `DEEPSEEK_MODEL` = `deepseek-chat` (default) or `deepseek-reasoner`
2. **Redeploy** or restart the service so it picks up the new env.
3. **Trigger one full analysis:**
   - Wait for the next scheduled run, or
   - Run manually (e.g. Render Shell: `cd Trade-Alerts && python run_analysis_now.py` or your usual trigger).
4. **Verify in logs:**
   - `✅ DeepSeek enabled (model: deepseek-chat)` at startup.
   - `Running DeepSeek analysis...` and `✅ DeepSeek analysis completed`.
   - `Completed 4/4 LLM analyses` (or 4/x if some other LLM failed).
5. **Verify in output:**
   - **Email:** Body includes a "DEEPSEEK RECOMMENDATIONS" section (if DeepSeek returned content).
   - **Market state:** Exported state includes `deepseek` in opportunity sources / consensus where applicable, and `llm_weights` includes `deepseek`.

---

## 2c. Optional local check (before or instead of Render)

From repo root (Trade-Alerts):

```bash
# Ensure .env has DEEPSEEK_API_KEY (or leave unset to test 3-LLM behavior)
python run_analysis_now.py
```

Check console for the same log lines as above and that no errors occur.

---

## Summary

| Phase              | DEEPSEEK_API_KEY | Expected |
|--------------------|------------------|----------|
| 2a. Deploy & verify| **Unset**        | 3/4 LLM analyses, no errors, emails and market state as before |
| 2b. Enable & run   | **Set**          | 4/4 LLM analyses, DeepSeek section in email, deepseek in market_state |

After 2b passes, Step 2 is complete. You can then proceed to Step 4 (Scalp-Engine UI + RL) when ready.
