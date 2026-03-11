#!/usr/bin/env python3
"""
Emy CLI entry point.

Usage:
    python emy.py run                       # Start main loop
    python emy.py ask "prompt text"         # Single query
    python emy.py status                    # Show dashboard
    python emy.py skills                    # List skills
    python emy.py agents                    # List agents
    python emy.py --help                    # Show help
"""

import sys
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

# Add emy directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file
load_dotenv(Path(__file__).parent / 'emy' / '.env')

from emy.main import EMyAgentLoop
from emy.core.database import EMyDatabase
from emy.core.cli_handler import EMyCliHandler
from emy.core.delegation_engine import EMyDelegationEngine
from emy.core.task_router import EMyTaskRouter
from emy.core.approval_gate import EMyApprovalGate
from emy.tools.api_client import OandaClient


def cmd_run(args):
    """Start main Emy loop."""
    loop = EMyAgentLoop()
    loop.run()


def cmd_ask(args):
    """Execute a single query."""
    try:
        # Initialize components
        db = EMyDatabase()
        db.initialize_schema()
        delegation_engine = EMyDelegationEngine(database=db)
        approval_gate = EMyApprovalGate(db)
        task_router = EMyTaskRouter(delegation_engine, approval_gate)
        cli_handler = EMyCliHandler(delegation_engine, task_router, db)

        # Process query
        success, response = cli_handler.handle_query(args.prompt)

        print(f"\n{response}\n")
        return 0 if success else 1

    except Exception as e:
        print(f"\nError: {e}\n")
        return 1


def cmd_status(args):
    """Show Emy status dashboard."""
    db = EMyDatabase()
    db.initialize_schema()

    # Get basic stats
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Task stats
        cursor.execute("SELECT status, COUNT(*) as count FROM emy_tasks GROUP BY status")
        tasks = {row['status']: row['count'] for row in cursor.fetchall()}

        # Daily spend
        daily_spend = db.get_daily_spend()
        daily_budget = float(__import__('os').getenv('EMY_DAILY_BUDGET_USD', '5.00'))

        # Skill success rate
        cursor.execute("""
            SELECT skill_name, COUNT(*) as total, SUM(success) as wins
            FROM skill_outcomes
            WHERE run_timestamp > datetime('now', '-1 day')
            GROUP BY skill_name
        """)
        skills = cursor.fetchall()

    print("\n" + "="*60)
    print("Emy - AI Chief of Staff")
    print("="*60)

    print("\n[Task Status]")
    for status, count in sorted(tasks.items()):
        print(f"  {status.upper()}: {count}")

    # OANDA Account Status
    print("\n[OANDA Account]")
    try:
        oanda_client = OandaClient(
            access_token=os.getenv('OANDA_ACCESS_TOKEN'),
            account_id=os.getenv('OANDA_ACCOUNT_ID')
        )
        account = oanda_client.get_account_summary()
        if account:
            print(f"  Equity: ${account['equity']:.2f}")
            print(f"  Margin Available: ${account['margin_available']:.2f}")
            margin_pct = (account['margin_used'] / account['equity'] * 100) if account['equity'] > 0 else 0
            print(f"  Margin Utilization: {margin_pct:.1f}%")
            print(f"  Unrealized P&L: ${account['unrealized_pl']:.2f}")

            # Show open trades count
            trades = oanda_client.get_open_trades()
            max_positions = int(os.getenv('OANDA_MAX_CONCURRENT_POSITIONS', '5'))
            print(f"  Open Positions: {len(trades)}/{max_positions}")
        else:
            print("  [WARN] Could not fetch account data (API error or not configured)")
    except Exception as e:
        print(f"  [WARN] OANDA client error: {str(e)}")

    print(f"\n[Budget]")
    budget_percent = (daily_spend / daily_budget * 100) if daily_budget > 0 else 0
    bar_length = 30
    filled = int(bar_length * budget_percent / 100)
    bar = "#" * filled + "-" * (bar_length - filled)
    print(f"  [{bar}] ${daily_spend:.2f} / ${daily_budget:.2f} ({budget_percent:.1f}%)")

    if skills:
        print(f"\n[Skills (24h)]")
        for row in skills:
            sr = row['wins'] / row['total'] * 100 if row['total'] > 0 else 0
            print(f"  {row['skill_name']}: {row['wins']}/{row['total']} ({sr:.0f}%)")

    print("\n" + "="*60)
    return 0


def cmd_skills(args):
    """List all registered skills."""
    skills_list = [
        ("trading_monitor", "trading", "Monitor Render services for Trading"),
        ("render_health_check", "trading", "Check Render health status"),
        ("job_search_daily", "job_search", "Daily job search across platforms"),
        ("resume_tailor", "job_search", "Tailor resumes for high-scoring jobs"),
        ("obsidian_update", "knowledge", "Update Obsidian dashboard"),
        ("memory_update", "knowledge", "Persist findings to MEMORY.md"),
        ("approval_gate", "system", "Request approval for destructive actions"),
        ("task_routing", "system", "Route tasks to appropriate agents"),
        ("skill_improvement", "system", "Auto-improve underperforming skills"),
        ("project_monitor", "project_monitor", "Monitor all Render services"),
        ("research_agent", "research", "Evaluate project feasibility"),
    ]

    print("\n" + "="*70)
    print("Emy Skills Registry")
    print("="*70)

    by_domain = {}
    for name, domain, desc in skills_list:
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append((name, desc))

    for domain in sorted(by_domain.keys()):
        print(f"\n[{domain.upper()}]")
        for name, desc in by_domain[domain]:
            print(f"  • {name:30s} — {desc}")

    print("\n" + "="*70)
    return 0


def cmd_agents(args):
    """List all sub-agents."""
    agents_list = [
        ("TradingAgent", "trading", "OANDA monitoring, Render health, Phase 1 logs"),
        ("JobSearchAgent", "job_search", "Multi-platform scraping, scoring, resume tailoring"),
        ("KnowledgeAgent", "knowledge", "Obsidian updates, MEMORY.md persistence, git commits"),
        ("ProjectMonitorAgent", "project_monitor", "Monitor all deployed services on Render"),
        ("ResearchAgent", "research", "Evaluate new projects for feasibility"),
    ]

    print("\n" + "="*70)
    print("Emy Sub-Agents")
    print("="*70)

    for name, domain, desc in agents_list:
        print(f"\n{name}")
        print(f"  Domain: {domain}")
        print(f"  Role: {desc}")

    print("\n" + "="*70)
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Emy — AI Chief of Staff',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python emy.py run                    Start main loop
  python emy.py status                 Show dashboard
  python emy.py ask "run job search"   Execute query
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # run
    subparsers.add_parser('run', help='Start main loop')

    # ask
    ask_parser = subparsers.add_parser('ask', help='Execute single query')
    ask_parser.add_argument('prompt', help='Query text')

    # status
    subparsers.add_parser('status', help='Show dashboard')

    # skills
    subparsers.add_parser('skills', help='List skills')

    # agents
    subparsers.add_parser('agents', help='List agents')

    args = parser.parse_args()

    # Dispatch to command
    if args.command == 'run':
        return cmd_run(args)
    elif args.command == 'ask':
        return cmd_ask(args)
    elif args.command == 'status':
        return cmd_status(args)
    elif args.command == 'skills':
        return cmd_skills(args)
    elif args.command == 'agents':
        return cmd_agents(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
