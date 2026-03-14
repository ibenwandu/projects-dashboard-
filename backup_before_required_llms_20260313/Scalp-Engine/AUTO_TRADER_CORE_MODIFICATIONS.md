# AUTO_TRADER_CORE.PY MODIFICATIONS
# Instructions for applying changes to integrate ExecutionModeEnforcer

## MODIFICATION 1: Add imports at the top (after line 17)

ADD after line 17:
```python
# Execution mode enforcer
from src.execution.execution_mode_enforcer import (
    ExecutionModeEnforcer,
    ExecutionDirective,
    ExecutionMode as EnforcerExecutionMode
)
```

## MODIFICATION 2: In PositionManager.__init__() method (after line 622)

ADD after line 622 (after cooldown tracking setup):
```python
        # Execution mode enforcer (CRITICAL for rogue trade prevention)
        self.execution_enforcer = ExecutionModeEnforcer(config)
        self.pending_signals = {}
        self.pending_signals_file = "/var/data/pending_signals.json"
        self._load_pending_signals()
        self.logger.info("✅ ExecutionModeEnforcer initialized")
```

## MODIFICATION 3: Replace open_trade() method (lines 969-1093)

REPLACE the entire open_trade() method with:
```python
    def open_trade(self, opportunity: Dict, market_state: Dict) -> Optional[ManagedTrade]:
        """Open trade with execution mode enforcement and run limits"""
        
        pair = opportunity.get('pair', '')
        direction = opportunity.get('direction', '').upper()
        
        # Check for existing position
        if self.has_existing_position(pair):
            self.logger.error(
                f"🚨 RED FLAG: Attempted to open duplicate order - {pair} already has an order "
                f"(ONLY ONE ORDER PER PAIR ALLOWED) - final safety check blocked"
            )
            return None
        
        # Check if can open
        can_open, reason = self.can_open_new_trade()
        if not can_open:
            self.logger.warning(f"⚠️ Cannot open trade: {reason}")
            return None
        
        # CRITICAL: Get current price for execution directive
        current_price = self._get_current_price(pair)
        if not current_price:
            self.logger.error(f"❌ Cannot get current price for {pair}")
            return None
        
        # Get max_runs from opportunity config
        max_runs = opportunity.get('execution_config', {}).get('max_runs', 1)
        
        # CRITICAL: Get execution directive from enforcer
        directive = self.execution_enforcer.get_execution_directive(
            opportunity, current_price, max_runs=max_runs
        )
        
        self.logger.info(
            f"📋 Execution directive: {directive.action} ({directive.order_type}) "
            f"- {directive.reason}"
        )
        
        # Handle directive
        if directive.action == "REJECT":
            self.logger.warning(f"⚠️ Opportunity rejected: {directive.reason}")
            return None
        
        elif directive.action == "WAIT_SIGNAL":
            self._store_pending_signal(opportunity, directive)
            self.logger.info(f"⏳ Stored, waiting for {directive.wait_for_signal}")
            return None
        
        elif directive.action in ["EXECUTE_NOW", "PLACE_PENDING"]:
            # Set order_type on opportunity (CRITICAL)
            opportunity['order_type'] = directive.order_type
            opportunity['current_price'] = directive.current_price
            
            # Final validation
            valid, reason = self.execution_enforcer.validate_opportunity_before_execution(opportunity)
            if not valid:
                self.logger.error(f"🚨 BLOCKED ROGUE TRADE: {reason}")
                return None
            
            # Create managed trade
            trade = self._create_trade_from_opportunity(opportunity, market_state)
            
            if self.config.trading_mode == TradingMode.MANUAL:
                self.logger.info(
                    f"📋 MANUAL MODE: Trade ready for approval: {trade.pair} {trade.direction} "
                    f"@ {trade.entry_price} (consensus: {trade.consensus_level})"
                )
                return trade
            
            # Execute trade
            order_or_trade_id = self.executor.open_trade(trade)
            if order_or_trade_id:
                # Record execution (CRITICAL - prevents repeated execution)
                opp_id = opportunity.get('id', f"{pair}_{direction}")
                self.execution_enforcer.record_execution(opp_id)
                
                trade.trade_id = order_or_trade_id
                
                # Duplicate check
                normalized_pair = self.normalize_pair(trade.pair)
                duplicate_found = False
                for existing_key, existing_trade in self.active_trades.items():
                    if self.normalize_pair(existing_trade.pair) == normalized_pair:
                        self.logger.error(
                            f"🚨 RED FLAG: Cannot add trade - duplicate pair: "
                            f"{normalized_pair} - closing new trade"
                        )
                        duplicate_found = True
                        try:
                            if trade.state == TradeState.PENDING:
                                self.executor.cancel_order(order_or_trade_id, "RED FLAG: Duplicate")
                            else:
                                self.executor.close_trade(order_or_trade_id, "RED FLAG: Duplicate")
                        except:
                            pass
                        break
                
                if not duplicate_found:
                    trade.state = TradeState.PENDING if directive.order_type in ['LIMIT', 'STOP'] else TradeState.OPEN
                    trade.opened_at = datetime.utcnow()
                    self.active_trades[order_or_trade_id] = trade
                    
                    # RL LOGGING
                    try:
                        from src.scalping_rl_enhanced import ScalpingRLEnhanced
                        from pathlib import Path
                        
                        if os.path.exists('/var/data'):
                            db_path = '/var/data/scalping_rl.db'
                        else:
                            data_dir = Path(__file__).parent.parent / 'data'
                            data_dir.mkdir(exist_ok=True)
                            db_path = str(data_dir / 'scalping_rl.db')
                        
                        rl_db = ScalpingRLEnhanced(db_path=db_path)
                        signal_id = rl_db.log_signal(
                            pair=trade.pair,
                            direction=trade.direction,
                            entry_price=trade.entry_price,
                            stop_loss=trade.stop_loss,
                            take_profit=trade.take_profit,
                            llm_sources=trade.llm_sources or [],
                            consensus_level=trade.consensus_level,
                            rationale=trade.rationale,
                            confidence=trade.confidence,
                            executed=True,
                            trade_id=order_or_trade_id,
                            position_size=trade.units,
                            fisher_signal=opportunity.get('fisher_signal', False)  # Track Fisher signals
                        )
                        trade.rl_signal_id = signal_id
                        self.logger.info(f"📊 RL: Logged trade signal {signal_id}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Could not log to RL: {e}")
                    
                    self._save_state()
                    self.logger.info(
                        f"✅ AUTO MODE: Created {order_or_trade_id}: {trade.pair} {trade.direction} "
                        f"{trade.units} units @ {trade.entry_price} (state: {trade.state.value})"
                    )
                    return trade
                else:
                    return None
            else:
                self.logger.warning(
                    f"⚠️ Trade rejected by OANDA for {trade.pair} {trade.direction} @ {trade.entry_price}"
                )
                return None
        
        return None
```

