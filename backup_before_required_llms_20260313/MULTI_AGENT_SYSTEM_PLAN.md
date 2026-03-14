# Multi-Agent Trading System Implementation Plan

**Date:** 2026-02-16
**Status:** Planning Phase
**Version:** 1.0

---

## Executive Summary

This plan designs a three-agent system that autonomously reviews trading logs, identifies improvement opportunities, recommends changes, and implements code improvements with built-in safety mechanisms.

**Agents:**
1. **Analyst Agent**: Log review & consistency validation
2. **Forex Trading Expert Agent**: Trade performance analysis & recommendations
3. **Coding Expert Agent**: Implementation of recommended improvements
4. **Orchestrator Agent**: Coordinates all agents, manages backups/rollback, tracks execution

**Key Features:**
- JSON-based inter-agent communication (primary)
- API fallback for complex data transfer
- Automatic git backups before code changes
- Rollback capability via git reset
- Daily execution cycle (user configurable)
- Structured audit trail of all changes

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────┐
│         Orchestrator Agent (Master Coordinator)      │
│  - Schedules daily analysis runs                      │
│  - Manages state machine for workflow                 │
│  - Backup/rollback operations                         │
│  - Error recovery and retry logic                     │
│  - Audit log maintenance                              │
└──────┬──────────────────┬──────────────────┬─────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Analyst Agent   │  │  Forex Trading   │  │  Coding Expert   │
│                  │  │     Expert       │  │     Agent        │
│ • Log parsing    │  │                  │  │                  │
│ • Validation     │  │ • Performance    │  │ • Code review    │
│ • Consistency    │  │   analysis       │  │ • Implementation │
│   checks         │  │ • Risk metrics   │  │ • Testing        │
│ • Data export    │  │ • Opportunity    │  │ • Validation     │
│                  │  │   identification │  │ • Deployment     │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Shared JSON        │
                    │  Communication      │
                    │  File System        │
                    └─────────────────────┘
