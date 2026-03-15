# Emy Dashboard UI Design

**Date**: March 15, 2026
**Status**: ✅ Approved
**Priority**: Week 1 of Production Roadmap
**Reference Design**: mission_control_interactive.html

---

## Vision

Replace JSON API outputs with an interactive real-time dashboard for monitoring Emy's autonomous operation. Enable users to see agent health, workflow execution, budget usage, and system metrics at a glance.

---

## Architecture Overview

```
Browser (dashboard.html)
    ↓
    ├─ WebSocket → /ws/metrics (real-time updates)
    │   └─ Receives: agent status, workflow updates, budget changes
    │
    └─ HTTP Polling (fallback) → /api/metrics (every 3s if no WebSocket)
        └─ GET /api/metrics → returns current system state

Brain Service (provides data)
    ├─ Agent status (healthy/executing/error)
    ├─ Workflow executions (live count, recent list)
    ├─ Budget usage tracking
    └─ System metrics (latency, disk, rate limits)
```

**Key Decision**: Standalone HTML file served from `GET /dashboard` endpoint. No Gradio integration initially (can add later if needed).

**Real-time Strategy**: Hybrid WebSocket + polling fallback
- WebSocket for responsiveness (~100ms updates)
- HTTP polling fallback (~3s updates) if WebSocket unavailable
- Ensures dashboard works even if WebSocket connection drops

---

## Frontend Structure

### File Organization
```
emy/
├── templates/
│   └── dashboard.html              (main dashboard)
├── static/
│   ├── dashboard.css               (styling)
│   ├── dashboard.js                (interactions)
│   └── theme.css                   (CSS variables)
└── gateway/
    └── api.py                      (updated: /dashboard route)
```

### Dashboard Layout

**Header Section** (20px padding)
- Pulsing green indicator + "All agents active — autonomous mode"
- Title: "Emy Dashboard"
- Live clock (updates every second, HH:MM:SS format)
- Last update badge (timestamp + latest event description)

**Metrics Row** (4 cards, equal width, CSS grid)
1. **Real-time Activity** (Green accent)
   - Number: Count of active workflows + agent executions
   - Label: "Active Operations"
   - Detail: "X workflows running, X agent executions today"
   - Data source: `/api/metrics.workflows.running + agent activity`

2. **Workflow Tracking** (Blue accent)
   - Number: Total workflows completed today
   - Label: "Workflow Status"
   - Detail: "Completed: X | Failed: X | Running: X"
   - Data source: `/api/metrics.workflows.{total_today,completed,failed}`

3. **Budget & Cost** (Amber accent)
   - Number: Dollar amount spent ($X.XX of $10.00)
   - Label: "Daily Budget"
   - Detail: "X% consumed | $Y remaining"
   - Data source: `/api/metrics.budget.{spent,percentage_used,remaining}`

4. **System Health** (Red/status accent)
   - Number: Response time in milliseconds (XXms)
   - Label: "System Health"
   - Detail: "DB: X.XGB | Rate limits: X hits | Status: OK"
   - Data source: `/api/metrics.system.{response_time_ms,db_disk_usage_gb,rate_limit_hits_today}`

**Main Content Grid** (2-column layout: 1fr 320px)

**Left Column: Agent Status**
- Section label: "Active Agents (3)"
- 3 agent status cards (TradingAgent, ResearchAgent, KnowledgeAgent)
- Each card shows:
  - Status indicator: ● (green=healthy, amber=executing, red=error, gray=disabled)
  - Agent name (bold)
  - Last execution: "2m ago" or "executing now"
  - Execution count today: "Executions: 24"
  - Last operation: "Market analysis" or "Evaluating project"
- Hover effect: Subtle border highlight + slight translate

**Right Column: System Metrics Panel**
- Section label: "System Status"
- **Budget Gauge**: Visual progress bar
  - Width: percentage of daily budget used
  - Color: green if <50%, amber if 50-80%, red if >80%
  - Label: "Budget: $X.XX / $10.00"

- **Response Metrics**:
  - "Response Time: XXms" (with up/down indicator if trending)
  - "Database: X.X / 2.0 GB" (with bar chart)
  - "Rate Limits: X hits today"

- **Overall Status**: Big text "✓ OK" or "⚠ WARNING" or "✗ ERROR"

