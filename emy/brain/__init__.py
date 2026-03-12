"""Emy Brain - LangGraph-based workflow orchestration engine.

Phase 2 component providing multi-step workflow orchestration with browser automation,
memory persistence, and intelligent request routing via Claude.
"""

from emy.brain.engine import EMyBrain
from emy.brain.state import WorkflowState

__all__ = [
    'EMyBrain',
    'WorkflowState',
]