## MODIFICATION 4: Add helper methods at the end of PositionManager class (before any other methods that follow)

ADD these new methods:
```python
    def _get_current_price(self, pair: str) -> Optional[float]:
        """Get current market price from OANDA"""
        try:
            from oandapyV20.endpoints.pricing import PricingInfo
            
            oanda_pair = pair.replace('/', '_').replace('-', '_')
            params = {"instruments": oanda_pair}
            r = PricingInfo(accountID=self.executor.account_id, params=params)
            
            self.executor.client.request(r)
            prices = r.response.get('prices', [])
            
            if prices:
                bid = float(prices[0].get('bids', [{}])[0].get('price', 0))
                ask = float(prices[0].get('asks', [{}])[0].get('price', 0))
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting price for {pair}: {e}")
            return None

    def _store_pending_signal(self, opportunity: Dict, directive: ExecutionDirective):
        """Store opportunity waiting for signal"""
        signal_id = f"{opportunity['pair']}_{opportunity['direction']}_{directive.wait_for_signal}"
        self.pending_signals[signal_id] = {
            'opportunity': opportunity,
            'directive': {
                'action': directive.action,
                'order_type': directive.order_type,
                'reason': directive.reason,
                'wait_for_signal': directive.wait_for_signal,
                'current_price': directive.current_price,
                'max_runs': directive.max_runs
            },
            'stored_at': datetime.utcnow().isoformat()
        }
        self._save_pending_signals()

    def _save_pending_signals(self):
        """Save pending signals to disk"""
        try:
            os.makedirs(os.path.dirname(self.pending_signals_file), exist_ok=True)
            with open(self.pending_signals_file, 'w') as f:
                json.dump(self.pending_signals, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving pending signals: {e}")

    def _load_pending_signals(self):
        """Load pending signals from disk"""
        try:
            if os.path.exists(self.pending_signals_file):
                with open(self.pending_signals_file, 'r') as f:
                    self.pending_signals = json.load(f)
                self.logger.info(f"📂 Loaded {len(self.pending_signals)} pending signals")
        except Exception as e:
            self.logger.warning(f"Could not load pending signals: {e}")
```

## IMPORTANT NOTES:
1. The ExecutionModeEnforcer prevents rogue MARKET executions when RECOMMENDED is configured
2. Run limit tracking (max_runs) applies to ALL opportunities (LLM + Fisher)
3. Fisher opportunities are marked with fisher_signal=True in RL logging
4. The enforcer blocks Fisher opportunities from executing in FULL-AUTO mode
5. Test thoroughly before deploying

## TO APPLY THESE CHANGES:
1. Back up current auto_trader_core.py
2. Apply modifications in order (1, 2, 3, 4)
3. Test locally first
4. Deploy to GitHub for auto-deployment
