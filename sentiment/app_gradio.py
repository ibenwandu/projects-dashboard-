#!/usr/bin/env python3
"""
Gradio web application for Sentiment-Aware Forex Monitor
Compatible with Hugging Face Spaces
"""

import gradio as gr
import os
from src.database import Database
from datetime import datetime

# Check database connection before initializing
db_url = os.getenv('DATABASE_URL')
if db_url:
    print(f"✅ DATABASE_URL is set (PostgreSQL)")
    # Mask password for security
    if '@' in db_url:
        masked_url = db_url.split('@')[0].split(':')[0] + ':***@' + '@'.join(db_url.split('@')[1:])
        print(f"   Connection: {masked_url}")
else:
    print(f"⚠️  DATABASE_URL not set - using SQLite fallback")

# Initialize database
db = Database()

def get_watchlist_table():
    """Get watchlist as HTML table"""
    trades = db.get_all_trades(active_only=True)
    
    if not trades:
        return "No trades in watchlist. Add your first trade below."
    
    html = "<table style='width:100%; border-collapse: collapse;'>"
    html += "<tr style='background:#f0f0f0;'><th style='padding:10px; border:1px solid #ddd;'>Asset</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Direction</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Bias</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Sensitivity</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Last Alert</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Last Sentiment</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Actions</th></tr>"
    
    for trade in trades:
        state = db.get_asset_state(trade['asset'])
        last_alert = state.get('last_alert_time', '')[:16].replace('T', ' ') if state and state.get('last_alert_time') else 'Never'
        last_sentiment = state.get('last_sentiment', '-').upper() if state and state.get('last_sentiment') else '-'
        
        direction_color = '#10b981' if trade['trade_direction'] == 'long' else '#ef4444'
        html += f"<tr><td style='padding:10px; border:1px solid #ddd;'><strong>{trade['asset']}</strong></td>"
        html += f"<td style='padding:10px; border:1px solid #ddd;'><span style='background:{direction_color}; color:white; padding:4px 8px; border-radius:4px;'>{trade['trade_direction'].upper()}</span></td>"
        html += f"<td style='padding:10px; border:1px solid #ddd;'>{trade.get('bias_expectation', '-')}</td>"
        html += f"<td style='padding:10px; border:1px solid #ddd;'>{trade.get('sensitivity', 'medium').upper()}</td>"
        html += f"<td style='padding:10px; border:1px solid #ddd;'>{last_alert}</td>"
        html += f"<td style='padding:10px; border:1px solid #ddd;'>{last_sentiment}</td>"
        asset_escaped = trade['asset'].replace('"', '&quot;')
        html += f"<td style='padding:10px; border:1px solid #ddd;'><button onclick='deleteTrade(\"{asset_escaped}\")' style='background:#ef4444; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;'>Delete</button></td></tr>"
    
    html += "</table>"
    return html