**Recent Workflows Section**
- Section label: "Recent Executions (Last 10)"
- Table structure:
  - Columns: Time | Workflow Type | Agent | Status | Duration
  - Rows: Each workflow execution
  - Status color-coded: green (✓), amber (running), red (✗)
  - Clickable rows: Expand to show full workflow output JSON
  - Sort: Most recent first

**Activity Log** (bottom, full width)
- Section label: "Live Activity"
- Scrollable container (max 10 entries visible)
- Each entry:
  - Format: `[HH:MM:SS] Agent: Event message`
  - Example: `[18:30:45] TradingAgent: Market analysis complete (8.2s)`
  - Color-coded: green (✓ success), blue (→ running), amber (⚠ warning), red (✗ error)
- Auto-scroll to latest entry when new events arrive

---

## Styling & Theme

**CSS Variables** (match mission_control_interactive.html):
```css
:root {
  --bg: #09090f;              /* Main background */
  --surface: #111118;         /* Card/panel background */
  --surface2: #18181f;        /* Hover background */
  --border: rgba(255,255,255,0.07);
  --border-bright: rgba(255,255,255,0.18);

  --green: #00ff88;           /* Success, healthy */
  --green-dim: rgba(0,255,136,0.1);
  --blue: #4488ff;            /* Info, running */
  --blue-dim: rgba(68,136,255,0.1);
  --amber: #ffb340;           /* Warning, budget warning */
  --amber-dim: rgba(255,179,64,0.1);
  --red: #ff4466;             /* Error, system down */
  --red-dim: rgba(255,68,102,0.1);

  --text: #e8e8f0;            /* Primary text */
  --muted: #5a5a70;           /* Secondary text */

  --mono: 'Space Mono', monospace;
  --sans: 'Syne', sans-serif;
}
```

**Key Animations**:
- Pulsing indicator: 2s ease-in-out loop (green pulse on active status)
- Metric card hover: Subtle translateY(-2px) + border-color change
- Progress bar: Smooth fill animation (0.8s ease)
- Scan line: Continuous top-to-bottom sweep (8s linear)

**Responsiveness**:
- Desktop (≥1200px): 2-column main grid as described
- Tablet (768-1199px): 1 column, panels stack vertically
- Mobile (<768px): Single column, metric cards 2x2 grid

---

## Backend Implementation

### Endpoint 1: GET `/dashboard`
- **Purpose**: Serve the dashboard HTML
- **Response**: `text/html` with dashboard.html content
- **No parameters**
- **Status**: 200 OK
- **Implementation**:
  ```python
  from pathlib import Path

  @app.get("/dashboard")
  async def dashboard():
      dashboard_path = Path(__file__).parent.parent / "templates" / "dashboard.html"
      return FileResponse(dashboard_path, media_type="text/html")
  ```

### Endpoint 2: GET `/api/metrics`
- **Purpose**: Return current system state (used by polling + initial load)
- **Response**: JSON object (see schema below)
- **Status**: 200 OK
- **Latency**: <500ms target
- **Parameters**: None

**Response Schema**:
```json
{
  "timestamp": "2026-03-15T18:30:45.123Z",

  "agents": [
    {
      "name": "TradingAgent",
      "status": "healthy|executing|error|disabled",
      "last_execution": "2026-03-15T18:25:30Z",
      "execution_count_today": 5,
      "last_result_summary": "Market analysis complete"
    },
    {
      "name": "ResearchAgent",
      "status": "healthy",
      "last_execution": "2026-03-15T18:20:15Z",
      "execution_count_today": 2,
      "last_result_summary": "Feasibility evaluation"
    },
    {
      "name": "KnowledgeAgent",
      "status": "executing",
      "last_execution": "2026-03-15T18:30:40Z",
      "execution_count_today": 8,
      "last_result_summary": "Querying knowledge base..."
    }
  ],

  "workflows": {
    "total_today": 15,
    "running": 2,
    "completed": 12,
    "failed": 1,
    "recent": [
      {
        "workflow_id": "wf_20260315_183045_abc123",
        "type": "trading_health",
        "agent": "TradingAgent",
        "status": "completed|running|failed",
        "created_at": "2026-03-15T18:25:00Z",
        "completed_at": "2026-03-15T18:25:08.5Z",
        "duration_seconds": 8.5,
        "output_summary": "EUR/USD BUY signal, GBP/USD SELL...",
        "full_output": "{...complete JSON...}"
      }
    ]
  },

  "budget": {
    "daily_limit": 10.0,
    "spent_today": 3.45,
    "percentage_used": 34.5,
    "remaining": 6.55,
    "currency": "USD"
  },

  "system": {
    "response_time_ms": 145,
    "db_disk_usage_gb": 0.35,
    "db_disk_limit_gb": 2.0,
    "db_usage_percentage": 17.5,
    "rate_limit_hits_today": 2,
    "rate_limit_max": 6000,
    "uptime_seconds": 86400,
    "status": "ok|warning|error"
  }
}
```

