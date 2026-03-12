# Emy Phase 1a — Complete Implementation

**Status**: ✅ Phase 1a Complete (March 12, 2026)

Emy is an autonomous AI Chief of Staff system for Ibe Nwandu that orchestrates multiple specialized agents (Trading, Job Search, Knowledge, Project Monitor) with persistent SQLite storage, FastAPI gateway, Click CLI, and Gradio UI.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [API Documentation](#api-documentation)
4. [CLI Usage](#cli-usage)
5. [Development Setup](#development-setup)
6. [Docker Deployment](#docker-deployment)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Option A: Docker Compose (Recommended)

**Prerequisites**: Docker & Docker Compose installed

```bash
# Navigate to emy directory
cd emy/

# Start Emy API + SQLite Web Inspector
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f emy-api
```

**Access**:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **DB Inspector**: http://localhost:8081
- **Health Check**: `curl http://localhost:8000/health`

**Stop**:
```bash
docker-compose down
```

### Option B: Manual Installation

**Prerequisites**: Python 3.11+, pip, git

```bash
# Clone/navigate to project
cd emy/

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from emy.core.database import EMyDatabase; db = EMyDatabase(); db.initialize_schema()"

# Start API server
python -m uvicorn emy.gateway.api:app --host 0.0.0.0 --port 8000

# In another terminal, use CLI
python emy.py ask "What is the status?"
```

---

## Architecture

### System Overview

```
User/UI Layer
    ↓
┌───────────────────────────────┐
│  Gradio UI / Click CLI        │  ← User-facing interfaces
└──────────────┬────────────────┘
               ↓
┌───────────────────────────────┐
│  FastAPI Gateway              │  ← REST API layer (6 endpoints)
│  (gateway/api.py)             │
└──────────────┬────────────────┘
               ↓
┌───────────────────────────────┐
│  Agent Orchestration          │  ← Task routing, delegation
│  (core/task_router.py)        │
│  (core/delegation_engine.py)  │
└──────────────┬────────────────┘
               ↓
┌───────────────────────────────┐
│  Agents Layer                 │  ← Specialized sub-agents
│  • TradingAgent               │
│  • KnowledgeAgent             │
│  • ResearchAgent              │
│  • ProjectMonitorAgent        │
└──────────────┬────────────────┘
               ↓
┌───────────────────────────────┐
│  Persistence Layer            │
│  SQLite Database              │  ← Task history, agent runs,
│  (core/database.py)           │     skill outcomes, approvals
└───────────────────────────────┘
```

### Phase 1a Components

| Component | Purpose | Status |
|-----------|---------|--------|
| **Storage** | SQLite database with task/agent/skill tables | ✅ Complete |
| **Gateway** | FastAPI REST API (6 endpoints) | ✅ Complete |
| **CLI** | Click command-line interface | ✅ Complete |
| **UI** | Gradio web interface | ✅ Complete |
| **Integration Tests** | End-to-end test suite (8+ tests) | ✅ Complete |
| **Docker** | Containerized deployment | ✅ Complete |

### Directory Structure

```
emy/
├── agents/                    # Sub-agent implementations
│   ├── base_agent.py
│   ├── trading_agent.py
│   ├── knowledge_agent.py
│   ├── research_agent.py
│   └── project_monitor_agent.py
├── core/                      # Orchestration & persistence
│   ├── database.py           # SQLite schema & queries
│   ├── task_router.py        # Task routing logic
│   ├── delegation_engine.py  # Agent delegation
│   ├── approval_gate.py      # Approval workflows
│   └── skill_improver.py     # Skill self-improvement
├── gateway/                   # REST API Layer
│   ├── api.py                # FastAPI endpoints
│   └── __init__.py
├── cli/                       # Command-line interface
│   ├── main.py               # Click CLI implementation
│   └── __init__.py
├── ui/                        # Gradio Web Interface
│   ├── gradio_app.py
│   └── __init__.py
├── skills/                    # Skill definitions
├── tools/                     # Tool implementations
├── data/                      # SQLite database (created at runtime)
├── tests/                     # Test suite
│   ├── test_integration.py   # Integration tests (Phase 1a)
│   ├── test_cli.py
│   └── ...
├── Dockerfile                # Container image (Phase 1a)
├── docker-compose.yml        # Multi-container setup (Phase 1a)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .emy_disabled             # Kill-switch for emergency shutdown
└── README.md                 # This file
```

---

## API Documentation

### Base URL
- **Local**: `http://localhost:8000`
- **Production**: Set via `EMY_API_URL` env var

### Endpoints (6 total)

#### 1. Health Check
```
GET /health
```
**Response** (200):
```json
{
  "status": "ok",
  "timestamp": "2026-03-12T10:15:00"
}
```

#### 2. Execute Workflow
```
POST /workflows/execute
```
**Request**:
```json
{
  "workflow_type": "analysis",
  "agents": ["KnowledgeAgent", "TradingAgent"],
  "input": {
    "query": "What is the trading health?",
    "context": "full"
  }
}
```
**Response** (200):
```json
{
  "workflow_id": "wf_a1b2c3d4",
  "type": "analysis",
  "status": "pending",
  "created_at": "2026-03-12T10:15:00",
  "input": "{\"query\": \"...\"}"
}
```

#### 3. Get Workflow Status
```
GET /workflows/{workflow_id}
```
**Response** (200):
```json
{
  "workflow_id": "wf_a1b2c3d4",
  "type": "analysis",
  "status": "completed",
  "created_at": "2026-03-12T10:15:00",
  "updated_at": "2026-03-12T10:16:30",
  "output": "{\"result\": \"...\"}"
}
```
**Response** (404): Workflow not found

#### 4. List Workflows
```
GET /workflows?limit=10&offset=0
```
**Query Parameters**:
- `limit` (1-100, default: 10)
- `offset` (≥0, default: 0)

**Response** (200):
```json
{
  "workflows": [
    {
      "workflow_id": "wf_a1b2c3d4",
      "type": "analysis",
      "status": "completed",
      "created_at": "2026-03-12T10:15:00"
    }
  ],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

#### 5. Get Agent Status
```
GET /agents/status
```
**Response** (200):
```json
{
  "agents": [
    {
      "agent_name": "TradingAgent",
      "status": "healthy",
      "tasks_completed": 15,
      "tasks_failed": 0,
      "last_activity": "2026-03-12T10:16:00"
    },
    {
      "agent_name": "KnowledgeAgent",
      "status": "healthy",
      "tasks_completed": 8,
      "tasks_failed": 0,
      "last_activity": "2026-03-12T10:15:00"
    }
  ]
}
```

---

## CLI Usage

### Setup
```bash
# Verify Emy API is running (http://localhost:8000)
curl http://localhost:8000/health

# Set custom API URL (optional)
export EMY_API_URL=http://myserver:8000

# Or use individual commands with --api-url flag (if implemented)
```

### Commands

#### Execute Workflow
```bash
python emy.py execute <workflow_type> <agent1> [agent2] [--input='{"key": "value"}']
```
**Example**:
```bash
python emy.py execute analysis KnowledgeAgent
python emy.py execute trading_check TradingAgent --input='{"check_type": "health"}'
```

#### Check Workflow Status
```bash
python emy.py status <workflow_id>
```
**Example**:
```bash
python emy.py status wf_a1b2c3d4
```

#### List Workflows
```bash
python emy.py list [--limit=20] [--offset=0]
```
**Example**:
```bash
python emy.py list --limit=10
```

#### View Agent Status
```bash
python emy.py agents
```

#### Health Check
```bash
python emy.py health
```

### Example Workflow
```bash
# 1. Execute a workflow
$ python emy.py execute analysis KnowledgeAgent
Workflow created: wf_a1b2c3d4
Status: pending

# 2. Check status
$ python emy.py status wf_a1b2c3d4
ID:     wf_a1b2c3d4
Type:   analysis
Status: completed
Result: {"insight": "..."}

# 3. List all workflows
$ python emy.py list
Total: 42 workflows
[Showing 10 most recent...]
```

---

## Development Setup

### Prerequisites
- Python 3.11+ (`python --version`)
- pip / poetry
- Git
- (Optional) Docker & Docker Compose

### Installation

1. **Clone/navigate to project**:
```bash
cd emy/
```

2. **Create virtual environment** (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Initialize database**:
```bash
python -c "from emy.core.database import EMyDatabase; db = EMyDatabase(); db.initialize_schema()"
```

5. **Create .env file** (optional):
```bash
cp .env.example .env
# Edit .env with your settings
```

### Running Tests

```bash
# Run all tests (unit + integration)
pytest tests/ -v

# Run only integration tests
pytest tests/test_integration.py -v

# Run specific test class
pytest tests/test_integration.py::TestFullWorkflowExecution -v

# Run with coverage
pytest tests/ --cov=emy --cov-report=html
```

### Running Services

**Start API Gateway**:
```bash
python -m uvicorn emy.gateway.api:app --host 0.0.0.0 --port 8000 --reload
```

**Start Gradio UI** (in separate terminal):
```bash
python emy/ui/gradio_app.py
```

**Use CLI** (in separate terminal):
```bash
python emy.py ask "What is the trading status?"
python emy.py execute analysis KnowledgeAgent
```

---

## Docker Deployment

### Building Image

```bash
# Build from Dockerfile
docker build -t emy:latest .

# Run API server
docker run -p 8000:8000 emy:latest

# Run CLI command
docker run emy:latest python emy.py ask "What is the status?"

# Run with persistent database
docker run -v emy-data:/app/emy/data -p 8000:8000 emy:latest
```

### Using Docker Compose

```bash
# Start full stack (API + SQLite Web Inspector)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f emy-api

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Configuration

**Environment Variables** (in `docker-compose.yml`):
```yaml
environment:
  - EMY_API_URL=http://emy-api:8000
  - EMY_LOG_LEVEL=INFO
  - PYTHONUNBUFFERED=1
```

**Volumes**:
- `emy-data:/app/emy/data` — SQLite database persistence

**Ports**:
- `8000` — Emy API Gateway
- `8081` — SQLite Web Inspector (optional)

### Deployment Best Practices

1. **Never run as root**: Dockerfile uses `emy` user (UID 1000)
2. **Health checks**: Built-in healthcheck on /health endpoint
3. **Log aggregation**: Set `EMY_LOG_LEVEL=INFO` or `DEBUG`
4. **Database backups**: Mount `emy-data` volume from host or backup service
5. **Security**: Use reverse proxy (nginx) for TLS, authentication

---

## Testing

### Test Coverage

| Test Category | Tests | Status |
|---------------|-------|--------|
| **Integration** | 35+ tests in `test_integration.py` | ✅ |
| **CLI** | 16+ tests in `test_cli.py` | ✅ |
| **Knowledge Agent** | 8+ tests | ✅ |
| **Database** | 8+ tests in `test_database_crud.py` | ✅ |
| **Trading Agent** | 5+ tests | ✅ |
| **TOTAL** | **80+ tests** | ✅ |

### Running Tests

```bash
# All tests
pytest tests/ -v

# Integration only
pytest tests/test_integration.py -v

# With coverage
pytest tests/ --cov=emy --cov-report=term-missing

# Specific test class
pytest tests/test_integration.py::TestAPIGatewayHealth -v

# Specific test
pytest tests/test_integration.py::TestAPIGatewayHealth::test_health_check_endpoint -v
```

### Test Categories

**Integration Tests** (`test_integration.py`):
- ✅ Full workflow execution (CLI → API → Storage)
- ✅ Multi-agent workflows
- ✅ Data persistence across restarts
- ✅ API gateway health (6 endpoints)
- ✅ CLI-to-API communication
- ✅ UI-to-API communication
- ✅ Error handling
- ✅ Concurrent workflows

**CLI Tests** (`test_cli.py`):
- Execute command with various inputs
- Status command retrieval
- List command with pagination
- Agent status display
- Error handling

**Database Tests** (`test_database_crud.py`):
- CRUD operations on tasks, agent runs, skills
- Schema validation
- Transaction handling

---

## Troubleshooting

### API Server Won't Start

**Error**: `Address already in use`
```bash
# Find process using port 8000
lsof -i :8000

# Kill process (replace PID)
kill -9 <PID>

# Or use different port
python -m uvicorn emy.gateway.api:app --port 8001
```

**Error**: `ModuleNotFoundError: No module named 'emy'`
```bash
# Install package in development mode
pip install -e .

# Or run from project root
cd /path/to/emy
python -m uvicorn emy.gateway.api:app
```

### CLI Can't Connect to API

**Error**: `Error: Server unavailable`
```bash
# Verify API is running
curl http://localhost:8000/health

# Check EMY_API_URL
echo $EMY_API_URL

# Set correct URL
export EMY_API_URL=http://localhost:8000

# Or in docker-compose
docker-compose logs emy-api
```

### Database Issues

**Error**: `database is locked`
```bash
# Restart API server (will close existing connections)
docker-compose restart emy-api

# Or manually remove lock file
rm -f emy/data/emy.db-journal
```

**Error**: `No such table: emy_tasks`
```bash
# Initialize schema
python -c "from emy.core.database import EMyDatabase; db = EMyDatabase(); db.initialize_schema()"
```

### Docker Issues

**Error**: `Docker daemon not running`
```bash
# Start Docker (macOS)
open /Applications/Docker.app

# Start Docker (Linux)
sudo systemctl start docker

# Start Docker (Windows)
# Open Docker Desktop application
```

**Error**: `Cannot connect to Docker daemon`
```bash
# Check Docker status
docker ps

# Or use with sudo (if needed)
sudo docker-compose up
```

**Port conflicts**:
```bash
# Change port in docker-compose.yml
ports:
  - "9000:8000"  # Use 9000 instead of 8000

# Or kill existing container
docker stop emy-api
docker rm emy-api
```

### Test Failures

**Error**: `Connection refused during tests`
```bash
# Start API server first
python -m uvicorn emy.gateway.api:app --port 8000 &

# Then run tests
pytest tests/test_integration.py -v
```

**Error**: `Database locked during tests`
```bash
# Use temporary database for tests
pytest tests/test_integration.py --db-path=/tmp/test.db -v

# Or run sequentially instead of parallel
pytest tests/ -v -n 0
```

---

## Next Steps (Phase 1b & Beyond)

### Phase 1b: Async + Redis (Coming Soon)
- Replace in-memory workflow storage with Redis
- Implement async task queue for long-running workflows
- Add WebSocket support for real-time status updates
- Performance testing and optimization

### Phase 2: Multi-Agent Collaboration
- Agent-to-agent communication
- Shared context and memory
- Approval workflow implementation
- Skill self-improvement engine

### Phase 3: Extended Domains
- Job search integration (Indeed, LinkedIn)
- Trading domain expansion (OANDA real-time data)
- Knowledge management (Obsidian vault integration)
- Project monitoring and alerts

---

## Contributing

### Code Style
- Black for formatting: `black emy/ tests/`
- Flake8 for linting: `flake8 emy/ tests/`
- Type hints on all functions

### Adding Tests
1. Add test to appropriate file in `tests/`
2. Run: `pytest tests/<file> -v`
3. Commit with test coverage

### Deployment
1. Update code on main branch
2. Docker image automatically built from latest commit
3. Deploy to Render or other hosting platform

---

## License

Internal project for Ibe Nwandu. All rights reserved.

---

## Support

**Issues**: Create GitHub issue in personal portfolio repo
**Questions**: Refer to CLAUDE.md for project guidelines
**API Docs**: Visit http://localhost:8000/docs (Swagger UI)

---

**Last Updated**: March 12, 2026
**Phase 1a Status**: ✅ COMPLETE
**Ready for Phase 1b**: ✅ YES
