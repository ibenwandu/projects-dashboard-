"""
Base agent class for all Emy sub-agents.

All sub-agents inherit from EMySubAgent and implement run().
"""

import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any
from anthropic import Anthropic
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

    def _call_claude(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        Call Claude API with a prompt.

        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens in response (default 1024)

        Returns:
            The Claude response text

        Raises:
            Exception: If API call fails
        """
        try:
            client = Anthropic()
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = message.content[0].text
            self.logger.debug(f"Claude response: {response_text[:100]}...")
            return response_text
        except Exception as e:
            self.logger.error(f"Claude API error: {e}")
            raise

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