```

### Data Flow Diagram

```
Daily Cycle (User Configurable Time):
1. Orchestrator triggers workflow
2. Analyst pulls logs → analyzes → produces analysis.json
3. Forex Expert reads analysis.json → produces recommendations.json
4. Orchestrator reviews for implementation feasibility
5. Coding Expert reads recommendations.json → implements → produces implementation_report.json
6. Orchestrator validates → creates backup → applies changes → commits to git
7. All agents produce final audit_trail.json entry
```

---

## Directory Structure

```
Trade-Alerts/
├── agents/                                    # New agents directory
│   ├── __init__.py
│   ├── orchestrator_agent.py                  # Main coordinator
│   ├── analyst_agent.py                       # Log analyzer
│   ├── forex_trading_expert_agent.py          # Trade recommender
│   ├── coding_expert_agent.py                 # Code implementer
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── json_schema.py                     # Shared JSON schemas
│   │   ├── backup_manager.py                  # Git backup/rollback
│   │   ├── agent_communication.py             # JSON file I/O + API fallback
│   │   └── audit_logger.py                    # Centralized audit logging
│   └── tests/
│       ├── __init__.py
│       ├── test_analyst_agent.py
│       ├── test_forex_expert.py
│       ├── test_coding_expert.py
│       └── test_orchestrator.py
│
├── agent_data/                                # Persistent JSON files
│   ├── README.md                              # Data directory guide
│   ├── analysis/
│   │   ├── latest_analysis.json               # Current analysis output
│   │   ├── analysis_history.jsonl             # Line-delimited archive
│   │   └── metadata.json                      # Analysis metadata
│   ├── recommendations/
│   │   ├── latest_recommendations.json        # Current recommendations
│   │   ├── recommendations_history.jsonl      # Archive
│   │   └── metadata.json
│   ├── implementations/
│   │   ├── latest_implementation_report.json  # Current implementation results
│   │   ├── implementation_history.jsonl       # Archive
│   │   └── metadata.json
│   ├── orchestrator/
│   │   ├── workflow_state.json                # Current workflow state
│   │   ├── schedule.json                      # Execution schedule
│   │   ├── backups.json                       # Backup registry (for rollback)
│   │   └── audit_trail.jsonl                  # Complete audit log
│   └── logs/
│       ├── analyst_logs.jsonl                 # Analyst execution logs
│       ├── expert_logs.jsonl                  # Forex expert logs
│       ├── coding_logs.jsonl                  # Coding expert logs
│       └── orchestrator_logs.jsonl            # Orchestrator logs
│
└── agent_scheduler.py                         # Scheduler for daily runs
```

---

## JSON Communication Schemas

### 1. Analyst Output: `analysis/latest_analysis.json`

```json
{
  "metadata": {
    "timestamp": "2026-02-16T10:30:00Z",
    "analysis_id": "analysis_20260216_103000",
    "agent_version": "1.0.0",
    "cycle_number": 42
  },
  "summary": {
    "total_trades_reviewed": 12,
    "period_start": "2026-02-15T00:00:00Z",
    "period_end": "2026-02-16T00:00:00Z",
    "overall_health": "GOOD",  # CRITICAL, WARNING, GOOD
    "confidence_score": 0.87
  },
  "trade_consistency": {
    "ui_scalp_engine_match": {
      "status": "VALID",  # VALID, MISMATCH, WARNING
      "matches": 11,
      "mismatches": 1,
      "details": [
        {
          "trade_id": "EUR/USD_LONG_1",
          "issue": "Entry price differs by 15 pips",
          "ui_value": 1.0850,
          "scalp_engine_value": 1.0865,
          "severity": "MEDIUM"
        }
      ]
    },
    "scalp_engine_oanda_match": {
      "status": "VALID",
      "matches": 11,
      "mismatches": 1,
      "details": [
        {
          "trade_id": "GBP/USD_SHORT_2",
          "issue": "OANDA position missing from scalp-engine logs",
          "severity": "HIGH"
        }
      ]
    }
  },
  "stop_loss_validation": {
    "total_sl_checks": 12,
    "sl_correct": 10,
    "sl_issues": 2,
    "details": [
      {
        "trade_id": "EUR/USD_LONG_1",
        "expected_sl_type": "ATR_TRAILING",
        "actual_sl_type": "ATR_TRAILING",
        "status": "VALID",
        "sl_value": 1.0800,
        "current_price": 1.0900,
        "profit_pips": 100
      },
      {
        "trade_id": "GBP/USD_SHORT_2",
        "expected_sl_type": "STRUCTURE_ATR_STAGED",
        "actual_sl_type": "FIXED",
        "status": "INVALID",
        "severity": "HIGH",
        "root_cause": "Failed to transition from FIXED to BE_TO_TRAILING phase"
      }
    ]
  },
  "trailing_sl_analysis": {
    "total_trailing_sl": 8,
    "actively_trailing": 6,
    "not_trailing": 2,
    "issues": [
      {
        "trade_id": "AUD/USD_LONG_3",
        "problem": "Trailing SL not updating after 30 minutes",
        "current_sl": 0.6800,
        "expected_sl": 0.6850,
        "last_update": "2026-02-16T08:45:00Z",
        "time_since_update_minutes": 105,
        "status": "STALLED",
        "root_cause_hypothesis": "Possible issue in _update_trailing_sl logic"
      },
      {
        "trade_id": "USD/JPY_SHORT_5",
        "problem": "Trailing SL jumping erratically",
        "recent_updates": [
          {"timestamp": "2026-02-16T09:30:00Z", "sl": 108.50},
          {"timestamp": "2026-02-16T09:35:00Z", "sl": 108.35},
          {"timestamp": "2026-02-16T09:40:00Z", "sl": 108.60}
        ],
        "status": "ERRATIC",
        "root_cause_hypothesis": "Possible race condition in ATR calculation or regime detection"
      }
    ]
  },
  "profitability_metrics": {
    "total_profit_pips": 245,
    "total_loss_pips": -85,
    "net_profit_pips": 160,
    "win_rate": 0.75,  # 9 wins / 12 trades
    "winning_trades": 9,
    "losing_trades": 3,
    "average_win_pips": 27.2,
    "average_loss_pips": -28.3,
    "profit_factor": 2.88,  # Total profit / Total loss
    "risk_reward_ratio": 0.96
  },
  "risk_management_metrics": {
    "max_drawdown_pips": 145,
    "max_drawdown_percent": 2.3,
    "stop_loss_hit_rate": 0.25,  # 3 trades hit SL out of 12
    "average_sl_distance_pips": 35,
    "largest_winning_trade_pips": 85,
    "largest_losing_trade_pips": -45
  },
  "recommendations_for_expert": {
    "priority_issues": [
      {
        "issue_id": "TRAILING_SL_STALL",
        "severity": "HIGH",
        "trade_ids_affected": ["AUD/USD_LONG_3"],
        "description": "Trailing stop loss not updating for extended period"
      },
      {
        "issue_id": "PHASE_TRANSITION_FAILURE",
        "severity": "HIGH",
        "trade_ids_affected": ["GBP/USD_SHORT_2"],
        "description": "STRUCTURE_ATR_STAGED failing to transition from FIXED to BE_TO_TRAILING"
      },
      {
        "issue_id": "ATR_VOLATILITY_REGIME_RACE",
        "severity": "MEDIUM",
        "trade_ids_affected": ["USD/JPY_SHORT_5"],
        "description": "Possible race condition in volatility regime detection causing erratic SL updates"
      }
    ],
    "opportunities": [
      {
        "opportunity_id": "IMPROVE_FISHER_SIGNAL",
        "description": "Fisher Transform signals consistently 5-10 minutes late; pre-filtering with volume could improve entry timing",
        "potential_improvement": "2-5% win rate increase"
      }
    ]
  },
  "log_locations": {
    "ui_logs": "Scalp-Engine/logs/ui_activity.log",
    "scalp_engine_logs": "Scalp-Engine/logs/scalp_engine.log",
    "oanda_logs": "Scalp-Engine/logs/oanda_trades.log"
  }
}
```

### 2. Forex Trading Expert Output: `recommendations/latest_recommendations.json`

```json
{
  "metadata": {
    "timestamp": "2026-02-16T10:45:00Z",
    "recommendation_id": "rec_20260216_104500",
    "agent_version": "1.0.0",
    "analysis_id": "analysis_20260216_103000",
    "cycle_number": 42
  },
  "executive_summary": {
    "overall_assessment": "System performing well with specific areas for improvement",
    "confidence_level": 0.85,
    "recommended_actions": 3,
    "estimated_impact": {
      "win_rate_improvement": 0.08,  # 8% improvement potential
      "risk_reward_improvement": 0.15,  # 15% improvement
      "max_drawdown_reduction_percent": 10
    }
  },
  "critical_issues_requiring_code_changes": [
    {
      "issue_id": "TRAILING_SL_STALL_FIX",
      "priority": "CRITICAL",
      "description": "AUD/USD_LONG_3 trailing SL stopped updating",
      "affected_code_file": "Scalp-Engine/auto_trader_core.py",
      "affected_methods": ["_update_trailing_sl", "_check_atr_trailing_conversion"],
      "root_cause_analysis": "The trailing SL update loop may have an exception being silently caught. Need to add explicit logging and validation.",
      "recommended_fix": {
        "type": "CODE_CHANGE",
        "priority": "CRITICAL",
        "files_to_modify": [
          {
            "file": "Scalp-Engine/auto_trader_core.py",
            "method": "_update_trailing_sl",
            "changes": [
              "Add try-except blocks with detailed logging around ATR fetch",
              "Add validation to ensure SL moves only in profit direction",
              "Log every SL update with timestamp for debugging"
            ]
          }
        ],
        "testing_required": [
          "Verify SL updates every 30 seconds for ATR_TRAILING trades",
          "Verify SL never moves against profit",
          "Test with different volatility regimes (HIGH_VOL, NORMAL)"
        ]
      }
    },
    {
      "issue_id": "PHASE_TRANSITION_RACE_CONDITION",
      "priority": "CRITICAL",
      "description": "STRUCTURE_ATR_STAGED not transitioning from FIXED to BE_TO_TRAILING phase",
      "affected_code_file": "Scalp-Engine/auto_trader_core.py",
      "affected_methods": ["_check_structure_atr_staged_phase2", "breakeven_applied flag"],
      "root_cause_analysis": "Race condition where phase 2.1 flag not being set correctly, preventing subsequent transitions",
      "recommended_fix": {
        "type": "CODE_CHANGE",
        "priority": "CRITICAL",
        "files_to_modify": [
          {
            "file": "Scalp-Engine/auto_trader_core.py",
            "method": "_check_structure_atr_staged_phase2",
            "changes": [
              "Ensure breakeven_applied flag is atomically set before phase 2.2 check",
              "Add guard to prevent duplicate breakeven transitions",
              "Add logging to track flag state changes"
            ]
          }
        ],
        "testing_required": [
          "Trade to +1R and verify phase 2.1 applied",
          "Trade to +2R and verify phase 2.2 applied",
          "Trade to +3R and verify phase 2.3 applied",
          "Verify no duplicate transitions"
        ]
      }
    },
    {
      "issue_id": "VOLATILITY_REGIME_RACE_CONDITION",
      "priority": "HIGH",
      "description": "Erratic trailing SL updates suggesting race condition in volatility regime detection",
      "affected_code_file": "Scalp-Engine/auto_trader_core.py",
      "affected_methods": ["_get_current_atr", "_detect_volatility_regime", "_update_atr_trailing_distance"],
      "root_cause_analysis": "Multiple calls to volatility regime may return different results in rapid succession, causing SL to jump",
      "recommended_fix": {
        "type": "CODE_CHANGE",
        "priority": "HIGH",
        "files_to_modify": [
          {
            "file": "Scalp-Engine/auto_trader_core.py",
            "method": "_check_atr_trailing_conversion",
            "changes": [
              "Cache volatility regime for minimum 5-minute window",
              "Only update regime if change persists for 2+ consecutive checks",
              "Add smoothing to ATR calculation to reduce jumps"
            ]
          }
        ],
        "testing_required": [
          "Verify SL updates smoothly without erratic jumps",
          "Verify regime changes only when confirmed over time",
          "Test with volatile market conditions (high ATR swings)"
        ]
      }
    }
  ],
  "performance_improvement_recommendations": [
    {
      "recommendation_id": "FISHER_SIGNAL_TIMING",
      "priority": "MEDIUM",
      "category": "ENTRY_OPTIMIZATION",
      "description": "Fisher Transform signals are consistently 5-10 minutes late",
      "current_behavior": "Signal generated when Fisher crosses threshold",
      "suggested_behavior": "Pre-filter with volume spike to catch Fisher earlier",
      "implementation_effort": "MEDIUM",
      "estimated_impact": {
        "win_rate_change": 0.05,  # 5% improvement
        "average_win_size_change": 0.08  # 8% larger wins
      },
      "code_changes_needed": [
        {
          "file": "Scalp-Engine/src/indicators/fisher_reversal_analyzer.py",
          "change_type": "ADD_VOLUME_FILTER",
          "description": "Add volume spike detection before Fisher confirmation"
        }
      ]
    },
    {
      "recommendation_id": "DMI_EMA_ALIGNMENT_TIGHTENING",
      "priority": "MEDIUM",
      "category": "SIGNAL_QUALITY",
      "description": "Current DMI-EMA alignment threshold may be too loose, accepting weak setups",
      "suggestion": "Tighten alignment requirement from ±30 pips to ±20 pips",
      "estimated_impact": {
        "win_rate_change": 0.03,  # 3% improvement (fewer losing trades)
        "trade_frequency_change": -0.20  # 20% fewer trades (more selective)
      }
    }
  ],
  "non_code_recommendations": [
    {
      "recommendation_id": "POSITION_SIZING_REVIEW",
      "priority": "MEDIUM",
      "description": "Current position sizing not accounting for recent volatility changes",
      "current_approach": "Fixed 2% per trade",
      "suggested_approach": "Dynamic sizing: 2% for NORMAL volatility, 1% for HIGH_VOL",
      "rationale": "Would reduce max drawdown by ~10% during high volatility periods"
    }
  ]
}
```

### 3. Coding Expert Output: `implementations/latest_implementation_report.json`

```json
{
  "metadata": {
    "timestamp": "2026-02-16T14:30:00Z",
    "implementation_id": "impl_20260216_143000",
    "agent_version": "1.0.0",
    "recommendation_id": "rec_20260216_104500",
    "cycle_number": 42
  },
  "summary": {
    "recommendations_processed": 3,
    "recommendations_implemented": 3,
    "recommendations_deferred": 0,
    "total_files_modified": 2,
    "total_commits": 1,
    "testing_status": "PASSED",
    "deployment_status": "READY_FOR_ORCHESTRATOR_APPROVAL"
  },
  "implementations": [
    {
      "implementation_id": "impl_1",
      "recommendation_id": "TRAILING_SL_STALL_FIX",
      "status": "COMPLETED",
      "file": "Scalp-Engine/auto_trader_core.py",
      "method": "_update_trailing_sl",
      "changes_made": [
        {
          "change_type": "ADD_LOGGING",
          "description": "Added detailed logging for every SL update",
          "line_numbers": [2450, 2475],
          "code_snippet": "logger.debug(f'ATR_TRAILING SL update: {trade_id} from {old_sl} to {new_sl}')"
        },
        {
          "change_type": "ADD_VALIDATION",
          "description": "Added validation to ensure SL only moves in profit direction",
          "line_numbers": [2470],
          "code_snippet": "if is_long and new_sl <= old_sl:\n    new_sl = old_sl  # Never move SL backwards"
        },
        {
          "change_type": "ADD_EXCEPTION_HANDLING",
          "description": "Wrapped ATR fetch in try-except with explicit logging",
          "line_numbers": [2455, 2465],
          "code_snippet": "try:\n    atr = self.market_bridge.get_atr(...)\nexcept Exception as e:\n    logger.error(f'Failed to fetch ATR for {trade_id}: {e}')"
        }
      ],
      "testing_performed": [
        {
          "test_name": "test_sl_updates_continuously",
          "status": "PASSED",
          "description": "Verified SL updates every 30 seconds"
        },
        {
          "test_name": "test_sl_never_moves_against_profit",
          "status": "PASSED",
          "description": "Verified SL never decreases for LONG or increases for SHORT"
        }
      ],
      "risk_assessment": "LOW - Changes are additive (logging/validation), not modifying core SL calculation",
      "rollback_hash": "abc123def456"  # Git commit hash for quick rollback
    },
    {
      "implementation_id": "impl_2",
      "recommendation_id": "PHASE_TRANSITION_RACE_CONDITION",
      "status": "COMPLETED",
      "file": "Scalp-Engine/auto_trader_core.py",
      "method": "_check_structure_atr_staged_phase2",
      "changes_made": [
        {
          "change_type": "FIX_FLAG_ATOMICITY",
          "description": "Ensure breakeven_applied flag is set atomically before phase 2.2 check",
          "line_numbers": [2520, 2525],
          "code_snippet": "# Set flag BEFORE phase 2.2 check to prevent duplicate phase 2.1 executions\nposition.breakeven_applied = True\nself.update_trade_position(position)"
        },
        {
          "change_type": "ADD_GUARD_CONDITION",
          "description": "Added explicit guard to prevent duplicate transitions",
          "line_numbers": [2515],
          "code_snippet": "if position.profit_pips >= 1.0 * position.risk_pips and not position.breakeven_applied:"
        }
      ],
      "testing_performed": [
        {
          "test_name": "test_phase_2_1_completes",
          "status": "PASSED",
          "description": "Trade at +1R transitions to breakeven"
        },
        {
          "test_name": "test_phase_2_2_after_2_1",
          "status": "PASSED",
          "description": "Trade at +2R triggers partial close only after 2.1 complete"
        },
        {
          "test_name": "test_no_duplicate_phase_2_1",
          "status": "PASSED",
          "description": "Verified breakeven transition only happens once"
        }
      ],
      "risk_assessment": "MEDIUM - Modifying flag logic which affects multiple phases",
      "rollback_hash": "abc123def456"
    },
    {
      "implementation_id": "impl_3",
      "recommendation_id": "VOLATILITY_REGIME_RACE_CONDITION",
      "status": "COMPLETED",
      "file": "Scalp-Engine/auto_trader_core.py",
      "method": "_check_atr_trailing_conversion",
      "changes_made": [
        {
          "change_type": "ADD_VOLATILITY_REGIME_CACHE",
          "description": "Cache volatility regime for minimum 5-minute window",
          "line_numbers": [2600, 2620],
          "code_snippet": "last_regime_check = getattr(position, 'last_regime_check_time', None)\nif last_regime_check and now - last_regime_check < 300:  # 5 minutes\n    regime = getattr(position, 'cached_regime', None)\nelse:\n    regime = self._detect_volatility_regime()"
        },
        {
          "change_type": "ADD_CONFIRMATION_REQUIREMENT",
          "description": "Only update regime if change persists for 2+ consecutive checks",
          "line_numbers": [2625, 2640],
          "code_snippet": "if regime != position.cached_regime:\n    consecutive_changes = getattr(position, 'regime_change_count', 0) + 1\n    if consecutive_changes >= 2:\n        position.cached_regime = regime"
        }
      ],
      "testing_performed": [
        {
          "test_name": "test_sl_updates_smoothly",
          "status": "PASSED",
          "description": "Verified no erratic jumps in SL values"
        },
        {
          "test_name": "test_regime_change_persistence",
          "status": "PASSED",
          "description": "Verified regime only changes after 2+ confirmations"
        }
      ],
      "risk_assessment": "LOW - Changes add smoothing/caching, don't modify core calculation",
      "rollback_hash": "abc123def456"
    }
  ],
  "git_details": {
    "commit_hash": "abc123def456",
    "commit_message": "fix: Resolve trailing SL stalls, phase transition races, and volatility regime erratic updates\n\n- Add detailed logging for SL updates to detect stalls\n- Add validation to prevent SL moving against profit\n- Fix STRUCTURE_ATR_STAGED phase transition atomicity\n- Add volatility regime caching and confirmation requirement\n- Resolves issues: TRAILING_SL_STALL, PHASE_TRANSITION_RACE, VOLATILITY_REGIME_RACE",
    "files_changed": [
      "Scalp-Engine/auto_trader_core.py"
    ],
    "insertions": 87,
    "deletions": 12,
    "backup_hash": "xyz789uvw123"  # Previous git state for quick rollback
  },
  "test_results": {
    "unit_tests": {
      "total": 12,
      "passed": 12,
      "failed": 0,
      "coverage": 0.94
    },
    "integration_tests": {
      "total": 5,
      "passed": 5,
      "failed": 0
    },
    "performance_tests": {
      "total": 3,
      "passed": 3,
      "failed": 0,
      "metrics": {
        "average_sl_update_time_ms": 45,
        "max_sl_update_time_ms": 150,
        "atm_cache_hit_rate": 0.87
      }
    }
  },
  "deployment_readiness": {
    "status": "READY",
    "blockers": [],
    "warnings": [
      {
        "severity": "INFO",
        "message": "Changes affect ATR_TRAILING and STRUCTURE_ATR_STAGED trades. Monitor logs for 48 hours post-deployment."
      }
    ],
    "recommended_next_steps": [
      "Orchestrator reviews this report",
      "Create git backup at: git tag backup-before-deployment-20260216",
      "Deploy to Render staging environment first for 24-hour smoke test",
      "Deploy to production if staging passes"
    ]
  }
}
```

### 4. Orchestrator State: `orchestrator/workflow_state.json`

```json
{
  "metadata": {
    "timestamp": "2026-02-16T14:45:00Z",
    "cycle_number": 42,
    "workflow_version": "1.0.0"
  },
  "current_workflow_state": {
    "phase": "IMPLEMENTATION_REVIEW",
    "status": "IN_PROGRESS",
    "started_at": "2026-02-16T10:00:00Z",
    "expected_completion": "2026-02-16T15:30:00Z"
  },
  "phase_transitions": [
    {
      "phase": "ANALYSIS",
      "status": "COMPLETED",
      "started_at": "2026-02-16T10:00:00Z",
      "completed_at": "2026-02-16T10:30:00Z",
      "output_file": "agent_data/analysis/latest_analysis.json",
      "health": "GOOD"
    },
    {
      "phase": "FOREX_EXPERT_REVIEW",
      "status": "COMPLETED",
      "started_at": "2026-02-16T10:30:00Z",
      "completed_at": "2026-02-16T10:45:00Z",
      "output_file": "agent_data/recommendations/latest_recommendations.json",
      "health": "GOOD"
    },
    {
      "phase": "IMPLEMENTATION",
      "status": "COMPLETED",
      "started_at": "2026-02-16T10:45:00Z",
      "completed_at": "2026-02-16T14:30:00Z",
      "output_file": "agent_data/implementations/latest_implementation_report.json",
      "health": "GOOD"
    },
    {
      "phase": "IMPLEMENTATION_REVIEW",
      "status": "IN_PROGRESS",
      "started_at": "2026-02-16T14:30:00Z",
      "review_criteria": [
        "Test coverage >= 90%",
        "No new warnings in code",
        "Rollback path documented",
        "Risk assessment documented"
      ],
      "approval_decision": "PENDING"  # APPROVED, REJECTED, PENDING, CHANGES_REQUESTED
    }
  ],
  "backup_registry": {
    "pre_implementation_backup": {
      "timestamp": "2026-02-16T10:45:00Z",
      "git_hash": "xyz789uvw123",
      "branch": "main",
      "files_backed_up": [
        "Scalp-Engine/auto_trader_core.py"
      ],
      "rollback_command": "git reset --hard xyz789uvw123"
    }
  },
  "next_actions": [
    {
      "action": "REVIEW_IMPLEMENTATION_REPORT",
      "responsible_agent": "ORCHESTRATOR",
      "deadline": "2026-02-16T14:45:00Z",
      "status": "IN_PROGRESS"
    },
    {
      "action": "APPROVE_OR_REJECT_IMPLEMENTATION",
      "responsible_agent": "ORCHESTRATOR",
      "deadline": "2026-02-16T15:00:00Z",
      "status": "PENDING",
      "decision_criteria": "Test coverage + Risk assessment"
    },
    {
      "action": "CREATE_DEPLOYMENT_TAG",
      "responsible_agent": "ORCHESTRATOR",
      "deadline": "2026-02-16T15:15:00Z",
      "status": "PENDING",
      "precondition": "APPROVE_OR_REJECT_IMPLEMENTATION = APPROVED"
    },
    {
      "action": "DEPLOY_TO_STAGING",
      "responsible_agent": "ORCHESTRATOR",
      "deadline": "2026-02-16T15:30:00Z",
      "status": "PENDING",
      "precondition": "CREATE_DEPLOYMENT_TAG = COMPLETED"
    }
  ]
}
```

### 5. Orchestrator Audit Trail: `orchestrator/audit_trail.jsonl`

Each line is a complete JSON event:

```jsonl
{"timestamp": "2026-02-16T10:00:00Z", "cycle": 42, "event": "WORKFLOW_STARTED", "phase": "ANALYSIS", "agent": "ORCHESTRATOR", "details": {"trigger": "SCHEDULED", "scheduled_time": "2026-02-16T10:00:00Z", "timezone": "UTC"}}
{"timestamp": "2026-02-16T10:00:05Z", "cycle": 42, "event": "ANALYST_AGENT_STARTED", "phase": "ANALYSIS", "agent": "ANALYST", "details": {"expected_duration_seconds": 300, "log_files_to_analyze": 3}}
{"timestamp": "2026-02-16T10:30:00Z", "cycle": 42, "event": "ANALYST_AGENT_COMPLETED", "phase": "ANALYSIS", "agent": "ANALYST", "details": {"execution_time_seconds": 1800, "analysis_id": "analysis_20260216_103000", "issues_found": 5, "output_file": "agent_data/analysis/latest_analysis.json"}}
{"timestamp": "2026-02-16T10:30:05Z", "cycle": 42, "event": "FOREX_EXPERT_STARTED", "phase": "FOREX_EXPERT_REVIEW", "agent": "FOREX_TRADING_EXPERT", "details": {"input_file": "agent_data/analysis/latest_analysis.json"}}
{"timestamp": "2026-02-16T10:45:00Z", "cycle": 42, "event": "FOREX_EXPERT_COMPLETED", "phase": "FOREX_EXPERT_REVIEW", "agent": "FOREX_TRADING_EXPERT", "details": {"execution_time_seconds": 900, "recommendation_id": "rec_20260216_104500", "critical_issues": 3, "code_changes_needed": 3}}
{"timestamp": "2026-02-16T10:45:05Z", "cycle": 42, "event": "CODING_EXPERT_STARTED", "phase": "IMPLEMENTATION", "agent": "CODING_EXPERT", "details": {"input_file": "agent_data/recommendations/latest_recommendations.json"}}
{"timestamp": "2026-02-16T10:45:10Z", "cycle": 42, "event": "PRE_IMPLEMENTATION_BACKUP", "phase": "IMPLEMENTATION", "agent": "ORCHESTRATOR", "details": {"backup_hash": "xyz789uvw123", "files_backed_up": ["Scalp-Engine/auto_trader_core.py"]}}
{"timestamp": "2026-02-16T14:30:00Z", "cycle": 42, "event": "CODING_EXPERT_COMPLETED", "phase": "IMPLEMENTATION", "agent": "CODING_EXPERT", "details": {"execution_time_seconds": 13050, "implementation_id": "impl_20260216_143000", "changes_committed": true, "commit_hash": "abc123def456", "test_passed": 12}}
{"timestamp": "2026-02-16T14:30:05Z", "cycle": 42, "event": "IMPLEMENTATION_REVIEW_STARTED", "phase": "IMPLEMENTATION_REVIEW", "agent": "ORCHESTRATOR", "details": {"review_criteria": 4}}
{"timestamp": "2026-02-16T14:45:00Z", "cycle": 42, "event": "IMPLEMENTATION_APPROVED", "phase": "IMPLEMENTATION_REVIEW", "agent": "ORCHESTRATOR", "details": {"implementation_id": "impl_20260216_143000", "reason": "All tests passed, risk low, rollback path documented"}}
{"timestamp": "2026-02-16T15:00:00Z", "cycle": 42, "event": "DEPLOYMENT_TAG_CREATED", "phase": "DEPLOYMENT", "agent": "ORCHESTRATOR", "details": {"tag_name": "deploy-20260216-143000", "commit_hash": "abc123def456"}}
{"timestamp": "2026-02-16T15:30:00Z", "cycle": 42, "event": "WORKFLOW_COMPLETED", "phase": "COMPLETED", "agent": "ORCHESTRATOR", "details": {"total_duration_seconds": 19800, "implementations_deployed": 1}}
```

---

## Agent Responsibilities & Workflows

### Agent 1: Analyst Agent (`analyst_agent.py`)

**Primary Responsibility**: Log review & consistency validation

**Daily Workflow** (starts ~10:00 AM UTC):

1. **Fetch Logs**
   - Read `Scalp-Engine/logs/scalp_engine.log` (last 24 hours)
   - Read `Scalp-Engine/logs/ui_activity.log` (last 24 hours)
   - Read OANDA API logs (via config API or file-based if available)

2. **Parse Trades**
   - Extract all completed + in-progress trades from UI logs
   - Extract all trades from scalp-engine logs
   - Fetch live OANDA positions via API

3. **Consistency Checks**
   - **UI ↔ Scalp-Engine Consistency**: Entry price, exit price, SL type, SL value match?
   - **Scalp-Engine ↔ OANDA Consistency**: All trades logged in scalp-engine appear in OANDA?
   - **SL Type Validation**: Is actual SL type matching expected type (ATR_TRAILING, FIXED, etc.)?

4. **Trailing SL Analysis**
   - For each ATR_TRAILING and STRUCTURE_ATR_STAGED trade:
     - Is SL updating every ~30 seconds?
     - Is SL moving only in profit direction?
     - Any stalls (no update for >1 hour)?
     - Any erratic jumps (>50% change in single update)?

5. **Performance Metrics**
   - Calculate: Win rate, average win/loss, profit factor, max drawdown, risk/reward ratio

6. **Export Analysis**
   - Write `agent_data/analysis/latest_analysis.json`
   - Append to `agent_data/analysis/analysis_history.jsonl`

**Error Handling**:
- If a log file is missing → log warning, continue with available logs
- If OANDA API fails → fallback to file-based trade records
- If consistency check fails → mark as MISMATCH, include both values

---

### Agent 2: Forex Trading Expert Agent (`forex_trading_expert_agent.py`)

**Primary Responsibility**: Trade performance analysis & improvement recommendations

**Daily Workflow** (starts after Analyst completes):

1. **Read Analysis**
   - Load `agent_data/analysis/latest_analysis.json`

2. **Categorize Issues**
   - **Critical** (CRITICAL severity): Requires code fix
   - **High** (HIGH severity): Performance issue, should fix
   - **Medium** (MEDIUM severity): Optimization opportunity
   - **Low** (LOW severity): Nice-to-have improvement

3. **Root Cause Analysis**
   - For each critical/high issue, analyze:
     - When did the issue occur?
     - What conditions triggered it?
     - Is it a code bug or configuration issue?
     - Which component is responsible?

4. **Generate Recommendations**
   - For code issues: Specify file, method, exact changes needed
   - For performance issues: Estimate impact (win rate %, drawdown %)
   - For configuration issues: Suggest specific parameter values

5. **Estimate Impact**
   - Win rate improvement potential
   - Risk/reward improvement potential
   - Max drawdown reduction potential

6. **Export Recommendations**
   - Write `agent_data/recommendations/latest_recommendations.json`
   - Append to `agent_data/recommendations/recommendations_history.jsonl`

**Expertise Areas**:
- Trailing stop loss logic (ATR calculations, volatility regimes, race conditions)
- Phase transition logic (STRUCTURE_ATR_STAGED phases)
- Entry point optimization (Fisher, DMI-EMA signal timing)
- Risk management (position sizing, SL distance, profit targets)

---

### Agent 3: Coding Expert Agent (`coding_expert_agent.py`)

**Primary Responsibility**: Implementation of code improvements

**Daily Workflow** (starts after Forex Expert completes):

1. **Read Recommendations**
   - Load `agent_data/recommendations/latest_recommendations.json`

2. **Pre-Implementation Backup**
   - Orchestrator creates git backup (via shared backup_manager)
   - Store commit hash in backups.json

3. **Implement Each Recommendation**
   - For each code change:
     - Read the affected file
     - Understand existing code logic
     - Apply the change with comments
     - Run unit tests for affected methods
     - Run integration tests
     - Document the change

4. **Commit Changes**
   - Create atomic commit with all changes
   - Include detailed message referencing recommendations
   - Include co-author: Claude Code Agent

5. **Run Test Suite**
   - Unit tests: >90% coverage required
   - Integration tests: All must pass
   - Performance tests: No regression

6. **Export Implementation Report**
   - Write `agent_data/implementations/latest_implementation_report.json`
   - Include: Files changed, commits, test results, rollback hash
   - Mark deployment readiness (READY, CHANGES_NEEDED, BLOCKED)

7. **Wait for Orchestrator Approval**
   - Implementation report reviewed by Orchestrator
   - If approved: Orchestrator handles deployment
   - If rejected: Changes remain in git history (can be reverted)

**Safety Mechanisms**:
- Never delete code, only modify
- Every change tracked in git
- Rollback hash always documented
- Code reviewed before committing (by self through detailed analysis)
- Test coverage requirement enforced

---

### Agent 4: Orchestrator Agent (`orchestrator_agent.py`)

**Primary Responsibility**: Coordination, scheduling, backup/rollback, error recovery

**Daily Workflow**:

1. **Schedule Check** (~10:00 AM UTC)
   - Check `agent_data/orchestrator/schedule.json` for configured run times
   - If it's time, initiate workflow

2. **Workflow Orchestration**
   - Start Analyst Agent
   - Wait for completion, verify output exists
   - Start Forex Expert Agent
   - Wait for completion, verify output exists
   - Create PRE-IMPLEMENTATION backup (if code changes needed)
   - Start Coding Expert Agent
   - Wait for completion, collect implementation report

3. **Implementation Review**
   - Verify test coverage >= 90%
   - Verify no new code warnings
   - Verify rollback path documented
   - Verify risk assessment acceptable

4. **Deployment Decision**
   - If APPROVED: Create deployment tag, initiate deployment to staging
   - If REJECTED: Revert git changes (using rollback hash), notify user
   - If CHANGES_REQUESTED: Pass feedback back to coding expert (for next cycle)

5. **Deployment Process**
   - Create git tag: `deploy-{timestamp}`
   - Push to staging environment (if available)
   - Monitor for 24 hours
   - If staging passes: Promote to production
   - If staging fails: Use rollback hash to revert

6. **Post-Deployment Monitoring** (first 48 hours)
   - Monitor logs for errors/warnings related to changes
   - Compare metrics to pre-deployment baseline
   - If issues detected: Automatic rollback to pre-implementation backup

7. **Record Audit Trail**
   - Every action logged to `orchestrator/audit_trail.jsonl`
   - Every decision documented with reasoning

**Backup/Rollback Mechanism**:

```
Pre-Implementation:
  1. Get current git HEAD: git rev-parse HEAD
  2. Create git tag: git tag backup-{timestamp}
  3. Store in backups.json: {timestamp, branch, hash}

