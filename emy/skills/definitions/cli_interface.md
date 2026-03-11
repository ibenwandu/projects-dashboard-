---
name: cli_interface
domain: system
model: claude-opus-4-6
agent: Emy
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Emy's conversational CLI interface powered by Anthropic function calling.

Accepts natural language queries and executes appropriate tasks via intelligent routing.
Provides formatted results optimized for terminal readability.

## CLI Commands

### `python emy.py run`
Start main event loop (blocking, infinite until Ctrl+C).

### `python emy.py status`
Display system dashboard with:
- Task counts by status
- Daily API budget usage
- Recent skill success rates (24h)

### `python emy.py ask "prompt"`
Execute single conversational query via Anthropic API.
Supports natural language like: "run job search", "check status", "improve skills"

### `python emy.py skills`
List all registered skills by domain with descriptions.

### `python emy.py agents`
List all sub-agents with roles and domains.

## Tool Use (Function Calling)

When processing "ask" queries, Anthropic can invoke these tools:

1. **run_task** — Execute task by routing to agent
   - Input: domain, task_type, description
   - Output: Task result or error

2. **get_status** — Get current system metrics
   - Input: none
   - Output: Task stats, budget, timestamp

3. **list_agents** — List available agents
   - Input: none
   - Output: Agent names and domains

4. **get_recent_tasks** — Get completed tasks
   - Input: limit (optional, default 5)
   - Output: Recent task details

## Response Formatting

- **Errors**: Concise error message with remediation advice
- **Task Results**: JSON formatted with success/failure indicator
- **Status**: Tabular format with progress bars
- **Lists**: Bulleted markdown format

## Requirements

- `ANTHROPIC_API_KEY` environment variable or .env file
- Claude Opus 4.6 model selected

## Self-Improvement Hooks

- If query_success_rate < 80%: Review tool definitions for clarity
- If response_latency > 5s: Consider caching status queries
- If tool_not_found errors > 5%: Update tool schema definitions