**Status Logic**:
- `system.status = "ok"` if: response_time < 1000ms AND db_usage < 80% AND no errors
- `system.status = "warning"` if: response_time 1-2s OR db_usage 80-95%
- `system.status = "error"` if: response_time > 2s OR db_usage > 95% OR agent errors

### Endpoint 3: WebSocket `/ws/metrics`
- **Purpose**: Stream real-time updates to connected clients
- **Upgrade**: HTTP → WebSocket
- **Message Format**:
  ```json
  {
    "event": "agent_status_change|workflow_complete|budget_update|system_metrics",
    "timestamp": "2026-03-15T18:30:45.123Z",
    "data": {...}
  }
  ```

**Event Types**:

1. **agent_status_change**: When agent status changes
   ```json
   {
     "event": "agent_status_change",
     "data": {
       "agent_name": "TradingAgent",
       "status": "healthy|executing|error|disabled",
       "last_execution": "2026-03-15T18:25:30Z",
       "execution_count_today": 5
     }
   }
   ```

2. **workflow_complete**: When a workflow finishes
   ```json
   {
     "event": "workflow_complete",
     "data": {
       "workflow_id": "wf_20260315_183045_abc123",
       "agent": "TradingAgent",
       "status": "completed|failed",
       "duration_seconds": 8.5,
       "result_summary": "Market analysis complete"
     }
   }
   ```

3. **budget_update**: When budget usage changes significantly (>1% change)
   ```json
   {
     "event": "budget_update",
     "data": {
       "spent_today": 3.45,
       "percentage_used": 34.5,
       "remaining": 6.55
     }
   }
   ```

4. **system_metrics**: Every 30 seconds (push system metrics)
   ```json
   {
     "event": "system_metrics",
     "data": {
       "response_time_ms": 145,
       "db_usage_percentage": 17.5,
       "status": "ok|warning|error"
     }
   }
   ```

**Implementation Notes**:
- Use FastAPI WebSockets + asyncio for concurrent connections
- Keep track of connected clients (set of WebSocket connections)
- Broadcast updates to all connected clients when events occur
- Handle client disconnection gracefully (remove from set)
- Timeout: Close connection if no activity for 5 minutes

---

## Frontend JavaScript Implementation

### Core Functions

**1. WebSocket Connection & Fallback**
```javascript
let ws = null;
let isUsingPolling = false;
const POLLING_INTERVAL = 3000;

async function initDashboard() {
  // Fetch initial state
  await updateMetricsFromAPI();

  // Try WebSocket
  connectWebSocket();

  // Fallback to polling if WebSocket unavailable
  setTimeout(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      startPolling();
    }
  }, 2000);

  // Update clock every second
  setInterval(updateClock, 1000);
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${protocol}://${window.location.host}/ws/metrics`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('WebSocket connected');
    isUsingPolling = false;
    updateStatusBadge('● Connected via WebSocket');
  };

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    handleMetricUpdate(message.event, message.data);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket closed, falling back to polling');
    startPolling();
  };
}

function startPolling() {
  isUsingPolling = true;
  updateStatusBadge('● Polling (WebSocket unavailable)');

  setInterval(async () => {
    await updateMetricsFromAPI();
  }, POLLING_INTERVAL);
}
```

**2. Data Fetching & Updating**
```javascript
async function updateMetricsFromAPI() {
  try {
    const response = await fetch('/api/metrics');
    const data = await response.json();
    updateAllDashboard(data);
  } catch (error) {
    console.error('Failed to fetch metrics:', error);
    updateStatusBadge('✗ Connection error');
  }
}