Post-Rejection/Rollback:
  1. Get backup hash from backups.json
  2. Execute: git reset --hard {backup_hash}
  3. Log rollback action to audit_trail.jsonl

Post-Deployment Issues:
  1. Orchestrator monitors logs for errors
  2. If error rate spikes: Automatic rollback
  3. Create incident report
  4. Notify user (for next cycle)
```

---

## Communication Protocols

### Primary: SQLite Database (Reliable, Queryable, Auditable)

**Advantages**:
- ✅ ACID compliance (no partial writes)
- ✅ Full query capability (find implementations by date, status, etc.)
- ✅ Built-in audit trail (approval_history, audit_trail tables)
- ✅ File-based (can be committed to git for history)
- ✅ No external dependencies (free)
- ✅ Easy to search/filter using SQL

**Update Protocol**:
```python
# Agent writes output to database
1. Connect to database (SQLite auto-creates if missing)
2. Serialize output to JSON string
3. INSERT INTO agent_analyses (cycle_number, timestamp, analysis_json, status)
4. Commit transaction
5. Export to JSON file: agents/audit_exports/analysis_20260216_115959.json
6. Git commit: "Agent output: cycle 42 analysis"

# Orchestrator reads output from database
1. Connect to database
2. SELECT * FROM agent_analyses WHERE cycle_number = ? AND status = 'COMPLETED'
3. Deserialize JSON from database
4. Validate schema matches expected format
5. Proceed to next agent

