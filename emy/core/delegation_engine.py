"""
Delegation engine - spawns and manages sub-agent execution.

Coordinates agent instantiation, execution, logging, and result handling.
"""

import logging
import json
from typing import Tuple, Dict, Any, Callable, List, Optional
from datetime import datetime

logger = logging.getLogger('DelegationEngine')


class EMyDelegationEngine:
    """Manages sub-agent delegation and execution."""

    def __init__(self, database=None):
        """Initialize delegation engine."""
        self.db = database
        self.registered_agents: Dict[str, type] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger('DelegationEngine')

    def register_agent(self, name: str, agent_class: type) -> bool:
        """Register an agent class for later spawning."""
        try:
            self.registered_agents[name] = agent_class
            self.logger.info(f"[REGISTER] Agent {name}: {agent_class.__name__}")
            return True
        except Exception as e:
            self.logger.error(f"Error registering agent {name}: {e}")
            return False

    def spawn(self, agent_class: type, task_id: int = None,
              *args, **kwargs) -> Tuple[bool, Dict[str, Any]]:
        """
        Spawn and execute a sub-agent.

        Args:
            agent_class: Agent class to instantiate
            task_id: Associated task ID (for database logging)
            *args, **kwargs: Arguments for agent.__init__

        Returns:
            (success: bool, results: Dict)
        """
        agent_name = agent_class.__name__
        start_time = datetime.now()

        try:
            # Instantiate agent
            agent = agent_class(*args, **kwargs)
            self.logger.debug(f"[SPAWN] {agent_name} instantiated")

            # Execute agent
            success, results = agent.run()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Log to database
            if self.db and task_id:
                self.db.log_agent_run(
                    task_id=task_id,
                    agent_name=agent_name,
                    model=agent.model,
                    status='success' if success else 'failed',
                    result_summary=json.dumps(results) if results else None
                )

            # Track in history
            execution_record = {
                'agent': agent_name,
                'task_id': task_id,
                'success': success,
                'duration_seconds': duration,
                'timestamp': start_time.isoformat(),
                'results_keys': list(results.keys()) if results else []
            }
            self.execution_history.append(execution_record)

            self.logger.info(f"[EXECUTE] {agent_name}: success={success}, "
                           f"duration={duration:.2f}s")

            return (success, results)

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_msg = str(e)

            self.logger.error(f"[ERROR] {agent_name}: {error_msg}")

            # Log error to database
            if self.db and task_id:
                self.db.log_agent_run(
                    task_id=task_id,
                    agent_name=agent_name,
                    model=getattr(agent_class, '__name__', 'unknown'),
                    status='failed',
                    error_message=error_msg
                )

            return (False, {'error': error_msg, 'duration_seconds': duration})

    def spawn_registered(self, agent_name: str, task_id: int = None,
                        *args, **kwargs) -> Tuple[bool, Dict[str, Any]]:
        """
        Spawn a registered agent by name.

        Args:
            agent_name: Registered agent name
            task_id: Associated task ID

        Returns:
            (success, results)
        """
        if agent_name not in self.registered_agents:
            self.logger.error(f"[ERROR] Agent not registered: {agent_name}")
            return (False, {'error': f'agent_not_registered: {agent_name}'})

        agent_class = self.registered_agents[agent_name]
        return self.spawn(agent_class, task_id, *args, **kwargs)

    def list_agents(self) -> List[str]:
        """List registered agent names."""
        return sorted(self.registered_agents.keys())

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return self.execution_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get delegation engine statistics."""
        total_executions = len(self.execution_history)
        successful = sum(1 for e in self.execution_history if e['success'])
        failed = total_executions - successful

        avg_duration = 0
        if self.execution_history:
            avg_duration = sum(e['duration_seconds'] for e in self.execution_history) / len(self.execution_history)

        return {
            'registered_agents': self.list_agents(),
            'total_executions': total_executions,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total_executions if total_executions > 0 else 0,
            'avg_duration_seconds': avg_duration
        }
