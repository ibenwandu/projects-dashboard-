# RL System Quick Reference

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install yfinance pandas numpy
   ```

2. **Run historical backfill (ONE TIME):**
   ```bash
   python historical_backfill.py
   ```

3. **Add daily learning job (Render):**
   - Command: `python src/daily_learning.py`
   - Schedule: `0 23 * * *` (11pm UTC)

4. **Done!** System now learns automatically.

---

## 📊 Key Files

| File | Purpose |
|------|---------|
| `src/trade_alerts_rl.py` | Core RL system (database, parser, evaluator, learning engine) |
| `historical_backfill.py` | One-time script to process all historical files |
| `src/daily_learning.py` | Daily job to evaluate outcomes and update weights |
| `main.py` | Enhanced with RL integration |
| `trade_alerts_rl.db` | SQLite database storing all recommendations and outcomes |

---

## 🔍 Database Queries

```sql
-- See recent recommendations
SELECT llm_source, pair, direction, outcome, pnl_pips 
FROM recommendations 
ORDER BY timestamp DESC LIMIT 20;

-- LLM performance summary
SELECT llm_source, 
       COUNT(*) as total,
       AVG(CASE WHEN outcome IN ('WIN_TP1', 'WIN_TP2') THEN 1.0 ELSE 0.0 END) as win_rate,
       AVG(pnl_pips) as avg_pnl
FROM recommendations
WHERE evaluated = 1
GROUP BY llm_source;

-- Latest weights
SELECT * FROM learning_checkpoints ORDER BY timestamp DESC LIMIT 1;
```

---

## ⚙️ Environment Variables

No new environment variables needed! Uses existing:
- `GOOGLE_DRIVE_FOLDER_ID` - For fetching historical files

---

## 📈 What Gets Logged

Every recommendation includes:
- LLM source (ChatGPT, Gemini, Claude, Synthesis)
- Currency pair and direction
- Entry price, stop loss, take profit levels
- Position size
- Confidence level
- Rationale

After 4+ hours, system evaluates:
- Outcome (WIN_TP1, WIN_TP2, LOSS_SL, NEUTRAL)
- Exit price
- P&L in pips
- Bars held
- Max favorable/adverse excursions

---

## 🎯 How Weights Work

Weights are calculated based on:
- **Win Rate** (60% weight)
- **Profit Factor** (40% weight)

Weights normalize to sum to 100%, so best-performing LLM gets highest weight.

---

## 🔄 Daily Learning Schedule

- **Time:** 11pm UTC daily
- **What it does:**
  1. Finds recommendations 4+ hours old
  2. Evaluates outcomes using market data
  3. Recalculates LLM weights
  4. Saves checkpoint
  5. Updates weights for next day's recommendations

---

## 💡 Email Enhancements

Every email now includes:
- Current LLM performance weights
- Historical win rates per LLM
- Consensus analysis (ALL_AGREE vs 2_AGREE vs DISAGREE)
- Best-performing LLM identification
- Actionable recommendations

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| All weights 0.25 | Need more data - wait for daily learning |
| No recommendations logged | Check that analysis ran successfully |
| Evaluation fails | Normal for very recent trades (<4 hours old) |
| Import errors | Ensure `src/trade_alerts_rl.py` exists |

---

## 📞 Support

- Full guide: `RL_SETUP_GUIDE.md`
- Logs: `logs/trade_alerts_*.log`
- Database: `trade_alerts_rl.db`