# User reviews approvals
1. Query: SELECT * FROM approval_history WHERE user_reviewed = FALSE
2. Display approval details in web UI
3. User clicks "Approve" or "Reject"
4. UPDATE approval_history SET user_reviewed = TRUE, decision = ?
5. INSERT into audit_trail: USER_APPROVAL_RECORDED
```

**Database Update Transaction Example**:
```python
import sqlite3
import json
from datetime import datetime

def save_analysis_to_db(analysis_json: dict, cycle_number: int):
    """Save analysis to database with transaction safety"""
    conn = sqlite3.connect('data/agent_system.db')
    try:
        conn.execute('''
            INSERT INTO agent_analyses (cycle_number, timestamp, analysis_json, status)
            VALUES (?, ?, ?, ?)
        ''', (
            cycle_number,
            datetime.utcnow().isoformat(),
            json.dumps(analysis_json),
            'COMPLETED'
        ))
        conn.commit()

        # Also export to JSON for git visibility
        export_path = f'agents/audit_exports/analysis_{cycle_number}_{datetime.utcnow().isoformat().replace(":", "-")}.json'
        with open(export_path, 'w') as f:
            json.dump(analysis_json, f, indent=2)
    finally:
        conn.close()
```

### Secondary: JSON File Exports (Git History & Debugging)

**Purpose**: Keep human-readable copies in git for traceability

**Export Locations**:
```
agents/audit_exports/
├── analysis_20260216_233959.json          # Individual cycle exports
├── recommendations_20260216_233959.json
├── implementation_20260216_233959.json
├── approval_history.json                  # Latest approval record (updated daily)
└── audit_trail.json                       # Complete audit log (for user review)
```

**Daily Export Job** (Orchestrator):
```python
# After workflow completes
1. Export latest approvals: approval_history.json
2. Export full audit trail: audit_trail.json
3. Git commit: "Agent workflow cycle 42: analysis, recommendations, implementation"
4. Push to remote
```

### Tertiary: REST API (Real-time Queries)

**When to Use**:
- Web UI needs real-time approval data
- User wants current workflow status
- Integration with external services

**API Endpoints**:

```
GET /api/agent-status
  → Returns current workflow state
  → { "phase": "IMPLEMENTATION", "cycle": 42, "status": "IN_PROGRESS" }

