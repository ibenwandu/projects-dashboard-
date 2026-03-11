"""
Task router - maps incoming tasks to appropriate handlers.

Routes tasks by domain → agent, with approval gates for destructive operations.
"""

import logging
from typing import Callable, Optional, Dict, Any, Tuple

logger = logging.getLogger('TaskRouter')


class EMyTaskRouter:
    """Routes tasks to appropriate agents and handlers."""

    def __init__(self, delegation_engine, approval_gate):
        """Initialize router with delegation engine and approval gate."""
        self.delegation_engine = delegation_engine
        self.approval_gate = approval_gate
        self.logger = logging.getLogger('TaskRouter')

        # Domain → Agent mappings
        self.domain_handlers = {
            'trading': 'TradingAgent',
            'job_search': 'JobSearchAgent',
            'knowledge': 'KnowledgeAgent',
            'project_monitor': 'ProjectMonitorAgent',
            'research': 'ResearchAgent',
        }

        # Destructive action types requiring approval
        self.destructive_actions = {
            'delete_file',
            'reset_database',
            'disable_agent',
            'clear_cache',
            'modify_config',
            'force_reconciliation',
        }

    def can_route_task(self, domain: str) -> bool:
        """Check if router can handle this domain."""
        return domain in self.domain_handlers

    def route_task(self,
                  domain: str,
                  task_type: str,
                  description: str,
                  reason: str = None,
                  is_destructive: bool = False,
                  task_id: int = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Route a task to appropriate handler.

        Args:
            domain: Task domain (trading, job_search, knowledge, etc.)
            task_type: Type of task (health_check, search, etc.)
            description: Human-readable description
            reason: Why the task is needed
            is_destructive: Whether task is destructive (requires approval)
            task_id: Associated task ID in database

        Returns:
            (success, results) tuple
        """
        try:
            # Validate domain
            if not self.can_route_task(domain):
                return False, {'error': f'Unknown domain: {domain}'}

            # Check for approval if destructive
            if is_destructive:
                approved = self.approval_gate.request_approval(
                    action=task_type,
                    description=description,
                    reason=reason or 'System operation',
                    agent=domain
                )
                if not approved:
                    self.logger.warning(f"[ROUTER] Task {task_id} rejected: approval denied")
                    return False, {'error': 'Approval denied or timeout'}

            # Route to agent
            agent_name = self.domain_handlers[domain]
            self.logger.info(f"[ROUTER] Routing task {task_id} to {agent_name}")

            success, results = self.delegation_engine.spawn_registered(
                agent_name,
                task_id
            )

            return success, results

        except Exception as e:
            self.logger.error(f"[ROUTER] Error routing task: {e}")
            return False, {'error': str(e)}

    def is_destructive(self, action: str) -> bool:
        """Check if an action requires approval."""
        return action in self.destructive_actions

    def register_domain(self, domain: str, agent_name: str):
        """Register a new domain → agent mapping."""
        self.domain_handlers[domain] = agent_name
        self.logger.info(f"[ROUTER] Registered domain '{domain}' → {agent_name}")

    def mark_destructive(self, action: str):
        """Mark an action as destructive (requires approval)."""
        self.destructive_actions.add(action)
        self.logger.debug(f"[ROUTER] Marked '{action}' as destructive")

    def list_domains(self) -> list:
        """Return list of routable domains."""
        return list(self.domain_handlers.keys())

    def get_agent_for_domain(self, domain: str) -> Optional[str]:
        """Get agent name for a domain."""
        return self.domain_handlers.get(domain)
