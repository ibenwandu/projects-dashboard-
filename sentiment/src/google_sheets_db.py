"""Google Sheets database implementation for sentiment monitor"""

import os
from typing import List, Dict, Optional
from datetime import datetime
import json

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

class GoogleSheetsDatabase:
    """Database manager using Google Sheets - supports shared access from multiple services"""
    
    def __init__(self, spreadsheet_id: str = None, credentials_json: str = None):
        """
        Initialize Google Sheets database
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID (from URL)
            credentials_json: JSON string of service account credentials (from env var)
        """
        if not GSHEETS_AVAILABLE:
            raise ImportError("gspread not installed. Install with: pip install gspread google-auth")
        
        self.spreadsheet_id = spreadsheet_id or os.getenv('GOOGLE_SHEETS_ID')
        credentials_json = credentials_json or os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
        
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_ID environment variable not set")
        if not credentials_json:
            raise ValueError("GOOGLE_SHEETS_CREDENTIALS_JSON environment variable not set")
        
        # Initialize Google Sheets client
        try:
            creds_dict = json.loads(credentials_json)
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            print("✅ Connected to Google Sheets")
        except Exception as e:
            print(f"❌ Failed to connect to Google Sheets: {e}")
            raise
        
        # Initialize worksheets (create if they don't exist)
        self._init_worksheets()
    
    def _init_worksheets(self):
        """Initialize or get worksheets"""
        try:
            self.watchlist_sheet = self.spreadsheet.worksheet('watchlist')
        except:
            self.watchlist_sheet = self.spreadsheet.add_worksheet(title='watchlist', rows=1000, cols=10)
            # Add headers
            self.watchlist_sheet.append_row(['id', 'asset', 'trade_direction', 'bias_expectation', 
                                           'sensitivity', 'notes', 'active', 'created_at', 'updated_at'])
        
        try:
            self.alerts_sheet = self.spreadsheet.worksheet('alert_history')
        except:
            self.alerts_sheet = self.spreadsheet.add_worksheet(title='alert_history', rows=1000, cols=10)
            self.alerts_sheet.append_row(['id', 'asset', 'sentiment', 'sentiment_direction', 
                                         'confidence', 'alert_data', 'created_at'])
        
        try:
            self.state_sheet = self.spreadsheet.worksheet('asset_state')
        except:
            self.state_sheet = self.spreadsheet.add_worksheet(title='asset_state', rows=1000, cols=10)
            self.state_sheet.append_row(['asset', 'last_alert_time', 'last_sentiment', 
                                        'last_sentiment_direction', 'last_confidence', 'last_check_time'])
        
        try:
            self.events_sheet = self.spreadsheet.worksheet('high_impact_events')
        except:
            self.events_sheet = self.spreadsheet.add_worksheet(title='high_impact_events', rows=1000, cols=10)
            self.events_sheet.append_row(['id', 'asset', 'event_type', 'event_description', 
                                         'event_date', 'is_active', 'created_at'])
        
        print("✅ Worksheets initialized")
    
    def _get_next_id(self, sheet) -> int:
        """Get next ID for a sheet"""
        try:
            records = sheet.get_all_records()
            if not records:
                return 1
            ids = []
            for r in records:
                id_val = r.get('id')
                if id_val:
                    try:
                        ids.append(int(id_val))
                    except (ValueError, TypeError):
                        pass
            return max(ids, default=0) + 1
        except Exception as e:
            print(f"Error getting next ID: {e}")
            return 1
    
    # Watchlist operations
    def add_trade(self, asset: str, trade_direction: str, bias_expectation: str = "",
                  sensitivity: str = "medium", notes: str = "") -> bool:
        """Add a trade to watchlist"""
        try:
            # Check if asset already exists
            records = self.watchlist_sheet.get_all_records()
            for i, record in enumerate(records):
                if record.get('asset') == asset and (record.get('active') == '1' or record.get('active') == 1):
                    # Update existing
                    row_num = i + 2  # +2 because headers + 1-indexed
                    self.watchlist_sheet.update(f'C{row_num}:F{row_num}', 
                                              [[trade_direction, bias_expectation, sensitivity, notes]])
                    self.watchlist_sheet.update(f'I{row_num}', [[datetime.now().isoformat()]])
                    return True
            
            # Add new
            next_id = self._get_next_id(self.watchlist_sheet)
            self.watchlist_sheet.append_row([
                next_id, asset, trade_direction, bias_expectation, 
                sensitivity, notes, 1, datetime.now().isoformat(), datetime.now().isoformat()
            ])
            return True
        except Exception as e:
            print(f"Error adding trade: {e}")
            return False
    
    def get_all_trades(self, active_only: bool = True) -> List[Dict]:
        """Get all trades from watchlist"""
        try:
            records = self.watchlist_sheet.get_all_records()
            if active_only:
                return [r for r in records if r.get('active') == '1' or r.get('active') == 1]
            return records
        except Exception as e:
            print(f"Error getting trades: {e}")
            return []
    
    def get_trade(self, asset: str) -> Optional[Dict]:
        """Get a specific trade"""
        trades = self.get_all_trades(active_only=False)
        for trade in trades:
            if trade.get('asset') == asset:
                return trade
        return None
    
    def update_trade(self, asset: str, trade_direction: str = None, bias_expectation: str = None,
                    sensitivity: str = None, notes: str = None) -> bool:
        """Update a trade"""
        try:
            records = self.watchlist_sheet.get_all_records()
            for i, record in enumerate(records):
                if record.get('asset') == asset:
                    row_num = i + 2  # +2 because headers + 1-indexed
                    updates = {}
                    if trade_direction is not None:
                        updates[f'C{row_num}'] = trade_direction
                    if bias_expectation is not None:
                        updates[f'D{row_num}'] = bias_expectation
                    if sensitivity is not None:
                        updates[f'E{row_num}'] = sensitivity
                    if notes is not None:
                        updates[f'F{row_num}'] = notes
                    updates[f'I{row_num}'] = datetime.now().isoformat()
                    
                    # Batch update
                    self.watchlist_sheet.batch_update([{'range': k, 'values': [[v]]} for k, v in updates.items()])
                    return True
            return False
        except Exception as e:
            print(f"Error updating trade: {e}")
            return False
    
    def delete_trade(self, asset: str) -> bool:
        """Delete (deactivate) a trade"""
        try:
            records = self.watchlist_sheet.get_all_records()
            for i, record in enumerate(records):
                if record.get('asset') == asset:
                    row_num = i + 2  # +2 because headers + 1-indexed
                    self.watchlist_sheet.update(f'G{row_num}', [[0]])
                    return True
            return False
        except Exception as e:
            print(f"Error deleting trade: {e}")
            return False
    
    # Alert history operations
    def add_alert(self, asset: str, sentiment: str, sentiment_direction: str = None,
                  confidence: float = None, alert_data: Dict = None):
        """Add alert to history"""
        try:
            next_id = self._get_next_id(self.alerts_sheet)
            alert_data_str = json.dumps(alert_data) if alert_data else ''
            self.alerts_sheet.append_row([
                next_id, asset, sentiment, sentiment_direction,
                confidence, alert_data_str, datetime.now().isoformat()
            ])
        except Exception as e:
            print(f"Error adding alert: {e}")
    
    def get_recent_alerts(self, asset: str = None, hours: int = 24) -> List[Dict]:
        """Get recent alerts"""
        try:
            records = self.alerts_sheet.get_all_records()
            cutoff = datetime.now().timestamp() - (hours * 3600)
            filtered = []
            for record in records:
                created_at = record.get('created_at', '')
                if created_at:
                    try:
                        record_time = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                        if record_time > cutoff:
                            if not asset or record.get('asset') == asset:
                                filtered.append(record)
                    except:
                        pass
            return sorted(filtered, key=lambda x: x.get('created_at', ''), reverse=True)
        except Exception as e:
            print(f"Error getting alerts: {e}")
            return []
    
    # Asset state operations
    def update_asset_state(self, asset: str, last_sentiment: str = None,
                          last_sentiment_direction: str = None, last_confidence: float = None,
                          last_alert_time: datetime = None):
        """Update asset state"""
        try:
            records = self.state_sheet.get_all_records()
            for i, record in enumerate(records):
                if record.get('asset') == asset:
                    row_num = i + 2  # +2 because headers + 1-indexed
                    updates = {}
                    if last_sentiment is not None:
                        updates[f'C{row_num}'] = last_sentiment
                    if last_sentiment_direction is not None:
                        updates[f'D{row_num}'] = last_sentiment_direction
                    if last_confidence is not None:
                        updates[f'E{row_num}'] = last_confidence
                    if last_alert_time:
                        updates[f'B{row_num}'] = last_alert_time.isoformat()
                    updates[f'F{row_num}'] = datetime.now().isoformat()
                    self.state_sheet.batch_update([{'range': k, 'values': [[v]]} for k, v in updates.items()])
                    return
            
            # Create new state
            self.state_sheet.append_row([
                asset,
                last_alert_time.isoformat() if last_alert_time else '',
                last_sentiment or '',
                last_sentiment_direction or '',
                last_confidence or '',
                datetime.now().isoformat()
            ])
        except Exception as e:
            print(f"Error updating asset state: {e}")
    
    def get_asset_state(self, asset: str) -> Optional[Dict]:
        """Get asset state"""
        try:
            records = self.state_sheet.get_all_records()
            for record in records:
                if record.get('asset') == asset:
                    state = dict(record)
                    state['active_events'] = self.get_active_events(asset=asset)
                    return state
            return None
        except Exception as e:
            print(f"Error getting asset state: {e}")
            return None
    
    def was_alerted_recently(self, asset: str, minutes: int = 60) -> bool:
        """Check if alerted recently"""
        state = self.get_asset_state(asset)
        if not state or not state.get('last_alert_time'):
            return False
        try:
            last_alert = datetime.fromisoformat(state['last_alert_time'].replace('Z', '+00:00'))
            cutoff = datetime.now().timestamp() - (minutes * 60)
            return last_alert.timestamp() > cutoff
        except:
            return False
    
    # High-impact events operations
    def add_high_impact_event(self, asset: str, event_type: str, event_description: str,
                              event_date: datetime = None):
        """Add high-impact event"""
        try:
            next_id = self._get_next_id(self.events_sheet)
            self.events_sheet.append_row([
                next_id, asset, event_type, event_description,
                event_date.isoformat() if event_date else '', 1, datetime.now().isoformat()
            ])
        except Exception as e:
            print(f"Error adding event: {e}")
    
    def get_active_events(self, asset: str = None) -> List[Dict]:
        """Get active high-impact events"""
        try:
            records = self.events_sheet.get_all_records()
            filtered = [r for r in records if r.get('is_active') == '1' or r.get('is_active') == 1]
            if asset:
                filtered = [r for r in filtered if r.get('asset') == asset]
            return filtered
        except Exception as e:
            print(f"Error getting events: {e}")
            return []
    
    def deactivate_event(self, event_id: int):
        """Deactivate an event"""
        try:
            records = self.events_sheet.get_all_records()
            for record in records:
                if str(record.get('id')) == str(event_id):
                    row_num = records.index(record) + 2
                    self.events_sheet.update(f'F{row_num}', [[0]])
                    return
        except Exception as e:
            print(f"Error deactivating event: {e}")

