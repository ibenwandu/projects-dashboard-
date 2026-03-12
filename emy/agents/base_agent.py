"""
Base agent class for all Emy sub-agents.

All sub-agents inherit from EMySubAgent and implement run().
"""

import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any
from emy.core.disable_guard import EMyDisableGuard

logger = logging.getLogger('EMySubAgent')


class EMySubAgent(ABC):
    """Base class for all Emy sub-agents."""

    def __init__(self, agent_name: str, model: str):
        """Initialize sub-agent."""
        self.agent_name = agent_name
        self.model = model
        self.disable_guard = EMyDisableGuard()
        self.logger = logging.getLogger(agent_name)

    def check_disabled(self) -> bool:
        """Check if Emy is disabled."""
        return self.disable_guard.is_disabled()

    @abstractmethod
    def run(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute the agent's primary task.

        Returns:
            (success: bool, results: Dict)
                success=True if task completed successfully
                results contains outcome data
        """
        pass

    def report_result(self, success: bool, result_json: str = None, error: str = None):
        """
        Report agent execution result.

        Logs to database for monitoring and debugging.
        """
        status = 'success' if success else 'failed'
        self.logger.info(f"[{status.upper()}] {self.agent_name} execution complete")
        if error:
            self.logger.error(f"Error: {error}")
        return (success, result_json)
