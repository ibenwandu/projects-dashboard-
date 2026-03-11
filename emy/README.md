# Emy — AI Chief of Staff

Persistent, autonomous AI agent managing Ibe's personal affairs, professional career, and technical projects.

## Architecture

```
emy/
├── core/                  # Orchestration (agent loop, task router, delegation engine)
├── memory/                # Persistence (SQLite + Markdown coordinator)
├── agents/                # Sub-agent implementations (trading, job search, knowledge, etc.)
├── skills/                # Skill definitions + outcome tracking
├── scheduler/             # Tick-based scheduling (no external cron required)
├── tools/                 # Tool implementations (file ops, API clients, browser, etc.)
├── shared/                # Copied modules from Trade-Alerts (database, audit_logger, etc.)
├── data/                  # SQLite database + .gitignore
└── README.md              # This file
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start Emy main loop
python emy.py run

# Run single query
python emy.py ask "check trading health"

# Check status
python emy.py status

# List skills
python emy.py skills
```

## Development Phases

- **Phase 0**: Foundation (directory structure, DB, scheduler, CLI) ← YOU ARE HERE
- **Phase 1**: Trading domain (log monitoring, Render health, OANDA queries)
- **Phase 2**: Job search domain (daily pipeline, resume tailoring)
- **Phase 3**: Knowledge management (Obsidian, session logs, MEMORY.md)
- **Phase 4**: Approval gates + skill self-improvement
- **Phase 5**: CLI polish + Anthropic tool-use integration

## Safety Mechanisms

- Budget tracking via `EMY_DAILY_BUDGET_USD` env var
- `.emy_disabled` kill-switch for emergency shutdown
- Approval gate for destructive actions (24h timeout)
- Skill versioning + auto-rollback if new version fails