GET /api/pending-approvals
  → Returns implementations awaiting approval
  → [ { "cycle": 42, "test_coverage": 0.94, "risk": "LOW", "decision": "PENDING" } ]

GET /api/approval-history
  → Returns all approvals with user reviews
  → [ { "cycle": 41, "decision": "APPROVED", "reason": "...", "approved_by": "user" } ]

GET /api/audit-trail?since={timestamp}&limit={n}
  → Returns audit events
  → [ { "timestamp": "...", "event": "ANALYST_COMPLETED", "agent": "ANALYST" } ]

POST /api/approve-implementation/{cycle}
  → Approve or reject implementation
  → { "decision": "APPROVED", "reason": "Tests passed, low risk", "user": "user@example.com" }

GET /api/agent-logs/{agent_name}
  → Returns agent execution logs
  → [ { "timestamp": "...", "level": "INFO", "message": "..." } ]
```

**Pushover Integration**:
```
When approval needed:
  POST to Pushover API
  Title: "Agent Implementation #42 Awaiting Approval"
  Message: "Test coverage: 94%, Risk: LOW. 3 critical fixes + 5 unit tests."
  URL: https://your-domain.com/approvals/42
  Priority: HIGH (requires response)

When approved:
  POST to Pushover API
  Title: "Agent Implementation #42 APPROVED"
  Message: "Auto-approved. Test coverage 97% > 95% threshold."
  Priority: NORMAL
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create agent directory structure
- [ ] Define JSON schemas (shared/json_schema.py)
- [ ] Implement backup_manager.py
- [ ] Implement agent_communication.py
- [ ] Implement audit_logger.py
- [ ] Create orchestrator_agent.py skeleton

### Phase 2: Analyst Agent (Week 2)
- [ ] Implement log parsing (scalp_engine.log, ui_activity.log)
- [ ] Implement consistency checks (UI ↔ SE, SE ↔ OANDA)
- [ ] Implement trailing SL analysis
- [ ] Implement performance metrics calculation
- [ ] Write analyst_agent.py
- [ ] Test with real logs

### Phase 3: Forex Expert Agent (Week 3)
- [ ] Implement issue categorization logic
- [ ] Implement root cause analysis
- [ ] Implement recommendation generation
- [ ] Write forex_trading_expert_agent.py
- [ ] Test with sample analysis.json

### Phase 4: Coding Expert Agent (Week 4)
- [ ] Implement code change logic (file reading, modification)
- [ ] Implement git commit logic
- [ ] Implement test runner integration
- [ ] Write coding_expert_agent.py
- [ ] Test with sample recommendations.json

### Phase 5: Orchestrator & Integration (Week 5)
- [ ] Complete orchestrator_agent.py
- [ ] Implement workflow orchestration
- [ ] Implement deployment logic
- [ ] Implement post-deployment monitoring
- [ ] Integration testing: Full workflow end-to-end
- [ ] Deploy to Render with schedule

### Phase 6: Monitoring & Refinement (Ongoing)
- [ ] Monitor agent outputs for quality
- [ ] Refine detection logic based on real data
- [ ] Add more specialized detection rules
- [ ] Gather feedback on recommendations

---

## Database Architecture

### Database Choice: SQLite

**Why SQLite**:
- ✅ Free (no external service needed)
- ✅ Already used in codebase (`trade_alerts_rl.db`)
- ✅ Works perfectly for structured agent data + audit logs
- ✅ File-based (can be committed to git)
- ✅ ACID compliance for data integrity
- ✅ Zero setup required

**Database Location**:
- Development: `data/agent_system.db`
- Render: `/var/data/agent_system.db` (persistent disk)

