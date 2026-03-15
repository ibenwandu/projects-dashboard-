"""Intelligent agent selection for workflow tasks."""

import logging
from typing import List, Dict, Any, Optional
from emy.brain.nodes import AGENT_REGISTRY

logger = logging.getLogger('EMyBrain.AgentSelector')


class AgentSelector:
    """Intelligently select agents based on task requirements."""

    # Define agent capabilities
    AGENT_CAPABILITIES = {
        'TradingAgent': [
            'market_analysis',
            'forex_signals',
            'price_prediction',
            'technical_analysis',
            'risk_assessment'
        ],
        'ResearchAgent': [
            'research',
            'project_evaluation',
            'feasibility_analysis',
            'data_collection',
            'summary_generation'
        ],
        'KnowledgeAgent': [
            'knowledge_query',
            'project_status',
            'memory_retrieval',
            'context_synthesis',
            'documentation'
        ],
        'ProjectMonitorAgent': [
            'project_monitoring',
            'status_tracking',
            'milestone_tracking',
            'email_notifications',
            'daily_reports'
        ],
        'JobSearchAgent': [
            'job_search',
            'job_application',
            'cover_letter_generation',
            'follow_up_emails',
            'opportunity_ranking'
        ]
    }

    # Define agent affinity keywords
    AGENT_KEYWORDS = {
        'TradingAgent': ['market', 'trade', 'forex', 'price', 'signal', 'analysis', 'sell', 'buy'],
        'ResearchAgent': ['research', 'evaluate', 'feasibility', 'project', 'opportunity', 'analysis'],
        'KnowledgeAgent': ['knowledge', 'status', 'query', 'information', 'memory', 'project'],
        'ProjectMonitorAgent': ['monitor', 'status', 'track', 'milestone', 'email', 'report'],
        'JobSearchAgent': ['job', 'apply', 'search', 'opportunity', 'employment']
    }

    def select_agents(
        self,
        task: Dict[str, Any],
        mode: str = 'auto',
        agents: Optional[List[str]] = None
    ) -> List[str]:
        """
        Select agents for task.

        Args:
            task: Task dict with type, input, required_capabilities
            mode: 'auto' for intelligent selection, 'explicit' for manual list
            agents: List of agents (for explicit mode)

        Returns:
            List of agent names to execute
        """
        if mode == 'explicit' and agents:
            # Validate agents exist
            valid_agents = [a for a in agents if self.is_valid_agent(a)]
            return valid_agents

        # Auto-select agents
        selected = set()

        # Check required capabilities
        required_caps = task.get('required_capabilities', [])
        if required_caps:
            for cap in required_caps:
                for agent_name, caps in self.AGENT_CAPABILITIES.items():
                    if cap in caps:
                        selected.add(agent_name)

        # Check task type
        task_type = task.get('type', '').lower()
        for agent_name, keywords in self.AGENT_KEYWORDS.items():
            if task_type in keywords:
                selected.add(agent_name)
            # Also check if any keyword is in the task type (e.g., 'market' in 'market_analysis')
            for keyword in keywords:
                if keyword in task_type:
                    selected.add(agent_name)
                    break

        # Check task input text
        task_input = task.get('input', '').lower()
        for agent_name, keywords in self.AGENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_input:
                    selected.add(agent_name)
                    break

        # If nothing selected, use KnowledgeAgent as fallback
        if not selected:
            selected.add('KnowledgeAgent')

        # Convert to sorted list for consistency
        result = sorted(list(selected))
        logger.info(f"Selected agents for task: {result}")
        return result

    def is_valid_agent(self, agent_name: str) -> bool:
        """
        Check if agent exists.

        Args:
            agent_name: Agent name to validate

        Returns:
            True if agent exists, False otherwise
        """
        return agent_name in AGENT_REGISTRY

    def get_agent_capabilities(self, agent_name: str) -> List[str]:
        """
        Get capabilities for agent.

        Args:
            agent_name: Agent name

        Returns:
            List of capability strings
        """
        return self.AGENT_CAPABILITIES.get(agent_name, [])
