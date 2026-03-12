"""
Emy CLI Client - Command-line interface for interacting with Emy gateway server.

Commands:
  execute  - Start a new workflow
  status   - Check workflow status
  list     - List all workflows with pagination
  agents   - View agent status
  health   - Check server health
"""

import os
import sys
import json
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Setup logging
logger = logging.getLogger('EmyCLI')


class EMyAPIClient:
    """Client for communicating with Emy FastAPI gateway."""

    def __init__(self, api_url: Optional[str] = None, timeout: int = 5, verbose: bool = False):
        """Initialize API client.

        Args:
            api_url: Base URL for Emy API (defaults to EMY_API_URL env var or http://localhost:8000)
            timeout: Request timeout in seconds
            verbose: Enable verbose error output
        """
        self.api_url = api_url or os.getenv('EMY_API_URL', 'http://localhost:8000')
        self.timeout = timeout
        self.verbose = verbose
        self.console = Console()

    def _handle_error(self, error: Exception, operation: str = 'API call') -> None:
        """Handle and display API errors.

        Args:
            error: Exception that occurred
            operation: Description of operation that failed
        """
        if isinstance(error, requests.exceptions.ConnectionError):
            click.secho(
                f'Error: Server unavailable. Is Emy API running at {self.api_url}?',
                fg='red',
                err=True
            )
        elif isinstance(error, requests.exceptions.Timeout):
            click.secho(
                f'Error: Request timeout after {self.timeout}s',
                fg='red',
                err=True
            )
        elif isinstance(error, requests.exceptions.RequestException):
            click.secho(f'Error: {operation} failed: {str(error)}', fg='red', err=True)
        else:
            click.secho(f'Error: {str(error)}', fg='red', err=True)

    def _handle_response_error(self, response: requests.Response) -> None:
        """Handle HTTP error responses.

        Args:
            response: HTTP response object
        """
        try:
            error_data = response.json()
            error_msg = error_data.get('error', response.text)
        except (json.JSONDecodeError, ValueError):
            error_msg = response.text

        if self.verbose:
            click.secho(
                f'Error: HTTP {response.status_code}: {error_msg}',
                fg='red',
                err=True
            )
        else:
            # Show concise error message
            if response.status_code == 404:
                click.secho('Error: Resource not found', fg='red', err=True)
            elif response.status_code == 400:
                click.secho(f'Error: Bad request: {error_msg}', fg='red', err=True)
            elif response.status_code >= 500:
                click.secho('Error: Server error. Use --verbose for details', fg='red', err=True)
            else:
                click.secho(f'Error: {error_msg}', fg='red', err=True)

    def execute_workflow(self, workflow_type: str, agents: str, input_data: Optional[str] = None) -> Optional[dict]:
        """Execute a new workflow.

        Args:
            workflow_type: Type of workflow to execute
            agents: Comma-separated list of agents
            input_data: Optional JSON input data

        Returns:
            Workflow response dict or None if error
        """
        try:
            # Parse input data if provided
            parsed_input = None
            if input_data:
                try:
                    parsed_input = json.loads(input_data)
                except json.JSONDecodeError as e:
                    self.console.print(f'[red]Error:[/red] Invalid JSON input: {str(e)}', file=sys.stderr)
                    return None

            # Parse agents list
            agent_list = [a.strip() for a in agents.split(',')]

            url = f'{self.api_url}/workflows/execute'
            payload = {
                'workflow_type': workflow_type,
                'agents': agent_list,
                'input': parsed_input
            }

            response = requests.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                self._handle_response_error(response)
                return None

        except requests.exceptions.RequestException as e:
            self._handle_error(e, 'execute workflow')
            return None

    def get_workflow_status(self, workflow_id: str) -> Optional[dict]:
        """Get status of a workflow.

        Args:
            workflow_id: ID of workflow to check

        Returns:
            Workflow status dict or None if error
        """
        try:
            url = f'{self.api_url}/workflows/{workflow_id}'
            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                self._handle_response_error(response)
                return None

        except requests.exceptions.RequestException as e:
            self._handle_error(e, 'get workflow status')
            return None

    def list_workflows(self, limit: int = 10, offset: int = 0) -> Optional[dict]:
        """List workflows with pagination.

        Args:
            limit: Number of results to return
            offset: Number of results to skip

        Returns:
            Workflows list dict or None if error
        """
        try:
            url = f'{self.api_url}/workflows'
            params = {'limit': limit, 'offset': offset}
            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                self._handle_response_error(response)
                return None

        except requests.exceptions.RequestException as e:
            self._handle_error(e, 'list workflows')
            return None

    def get_agents_status(self) -> Optional[dict]:
        """Get status of all agents.

        Returns:
            Agents status dict or None if error
        """
        try:
            url = f'{self.api_url}/agents/status'
            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                self._handle_response_error(response)
                return None

        except requests.exceptions.RequestException as e:
            self._handle_error(e, 'get agents status')
            return None

    def health_check(self) -> Optional[dict]:
        """Check server health.

        Returns:
            Health status dict or None if error
        """
        try:
            url = f'{self.api_url}/health'
            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                self._handle_response_error(response)
                return None

        except requests.exceptions.RequestException as e:
            self._handle_error(e, 'health check')
            return None


