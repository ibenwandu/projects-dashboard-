# Quick Guide: Check RL Improvement in Trade-Alerts

## 🎯 Main Indicator: LLM Weights

**RL is improving if weights are NOT equal (25% each).**

Example of improvement:
- ❌ **Before RL**: `chatgpt: 25%, gemini: 25%, claude: 25%, synthesis: 25%`
- ✅ **After RL learns**: `chatgpt: 40%, gemini: 30%, claude: 20%, synthesis: 10%`

---

## ✅ Quickest Method: Check Email

**Every Trade-Alerts email includes RL insights at the bottom:**

Look for:
```
🧠 MACHINE LEARNING INSIGHTS (Based on Historical Performance)
📊 LLM Performance Weights (Based on Past Accuracy):
  • CHATGPT: 40% weight (Win Rate: 65%, Avg P&L: 45 pips)
  • GEMINI: 30% weight (Win Rate: 58%, Avg P&L: 32 pips)
  ...
🏆 Highest Accuracy: CHATGPT (40% confidence weight)
```

**If weights differ from 25% each → RL is working! ✅**

---

## 📋 Detailed Check: Run This Script

**In Render Dashboard → `trade-alerts` → Shell:**

```bash
cd /opt/render/project/src
python << 'EOF'
from src.trade_alerts_rl import RecommendationDatabase, LLMLearningEngine

db = RecommendationDatabase()
engine = LLMLearningEngine(db)

# Get current weights
weights = engine.calculate_llm_weights()
print("📊 Current LLM Weights:")
for llm, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    print(f"   {llm}: {weight*100:.1f}%")

# Generate performance report
report = engine.generate_performance_report()
print("\n🎯 Performance by LLM:")
for llm, stats in report['llm_performance'].items():
    if stats['total_recs'] > 0:
        print(f"\n   {llm.upper()}:")
        print(f"     Total: {stats['total_recs']} recommendations")
        print(f"     Win Rate: {stats['win_rate']*100:.1f}%")
        print(f"     Avg P&L: {stats['avg_pnl']:.1f} pips")
        print(f"     Profit Factor: {stats['profit_factor']:.2f}")
EOF
```

---

## ✅ What to Look For

1. **Weights differ from 25% each** → RL has learned
2. **Weights change over time** → RL is adapting
3. **Higher-weighted LLMs have better metrics** → RL is correctly identifying good performers
4. **Email shows RL insights** → System is working

---

**Last Updated**: 2025-01-11
