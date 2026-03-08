"""
Execution Mode Enforcer - Ensures opportunities respect execution_mode config
Prevents rogue MARKET executions when RECOMMENDED is configured
Tracks run counts to prevent repeated execution of same opportunity
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass
import logging
import json
import os
from datetime import datetime, timedelta

from .opportunity_id import get_stable_opportunity_id

# Backward-compat alias so callers can keep using get_stable_opp_id
get_stable_opp_id = get_stable_opportunity_id


class ExecutionMode(Enum):
    MARKET = "MARKET"
    RECOMMENDED = "RECOMMENDED"
    MACD_CROSSOVER = "MACD_CROSSOVER"
    HYBRID = "HYBRID"
    FISHER_MULTI_TF = "FISHER_MULTI_TF"  # Fisher Transform system

@dataclass
class ExecutionDirective:
    """What the system should do with this opportunity"""
    action: str  # "EXECUTE_NOW", "PLACE_PENDING", "WAIT_SIGNAL", "REJECT"
    order_type: str  # "MARKET", "LIMIT", "STOP"
    reason: str
    wait_for_signal: Optional[str] = None  # "MACD", "FISHER_H1", etc.
    current_price: Optional[float] = None
    max_runs: int = 1  # Maximum times this opportunity can be executed

class ExecutionModeEnforcer:
    """
    Central authority for determining HOW an opportunity should be executed
    Prevents execution_mode bypasses and rogue trades
    Tracks run counts to prevent repeated execution
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('ExecutionModeEnforcer')
        
        # Track execution history
        self.execution_history_file = "/var/data/execution_history.json"
        self.execution_history = {}  # {opp_id: {'count': int, 'last_executed': datetime}}
        self._load_execution_history()
    
    def get_execution_directive(self, 
                               opportunity: Dict, 
                               current_price: float,
                               max_runs: int = 1,
                               skip_max_runs_check: bool = False) -> ExecutionDirective:
        """
        Determine HOW this opportunity should be executed based on config
        
        Args:
            opportunity: Opportunity dict with pair, direction, entry, etc.
            current_price: Current market price
            max_runs: Maximum times this opportunity can execute (default: 1)
            skip_max_runs_check: If True, do not reject for max_runs (used when replacing pending order)
        
        Returns:
            ExecutionDirective with action, order_type, and reason
        
        This is the SINGLE SOURCE OF TRUTH for execution decisions
        """
        
        # Use stable opp ID for run count (must match UI semi-auto key so reset run count works)
        opp_id = get_stable_opportunity_id(opportunity)
        pair = (opportunity.get('pair') or '').strip().replace('_', '/')
        direction_raw = (opportunity.get('direction') or '').upper()
        
        # Check run count FIRST (applies to ALL execution modes)
        # Skip when skip_max_runs_check=True (e.g. replace pending - same run as cancelled order)
        # No auto-reset when trade closes: user must explicitly "Reset run count" in UI to allow more runs.
        if not skip_max_runs_check and self._has_exceeded_max_runs(opp_id, max_runs):
            return ExecutionDirective(
                action="REJECT",
                order_type="NONE",
                reason=f"Exceeded max_runs ({max_runs}): This opportunity has already been executed {max_runs} time(s)",
                max_runs=max_runs
            )
        
        # FT-DMI-EMA: when 15m trigger not yet met, wait for it (mirror Fisher WAIT_SIGNAL); when met, execute
        if opportunity.get("source") == "FT_DMI_EMA":
            if opportunity.get("ft_15m_trigger_met") is not True:
                return ExecutionDirective(
                    action="WAIT_SIGNAL",
                    order_type="MARKET",
                    reason="FT-DMI-EMA: Setup ready, waiting for 15m Fisher crossover",
                    wait_for_signal="FT_DMI_EMA_M15_TRIGGER",
                    current_price=current_price,
                    max_runs=max_runs
                )
            # 15m trigger met: execute now (FISHER_M15_TRIGGER -> LIMIT/STOP at entry; IMMEDIATE_MARKET -> MARKET)
            mode = (opportunity.get("execution_config") or {}).get("mode", "FISHER_M15_TRIGGER")
            if mode == "IMMEDIATE_MARKET":
                return ExecutionDirective(
                    action="EXECUTE_NOW",
                    order_type="MARKET",
                    reason="FT-DMI-EMA: 15m Fisher trigger met, setup valid (immediate market)",
                    current_price=current_price,
                    max_runs=max_runs
                )
            entry = opportunity.get("entry") or current_price
            direction = (opportunity.get("direction") or "").upper()
            is_long = direction == "LONG"
            if is_long:
                order_type = "LIMIT" if entry < current_price else "STOP"
            else:
                order_type = "LIMIT" if entry > current_price else "STOP"
            return ExecutionDirective(
                action="EXECUTE_NOW",
                order_type=order_type,
                reason="FT-DMI-EMA: 15m Fisher trigger met, limit/stop at entry",
                current_price=current_price,
                max_runs=max_runs
            )
        
        # DMI-EMA: 15m Fisher trigger, 15m +DI/-DI trigger, or IMMEDIATE_MARKET
        if opportunity.get("source") == "DMI_EMA":
            mode = (opportunity.get("execution_config") or {}).get("mode", "FISHER_M15_TRIGGER")
            if mode == "DMI_M15_TRIGGER":
                trigger_met = opportunity.get("dmi_15m_trigger_met") is True
                wait_reason = "DMI-EMA: Setup ready, waiting for 15m +DI/-DI crossover"
                wait_signal = "DMI_EMA_DMI_M15_TRIGGER"
            else:
                trigger_met = opportunity.get("ft_15m_trigger_met") is True
                wait_reason = "DMI-EMA: Setup ready, waiting for 15m Fisher crossover"
                wait_signal = "DMI_EMA_M15_TRIGGER"
            if not trigger_met:
                return ExecutionDirective(
                    action="WAIT_SIGNAL",
                    order_type="MARKET",
                    reason=wait_reason,
                    wait_for_signal=wait_signal,
                    current_price=current_price,
                    max_runs=max_runs
                )
            if mode == "IMMEDIATE_MARKET":
                return ExecutionDirective(
                    action="EXECUTE_NOW",
                    order_type="MARKET",
                    reason="DMI-EMA: 15m trigger met (immediate market)",
                    current_price=current_price,
                    max_runs=max_runs
                )
            entry = opportunity.get("entry") or current_price
            direction = (opportunity.get("direction") or "").upper()
            is_long = direction == "LONG"
            if is_long:
                order_type = "LIMIT" if entry < current_price else "STOP"
            else:
                order_type = "LIMIT" if entry > current_price else "STOP"
            return ExecutionDirective(
                action="EXECUTE_NOW",
                order_type=order_type,
                reason="DMI-EMA: 15m trigger met, limit/stop at entry",
                current_price=current_price,
                max_runs=max_runs
            )
        
        # Fisher opportunities use per-opportunity activation (H1/M15 crossover, IMMEDIATE, etc.)
        if (opportunity.get('fisher_config') or
            opportunity.get('signal_source') == 'FISHER_REVERSAL' or
            opportunity.get('fisher_signal')):
            return self._handle_fisher_mode(opportunity, current_price, max_runs)
        
        # Semi-auto: honor per-opportunity execution_config.mode for non-Fisher (e.g. LLM) opportunities
        per_opp_mode = (opportunity.get('execution_config') or {}).get('mode')
        if per_opp_mode == 'FISHER_H1_CROSSOVER':
            return ExecutionDirective(
                action="WAIT_SIGNAL",
                order_type="MARKET",
                reason="Semi-auto: Waiting for FT crossover (1h)",
                wait_for_signal="H1_CROSSOVER",
                current_price=current_price,
                max_runs=max_runs
            )
        if per_opp_mode == 'FISHER_M15_CROSSOVER':
            return ExecutionDirective(
                action="WAIT_SIGNAL",
                order_type="MARKET",
                reason="Semi-auto: Waiting for FT crossover (15m)",
                wait_for_signal="M15_CROSSOVER",
                current_price=current_price,
                max_runs=max_runs
            )
        if per_opp_mode == 'DMI_H1_CROSSOVER':
            return ExecutionDirective(
                action="WAIT_SIGNAL",
                order_type="MARKET",
                reason="Semi-auto: Waiting for +DI/-DI crossover (1h)",
                wait_for_signal="DMI_H1_CROSSOVER",
                current_price=current_price,
                max_runs=max_runs
            )
        if per_opp_mode == 'DMI_M15_CROSSOVER':
            return ExecutionDirective(
                action="WAIT_SIGNAL",
                order_type="MARKET",
                reason="Semi-auto: Waiting for +DI/-DI crossover (15m)",
                wait_for_signal="DMI_M15_CROSSOVER",
                current_price=current_price,
                max_runs=max_runs
            )
        
        execution_mode = self.config.execution_mode
        # Use per-opportunity mode from semi-auto when present and known; otherwise global config
        known_modes = ('MARKET', 'RECOMMENDED', 'MACD_CROSSOVER', 'HYBRID')
        if per_opp_mode in known_modes:
            mode_val = per_opp_mode
        else:
            mode_val = execution_mode.value if hasattr(execution_mode, 'value') else str(execution_mode)
        
        entry_price = opportunity.get('entry', 0.0)
        direction = opportunity.get('direction', '').upper()
        
        self.logger.info(
            f"🔍 Enforcing execution mode {mode_val} for "
            f"{opportunity.get('pair')} {direction} (run: {self._get_run_count(opp_id) + 1}/{max_runs})"
        )
        
        # CRITICAL: Mode-specific logic (compare by value - config may use different ExecutionMode enum)
        if mode_val == ExecutionMode.MARKET.value:
            return self._handle_market_mode(opportunity, current_price, max_runs)
        
        elif mode_val == ExecutionMode.RECOMMENDED.value:
            return self._handle_recommended_mode(opportunity, entry_price, current_price, direction, max_runs)
        
        elif mode_val == ExecutionMode.MACD_CROSSOVER.value:
            return self._handle_macd_mode(opportunity, current_price, max_runs)
        
        elif mode_val == ExecutionMode.HYBRID.value:
            return self._handle_hybrid_mode(opportunity, entry_price, current_price, direction, max_runs)
        
        elif mode_val == ExecutionMode.FISHER_MULTI_TF.value:
            return self._handle_fisher_mode(opportunity, current_price, max_runs)
        
        else:
            self.logger.error(f"❌ Unknown execution mode: {execution_mode}")
            return ExecutionDirective(
                action="REJECT",
                order_type="NONE",
                reason=f"Unknown execution mode: {execution_mode}",
                max_runs=max_runs
            )
    
    def _handle_market_mode(self, opportunity: Dict, current_price: float, max_runs: int) -> ExecutionDirective:
        """MARKET: Execute immediately at current price"""
        return ExecutionDirective(
            action="EXECUTE_NOW",
            order_type="MARKET",
            reason="MARKET mode - immediate execution",
            current_price=current_price,
            max_runs=max_runs
        )
    
    def _handle_recommended_mode(self, opportunity: Dict, entry_price: float, 
                                current_price: float, direction: str, max_runs: int) -> ExecutionDirective:
        """RECOMMENDED: Place pending order at entry price"""
        
        # Determine LIMIT vs STOP based on entry vs current
        is_long = direction in ['LONG', 'BUY']
        
        if is_long:
            # LONG: entry < current = LIMIT (wait for pullback)
            #       entry > current = STOP (breakout)
            if entry_price < current_price:
                order_type = "LIMIT"
                reason = f"LIMIT order: Entry {entry_price} below current {current_price} (wait for pullback)"
            else:
                order_type = "STOP"
                reason = f"STOP order: Entry {entry_price} above current {current_price} (breakout entry)"
        else:  # SHORT
            # SHORT: entry > current = LIMIT (wait for bounce)
            #        entry < current = STOP (breakdown)
            if entry_price > current_price:
                order_type = "LIMIT"
                reason = f"LIMIT order: Entry {entry_price} above current {current_price} (wait for bounce)"
            else:
                order_type = "STOP"
                reason = f"STOP order: Entry {entry_price} below current {current_price} (breakdown entry)"
        
        return ExecutionDirective(
            action="PLACE_PENDING",
            order_type=order_type,
            reason=reason,
            current_price=current_price,
            max_runs=max_runs
        )
    
    def _handle_macd_mode(self, opportunity: Dict, current_price: float, max_runs: int) -> ExecutionDirective:
        """MACD_CROSSOVER: Wait for MACD signal, then execute at MARKET"""
        return ExecutionDirective(
            action="WAIT_SIGNAL",
            order_type="MARKET",  # Will execute at market when signal arrives
            reason="Waiting for MACD crossover signal",
            wait_for_signal="MACD",
            current_price=current_price,
            max_runs=max_runs
        )
    
    def _handle_hybrid_mode(self, opportunity: Dict, entry_price: float,
                           current_price: float, direction: str, max_runs: int) -> ExecutionDirective:
        """HYBRID: Place pending order AND watch for MACD"""
        
        # Same logic as RECOMMENDED for order type
        is_long = direction in ['LONG', 'BUY']
        
        if is_long:
            order_type = "LIMIT" if entry_price < current_price else "STOP"
        else:
            order_type = "LIMIT" if entry_price > current_price else "STOP"
        
        return ExecutionDirective(
            action="PLACE_PENDING",
            order_type=order_type,
            reason=f"HYBRID: Pending {order_type} order + MACD watch (whichever triggers first)",
            wait_for_signal="MACD",  # Also watching MACD
            current_price=current_price,
            max_runs=max_runs
        )
    
    def _handle_fisher_mode(self, opportunity: Dict, current_price: float, max_runs: int) -> ExecutionDirective:
        """FISHER_MULTI_TF: Fisher Transform system (SEMI-AUTO/MANUAL only, never FULL-AUTO)"""
        
        # Check if opportunity has Fisher configuration
        fisher_config = opportunity.get('fisher_config', {})
        
        if not fisher_config:
            return ExecutionDirective(
                action="REJECT",
                order_type="NONE",
                reason="FISHER_MULTI_TF mode but opportunity has no fisher_config",
                max_runs=max_runs
            )
        
        # CRITICAL: Fisher can NEVER execute on AUTO
        # Must be MANUAL or SEMI_AUTO
        trading_mode = getattr(self.config, 'trading_mode', 'MANUAL')
        if str(trading_mode).upper() == 'AUTO':
            return ExecutionDirective(
                action="REJECT",
                order_type="NONE",
                reason="🚨 FISHER BLOCKED: Fisher opportunities can only trade on MANUAL or SEMI-AUTO mode, never FULL-AUTO",
                max_runs=max_runs
            )
        
        # Fisher mode respects per-opportunity configuration
        activation_trigger = fisher_config.get('activation_trigger', 'H1_CROSSOVER')
        
        if activation_trigger == 'IMMEDIATE':
            return ExecutionDirective(
                action="EXECUTE_NOW",
                order_type="MARKET",
                reason="Fisher: Immediate execution (already confirmed)",
                current_price=current_price,
                max_runs=max_runs
            )
        
        elif activation_trigger in ['H1_CROSSOVER', 'M15_CROSSOVER', 'DMI_H1_CROSSOVER', 'DMI_M15_CROSSOVER']:
            return ExecutionDirective(
                action="WAIT_SIGNAL",
                order_type="MARKET",
                reason=f"Fisher: Waiting for {activation_trigger} confirmation",
                wait_for_signal=activation_trigger,
                current_price=current_price,
                max_runs=max_runs
            )
        
        elif activation_trigger == 'RECOMMENDED_PRICE':
            # Use standard recommended price logic
            return self._handle_recommended_mode(
                opportunity, 
                opportunity.get('entry', current_price),
                current_price,
                opportunity.get('direction', 'LONG'),
                max_runs
            )
        
        else:
            return ExecutionDirective(
                action="REJECT",
                order_type="NONE",
                reason=f"Unknown Fisher activation trigger: {activation_trigger}",
                max_runs=max_runs
            )
    
    def validate_opportunity_before_execution(self, opportunity: Dict) -> tuple:
        """
        Final validation before any execution
        Catches any attempts to bypass execution mode
        
        Returns:
            (valid: bool, reason: str)
        """
        
        # Check if order_type is set
        order_type = opportunity.get('order_type')
        
        if not order_type:
            return False, "No order_type set on opportunity"
        
        # Fisher activation (was waiting for M15/H1 crossover, now execute immediately): MARKET is intended
        fc = opportunity.get('fisher_config') or {}
        if order_type == 'MARKET' and fc.get('activation_trigger') == 'IMMEDIATE':
            return True, "OK"
        
        # Per-opportunity execution mode (semi-auto: "Immediate market" for DMI-EMA/FT-DMI-EMA) overrides global
        # User explicitly chose Immediate market in UI; do not block as "rogue" when global is RECOMMENDED
        exec_cfg = opportunity.get('execution_config') or {}
        if order_type == 'MARKET' and exec_cfg.get('mode') == 'IMMEDIATE_MARKET':
            return True, "OK"
        
        # Verify order_type matches execution mode expectations (compare by value - config may use different enum)
        em = self.config.execution_mode
        em_val = em.value if hasattr(em, 'value') else str(em)
        if em_val == ExecutionMode.RECOMMENDED.value:
            if order_type not in ['LIMIT', 'STOP']:
                return False, (
                    f"🚨 RECOMMENDED mode requires LIMIT/STOP orders, "
                    f"but got {order_type} - BLOCKING ROGUE TRADE"
                )
        
        elif em_val == ExecutionMode.MARKET.value:
            if order_type != 'MARKET':
                self.logger.warning(
                    f"⚠️ MARKET mode but order_type is {order_type} - "
                    f"should be MARKET. Allowing but logging discrepancy."
                )
        
        # Check if Fisher opportunity in AUTO mode (should never happen)
        if opportunity.get('fisher_signal', False):
            trading_mode = getattr(self.config, 'trading_mode', 'MANUAL')
            if str(trading_mode).upper() == 'AUTO':
                return False, "🚨 BLOCKED: Fisher opportunities cannot execute in FULL-AUTO mode"
        
        return True, "OK"
    
    def record_execution(self, opp_id: str):
        """
        Record that an opportunity was executed
        Increments run count for this opportunity
        
        Args:
            opp_id: Unique opportunity identifier
        """
        if opp_id not in self.execution_history:
            self.execution_history[opp_id] = {
                'count': 0,
                'first_executed': datetime.utcnow().isoformat(),
                'last_executed': None
            }
        
        self.execution_history[opp_id]['count'] += 1
        self.execution_history[opp_id]['last_executed'] = datetime.utcnow().isoformat()
        
        self.logger.info(
            f"📊 Recorded execution for {opp_id}: "
            f"Run #{self.execution_history[opp_id]['count']}"
        )
        
        self._save_execution_history()
    
    def _get_run_count(self, opp_id: str) -> int:
        """Get current run count for opportunity. Fall back to legacy key (pair_direction) if not found."""
        count = self.execution_history.get(opp_id, {}).get('count', 0)
        if count == 0 and '_' in opp_id:
            legacy_key = opp_id.split('_', 1)[-1]
            count = self.execution_history.get(legacy_key, {}).get('count', 0)
        return count
    
    def _has_exceeded_max_runs(self, opp_id: str, max_runs: int) -> bool:
        """Check if opportunity has exceeded max run count"""
        current_count = self._get_run_count(opp_id)
        return current_count >= max_runs
    
    def reset_run_count(self, opp_id: str):
        """
        Reset run count for an opportunity
        Use when opportunity is updated with new parameters
        """
        if opp_id in self.execution_history:
            del self.execution_history[opp_id]
            self._save_execution_history()
            self.logger.info(f"🔄 Reset run count for {opp_id}")
    
    def _save_execution_history(self):
        """Save execution history to disk"""
        try:
            os.makedirs(os.path.dirname(self.execution_history_file), exist_ok=True)
            with open(self.execution_history_file, 'w') as f:
                json.dump(self.execution_history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving execution history: {e}")
    
    def _load_execution_history(self):
        """Load execution history from disk"""
        try:
            if os.path.exists(self.execution_history_file):
                with open(self.execution_history_file, 'r') as f:
                    self.execution_history = json.load(f)
                self.logger.info(f"📂 Loaded execution history: {len(self.execution_history)} opportunities tracked")
        except Exception as e:
            self.logger.warning(f"Could not load execution history: {e}")
            self.execution_history = {}
    
    def cleanup_old_history(self, days: int = 30):
        """
        Clean up execution history older than specified days
        
        Args:
            days: Remove records older than this many days
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        to_remove = []
        
        for opp_id, data in self.execution_history.items():
            last_exec = data.get('last_executed')
            if last_exec:
                try:
                    last_exec_dt = datetime.fromisoformat(last_exec)
                    if last_exec_dt < cutoff:
                        to_remove.append(opp_id)
                except:
                    pass
        
        for opp_id in to_remove:
            del self.execution_history[opp_id]
        
        if to_remove:
            self._save_execution_history()
            self.logger.info(f"🧹 Cleaned up {len(to_remove)} old execution records")