def _format_timestamp(timestamp_str: str) -> str:
    """Convert ISO timestamp to local time string.

    Args:
        timestamp_str: ISO format timestamp

    Returns:
        Formatted local time string
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError):
        return timestamp_str


@click.group()
@click.version_option()
def cli():
    """Emy CLI - Control and monitor your AI Chief of Staff."""
    pass


@cli.command()
@click.argument('workflow_type')
@click.argument('agents')
@click.argument('input', required=False)
@click.option('--verbose', is_flag=True, help='Show detailed error messages')
def execute(workflow_type: str, agents: str, input: Optional[str], verbose: bool):
    """Execute a new workflow.

    WORKFLOW_TYPE: Type of workflow (e.g., 'analysis', 'health_check')
    AGENTS: Comma-separated list of agents (e.g., 'KnowledgeAgent,TradingAgent')
    INPUT: Optional JSON input data (optional)
    """
    try:
        client = EMyAPIClient(verbose=verbose)
        result = client.execute_workflow(workflow_type, agents, input)

        if result:
            click.secho('✓ Workflow created', fg='green')
            click.echo(f"  ID: {result.get('workflow_id', 'N/A')}")
            click.echo(f"  Status: {result.get('status', 'N/A')}")
            created_at = result.get('created_at', '')
            if created_at:
                click.echo(f"  Created: {_format_timestamp(created_at)}")
        else:
            sys.exit(1)
    except Exception as e:
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        sys.exit(1)


@cli.command()
@click.argument('workflow_id')
@click.option('--verbose', is_flag=True, help='Show detailed error messages')
def status(workflow_id: str, verbose: bool):
    """Check status of a workflow.

    WORKFLOW_ID: ID of the workflow to check
    """
    try:
        client = EMyAPIClient(verbose=verbose)
        result = client.get_workflow_status(workflow_id)

        if result:
            # Create table for display
            table = Table(title=f"Workflow: {workflow_id}", show_header=False, box=None)
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Type", result.get('type', 'N/A'))
            table.add_row("Status", result.get('status', 'N/A'))

            created_at = result.get('created_at', '')
            if created_at:
                table.add_row("Created", _format_timestamp(created_at))

            updated_at = result.get('updated_at', '')
            if updated_at:
                table.add_row("Updated", _format_timestamp(updated_at))

            input_data = result.get('input', '')
            if input_data:
                if isinstance(input_data, str) and len(input_data) > 50:
                    input_data = input_data[:50] + '...'
                table.add_row("Input", str(input_data))

            output_data = result.get('output', '')
            if output_data:
                if isinstance(output_data, str) and len(output_data) > 50:
                    output_data = output_data[:50] + '...'
                table.add_row("Output", str(output_data))

            console = Console()
            console.print(table)
        else:
            sys.exit(1)
    except Exception as e:
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        sys.exit(1)


@cli.command()
@click.option('--limit', default=10, help='Number of results (default: 10)')
@click.option('--offset', default=0, help='Number of results to skip (default: 0)')
@click.option('--verbose', is_flag=True, help='Show detailed error messages')
def list(limit: int, offset: int, verbose: bool):
    """List all workflows with pagination.

    Use --limit and --offset to paginate through results.
    """
    try:
        client = EMyAPIClient(verbose=verbose)
        result = client.list_workflows(limit=limit, offset=offset)

        if result:
            workflows = result.get('workflows', [])

            if not workflows:
                click.echo('No workflows found')
                return

            # Create table
            table = Table(title=f"Workflows (limit: {limit}, offset: {offset})")
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Created", style="yellow")

            for wf in workflows:
                created_at = wf.get('created_at', '')
                formatted_time = _format_timestamp(created_at) if created_at else 'N/A'
                table.add_row(
                    wf.get('workflow_id', 'N/A'),
                    wf.get('type', 'N/A'),
                    wf.get('status', 'N/A'),
                    formatted_time
                )

            console = Console()
            console.print(table)
            console.print(f"\n[dim]Total: {result.get('total', 'N/A')} workflows[/dim]")
        else:
            sys.exit(1)
    except Exception as e:
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        sys.exit(1)


@cli.command()
@click.option('--verbose', is_flag=True, help='Show detailed error messages')
def agents(verbose: bool):
    """View status of all agents."""
    try:
        client = EMyAPIClient(verbose=verbose)
        result = client.get_agents_status()

        if result:
            agent_list = result.get('agents', [])

            if not agent_list:
                click.echo('No agents found')
                return

            # Create table
            table = Table(title="Agent Status")
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Completed", style="yellow")
            table.add_column("Failed", style="red")
            table.add_column("Last Activity", style="magenta")

            for agent in agent_list:
                last_activity = agent.get('last_activity', '')
                formatted_time = _format_timestamp(last_activity) if last_activity else 'N/A'
                table.add_row(
                    agent.get('agent_name', 'N/A'),
                    agent.get('status', 'N/A'),
                    str(agent.get('tasks_completed', 0)),
                    str(agent.get('tasks_failed', 0)),
                    formatted_time
                )

            console = Console()
            console.print(table)
        else:
            sys.exit(1)
    except Exception as e:
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        sys.exit(1)


@cli.command()
@click.option('--verbose', is_flag=True, help='Show detailed error messages')
def health(verbose: bool):
    """Check Emy API server health."""
    try:
        client = EMyAPIClient(verbose=verbose)
        result = client.health_check()

        if result:
            status_str = result.get('status', 'unknown').upper()
            click.secho('✓ Server is healthy', fg='green')
            click.echo(f"  Status: {status_str}")

            timestamp = result.get('timestamp', '')
            if timestamp:
                click.echo(f"  Checked at: {_format_timestamp(timestamp)}")
        else:
            click.secho('✗ Server offline', fg='red')
            sys.exit(1)
    except Exception as e:
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
