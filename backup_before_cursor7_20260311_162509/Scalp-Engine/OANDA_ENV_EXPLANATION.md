# Why OANDA_ENV=practice?

## OANDA Has Two Environments

OANDA provides two separate environments for trading:

### 1. **Practice (Demo/Sandbox)**
- **Purpose**: Testing and development
- **Money**: Virtual/fake money
- **Risk**: Zero - no real money at stake
- **Use Case**: Testing your trading system, learning, debugging

### 2. **Live (Production)**
- **Purpose**: Real trading
- **Money**: Real money from your account
- **Risk**: Real - actual financial risk
- **Use Case**: Production trading after thorough testing

---

## Why Start with "practice"?

### ✅ Safety First
- **No financial risk** while testing
- You can make mistakes without losing money
- Perfect for initial deployment and debugging

### ✅ Testing
- Verify all components work correctly
- Test signal generation
- Verify order execution
- Check risk management
- Validate position sizing

### ✅ Learning
- Understand how the system behaves
- See real-time market data
- Practice without consequences

---

## When to Switch to "live"

**Only switch to "live" when:**
1. ✅ System has been tested thoroughly in practice mode
2. ✅ All components work correctly (signals, execution, risk management)
3. ✅ You've monitored it for at least a few days/weeks
4. ✅ You're confident in the risk settings
5. ✅ You understand how the system behaves
6. ✅ You're ready to trade with real money

**⚠️ WARNING**: Switching to "live" means real money trades. Make sure you're ready!

---

## How to Add OANDA_ENV in Render

If `OANDA_ENV` is not showing in the Render configuration:

### Option 1: Add Manually in Render Dashboard

1. Go to Render Dashboard → `scalp-engine` → **Environment**
2. Click **"Add Environment Variable"**
3. Add:
   - **Key**: `OANDA_ENV`
   - **Value**: `practice` (or `live` if you're ready)
4. Click **"Save Changes"**

### Option 2: Update render.yaml

The `render.yaml` already includes `OANDA_ENV` with `sync: false`, which means:
- It has a default value (`practice`)
- You can override it in the Render dashboard
- It will show up after deployment

### Option 3: Let it Use Default

If you don't set `OANDA_ENV`, the code defaults to `practice`:
```python
self.oanda_env = os.getenv('OANDA_ENV', 'practice')
```

So even if it's not in the environment variables, it will use `practice` by default.

---

## Current Configuration

In your `render.yaml`:
```yaml
- key: OANDA_ENV
  value: practice  # Use "practice" for testing, "live" for real trading
  sync: false  # Allow override in Render dashboard
```

This means:
- Default value is `practice` (safe for testing)
- You can change it to `live` in Render dashboard when ready
- The value is not synced from the YAML (you control it manually)

---

## Recommendation

**For Initial Deployment:**
1. ✅ Use `OANDA_ENV=practice` (default)
2. ✅ Test thoroughly for at least a week
3. ✅ Monitor all trades and signals
4. ✅ Verify risk management works
5. ✅ Check position sizing is appropriate
6. ✅ Then consider switching to `live`

**Never switch to `live` until you're 100% confident!**

---

## Summary

- **`practice`** = Safe testing environment (no real money)
- **`live`** = Real trading (real money at risk)
- **Default is `practice`** for your safety
- **You can add it manually** in Render if it's not showing
- **Or leave it unset** - code defaults to `practice` anyway

**Bottom line**: Starting with `practice` protects you from accidental real money trades during testing! 🛡️