function updateAllDashboard(data) {
  updateMetricCards(data);
  updateAgentCards(data.agents);
  updateSystemMetrics(data.system);
  updateWorkflowList(data.workflows.recent);
  updateLastUpdatedBadge(data.timestamp);
}
```

**3. Event Handlers for WebSocket**
```javascript
function handleMetricUpdate(event, data) {
  switch(event) {
    case 'agent_status_change':
      updateAgentCard(data.agent_name, data);
      addActivityLogEntry(`${data.agent_name}: Status changed to ${data.status}`);
      break;

    case 'workflow_complete':
      addActivityLogEntry(`${data.agent}: ${data.result_summary} (${data.duration_seconds}s)`);
      // Re-fetch workflows to get updated list
      updateMetricsFromAPI();
      break;

    case 'budget_update':
      updateBudgetCard(data);
      break;

    case 'system_metrics':
      updateSystemMetrics(data);
      break;
  }
}
```

**4. DOM Update Functions**
```javascript
function updateMetricCards(data) {
  // Card 1: Real-time Activity
  const activeOps = data.workflows.running + countExecuting(data.agents);
  document.getElementById('metric-1-num').textContent = activeOps;

  // Card 2: Workflow Tracking
  document.getElementById('metric-2-num').textContent = data.workflows.total_today;
  document.getElementById('metric-2-detail').innerHTML =
    `Completed: ${data.workflows.completed} | Failed: ${data.workflows.failed}`;

  // Card 3: Budget
  document.getElementById('metric-3-num').textContent = `$${data.budget.spent_today.toFixed(2)}`;
  document.getElementById('metric-3-pct').textContent = `${Math.round(data.budget.percentage_used)}%`;

  // Card 4: System Health
  document.getElementById('metric-4-num').textContent = `${data.system.response_time_ms}ms`;
}

function updateAgentCard(agentName, data) {
  const card = document.querySelector(`[data-agent="${agentName}"]`);
  if (!card) return;

  card.querySelector('.agent-status').className =
    `agent-status agent-${data.status}`;
  card.querySelector('.agent-last-exec').textContent =
    `Last: ${formatRelativeTime(data.last_execution)}`;
  card.querySelector('.agent-count').textContent =
    `Executions: ${data.execution_count_today}`;
}

function updateWorkflowList(workflows) {
  const tbody = document.getElementById('workflows-tbody');
  tbody.innerHTML = workflows.map(wf => `
    <tr onclick="toggleWorkflowDetail('${wf.workflow_id}')">
      <td>${formatTime(wf.created_at)}</td>
      <td>${wf.type}</td>
      <td>${wf.agent}</td>
      <td><span class="status-${wf.status}">${wf.status}</span></td>
      <td>${wf.duration_seconds.toFixed(1)}s</td>
    </tr>
  `).join('');
}

function addActivityLogEntry(message) {
  const timestamp = new Date().toLocaleTimeString();
  const entry = document.createElement('div');
  entry.className = 'activity-log-entry';
  entry.innerHTML = `<span class="log-time">[${timestamp}]</span> ${message}`;

  const log = document.getElementById('activity-log');
  log.insertBefore(entry, log.firstChild);

  // Keep only last 10 entries
  while (log.children.length > 10) {
    log.removeChild(log.lastChild);
  }
}

