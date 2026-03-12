"""Emy Brain - LangGraph-based workflow orchestration engine.

Phase 2 component providing multi-step workflow orchestration with browser automation,
memory persistence, and intelligent request routing via Claude.

Phase 2a: Domain agent nodes with conditional routing.
"""

from emy.brain.engine import EMyBrain
from emy.brain.state import WorkflowState
from emy.brain import nodes

__all__ = [
    'EMyBrain',
    'WorkflowState',
    'nodes',
]
