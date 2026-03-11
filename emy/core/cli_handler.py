"""
CLI handler for Emy conversational interface.

Processes user queries via Anthropic API with tool use (function calling).
Executes requested tasks and returns formatted results.
"""

import logging
import os
import json
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger('CliHandler')


class EMyCliHandler:
    """Handle CLI queries via Anthropic API with tool use."""

    def __init__(self, delegation_engine, task_router, database):
        """Initialize CLI handler."""
        self.delegation_engine = delegation_engine
        self.task_router = task_router
        self.db = database
        self.logger = logging.getLogger('CliHandler')

        # Import Anthropic here to avoid import errors if API key missing
        try:
            from anthropic import Anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                self.logger.warning("[CLI] ANTHROPIC_API_KEY not set")
                self.client = None
            else:
                self.client = Anthropic(api_key=api_key)
        except ImportError:
            self.logger.error("[CLI] Anthropic SDK not available")
            self.client = None

    def handle_query(self, query: str) -> Tuple[bool, str]:
        """
        Handle user query via Anthropic with tool use.

        Args:
            query: User's natural language query

        Returns:
            (success, response_text)
        """
        if not self.client:
            return False, (
                "Error: ANTHROPIC_API_KEY not configured.\n"
                "Set environment variable: export ANTHROPIC_API_KEY=sk-...\n"
                "Or configure in .env file in emy/ directory."
            )

        try:
            self.logger.info(f"[CLI] Processing query: {query[:60]}...")

            # Log task to database
            task_id = self.db.log_task('cli', 'user_query', 'ask', query)

            # Build tools for Anthropic
            tools = self._build_tools()

            # Call Anthropic with tools
            response = self.client.messages.create(
                model='claude-opus-4-6',
                max_tokens=1000,
                tools=tools,
                messages=[
                    {
                        'role': 'user',
                        'content': query
                    }
                ]
            )

            # Process response (may include tool calls)
            result_text = self._process_response(response)

            # Log task completion
            self.db.update_task(task_id, 'completed', json.dumps({
                'query': query,
                'response': result_text[:200]
            }))

            return True, result_text

        except Exception as e:
            self.logger.error(f"[CLI] Error handling query: {e}")
            return False, f"Error: {str(e)}"

    def _build_tools(self) -> list:
        """Build tool definitions for Anthropic function calling."""
        return [
            {
                'name': 'run_task',
                'description': 'Execute a task by routing to appropriate agent',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'domain': {
                            'type': 'string',
                            'description': 'Task domain (trading, job_search, knowledge, project_monitor, research)'
                        },
                        'task_type': {
                            'type': 'string',
                            'description': 'Type of task to execute'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'What the task should do'
                        }
                    },
                    'required': ['domain', 'task_type']
                }
            },
            {
                'name': 'get_status',
                'description': 'Get current system status and metrics',
                'input_schema': {
                    'type': 'object',
                    'properties': {}
                }
            },
            {
                'name': 'list_agents',
                'description': 'List all available agents and their capabilities',
                'input_schema': {
                    'type': 'object',
                    'properties': {}
                }
            },
            {
                'name': 'get_recent_tasks',
                'description': 'Get recent completed tasks and their results',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'limit': {
                            'type': 'integer',
                            'description': 'Number of tasks to return (default 5)'
                        }
                    }
                }
            }
        ]

    def _process_response(self, response) -> str:
        """Process Anthropic response, handling tool calls."""
        try:
            # Check if response contains tool calls
            if hasattr(response, 'content') and response.content:
                for block in response.content:
                    if hasattr(block, 'type') and block.type == 'tool_use':
                        # Execute tool call
                        tool_result = self._execute_tool(block.name, block.input)
                        return self._format_result(tool_result)
                    elif hasattr(block, 'text'):
                        return block.text

            # Fallback to text
            if hasattr(response, 'content') and response.content:
                return response.content[0].text if response.content else "No response"

            return "No response from Anthropic"

        except Exception as e:
            self.logger.error(f"[CLI] Error processing response: {e}")
            return f"Error processing response: {str(e)}"

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool call."""
        try:
            if tool_name == 'run_task':
                domain = tool_input.get('domain')
                task_type = tool_input.get('task_type')
                description = tool_input.get('description', task_type)

                # Route task
                task_id = self.db.log_task('cli', domain, task_type, description)
                success, result = self.task_router.route_task(
                    domain, task_type, description, task_id=task_id
                )

                return {
                    'success': success,
                    'domain': domain,
                    'task_type': task_type,
                    'result': result
                }

            elif tool_name == 'get_status':
                return self._get_status()

            elif tool_name == 'list_agents':
                return self._list_agents()

            elif tool_name == 'get_recent_tasks':
                limit = tool_input.get('limit', 5)
                return self._get_recent_tasks(limit)

            else:
                return {'error': f'Unknown tool: {tool_name}'}

        except Exception as e:
            self.logger.error(f"[CLI] Error executing tool {tool_name}: {e}")
            return {'error': str(e)}

    def _get_status(self) -> Dict[str, Any]:
        """Get system status."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Task stats
                cursor.execute("""
                    SELECT status, COUNT(*) as count FROM emy_tasks GROUP BY status
                """)
                tasks = {row['status']: row['count'] for row in cursor.fetchall()}

                # Daily spend
                daily_spend = self.db.get_daily_spend()
                daily_budget = float(os.getenv('EMY_DAILY_BUDGET_USD', '5.00'))

                return {
                    'timestamp': datetime.now().isoformat(),
                    'tasks': tasks,
                    'budget': {
                        'daily_spend': round(daily_spend, 2),
                        'daily_budget': daily_budget,
                        'percent_used': round(daily_spend / daily_budget * 100, 1)
                    }
                }

        except Exception as e:
            self.logger.error(f"[CLI] Error getting status: {e}")
            return {'error': str(e)}

    def _list_agents(self) -> Dict[str, Any]:
        """List all agents."""
        domains = self.task_router.list_domains()
        agents = {}
        for domain in domains:
            agent = self.task_router.get_agent_for_domain(domain)
            agents[domain] = agent

        return {
            'agents': agents,
            'count': len(agents)
        }

    def _get_recent_tasks(self, limit: int = 5) -> Dict[str, Any]:
        """Get recent tasks."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, domain, task_type, status, description, completed_at
                    FROM emy_tasks
                    WHERE status != 'pending'
                    ORDER BY completed_at DESC
                    LIMIT ?
                """, (limit,))

                tasks = []
                for row in cursor.fetchall():
                    tasks.append({
                        'id': row['id'],
                        'domain': row['domain'],
                        'task_type': row['task_type'],
                        'status': row['status'],
                        'description': row['description']
                    })

                return {
                    'recent_tasks': tasks,
                    'count': len(tasks)
                }

        except Exception as e:
            self.logger.error(f"[CLI] Error getting recent tasks: {e}")
            return {'error': str(e)}

    def _format_result(self, result: Dict[str, Any]) -> str:
        """Format tool result as readable text."""
        try:
            if 'error' in result:
                return f"Error: {result['error']}"

            # Format as readable text
            lines = []

            if 'success' in result:
                status = "Success" if result['success'] else "Failed"
                lines.append(f"Status: {status}")

            if 'domain' in result:
                lines.append(f"Domain: {result['domain']}")

            if 'task_type' in result:
                lines.append(f"Task: {result['task_type']}")

            if 'result' in result:
                lines.append(f"Result: {json.dumps(result['result'], indent=2)}")

            if 'agents' in result:
                lines.append(f"Available Agents ({result['count']}):")
                for domain, agent in result['agents'].items():
                    lines.append(f"  - {domain}: {agent}")

            if 'tasks' in result:
                lines.append("Task Status:")
                for status, count in result['tasks'].items():
                    lines.append(f"  {status}: {count}")

            if 'budget' in result:
                budget = result['budget']
                lines.append(f"Budget: ${budget['daily_spend']:.2f} / ${budget['daily_budget']:.2f} ({budget['percent_used']:.1f}%)")

            if 'recent_tasks' in result:
                lines.append(f"Recent Tasks ({result['count']}):")
                for task in result['recent_tasks']:
                    lines.append(f"  [{task['id']}] {task['domain']}:{task['task_type']} — {task['status']}")

            return '\n'.join(lines) if lines else "No result"

        except Exception as e:
            return f"Error formatting result: {str(e)}"
