# ✅ CORRECT Command to Trigger Analysis

## ✅ Working Command

**In Render Dashboard → `trade-alerts` → Shell:**

```bash
cd /opt/render/project/src && python run_immediate_analysis.py
```

---

## ✅ What to Look For

After running, you should see:
- Step 8: Extracting entry/exit points...
- **Found X trading opportunities** ← Should be > 0 now (with the parser fix)!
- Step 9: Exporting market state...
- **Pairs: ['GBP/USD', 'GBP/JPY']** ← Should show pairs now!

---

**Last Updated**: 2025-01-11  
**Status**: ✅ Verified working command
