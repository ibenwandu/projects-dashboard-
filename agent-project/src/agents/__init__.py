"""
Agent and Sub-Agent Ecosystem

This package contains all agent implementations for the multi-agent system.
"""

from .base_agent import BaseAgent
from .primary_agent import PrimaryAgent
from .research_agent import ResearchAgent
from .analysis_agent import AnalysisAgent
from .writing_agent import WritingAgent
from .quality_control_agent import QualityControlAgent

__all__ = [
    'BaseAgent',
    'PrimaryAgent', 
    'ResearchAgent',
    'AnalysisAgent',
    'WritingAgent',
    'QualityControlAgent'
]

__version__ = '1.0.0'