def add_trade(asset, trade_direction, bias_expectation, sensitivity, notes):
    """Add a new trade"""
    try:
        if not asset:
            return "❌ Error: Asset is required", get_watchlist_table()
        
        asset = asset.strip().upper()
        
        # Validation
        if '/' not in asset:
            return "❌ Error: Invalid format. Use format: BASE/QUOTE (e.g., USD/CAD)", get_watchlist_table()
        
        parts = asset.split('/')
        if len(parts) != 2 or len(parts[0]) != 3 or len(parts[1]) != 3:
            return "❌ Error: Invalid format. Currency codes must be 3 letters. Use format: USD/CAD", get_watchlist_table()
        
        if trade_direction not in ['long', 'short']:
            return "❌ Error: Trade direction must be 'long' or 'short'", get_watchlist_table()
        
        print(f"📝 Attempting to add trade: {asset}, {trade_direction}")
        success = db.add_trade(asset, trade_direction, bias_expectation or "", sensitivity or "medium", notes or "")
        
        if success:
            print(f"✅ Trade {asset} added successfully to database")
            return f"✅ Trade {asset} added successfully!", get_watchlist_table()
        else:
            print(f"❌ Failed to add trade {asset} to database")
            return "❌ Error: Failed to add trade. Check logs for details.", get_watchlist_table()
    except Exception as e:
        print(f"❌ Exception while adding trade: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error: {str(e)}", get_watchlist_table()

def delete_trade(asset):
    """Delete a trade"""
    if not asset:
        return "❌ Error: Asset is required", get_watchlist_table()
    
    success = db.delete_trade(asset)
    
    if success:
        return f"✅ Trade {asset} deleted successfully!", get_watchlist_table()
    else:
        return "❌ Error: Failed to delete trade", get_watchlist_table()

def get_recent_alerts():
    """Get recent alerts"""
    alerts = db.get_recent_alerts(hours=24)
    
    if not alerts:
        return "No alerts in the last 24 hours."
    
    html = "<table style='width:100%; border-collapse: collapse;'>"
    html += "<tr style='background:#f0f0f0;'><th style='padding:10px; border:1px solid #ddd;'>Time</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Asset</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Sentiment</th>"
    html += "<th style='padding:10px; border:1px solid #ddd;'>Confidence</th></tr>"
    
    for alert in alerts[:10]:
        time_str = alert['created_at'][:16].replace('T', ' ') if alert.get('created_at') else '-'
        sentiment = alert.get('sentiment', '-').upper()
        confidence = f"{alert.get('confidence', 0) * 100:.0f}%" if alert.get('confidence') else '-'
        
        html += f"<tr><td style='padding:10px; border:1px solid #ddd;'>{time_str}</td>"
        html += f"<td style='padding:10px; border:1px solid #ddd;'><strong>{alert['asset']}</strong></td>"
        html += f"<td style='padding:10px; border:1px solid #ddd;'>{sentiment}</td>"
        html += f"<td style='padding:10px; border:1px solid #ddd;'>{confidence}</td></tr>"
    
    html += "</table>"
    return html

# Create Gradio interface
with gr.Blocks(title="Sentiment-Aware Forex Monitor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚨 Sentiment-Aware Forex Monitor")
    gr.Markdown("Monitor your forex trades for sentiment shifts")
    
    with gr.Tabs():
        with gr.Tab("Watchlist"):
            gr.Markdown("## Your Watchlist")
            watchlist_display = gr.HTML(value=get_watchlist_table())
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Add New Trade")
                    asset_input = gr.Textbox(
                        label="Forex Pair *",
                        placeholder="USD/CAD",
                        info="Format: BASE/QUOTE (e.g., USD/CAD, EUR/USD)"
                    )
                    trade_direction_input = gr.Radio(
                        choices=["long", "short"],
                        label="Trade Direction *",
                        value="long"
                    )
                    bias_input = gr.Textbox(
                        label="Bias Expectation",
                        placeholder="e.g., Weak USD"
                    )
                    sensitivity_input = gr.Radio(
                        choices=["low", "medium", "high"],
                        label="Sensitivity",
                        value="medium"
                    )
                    notes_input = gr.Textbox(
                        label="Notes",
                        placeholder="Optional notes about this trade",
                        lines=3
                    )
                    add_button = gr.Button("Add Trade", variant="primary")
                    status_output = gr.Textbox(label="Status", interactive=False)
                
                with gr.Column():
                    gr.Markdown("### Delete Trade")
                    delete_asset_input = gr.Textbox(
                        label="Asset to Delete",
                        placeholder="USD/CAD"
                    )
                    delete_button = gr.Button("Delete Trade", variant="stop")
            
            add_button.click(
                fn=add_trade,
                inputs=[asset_input, trade_direction_input, bias_input, sensitivity_input, notes_input],
                outputs=[status_output, watchlist_display]
            )
            
            delete_button.click(
                fn=delete_trade,
                inputs=[delete_asset_input],
                outputs=[status_output, watchlist_display]
            )
        
        with gr.Tab("Recent Alerts"):
            gr.Markdown("## Recent Alerts (Last 24 Hours)")
            alerts_display = gr.HTML(value=get_recent_alerts())
            refresh_alerts = gr.Button("Refresh")
            refresh_alerts.click(fn=get_recent_alerts, outputs=alerts_display)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)

