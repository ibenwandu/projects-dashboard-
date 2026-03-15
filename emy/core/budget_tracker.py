"""Budget tracking and enforcement for parallel agent execution."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from emy.core.database import EMyDatabase

logger = logging.getLogger('EMyBrain.BudgetTracker')


class BudgetTracker:
    """Track and enforce budget across parallel agent executions."""

    def __init__(self, daily_limit: float = 10.0):
        """
        Initialize budget tracker.

        Args:
            daily_limit: Daily budget limit in dollars (default $10)
        """
        self.daily_limit = daily_limit
        self.db = EMyDatabase()
        self._per_agent_limit = daily_limit  # Default to full limit per agent
        self._num_agents = 1  # Default to 1 agent for backward compatibility

    async def distribute_budget(self, agents: List[str]) -> Dict[str, float]:
        """
        Distribute daily budget equally across agents.

        Args:
            agents: List of agent names to distribute budget for

        Returns:
            Dict mapping agent name to allocated budget
        """
        self._num_agents = len(agents) if agents else 1
        self._per_agent_limit = self.daily_limit / self._num_agents
        return {agent: self._per_agent_limit for agent in agents}

    async def record_spending(self, agent_name: str, amount: float) -> None:
        """
        Record spending for an agent.

        Args:
            agent_name: Name of agent
            amount: Amount spent in dollars
        """
        today = datetime.utcnow().date()

        # Insert into agent_budget table
        self.db.execute("""
            INSERT INTO agent_budget (agent_name, date, spent_today)
            VALUES (?, ?, ?)
            ON CONFLICT(agent_name, date) DO UPDATE SET
            spent_today = spent_today + ?
        """, (agent_name, today, amount, amount))

        logger.info(f"Recorded ${amount:.2f} spending for {agent_name}")

    async def get_agent_spending(self, agent_name: str) -> float:
        """
        Get total spending for agent today.

        Args:
            agent_name: Name of agent

        Returns:
            Total spent today in dollars
        """
        today = datetime.utcnow().date()

        result = self.db.query_one("""
            SELECT spent_today FROM agent_budget
            WHERE agent_name = ? AND date = ?
        """, (agent_name, today))

        return result[0] if result else 0.0

    async def has_budget(self, agent_name: str, required_amount: float) -> bool:
        """
        Check if agent has sufficient budget remaining.

        Args:
            agent_name: Name of agent
            required_amount: Amount needed in dollars

        Returns:
            True if budget available, False otherwise
        """
        remaining = await self.get_remaining_budget(agent_name)
        return remaining >= required_amount

    async def get_remaining_budget(self, agent_name: str) -> float:
        """
        Get remaining budget for agent.

        Args:
            agent_name: Name of agent

        Returns:
            Remaining budget in dollars
        """
        spent = await self.get_agent_spending(agent_name)
        return max(0, self._per_agent_limit - spent)

    async def reset_daily_budget(self) -> None:
        """Reset daily budget (called at midnight UTC)."""
        logger.info(f"Resetting daily budget for all agents")
        # Budget is per-day in database, so no action needed
        # New entries are created automatically for new date

    async def get_budget_status(self, agent_name: str) -> Dict[str, float]:
        """
        Get comprehensive budget status for agent.

        Args:
            agent_name: Name of agent

        Returns:
            Dict with allocated, spent, remaining amounts
        """
        spent = await self.get_agent_spending(agent_name)
        remaining = await self.get_remaining_budget(agent_name)

        return {
            'allocated': self._per_agent_limit,
            'spent': spent,
            'remaining': remaining,
            'percentage_used': (spent / self._per_agent_limit * 100) if self._per_agent_limit > 0 else 0
        }