**Schema Overview**:
```sql
-- Core agent outputs
TABLE agent_analyses (
  id INTEGER PRIMARY KEY,
  cycle_number INTEGER,
  timestamp DATETIME,
  analysis_json TEXT,  -- Complete analysis.json stored as JSON
  status TEXT  -- COMPLETED, FAILED, PENDING
)

TABLE agent_recommendations (
  id INTEGER PRIMARY KEY,
  cycle_number INTEGER,
  timestamp DATETIME,
  recommendation_json TEXT,  -- Complete recommendations.json
  status TEXT
)

TABLE agent_implementations (
  id INTEGER PRIMARY KEY,
  cycle_number INTEGER,
  timestamp DATETIME,
  implementation_json TEXT,  -- Complete implementation_report.json
  status TEXT,  -- PENDING_APPROVAL, APPROVED, REJECTED, DEPLOYED
  git_commit_hash TEXT,
  approval_timestamp DATETIME,
  approval_decision TEXT,  -- APPROVED, AUTO_APPROVED, REJECTED, CHANGES_REQUESTED
  approval_reason TEXT,
  approved_by TEXT  -- 'orchestrator_auto', 'user_manual', etc.
)

TABLE orchestrator_state (
  id INTEGER PRIMARY KEY,
  cycle_number INTEGER,
  timestamp DATETIME,
  workflow_state_json TEXT,  -- Current workflow state
  phase TEXT  -- ANALYSIS, FOREX_EXPERT_REVIEW, IMPLEMENTATION, COMPLETED
)

-- Audit trail (critical for transparency)
TABLE audit_trail (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME,
  cycle_number INTEGER,
  event_type TEXT,  -- WORKFLOW_STARTED, ANALYST_COMPLETED, APPROVAL_DECISION, etc.
  agent_name TEXT,
  phase TEXT,
  event_data_json TEXT,  -- Details specific to event
  user_reviewed BOOLEAN DEFAULT FALSE  -- Tracks if user has reviewed this approval
)

-- Approval audit (for user review)
TABLE approval_history (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME,
  cycle_number INTEGER,
  implementation_id INTEGER,
  decision TEXT,  -- APPROVED, REJECTED, CHANGES_REQUESTED
  reason TEXT,
  auto_approved BOOLEAN,
  test_coverage FLOAT,
  risk_assessment TEXT,
  git_commit_hash TEXT,
  rollback_available BOOLEAN DEFAULT TRUE
)
```

