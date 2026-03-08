"""
LEGACY: Minimal Scalp-Engine (reference only).
Production uses scalp_engine.py (root) with auto_trader_core.
This file was moved from Scalp-Engine/Scalp-Engine/scalp_engine.py (2026-02-11).
Do not use for deployment; Render and docs reference root scalp_engine.py.
"""
# Rest of file unchanged from nested Scalp-Engine/scalp_engine.py
import os
import time
import sys
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import yaml
from pathlib import Path

# Add src to path (when run from Scalp-Engine root)
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.state_reader import MarketStateReader
from src.oanda_client import OandaClient
from src.signal_generator import SignalGenerator
from src.risk_manager import RiskManager
from src.scalping_rl import ScalpingRL

load_dotenv()

class ScalpEngine:
    """Main scalping engine (legacy minimal version)"""

    def __init__(self):
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.oanda_token = os.getenv('OANDA_ACCESS_TOKEN')
        self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID')
        self.oanda_env = os.getenv('OANDA_ENV', 'practice')

        if not self.oanda_token or not self.oanda_account_id:
            if os.getenv('OANDA_ACCESS_TOKEN') and os.getenv('OANDA_ACCOUNT_ID'):
                self.oanda_token = os.getenv('OANDA_ACCESS_TOKEN')
                self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID')
            else:
                raise ValueError("OANDA_ACCESS_TOKEN and OANDA_ACCOUNT_ID must be set")

        market_state_path = os.getenv('MARKET_STATE_FILE_PATH', '/var/data/market_state.json')
        if not market_state_path.endswith('.json'):
            market_state_path = '/var/data/market_state.json'
        if not os.path.exists(market_state_path) and os.path.exists('/var/data'):
            market_state_path = '/var/data/market_state.json'

        self.state_reader = MarketStateReader(state_file_path=market_state_path)
        self.oanda_client = OandaClient(
            access_token=self.oanda_token,
            account_id=self.oanda_account_id,
            environment=self.oanda_env
        )
        ema_periods = self.config.get('indicators', {}).get('ema_periods', [9, 21, 50])
        self.signal_generator = SignalGenerator(ema_periods=ema_periods)
        risk_config = self.config.get('risk', {})
        self.risk_manager = RiskManager(
            risk_per_trade_pct=risk_config.get('risk_per_trade_pct', 0.5),
            daily_max_loss_pct=risk_config.get('daily_max_loss_pct', 2.0),
            stop_loss_pips=risk_config.get('stop_loss_pips', 5.0),
            take_profit_pips=risk_config.get('take_profit_pips', 8.0),
            max_consecutive_losses=risk_config.get('max_consecutive_losses', 3)
        )
        self.max_spread_pips = self.config.get('execution', {}).get('max_spread_pips', 1.5)
        self.pairs = self.config.get('pairs', {}).get('primary', [])
        shared_dir = os.path.dirname(market_state_path)
        db_path = os.path.join(shared_dir, "scalping_rl.db")
        if (not os.path.exists(shared_dir) or not os.access(shared_dir, os.W_OK)) and shared_dir != '.':
            db_path = self.config.get('rl', {}).get('db_path', 'scalping_rl.db')
            if not os.path.isabs(db_path):
                db_path = str(Path(__file__).parent / db_path)
        self.rl_tracker = ScalpingRL(db_path)
        self.mode = self.config.get('execution', {}).get('mode', 'manual')
        self.last_state_update = 0
        self.state_update_interval = 60
        self.active_trades = {}
        self.last_trade_check = 0
        self.trade_check_interval = 30

    def check_spread(self, instrument: str) -> bool:
        price_data = self.oanda_client.get_current_price(instrument)
        return price_data and price_data['spread'] <= self.max_spread_pips

    def get_signal(self, pair: str, regime: str, bias: str) -> tuple:
        instrument = pair.replace("/", "_")
        candles = self.oanda_client.get_candles(instrument, granularity="M1", count=100)
        if not candles or len(candles) < 50:
            return None, 0.0, 0.0
        signal = self.signal_generator.generate_signal(candles, regime=regime, bias=bias)
        strength = self.signal_generator.get_signal_strength(candles)
        import pandas as pd
        closes = pd.Series([c['close'] for c in candles])
        ema_values = self.signal_generator.calculate_emas(closes)
        ema_spread = abs(ema_values.get('ema9', 0) - ema_values.get('ema21', 0)) / (ema_values.get('current_price', 1) or 1) * 10000 if ema_values else 0.0
        return signal, strength, ema_spread

    def execute_trade(self, pair: str, direction: str, account_balance: float, signal_id: Optional[int] = None):
        instrument = pair.replace("/", "_")
        if not self.check_spread(instrument):
            return None
        can_trade, _ = self.risk_manager.can_trade(account_balance)
        if not can_trade:
            return None
        pip_value = 10.0
        position_size = self.risk_manager.calculate_position_size(account_balance, stop_loss_pips=self.risk_manager.stop_loss_pips, pip_value=pip_value)
        units = position_size if direction == "BUY" else -position_size
        order_response = self.oanda_client.place_market_order(instrument=instrument, units=units, stop_loss_pips=self.risk_manager.stop_loss_pips, take_profit_pips=self.risk_manager.take_profit_pips)
        if order_response:
            fill_trans = order_response.get('orderFillTransaction', {})
            trade_id = fill_trans.get('tradeOpened', {}).get('id')
            if trade_id and signal_id:
                self.active_trades[signal_id] = trade_id
            return trade_id
        return None

    def _check_closed_trades(self):
        if not self.active_trades:
            return
        try:
            open_trades = self.oanda_client.get_open_trades()
            open_ids = {t.get('id') for t in open_trades}
            for sig_id, trade_id in list(self.active_trades.items()):
                if trade_id not in open_ids:
                    details = self.oanda_client.get_trade_details(trade_id)
                    if details:
                        pl = float(details.get('realizedPL', 0) or 0)
                        self.rl_tracker.update_outcome(sig_id, pl)
                    del self.active_trades[sig_id]
        except Exception as e:
            print(f"Error checking closed trades: {e}")

    def run(self):
        print("Scalp-Engine (legacy minimal) Started | MODE:", self.mode.upper())
        loop_count = 0
        while True:
            try:
                loop_count += 1
                current_time = time.time()
                if current_time - self.last_state_update > self.state_update_interval:
                    state = self.state_reader.load_state()
                    if state:
                        self.state_reader.last_state = state
                        self.last_state_update = current_time
                    else:
                        self.last_state_update = current_time
                state = self.state_reader.last_state
                if not state:
                    time.sleep(5)
                    continue
                approved_pairs = state.get('approved_pairs', [])
                if not approved_pairs:
                    time.sleep(5)
                    continue
                if loop_count % 20 == 0:
                    account_info = self.oanda_client.get_account_info()
                    if not account_info:
                        time.sleep(5)
                        continue
                    account_balance = float(account_info.get('balance', 0))
                    if current_time - self.last_trade_check > self.trade_check_interval:
                        self._check_closed_trades()
                        self.last_trade_check = current_time
                    regime = state.get('regime', 'NORMAL')
                    bias = state.get('global_bias', 'NEUTRAL')
                    for pair in approved_pairs:
                        if pair not in self.pairs:
                            continue
                        signal, strength, ema_spread = self.get_signal(pair, regime, bias)
                        if signal and strength > 0.5:
                            pip_value = 10.0
                            position_size = self.risk_manager.calculate_position_size(account_balance, stop_loss_pips=self.risk_manager.stop_loss_pips, pip_value=pip_value)
                            sig_id = self.rl_tracker.log_signal(pair, signal, regime, strength, ema_spread, position_size)
                            perf = self.rl_tracker.get_historical_performance(regime=regime, min_strength=strength)
                            min_win_rate = {'HIGH_VOL': 0.6, 'TRENDING': 0.5, 'RANGING': 0.55, 'NORMAL': 0.45}.get(regime, 0.45)
                            if perf['total_trades'] >= 10 and perf['win_rate'] < min_win_rate:
                                continue
                            should_execute = (input(f"Execute {signal} {pair}? (y/n): ").lower() == 'y') if self.mode == 'manual' else True
                            if should_execute:
                                self.execute_trade(pair, signal, account_balance, signal_id=sig_id)
                            time.sleep(5)
                time.sleep(0.5)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"ERROR: {e}")
                time.sleep(5)

if __name__ == "__main__":
    try:
        ScalpEngine().run()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
