# Tracking Anthropic API Credit Usage

Your Claude Console **Cost** and **Logs** pages are the right place to see what’s using your Anthropic API credit. Use this to track which process is consuming it.

---

## If you use the same key for all programs

With **one API key everywhere**, Cost and Logs can’t tell which app (Cursor, a script, Email Automation, etc.) used the credit.

**Best way to track:** use **separate API keys per program**.

1. In **Anthropic Console → Manage → API keys**, create a new key for each thing that calls the API, e.g.:
   - **Cursor** – only put this key in Cursor settings.
   - **Email Automation** – only in that project’s `.env` or config.
   - **Script X** – only in that script’s env.
2. Keep using your current key where you want; add the new keys only where you want to measure.
3. In **Cost**, filter by **API key**. You’ll see exactly which key (and thus which program) is spending.

You can create several keys in the same Anthropic account; they all draw from the same billing, but you get a breakdown by key.

**If you don’t want to change keys yet:** use **Logs** and match by **time** (when you ran a script or used Cursor). Or add the usage logger (`scripts/anthropic_usage_logger.py`) to each program with a different `PROCESS_NAME` so your local log shows which process made which calls; you can still correlate by timestamp with Logs.

---

## 1. See which API key is used where

- In **Anthropic Console** go to **Manage → API keys**.
- Check the **name/label** of each key (e.g. "Email Automation", "Cursor", "Default").
- In **Cost**, use the filter (e.g. "Email Automation", "All") to see cost **per key**.
- If one key has most of the cost, that key is what you need to track; then find where that key is configured (see below).

---

## 2. Likely sources of usage (no Anthropic code in this repo)

Your **personal** projects here use **Gemini** or **OpenAI**, not Anthropic. So the ~$2.09 is probably from:

| Source | What to check |
|--------|----------------|
| **Cursor IDE** | Cursor can use Claude for chat/completions. If your Anthropic API key is in Cursor settings, usage will show in Logs. Check: **Cursor Settings → Cursor Settings → API** (or similar). Use a **separate** API key for Cursor so you can filter by key in Cost/Logs. |
| **Another app or workspace** | Any app that has `ANTHROPIC_API_KEY` (or similar) in its env or config. Check other projects, Zapier/Make/n8n, or other tools that support Claude. |
| **“Email Automation”** | Your Cost page showed “Email Automation” as a filter. If that’s an **API key name**, that key is used by whatever app/project you gave that key to. Search your machine and configs for where that key is set. |

---

## 3. Use Logs to match requests to time and model

- **Analytics → Logs**: each row is one API request.
- **TIME (EST)** – when the request ran.
- **MODEL** – e.g. `claude-sonnet-4-5-*`, `claude-haiku-4-5-*`.
- **INPUT TOKENS** / **OUTPUT TOKENS** – main drivers of cost.
- **REQUEST (ⓘ)** – click for more detail; sometimes shows endpoint or metadata.

Correlate by **time**: note when you run a script or use Cursor; find that time in Logs to see the matching requests.

---

## 4. Tag future code so it shows up in Logs

When you **do** call Anthropic from code, use a **unique identifier** so you can recognize it in Logs:

- Set **`anthropic-version`** or **`metadata`** / **user** if the client supports it (Anthropic API allows metadata).
- Or use a **dedicated API key** for that project (e.g. “my-script”) and filter Cost/Logs by that key.

The optional script in **`personal/scripts/anthropic_usage_logger.py`** logs each call with a **process name** and token counts to `anthropic_usage.log`; use the same process name in your app so you can match Logs (by time) to your runs.

---

## 5. Quick checklist

- [ ] In Anthropic Console **Cost**, filter by **API key** and note which key has the most spend.
- [ ] Find where that key is configured (Cursor, .env, another app).
- [ ] In **Logs**, filter by **date** and **model**; compare **TIME** with when you run scripts or use Cursor.
- [ ] If you add new Anthropic code, use a **separate API key** or **metadata/user** and the usage logger so you can track that process.

---

## Optional: per-run token logger

See **`personal/scripts/anthropic_usage_logger.py`** for a small helper that logs **input/output tokens** and a **process name** to `anthropic_usage.log` for each Anthropic request. Use one process name per project (e.g. `email-automation`, `cursor`) so you can correlate with Logs by time. Run it once with `ANTHROPIC_API_KEY` and optional `PROCESS_NAME` to test.