**JSON Storage Strategy**:
- Store complete JSON objects as TEXT columns (SQLite's JSON functions available)
- Allows full history queries: `SELECT * FROM agent_analyses WHERE cycle_number > ?`
- Easy to export: `SELECT analysis_json FROM agent_analyses WHERE id = ?` returns valid JSON
- Searchable: Can use SQLite's JSON functions for filtering

---

## Deployment Architecture

### Local Development
```
Trade-Alerts/
├── agents/              # Agent code (local development)
├── data/
│   └── agent_system.db  # SQLite database (git-committed for history)
└── agent_scheduler.py   # Runs agents on schedule
```

**Run Locally**:
```bash
python agents/orchestrator_agent.py --run-once  # Trigger one cycle
python agents/orchestrator_agent.py --web      # Start web UI for approvals
```

### Render Deployment (Production)

**Service 1: Trade-Alerts Main** (existing)
- Runs `main.py`
- Generates `market_state.json`
- Provides `/api/market-state` endpoint

**Service 2: Scalp-Engine** (existing)
- Runs `scalp_engine.py`
- Monitors `market_state.json`
- Executes trades via OANDA

**Service 3: Agent Orchestrator** (NEW)
- Runs `agents/orchestrator_agent.py` as scheduled worker
- Triggers analyst → forex → coding workflow
- Uses SQLite database at `/var/data/agent_system.db` (persistent disk)
- Commits database + JSON exports to git repository daily
- Sends Pushover notifications for approvals/changes

**Service 4: Approval Web UI** (OPTIONAL)
- Simple Flask web app for reviewing/approving implementations
- Shows approval history + audit trail
- Allows user to manually approve/reject with comments

**Git Sync Strategy**:
- After each approval decision: Export approval_history + audit_trail to JSON files
- Daily: Commit database snapshots and JSON exports
- Visible in git history: `/agents/audit_exports/`

**Configuration** (Render Dashboard):
```
Service: Agent Orchestrator
Type: Worker (background)
Command: python agents/orchestrator_agent.py
Schedule: Daily at 11:30 PM UTC (5:30 PM EST)

Environment Variables:
  AGENT_RUN_ENVIRONMENT=render
  AGENT_DATA_DIR=/var/data
  DATABASE_PATH=/var/data/agent_system.db
  GIT_REPO_PATH=/app
  PUSHOVER_API_TOKEN=<your_token>
  PUSHOVER_USER_KEY=<your_key>
  ORCHESTRATOR_AUTO_APPROVE_THRESHOLD=0.95  # Auto-approve if test_coverage > 95%
```

---

## Approval Audit & User Review System

### Approval Decision Flow

```
┌─────────────────────────────────────────┐
│ Coding Expert: Implementation Complete  │
│ (test_coverage: 94%, risk: LOW)         │
└────────────────┬────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Check Thresholds   │
        └────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
   Coverage >95%      Coverage 90-95%
   Risk = LOW         Risk = LOW
        │                 │
        ▼                 ▼
  AUTO-APPROVE      PENDING USER REVIEW
  (record to DB)    (Pushover notification)
        │                 │
        └────────┬────────┘
                 │
                 ▼
         ┌───────────────────┐
         │ INSERT into       │
         │ approval_history  │
         │ (user_reviewed)   │
         └───────────────────┘
                 │
         ┌───────┴────────┐
         │                │
         ▼                ▼
    USER REVIEWS    AUTO-APPROVE RECORDED
    IN WEB UI       (awaiting monitoring)
         │
    ┌────┴──────┐
    │ Approve/  │
    │ Reject    │
    └────┬──────┘
         │
         ▼
    UPDATE approval_history
    + INSERT audit_trail event
    + Git commit changes
    + Pushover notification
```

### Approval Audit Trail (User-Visible Record)

**Database Table: `approval_history`**
```sql
CREATE TABLE approval_history (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME,
  cycle_number INTEGER,
  implementation_id INTEGER,

  -- Approval Details
  decision TEXT,  -- APPROVED, REJECTED, CHANGES_REQUESTED
  reason TEXT,
  auto_approved BOOLEAN,

  -- Test/Risk Assessment
  test_coverage FLOAT,  -- e.g., 0.94
  risk_assessment TEXT,  -- LOW, MEDIUM, HIGH, CRITICAL
  critical_issues_count INTEGER,

  -- Implementation Details
  git_commit_hash TEXT,
  files_modified TEXT,  -- JSON list of files
  changes_summary TEXT,  -- Brief description

  -- User Review
  user_reviewed BOOLEAN DEFAULT FALSE,
  user_reviewed_timestamp DATETIME,
  user_review_comments TEXT,

  -- Rollback Capability
  rollback_available BOOLEAN DEFAULT TRUE,
  rollback_hash TEXT,
  rollback_command TEXT
);
```

### Approval Records Exported to Git

**File: `agents/audit_exports/approval_history.json`** (Updated daily)

```json
[
  {
    "cycle": 42,
    "timestamp": "2026-02-16T23:30:00Z",
    "decision": "AUTO_APPROVED",
    "reason": "Test coverage 97% > 95% threshold, LOW risk assessment",
    "auto_approved": true,
    "test_coverage": 0.97,
    "risk_assessment": "LOW",
    "critical_issues_count": 0,
    "git_commit_hash": "abc123def456",
    "files_modified": [
      "Scalp-Engine/auto_trader_core.py"
    ],
    "changes_summary": "Fix trailing SL stalls by adding ATR fetch logging and validation",
    "user_reviewed": false,
    "user_review_comments": null,
    "rollback_available": true,
    "rollback_hash": "xyz789uvw123",
    "rollback_command": "git reset --hard xyz789uvw123"
  },
  {
    "cycle": 41,
    "timestamp": "2026-02-15T23:30:00Z",
    "decision": "APPROVED",
    "reason": "User approved: Well-tested changes, low risk. Monitoring for 48 hours recommended.",
    "auto_approved": false,
    "test_coverage": 0.92,
    "risk_assessment": "LOW",
    "critical_issues_count": 0,
    "git_commit_hash": "def789abc123",
    "files_modified": [
      "Scalp-Engine/src/indicators/fisher_reversal_analyzer.py"
    ],
    "changes_summary": "Add volume filter to Fisher Transform for earlier signal detection",
    "user_reviewed": true,
    "user_reviewed_timestamp": "2026-02-15T23:42:00Z",
    "user_review_comments": "Looks good. Let's monitor the win rate improvement over next 5 days.",
    "rollback_available": true,
    "rollback_hash": "abc456def789",
    "rollback_command": "git reset --hard abc456def789"
  },
  {
    "cycle": 40,
    "timestamp": "2026-02-14T23:30:00Z",
    "decision": "REJECTED",
    "reason": "User rejected: Test coverage only 87%, below 90% minimum",
    "auto_approved": false,
    "test_coverage": 0.87,
    "risk_assessment": "MEDIUM",
    "critical_issues_count": 1,
    "git_commit_hash": "ghi123jkl456",
    "files_modified": [
      "Scalp-Engine/auto_trader_core.py",
      "Scalp-Engine/src/risk_manager.py"
    ],
    "changes_summary": "Dynamic position sizing based on volatility regime",
    "user_reviewed": true,
    "user_reviewed_timestamp": "2026-02-14T23:35:00Z",
    "user_review_comments": "Good idea but needs more tests. Let's revisit in next cycle after Coding Expert improves coverage.",
    "rollback_available": true,
    "rollback_hash": "jkl789mno123",
    "rollback_command": "git reset --hard jkl789mno123"
  }
]
```

### Web UI for User Review

**Location**: Optional Flask app (`agents/approval_ui.py`)

**Features**:
- Display pending approvals with full details
- Show approval history with filtering
- One-click approve/reject
- Add comments for each approval
- View audit trail (all events)
- Download approval_history.json
- See rollback paths for each change

**Mock UI Flow**:
```
┌─ PENDING APPROVALS ──────────────────────────────────┐
│ Cycle 42: Trailing SL Fixes                          │
│ Status: PENDING (scheduled in 3 hours)               │
│ Test Coverage: 97% ✅ (>95% threshold)               │
│ Risk: LOW ✅                                         │
│ Files: auto_trader_core.py (87 insertions)           │
│                                                      │
│ [View Details] [Approve] [Reject] [View Rollback]   │
└──────────────────────────────────────────────────────┘

┌─ APPROVAL HISTORY ───────────────────────────────────┐
│ Filter: [All] [Approved] [Rejected] [Auto-Approved] │
│                                                      │
│ Cycle 42 | AUTO_APPROVED | 2026-02-16 23:30         │
│ Cycle 41 | APPROVED | 2026-02-15 23:42              │
│ Cycle 40 | REJECTED | 2026-02-14 23:35              │
│                                                      │
│ [Export as JSON] [View Audit Trail]                 │
└──────────────────────────────────────────────────────┘
```

### Pushover Notifications for Approvals

**When Auto-Approval Occurs**:
```
Title: ✅ Agent Implementation #42 Auto-Approved
Message: Trailing SL fixes
Details:
  • Test coverage: 97% (>95% threshold)
  • Risk: LOW
  • 3 critical issues fixed
  • Rollback available: git reset --hard xyz789uvw123
  • Ready for deployment to staging

Timestamp: 2026-02-16 23:30:00 EST
```

**When User Approval Needed**:
```
Title: ⏳ Agent Implementation #42 Awaiting Approval
Message: Dynamic Position Sizing
Details:
  • Test coverage: 92% (>90% minimum)
  • Risk: LOW
  • 5 test files covering position sizing changes
  • Ready for deployment
  • User approval required

Action URL: https://your-domain.com/approvals/42
Priority: HIGH
```

**When User Approves/Rejects**:
```
Title: ✅ Agent Implementation #42 APPROVED by User
Message: Comment: "Well-tested, low risk. Monitor for 48 hours."
Ready for deployment to staging

OR

Title: ❌ Agent Implementation #42 REJECTED by User
Message: Reason: "Test coverage needs improvement. Let's revisit next cycle."
Reverted: git reset --hard <rollback_hash>
```

---

## Error Handling & Recovery

### Agent Timeouts
```
If Analyst takes >1 hour:
  1. Orchestrator cancels workflow
  2. Logs timeout error to audit_trail.jsonl
  3. Retries next scheduled time
  4. Alert user if timeouts persist 3+ times

If Coding Expert takes >4 hours:
  1. Orchestrator cancels workflow
  2. Rolls back any partial commits (using backup hash)
  3. Logs error to audit_trail.jsonl
  4. Requires manual review next cycle
```

### Agent Failures
```
If Analyst fails (exception):
  1. Orchestrator catches exception
  2. Logs full stack trace to agent_logs.jsonl
  3. Skips Forex Expert (no input)
  4. Workflow marked FAILED
  5. User notified (can review logs)

If Forex Expert fails:
  1. Uses last valid recommendations (if available)
  2. Or skips Coding Expert phase
  3. Logs issue, continues monitoring

If Coding Expert fails:
  1. Rolls back any git commits (using backup hash)
  2. Full workflow marked FAILED
  3. User can review what went wrong
  4. Re-enable manually after fixing issue
```

### File System Issues
```
If agent_data/ directory missing:
  1. Orchestrator creates directory
  2. Creates empty metadata.json files
  3. Logs warning to audit_trail.jsonl
  4. Continues workflow

If JSON write fails:
  1. Agent retries up to 3 times
  2. If still fails: Exception caught, logged
  3. Workflow marked FAILED
  4. User reviews logs for disk space / permission issues
```

---

## Configuration

### Schedule Configuration (Database: `orchestrator_state` table)

```json
{
  "enabled": true,
  "timezone": "EST",
  "runs": [
    {
      "name": "daily_analysis",
      "time": "17:30",  # 5:30 PM EST (11:30 PM UTC)
      "enabled": true,
      "retry_policy": {
        "max_retries": 3,
        "retry_delay_minutes": 30,
        "timeout_hours": 6
      }
    }
  ],
  "approval_config": {
    "auto_approve_enabled": true,
    "auto_approve_test_coverage_threshold": 0.95,  # 95% coverage
    "auto_approve_risk_levels": ["LOW"],  # Never auto-approve MEDIUM/HIGH risk
    "require_user_approval_for": ["HIGH", "CRITICAL"],
    "user_approval_timeout_hours": 24
  },
  "deployment_config": {
    "enable_staging_test": true,
    "staging_test_duration_hours": 24,
    "enable_automatic_production_promotion": false,  # User must manually promote from staging
    "enable_pushover_notifications": true,
    "git_commit_enabled": true,
    "commit_frequency": "after_each_approval"
  }
}
```

### Pushover Configuration (.env variables)

```bash
# Pushover API credentials (add to Trade-Alerts/.env)
PUSHOVER_API_TOKEN=<your_app_token>
PUSHOVER_USER_KEY=<your_user_key>

# Render persistent disk path
AGENT_DATA_DIR=/var/data

# Database path
DATABASE_PATH=${AGENT_DATA_DIR}/agent_system.db

# Auto-approval threshold
ORCHESTRATOR_AUTO_APPROVE_THRESHOLD=0.95

# Git configuration for agent commits
AGENT_GIT_AUTHOR_NAME="Claude Code Agent"
AGENT_GIT_AUTHOR_EMAIL="agent@trade-alerts.local"
```

### Analyst Configuration (Database: `config` table)

```json
{
  "agent_name": "ANALYST",
  "log_sources": {
    "scalp_engine": {
      "path": "Scalp-Engine/logs/scalp_engine.log",
      "lookback_hours": 24
    },
    "ui_activity": {
      "path": "Scalp-Engine/logs/ui_activity.log",
      "lookback_hours": 24
    },
    "oanda_trades": {
      "path": "Scalp-Engine/logs/oanda_trades.log",
      "lookback_hours": 24,
      "optional": true
    }
  },
  "consistency_checks": {
    "enable_ui_se_check": true,
    "enable_se_oanda_check": true,
    "max_price_deviation_pips": 15,
    "max_time_deviation_minutes": 5
  },
  "trailing_sl_analysis": {
    "enable": true,
    "expected_update_interval_seconds": 30,
    "stall_threshold_minutes": 60,
    "stall_severity": "HIGH",
    "erratic_jump_threshold_percent": 50,
    "erratic_jump_severity": "MEDIUM"
  },
  "profitability_metrics": {
    "calculate_win_rate": true,
    "calculate_profit_factor": true,
    "calculate_max_drawdown": true,
    "calculate_risk_reward": true
  }
}
```

### Forex Trading Expert Configuration

```json
{
  "agent_name": "FOREX_TRADING_EXPERT",
  "issue_severity_mapping": {
    "TRAILING_SL_STALL": "CRITICAL",
    "PHASE_TRANSITION_FAILURE": "CRITICAL",
    "VOLATILITY_RACE_CONDITION": "HIGH",
    "FISHER_SIGNAL_LATENCY": "MEDIUM",
    "DMI_ALIGNMENT_LOOSE": "MEDIUM"
  },
  "impact_estimation": {
    "enable_win_rate_estimation": true,
    "enable_drawdown_estimation": true,
    "enable_risk_reward_estimation": true
  },
  "code_change_requirements": {
    "require_test_coverage": true,
    "min_test_coverage": 0.90,
    "require_rollback_hash": true
  }
}
```

### Coding Expert Configuration

```json
{
  "agent_name": "CODING_EXPERT",
  "code_change_safety": {
    "require_backup_before_changes": true,
    "require_test_coverage_minimum": 0.90,
    "require_rollback_documentation": true,
    "validate_git_commit_format": true
  },
  "testing_requirements": {
    "run_unit_tests": true,
    "run_integration_tests": true,
    "run_performance_tests": true,
    "fail_on_test_failure": true
  },
  "code_review_rules": {
    "check_imports": true,
    "check_docstrings": false,  # Don't require docs for existing code
    "check_type_hints": false,
    "max_lines_per_function": 200
  }
}
```

---

## Testing Strategy

### Unit Tests
- Test JSON schema validation
- Test log parsing logic
- Test consistency check logic
- Test recommendation generation

### Integration Tests
- Test full analyst → forex → coding workflow
- Test backup/rollback mechanism
- Test git commit/tag creation

### End-to-End Tests
- Deploy to Render staging
- Run full workflow with real logs
- Verify outputs in agent_data/
- Verify git commits created
- Test rollback mechanism

---

## Success Metrics

### Accuracy Metrics
- **Analyst**: Consistency checks must have <1% false positive rate
- **Forex Expert**: Recommendations must correlate with actual issue root causes
- **Coding Expert**: Fixes must resolve the identified issues (post-deployment validation)

### Efficiency Metrics
- **Analyst completion time**: <1 hour per cycle
- **Forex Expert completion time**: <30 minutes per cycle
- **Coding Expert completion time**: <3 hours per cycle
- **Total cycle time**: <6 hours (from 10 AM to 4 PM UTC)

### Safety Metrics
- **Backup success rate**: 100% (every code change has backup)
- **Rollback success rate**: 100% (can always revert to pre-implementation state)
- **Test pass rate**: 100% (all tests must pass before deployment)
- **Deployment success rate**: >95% (minimal post-deployment rollbacks)

---

## Git Commit Strategy for Agent Outputs

### Automated Git Commits (Orchestrator Responsibility)

**When**: After each major workflow phase completion

**Commit 1 - Analysis Complete** (after Analyst Agent finishes)
```
Commit Message:
  Agent analysis: cycle 42 - Trade consistency review

  • Analyzed 12 trades from last 24 hours
  • Found 1 consistency mismatch (GBP/USD entry price)
  • Found 2 trailing SL issues (1 stall, 1 erratic)
  • Overall health: GOOD (confidence: 87%)

  Output: agents/audit_exports/analysis_20260216_233959.json
  Database: agent_analyses table (id: 1337)

Files Changed:
  - agents/audit_exports/analysis_20260216_233959.json (new)

Authored-By: Claude Code Agent <agent@trade-alerts.local>
```

**Commit 2 - Recommendations Complete** (after Forex Expert finishes)
```
Commit Message:
  Agent recommendations: cycle 42 - Trading improvements

  • Critical issues: 3 (trailing SL, phase transitions, volatility race)
  • Code changes needed: 3
  • Performance improvements: 2
  • Risk-reward improvement estimate: 15%

  Output: agents/audit_exports/recommendations_20260216_233959.json
  Database: agent_recommendations table (id: 1337)

Files Changed:
  - agents/audit_exports/recommendations_20260216_233959.json (new)

Authored-By: Claude Code Agent <agent@trade-alerts.local>
```

**Commit 3 - Implementation Complete** (after Coding Expert finishes)
```
Commit Message:
  Agent implementation: cycle 42 - Fix trailing SL, phase transitions, volatility race

  Fixes:
  - Add logging to detect trailing SL stalls
  - Fix STRUCTURE_ATR_STAGED phase transition atomicity
  - Add volatility regime caching to prevent erratic updates

  Testing:
  - Unit tests: 12/12 passed
  - Integration tests: 5/5 passed
  - Test coverage: 94%

  Safety:
  - Backup hash: xyz789uvw123
  - Rollback available
  - Risk assessment: LOW

  Output: agents/audit_exports/implementation_20260216_233959.json
  Database: agent_implementations table (id: 1337)

Files Changed:
  - Scalp-Engine/auto_trader_core.py (+87, -12)

Authored-By: Claude Code Agent <agent@trade-alerts.local>
```

**Commit 4 - Approval Decision** (after approval decision made)
```
# If AUTO-APPROVED:
Commit Message:
  Agent approval: cycle 42 - AUTO-APPROVED

  Decision: AUTO_APPROVED
  Reason: Test coverage 97% > 95% threshold, LOW risk assessment

  Next: Deploying to staging environment
  Monitoring: 24 hours before production

  Rollback: git reset --hard xyz789uvw123

Files Changed:
  - agents/audit_exports/approval_history.json (updated)

# If USER-APPROVED:
Commit Message:
  Agent approval: cycle 42 - USER APPROVED

  Decision: APPROVED
  User: (from approval_history)
  Comment: "Well-tested changes, low risk. Monitor for 48 hours."

  Test coverage: 92%
  Risk assessment: LOW

  Next: Deploying to staging environment
  Rollback: git reset --hard xyz789uvw123

Files Changed:
  - agents/audit_exports/approval_history.json (updated)

# If REJECTED:
Commit Message:
  Agent approval: cycle 42 - REJECTED

  Decision: REJECTED
  User: (from approval_history)
  Reason: "Test coverage only 87%, below 90% minimum"

  Rollback: git reset --hard jkl789mno123

  Next cycle: Coding Expert can improve and resubmit

Files Changed:
  - agents/audit_exports/approval_history.json (updated)
```

### Daily Summary Commit (End of Day)

**When**: After workflow completes (or next morning if late night)

```
Commit Message:
  Agent workflow: cycle 42 completed (5:30 PM EST)

  Summary:
  ✅ Analysis: 12 trades reviewed, 2 issues found
  ✅ Recommendations: 3 critical fixes identified
  ✅ Implementation: 87 lines of code changes
  ✅ Approval: AUTO-APPROVED (test coverage 97%)

  Status: Ready for staging deployment
  Monitoring period: 24 hours

  Full details available in agents/audit_exports/
  Database: agent_system.db (cycle 42)

Files Changed:
  - agents/audit_exports/approval_history.json
  - agents/audit_exports/audit_trail.json
  - agents/audit_exports/analysis_20260216_233959.json
  - agents/audit_exports/recommendations_20260216_233959.json
  - agents/audit_exports/implementation_20260216_233959.json

Authored-By: Claude Code Agent <agent@trade-alerts.local>
```

### Visibility: Checking History

**Via Git Log**:
```bash
# See all agent workflow commits
git log --grep="Agent" --oneline

# See approval history
git log --grep="approval:" --oneline

# See specific cycle
git log --grep="cycle 42" --oneline

# See last 10 cycles
git log --grep="Agent workflow:" --oneline | head -10

# View approval_history.json evolution
git log -p agents/audit_exports/approval_history.json
```

**Via GitHub UI** (if on GitHub):
- View commits by "Claude Code Agent"
- Filter by "Agent" in commit message
- View approval_history.json changes over time

**Via Web UI** (if deployed):
- View approval history with user comments
- Filter by decision (Approved, Rejected, Auto-Approved)
- Download approval_history.json as backup
- View full audit trail

---

## Next Steps

1. **Review Updated Plan** ✅ (You're here)
   - Database: SQLite (free, already used in codebase)
   - Timing: 5:30 PM EST (11:30 PM UTC daily)
   - Auto-Approval: Test coverage > 95% + LOW risk → automatic approval
   - Approval Audit: Complete history in approval_history.json (git-committed)
   - Pushover Notifications: For all approvals (you already have subscription)
   - Git Commits: All agent outputs committed for full traceability

2. **Phase 1 Implementation**: Create agent directory structure and shared utilities
   - `agents/__init__.py`
   - `agents/shared/json_schema.py` - Define all JSON schemas
   - `agents/shared/backup_manager.py` - Git backup/rollback operations
   - `agents/shared/database.py` - SQLite connection + initialization
   - `agents/shared/audit_logger.py` - Centralized audit logging
   - `agents/shared/pushover_notifier.py` - Pushover integration
   - Database schema creation (agent_analyses, recommendations, implementations, approval_history, audit_trail)
   - Test database connectivity

3. **Phase 2-5**: Implement each agent incrementally (as outlined)

4. **Render Deployment**: Configure new worker service
   - Set schedule: 5:30 PM EST
   - Set auto-approval threshold: 0.95
   - Configure Pushover credentials
   - Attach persistent disk at `/var/data`

5. **Testing**: Run workflow with real logs

6. **Monitoring**: Observe first 5-10 cycles

---

## Implementation Checklist (Phase 1)

**Goal**: Foundation ready for agent implementation

- [ ] Create `agents/` directory structure
- [ ] Create `data/agent_system.db` SQLite database
- [ ] Create all database tables (agent_analyses, recommendations, etc.)
- [ ] Implement `shared/json_schema.py` with all 5 JSON schemas
- [ ] Implement `shared/database.py` with helper functions
- [ ] Implement `shared/backup_manager.py` (git operations)
- [ ] Implement `shared/audit_logger.py` (audit trail recording)
- [ ] Implement `shared/pushover_notifier.py` (Pushover integration)
- [ ] Create schedule configuration in database
- [ ] Create agent configuration files
- [ ] Test database creation and querying
- [ ] Test backup/rollback mechanism locally
- [ ] Document environment variables needed
- [ ] Update .env template with new variables
- [ ] Create README for agents/ directory
- [ ] Ready for Phase 2: Analyst Agent implementation

