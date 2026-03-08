# Fix: Training Script Database Path Issue

## Problem

The training script was using the **default database path** (`trade_alerts_rl.db` in the ephemeral filesystem), while the main service uses the **persistent disk** (`/var/data/trade_alerts_rl.db`).

**Result**: Training data was written to a different database than the one the service reads from!

---

## What Happened

1. ✅ Training script ran → Wrote data to `/opt/render/project/src/trade_alerts_rl.db` (ephemeral)
2. ✅ You saw correct weights in shell → That database had data
3. ❌ Service reads from `/var/data/trade_alerts_rl.db` (persistent disk) → This database was empty!
4. ❌ Service shows 25% weights → Because the persistent disk database is empty

---

## Fix Applied

Updated `train_rl_system.py` to use the **same database path logic as `main.py`**:

- **On Render**: Uses `/var/data/trade_alerts_rl.db` (persistent disk)
- **Locally**: Uses `data/trade_alerts_rl.db` (local directory)

Now the training script and main service use the **same database file**.

---

## Next Steps

1. **Wait for Render to deploy** the fix (1-2 minutes)

2. **Re-run training script** on Render:
   ```bash
   cd /opt/render/project/src
   python train_rl_system.py --import-csv trade-alert-eval.csv --all
   ```

3. **Verify weights updated**:
   ```bash
   python -c "
   from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine
   db = RecommendationDatabase()
   engine = LLMLearningEngine(db)
   weights = engine.calculate_llm_weights()
   print('\n📊 Current LLM Weights:')
   for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
       print(f'   {llm}: {weight*100:.1f}%')
   "
   ```

4. **Restart service** to load new weights

5. **Check logs** - Should now show correct weights:
   ```
   ⚖️  Current LLM Weights: synthesis: 39%, gemini: 35%, chatgpt: 23%, claude: 4%
   ```

---

## Why This Fixes It

**Before**: 
- Training → Writes to `/opt/render/project/src/trade_alerts_rl.db` (ephemeral)
- Service → Reads from `/var/data/trade_alerts_rl.db` (persistent)
- **Different databases!** ❌

**After**:
- Training → Writes to `/var/data/trade_alerts_rl.db` (persistent)
- Service → Reads from `/var/data/trade_alerts_rl.db` (persistent)
- **Same database!** ✅

---

## Summary

**The Issue**: Training script and main service were using different database files.

**The Fix**: Training script now uses the same persistent disk path as the main service.

**Result**: Training data will now be written to the correct database that the service reads from.
