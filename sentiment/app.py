#!/usr/bin/env python3
"""
Flask web application for Sentiment-Aware Forex Monitor
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from src.database import Database
import os

# Initialize Flask app with templates directory
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

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

@app.route('/')
def index():
    """Main dashboard"""
    trades = db.get_all_trades(active_only=True)
    recent_alerts = db.get_recent_alerts(hours=24)
    active_events = db.get_active_events()
    
    # Get state for each trade
    trades_with_state = []
    for trade in trades:
        state = db.get_asset_state(trade['asset'])
        asset_events = [e for e in active_events if e['asset'] == trade['asset']]
        trades_with_state.append({
            **trade,
            'last_alert_time': state.get('last_alert_time') if state else None,
            'last_sentiment': state.get('last_sentiment') if state else None,
            'last_sentiment_direction': state.get('last_sentiment_direction') if state else None,
            'active_events': asset_events
        })
    
    return render_template('index.html', 
                         trades=trades_with_state, 
                         recent_alerts=recent_alerts[:10],
                         active_events=active_events)

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """API: Get all trades"""
    trades = db.get_all_trades(active_only=False)
    return jsonify(trades)

@app.route('/api/trades', methods=['POST'])
def add_trade():
    """API: Add a new trade"""
    data = request.json
    
    asset = data.get('asset', '').strip().upper().replace(' ', '')
    trade_direction = data.get('trade_direction', '').lower()
    bias_expectation = data.get('bias_expectation', '').strip()
    sensitivity = data.get('sensitivity', 'medium').lower()
    notes = data.get('notes', '').strip()
    
    # Validation
    if not asset:
        return jsonify({'error': 'Asset is required. Please enter a currency pair (e.g., USD/CAD)'}), 400
    
    # Check format: should be BASE/QUOTE (e.g., USD/CAD)
    if '/' not in asset:
        return jsonify({'error': 'Invalid format. Use format: BASE/QUOTE (e.g., USD/CAD, EUR/USD)'}), 400
    
    parts = asset.split('/')
    if len(parts) != 2:
        return jsonify({'error': 'Invalid format. Must have exactly one "/" separator. Use format: USD/CAD'}), 400
    
    if len(parts[0]) != 3 or len(parts[1]) != 3:
        return jsonify({'error': 'Invalid format. Currency codes must be exactly 3 letters. Use format: USD/CAD'}), 400
    
    # Check for valid currency codes (basic check)
    if not parts[0].isalpha() or not parts[1].isalpha():
        return jsonify({'error': 'Invalid format. Currency codes must contain only letters. Use format: USD/CAD'}), 400
    
    if trade_direction not in ['long', 'short']:
        return jsonify({'error': 'Trade direction must be "long" or "short"'}), 400
    
    if sensitivity not in ['high', 'medium', 'low']:
        sensitivity = 'medium'
    
    success = db.add_trade(asset, trade_direction, bias_expectation, sensitivity, notes)
    
    if success:
        return jsonify({'message': 'Trade added successfully', 'asset': asset}), 201
    else:
        return jsonify({'error': 'Failed to add trade'}), 500

@app.route('/api/trades/<asset>', methods=['PUT'])
def update_trade(asset):
    """API: Update a trade"""
    data = request.json
    
    updates = {}
    if 'trade_direction' in data:
        if data['trade_direction'] not in ['long', 'short']:
            return jsonify({'error': 'Trade direction must be "long" or "short"'}), 400
        updates['trade_direction'] = data['trade_direction']
    
    if 'bias_expectation' in data:
        updates['bias_expectation'] = data['bias_expectation'].strip()
    
    if 'sensitivity' in data:
        if data['sensitivity'] not in ['high', 'medium', 'low']:
            return jsonify({'error': 'Sensitivity must be "high", "medium", or "low"'}), 400
        updates['sensitivity'] = data['sensitivity']
    
    if 'notes' in data:
        updates['notes'] = data['notes'].strip()
    
    success = db.update_trade(asset, **updates)
    
    if success:
        return jsonify({'message': 'Trade updated successfully'})
    else:
        return jsonify({'error': 'Failed to update trade'}), 500

@app.route('/api/trades/<asset>', methods=['DELETE'])
def delete_trade(asset):
    """API: Delete a trade"""
    success = db.delete_trade(asset)
    
    if success:
        return jsonify({'message': 'Trade deleted successfully'})
    else:
        return jsonify({'error': 'Failed to delete trade'}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """API: Get recent alerts"""
    asset = request.args.get('asset')
    hours = int(request.args.get('hours', 24))
    
    alerts = db.get_recent_alerts(asset=asset, hours=hours)
    return jsonify(alerts)

@app.route('/api/state/<asset>', methods=['GET'])
def get_asset_state(asset):
    """API: Get asset state"""
    state = db.get_asset_state(asset)
    active_events = db.get_active_events(asset=asset)
    
    return jsonify({
        'state': state,
        'active_events': active_events
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

