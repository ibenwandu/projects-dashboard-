# Scalp-Engine UI - Quick Start

## 🚀 Running the UI

### Option 1: PowerShell Script (Easiest)

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
.\run_ui.ps1
```

### Option 2: Direct Command

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
streamlit run scalp_ui.py
```

The UI will automatically open in your browser at `http://localhost:8501`

---

## 📊 UI Features

### Tab 1: Opportunities
- **Current Market State** - Regime, bias, approved pairs
- **Timestamp Display** - Shows how old the data is
- **Approved Pairs** - List of pairs ready for trading
- **Performance Metrics** - Win rate and PnL per pair
- **Trading Opportunities** - Detailed opportunity information

### Tab 2: Recent Signals
- **Signal History** - Last 20 signals (configurable)
- **Filters** - By outcome, pair, regime
- **Summary Stats** - Total, pending, wins, losses
- **Detailed View** - All signal parameters

### Tab 3: Performance
- **Overall Stats** - Total trades, win rate, PnL
- **By Regime** - Performance breakdown by market regime
- **By Pair** - Performance breakdown by currency pair
- **Top Performers** - Best performing pairs

### Tab 4: Market State
- **Raw JSON** - Full market state data
- **Timestamp Info** - Last update time and age

---

## 🔄 Refresh Functionality

### Manual Refresh
- Click **"🔄 Refresh Data"** button in sidebar
- Clears cache and reloads all data

### Auto-Refresh
- Enable **"Auto-refresh (30s)"** checkbox
- Automatically refreshes every 30 seconds

---

## ⚙️ Settings

### Sidebar Controls:
- **Show Pending Trades** - Toggle pending trade visibility
- **Show Closed Trades** - Toggle closed trade visibility
- **Recent Signals Limit** - Number of signals to display (10-50)

---

## 📱 What You'll See

### When Opportunities Available:
```
✅ Approved Trading Pairs
- EUR/USD (Win Rate: 65.0%, 20 trades)
- USD/JPY (Win Rate: 55.0%, 15 trades)

🎯 Trading Opportunities
- EUR/USD - BUY
  Entry: 1.0850
  Stop Loss: 1.0845
  Take Profit: 1.0858
```

### When No Opportunities:
```
⚠️ No approved pairs available. 
Waiting for Trade-Alerts to provide opportunities.
```

### Timestamp Display:
```
Last Updated: 2 minutes ago
2026-01-09 16:54:39
```

---

## 🔧 Troubleshooting

### UI won't start
```powershell
# Install Streamlit
pip install streamlit

# Try again
streamlit run scalp_ui.py
```

### No data showing
- Check if `scalping_rl.db` exists
- Check if `market_state.json` exists (from Trade-Alerts)
- Verify file paths are correct

### Timestamp shows "Unknown"
- Check timestamp format in database/market state
- Verify datetime parsing

---

## 🌐 Deploying UI to Web

### Streamlit Cloud (Free)

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect GitHub repo
4. Set main file: `scalp_ui.py`
5. Deploy!

### Self-Hosted

```bash
# Install streamlit
pip install streamlit

# Run with custom port
streamlit run scalp_ui.py --server.port 8501

# Or use nginx reverse proxy
```

---

## 📝 Notes

- **Data Source:** UI reads from `scalping_rl.db` and `market_state.json`
- **Cache:** Data is cached for 30 seconds to reduce database load
- **Real-time:** Use auto-refresh for near real-time updates
- **Offline:** UI works offline if database and market state files are available

---

**Enjoy your Scalp-Engine Dashboard!** 📈