function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleTimeString('en-US', { hour12: false });
}
```

---

## Success Criteria

**Dashboard is complete when:**

### Frontend Display
- [ ] `/dashboard` serves HTML with dark theme (matches mission_control)
- [ ] All 4 metric cards display with correct values (real-time, workflows, budget, system)
- [ ] Agent status cards show 3 agents (TradingAgent, ResearchAgent, KnowledgeAgent)
- [ ] Agent status indicators (● green/amber/red/gray) update correctly
- [ ] System metrics panel shows budget gauge, response time, disk usage
- [ ] Recent workflows table shows last 10 executions (time, type, agent, status, duration)
- [ ] Clicking workflow row expands to show full JSON output
- [ ] Activity log shows real-time feed with timestamps
- [ ] Live clock updates every second (HH:MM:SS format)
- [ ] Last-updated badge shows current timestamp

### Real-time Updates
- [ ] WebSocket connects on page load (verified in browser DevTools)
- [ ] Agent status changes appear in real-time (<500ms from API change)
- [ ] Workflow completions update dashboard immediately
- [ ] Budget updates reflected within 1s of agent execution
- [ ] System metrics refresh every 30s
- [ ] Activity log entries appear as events occur

### Fallback & Reliability
- [ ] If WebSocket unavailable, dashboard falls back to polling
- [ ] Polling interval set to 3 seconds (metrics refresh)
- [ ] If polling also fails, dashboard shows "Connection error" with retry option
- [ ] WebSocket reconnection attempts every 5 seconds when disconnected
- [ ] No data loss on reconnection (re-fetches current state)

### Styling & Responsiveness
- [ ] Dark theme with CSS custom properties (--bg, --surface, --green, --blue, --amber, --red)
- [ ] Pulsing green indicator on active state (2s ease-in-out)
- [ ] Hover effects on cards (border-color change + subtle translate)
- [ ] Metric cards color-coded (green/blue/amber/red accents)
- [ ] Status pills color-coded (green=complete, blue=running, amber=pending, red=error)
- [ ] Responsive: Single column on mobile, 2-column on desktop
- [ ] Dashboard loads in <2 seconds (including initial API call)

### Testing
- [ ] `/api/metrics` endpoint tested (returns valid schema)
- [ ] `/ws/metrics` endpoint tested (sends messages correctly)
- [ ] Polling fallback tested (WebSocket disabled, verify polling works)
- [ ] Agent status change triggers dashboard update
- [ ] Workflow completion triggers dashboard update
- [ ] Budget update reflected within 1 second
- [ ] Error scenarios handled (API down, invalid response, etc.)

---

## Testing Strategy

### Unit Tests (`emy/tests/test_dashboard_metrics.py`)
- Test `/api/metrics` response schema validation
- Test metric calculations (percentages, sums, averages)
- Test agent status determination logic
- Test budget percentage calculation
- Test system status determination (ok/warning/error)

### Integration Tests (`emy/tests/test_dashboard_integration.py`)
- Test `/api/metrics` with real database
- Test WebSocket connection + message format
- Test polling fallback (verify data consistency)
- Test workflow execution → metrics update pipeline
- Test agent status change → WebSocket broadcast
- Test concurrent WebSocket clients (2+)

### E2E Tests (manual browser verification)
1. Open `/dashboard` in browser
2. Verify all metrics load correctly
3. Submit workflow via API: `POST /workflows/execute`
4. Verify workflow appears in "Recent Executions" within 5 seconds
5. Verify activity log shows workflow completion
6. Verify agent execution count increments
7. Disable WebSocket (DevTools), verify polling takes over
8. Reconnect WebSocket, verify metrics update
9. Test on mobile view (responsive layout)

---

## Implementation Order

1. **Phase 1**: Create HTML/CSS/JS structure (2h)
2. **Phase 2**: Implement `/api/metrics` endpoint (1h)
3. **Phase 3**: Implement `/ws/metrics` WebSocket (1.5h)
4. **Phase 4**: Wire frontend JavaScript to endpoints (1h)
5. **Phase 5**: Testing & refinement (1.5h)
6. **Phase 6**: Deployment verification (1h)

**Total Effort**: ~8 hours

---

## Files to Create/Modify

**Create**:
- `emy/templates/dashboard.html` (500-800 lines)
- `emy/static/dashboard.css` (400-500 lines)
- `emy/static/dashboard.js` (600-800 lines)
- `emy/tests/test_dashboard_metrics.py` (4-5 tests)
- `emy/tests/test_dashboard_integration.py` (6-8 tests)

**Modify**:
- `emy/gateway/api.py` (add 3 new routes: `/dashboard`, `/api/metrics`, `/ws/metrics`)
- `emy/core/database.py` (add metrics query methods if needed)

---

## Dependencies

**Frontend**:
- No external libraries (vanilla HTML/CSS/JS)
- Browser WebSocket API (built-in)

**Backend**:
- FastAPI (already in use)
- FastAPI WebSockets (already available)
- asyncio (already in use)

**No new package dependencies required**

---

## Deployment Notes

- Dashboard accessible at `https://emy-phase1a.onrender.com/dashboard` (production)
- Dashboard accessible at `http://localhost:8000/dashboard` (local development)
- `/api/metrics` endpoint monitored for performance (target <500ms)
- WebSocket `/ws/metrics` monitored for connection stability
- Activity log entries persisted in SQLite (audit trail)

---

**Approved**: March 15, 2026
**Next Step**: Create implementation plan via superpowers:writing-plans
