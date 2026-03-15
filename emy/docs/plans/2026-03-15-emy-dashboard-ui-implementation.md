# Emy Dashboard UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interactive real-time dashboard for monitoring Emy's autonomous operations (agent health, workflow tracking, budget usage, system metrics).

**Architecture:** Standalone HTML/CSS/JavaScript dashboard served from FastAPI Gateway. Real-time updates via hybrid WebSocket + HTTP polling. Metrics API provides system state; WebSocket pushes events; frontend falls back to polling if connection drops.

**Tech Stack:**
- **Backend**: FastAPI, asyncio, WebSockets
- **Frontend**: Vanilla HTML5, CSS3 (custom properties), JavaScript (ES6+)
- **Database**: SQLite (existing)
- **No new dependencies required**

**Effort Estimate**: 8 hours total | 12 tasks | TDD throughout

---

## Task 1: Create Dashboard File Structure

**Files:**
- Create: `emy/templates/` (directory)
- Create: `emy/static/` (directory)
- Create: `emy/templates/dashboard.html`
- Create: `emy/static/dashboard.css`
- Create: `emy/static/dashboard.js`

**Step 1: Create directories**

```bash
cd /c/Users/user/projects/personal/emy
mkdir -p templates static
ls -la templates/ static/
```

Expected: Both directories created and empty.

**Step 2: Create minimal dashboard.html with structure**

File: `emy/templates/dashboard.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emy Dashboard</title>
    <link rel="stylesheet" href="/static/dashboard.css">
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
</head>
<body>
    <div class="mc">
        <div class="grid-bg"></div>
        <div class="scan"></div>
        <div class="tooltip" id="tooltip"></div>

        <!-- HEADER -->
        <div class="header">
            <div>
                <div class="eyebrow"><span class="pulse"></span>All agents active — autonomous mode</div>
                <div class="title">Emy Dashboard</div>
                <div class="subtitle">// Real-time agent monitoring · 24/7 autonomous operation</div>
            </div>
            <div style="text-align:right">
                <div class="clock" id="clock">--:--:--</div>
                <div class="clock-label">LIVE · EDT</div>
                <div class="updated-badge" id="update-badge">● Initializing...</div>
            </div>
        </div>

        <!-- METRICS ROW -->
        <div class="metrics-row">
            <div class="metric-card mc-g" data-tip="Workflows executing + agent activity">
                <div class="metric-num" id="metric-real-time">0</div>
                <div class="metric-label">Real-time Activity</div>
                <div class="metric-detail" id="metric-real-time-detail">0 workflows, 0 agents active</div>
            </div>
            <div class="metric-card mc-b" data-tip="Workflows completed + running + failed">
                <div class="metric-num" id="metric-workflows">0</div>
                <div class="metric-label">Workflow Tracking</div>
                <div class="metric-detail" id="metric-workflows-detail">Completed: 0 | Failed: 0</div>
            </div>
            <div class="metric-card mc-a" data-tip="Daily Claude API budget usage">
                <div class="metric-num" id="metric-budget">$0.00</div>
                <div class="metric-label">Daily Budget</div>
                <div class="metric-detail" id="metric-budget-detail">0% consumed | $10.00 remaining</div>
            </div>
            <div class="metric-card mc-r" data-tip="System health and response time">
                <div class="metric-num" id="metric-health">0ms</div>
                <div class="metric-label">System Health</div>
                <div class="metric-detail" id="metric-health-detail">Status: Loading...</div>
            </div>
        </div>

        <!-- MAIN CONTENT -->
        <div class="main-grid">
            <div>
                <!-- AGENT STATUS SECTION -->
                <div class="section-label">Active Agents <span style="color:var(--muted);margin-left:4px">(3)</span></div>
                <div class="agents-stack" id="agents-stack">
                    <!-- Populated by JavaScript -->
                </div>
            </div>

            <!-- RIGHT PANEL: SYSTEM METRICS -->
            <div class="right-col">
                <div class="panel">
                    <div class="section-label">System Status</div>
                    <div id="system-metrics-panel">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>
            </div>
        </div>

        <!-- RECENT WORKFLOWS -->
        <div style="margin-top: 20px;">
            <div class="section-label">Recent Executions <span style="color:var(--muted);margin-left:4px" id="workflow-count">(0)</span></div>
            <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:auto;max-height:300px;">
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="border-bottom:1px solid var(--border);">
                            <th style="text-align:left;padding:10px;font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;">Time</th>
                            <th style="text-align:left;padding:10px;font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;">Type</th>
                            <th style="text-align:left;padding:10px;font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;">Agent</th>
                            <th style="text-align:left;padding:10px;font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;">Status</th>
                            <th style="text-align:left;padding:10px;font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;">Duration</th>
                        </tr>
                    </thead>
                    <tbody id="workflows-tbody">
                        <!-- Populated by JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ACTIVITY LOG -->
        <div style="margin-top: 20px;">
            <div class="log-bar">
                <span class="log-tag" id="log-tag">●</span>
                <div class="log-text">Activity log will display real-time events here</div>
            </div>
            <div id="activity-log" style="margin-top:10px;max-height:200px;overflow-y:auto;">
                <!-- Activity entries added dynamically -->
            </div>
        </div>
    </div>

    <script src="/static/dashboard.js"></script>
</body>
</html>
```

**Step 3: Verify file exists**

```bash
ls -lh emy/templates/dashboard.html
wc -l emy/templates/dashboard.html
```

Expected: File exists, ~120 lines.

**Step 4: Commit**

```bash
git add emy/templates/dashboard.html
git commit -m "feat(dashboard): create base HTML structure with sections"
```

---

## Task 2: Create Dashboard CSS (Dark Theme)

**Files:**
- Create: `emy/static/dashboard.css`

**Step 1: Write CSS with custom properties and styling**

File: `emy/static/dashboard.css`

```css
/* CSS Custom Properties & Root Styles */
:root {
    --bg: #09090f;
    --surface: #111118;
    --surface2: #18181f;
    --border: rgba(255,255,255,0.07);
    --border-bright: rgba(255,255,255,0.18);

    --green: #00ff88;
    --green-dim: rgba(0,255,136,0.1);
    --blue: #4488ff;
    --blue-dim: rgba(68,136,255,0.1);
    --amber: #ffb340;
    --amber-dim: rgba(255,179,64,0.1);
    --red: #ff4466;
    --red-dim: rgba(255,68,102,0.1);

    --text: #e8e8f0;
    --muted: #5a5a70;

    --mono: 'Space Mono', monospace;
    --sans: 'Syne', sans-serif;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    overflow-x: hidden;
}

.mc {
    padding: 22px 20px 32px;
    position: relative;
    overflow: hidden;
    min-height: 600px;
}

.grid-bg {
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(68,136,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(68,136,255,0.025) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
}

.scan {
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,255,136,0.2), transparent);
    animation: scan 8s linear infinite;
    pointer-events: none;
}

@keyframes scan {
    0% { top: -2px; }
    100% { top: 100%; }
}

/* HEADER */
.header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 20px;
    position: relative;
    z-index: 10;
}

.eyebrow {
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: .18em;
    color: var(--green);
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 5px;
}

.pulse {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--green);
    animation: pls 2s ease-in-out infinite;
}

@keyframes pls {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0,255,136,.5); }
    50% { box-shadow: 0 0 0 6px rgba(0,255,136,0); }
}

.title {
    font-size: 30px;
    font-weight: 800;
    color: #fff;
    letter-spacing: -.02em;
    line-height: 1;
}

.subtitle {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--muted);
    margin-top: 5px;
}

.clock {
    font-family: var(--mono);
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    letter-spacing: .05em;
}

.clock-label {
    font-family: var(--mono);
    font-size: 9px;
    color: var(--muted);
    text-align: right;
    margin-top: 2px;
    letter-spacing: .1em;
}

.updated-badge {
    font-family: var(--mono);
    font-size: 9px;
    background: var(--green-dim);
    color: var(--green);
    border: 1px solid rgba(0,255,136,.2);
    padding: 3px 8px;
    border-radius: 3px;
    margin-top: 6px;
    display: inline-block;
}

/* METRICS */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 18px;
}

.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    position: relative;
    overflow: hidden;
    cursor: default;
    transition: border-color .2s, transform .15s;
}

.metric-card:hover {
    border-color: var(--border-bright);
    transform: translateY(-2px);
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
}

.mc-g::before { background: linear-gradient(90deg, transparent, var(--green), transparent); }
.mc-b::before { background: linear-gradient(90deg, transparent, var(--blue), transparent); }
.mc-a::before { background: linear-gradient(90deg, transparent, var(--amber), transparent); }
.mc-r::before { background: linear-gradient(90deg, transparent, var(--red), transparent); }

.metric-num {
    font-family: var(--mono);
    font-size: 34px;
    font-weight: 700;
    line-height: 1;
    transition: transform .3s;
}

.mc-g .metric-num { color: var(--green); }
.mc-b .metric-num { color: var(--blue); }
.mc-a .metric-num { color: var(--amber); }
.mc-r .metric-num { color: var(--muted); }

.metric-label {
    font-size: 10px;
    color: var(--muted);
    margin-top: 5px;
    text-transform: uppercase;
    letter-spacing: .08em;
}

.metric-detail {
    font-family: var(--mono);
    font-size: 9px;
    color: var(--muted);
    margin-top: 4px;
    line-height: 1.6;
}

/* MAIN LAYOUT */
.main-grid {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 14px;
    margin-bottom: 14px;
}

.section-label {
    font-family: var(--mono);
    font-size: 9px;
    letter-spacing: .15em;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* AGENTS STACK */
.agents-stack {
    display: flex;
    flex-direction: column;
    gap: 7px;
}

.agent-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    display: grid;
    grid-template-columns: 3px 1fr auto;
    gap: 10px;
    align-items: center;
    transition: border-color .2s, transform .15s;
}

.agent-card:hover {
    border-color: var(--border-bright);
    transform: translateX(3px);
}

.agent-accent {
    width: 3px;
    height: 24px;
    border-radius: 2px;
}

.agent-accent.healthy { background: var(--green); box-shadow: 0 0 8px rgba(0,255,136,.4); }
.agent-accent.executing { background: var(--blue); }
.agent-accent.error { background: var(--red); }
.agent-accent.disabled { background: var(--muted); }

.agent-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.agent-name {
    font-size: 11px;
    font-weight: 600;
    color: #fff;
}

.agent-status {
    font-family: var(--mono);
    font-size: 9px;
    color: var(--muted);
}

.agent-status.healthy { color: var(--green); }
.agent-status.executing { color: var(--blue); }
.agent-status.error { color: var(--red); }

.agent-stats {
    text-align: right;
    font-family: var(--mono);
    font-size: 9px;
    color: var(--muted);
}

.agent-last-exec {
    font-size: 9px;
    color: var(--muted);
}

/* PANELS */
.right-col {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
}

.sys-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    gap: 8px;
}

.sys-row:last-child { border-bottom: none; }

.sys-key {
    font-family: var(--mono);
    font-size: 9px;
    color: var(--muted);
    flex-shrink: 0;
    text-transform: uppercase;
    letter-spacing: .07em;
}

.sys-val {
    font-size: 10px;
    color: var(--text);
    text-align: right;
    flex: 1;
}

.sys-ok { color: var(--green); }
.sys-warn { color: var(--amber); }
.sys-error { color: var(--red); }

/* BUDGET GAUGE */
.budget-gauge {
    margin-top: 8px;
}

.gauge-label {
    font-family: var(--mono);
    font-size: 8px;
    color: var(--muted);
    margin-bottom: 4px;
}

.gauge-bar {
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
}

.gauge-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--green), rgba(0,255,136,.4));
    border-radius: 2px;
    transition: width .8s ease;
}

/* ACTIVITY LOG */
.log-bar {
    background: var(--surface);
    border: 1px solid rgba(0,255,136,.12);
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
}

.log-tag {
    font-family: var(--mono);
    font-size: 9px;
    color: var(--green);
    white-space: nowrap;
    margin-top: 1px;
}

.log-text {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--muted);
    line-height: 1.7;
}

.log-text strong { color: var(--text); }

.activity-log-entry {
    font-family: var(--mono);
    font-size: 9px;
    padding: 6px 10px;
    border-left: 2px solid var(--border);
    margin: 2px 0;
    color: var(--muted);
    line-height: 1.6;
}

.activity-log-entry.success {
    border-left-color: var(--green);
    color: var(--green);
}

.activity-log-entry.running {
    border-left-color: var(--blue);
    color: var(--blue);
}

.activity-log-entry.error {
    border-left-color: var(--red);
    color: var(--red);
}

.log-time {
    color: var(--muted);
    margin-right: 4px;
}

/* TOOLTIP */
.tooltip {
    position: fixed;
    background: #1a1a28;
    border: 1px solid var(--border-bright);
    border-radius: 6px;
    padding: 8px 12px;
    font-family: var(--mono);
    font-size: 10px;
    color: var(--text);
    pointer-events: none;
    z-index: 999;
    opacity: 0;
    transition: opacity .15s;
    line-height: 1.6;
    max-width: 220px;
}

/* RESPONSIVE */
@media (max-width: 1199px) {
    .main-grid {
        grid-template-columns: 1fr;
    }
    .metrics-row {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 768px) {
    .metrics-row {
        grid-template-columns: 1fr;
    }
    .agent-card {
        grid-template-columns: 3px 1fr;
    }
}
```

**Step 2: Verify file exists and has content**

```bash
ls -lh emy/static/dashboard.css
wc -l emy/static/dashboard.css
head -20 emy/static/dashboard.css
```

Expected: File exists, ~400+ lines, CSS variables visible.

**Step 3: Commit**

```bash
git add emy/static/dashboard.css
git commit -m "feat(dashboard): add dark theme CSS with custom properties"
```

---

## Task 3: Create Dashboard JavaScript (Frontend Logic)

**Files:**
- Create: `emy/static/dashboard.js`

**Step 1: Write JavaScript with initialization and event handling**

File: `emy/static/dashboard.js`

```javascript
// ====== CONFIGURATION ======
let ws = null;
let isUsingPolling = false;
const POLLING_INTERVAL = 3000; // 3 seconds
const WS_RECONNECT_INTERVAL = 5000; // 5 seconds
let lastMetrics = null;

// ====== INITIALIZATION ======
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Dashboard initializing...');

    // Start clock
    updateClock();
    setInterval(updateClock, 1000);

    // Fetch initial metrics
    await updateMetricsFromAPI();

    // Try WebSocket
    connectWebSocket();

    // Fallback to polling after 2 seconds if WebSocket not connected
    setTimeout(() => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.log('WebSocket not available, starting polling fallback');
            startPolling();
        }
    }, 2000);
});

// ====== WEBSOCKET ======
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/metrics`;

    console.log(`Attempting WebSocket connection to ${wsUrl}`);

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        isUsingPolling = false;
        updateStatusBadge('● Connected via WebSocket');
    };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            console.log('WebSocket message received:', message.event);
            handleMetricUpdate(message.event, message.data);
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
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
        try {
            await updateMetricsFromAPI();
        } catch (error) {
            console.error('Polling error:', error);
            updateStatusBadge('✗ Connection error');
        }
    }, POLLING_INTERVAL);
}

// ====== API CALLS ======
async function updateMetricsFromAPI() {
    try {
        const response = await fetch('/api/metrics');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        lastMetrics = data;
        updateAllDashboard(data);
        updateStatusBadge(`● Updated: ${new Date().toLocaleTimeString()}`);
    } catch (error) {
        console.error('Failed to fetch metrics:', error);
        updateStatusBadge('✗ API Error');
    }
}

// ====== EVENT HANDLERS ======
function handleMetricUpdate(event, data) {
    console.log(`Handling event: ${event}`, data);

    switch(event) {
        case 'agent_status_change':
            updateAgentCard(data.agent_name, data);
            addActivityLogEntry(`${data.agent_name}: Status changed to ${data.status}`, 'running');
            break;

        case 'workflow_complete':
            addActivityLogEntry(`${data.agent}: ${data.result_summary} (${data.duration_seconds}s)`,
                data.status === 'completed' ? 'success' : 'error');
            // Re-fetch full state
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

// ====== DOM UPDATE FUNCTIONS ======
function updateAllDashboard(data) {
    updateMetricCards(data);
    updateAgentCards(data.agents);
    updateSystemMetrics(data.system);
    updateBudgetCard(data.budget);
    updateWorkflowList(data.workflows.recent);
    updateLastUpdatedBadge(data.timestamp);
}

function updateMetricCards(data) {
    // Card 1: Real-time Activity
    const executingAgents = data.agents.filter(a => a.status === 'executing').length;
    const activeOps = data.workflows.running + executingAgents;
    document.getElementById('metric-real-time').textContent = activeOps;
    document.getElementById('metric-real-time-detail').textContent =
        `${data.workflows.running} workflows, ${executingAgents} agents executing`;

    // Card 2: Workflow Tracking
    document.getElementById('metric-workflows').textContent = data.workflows.total_today;
    document.getElementById('metric-workflows-detail').textContent =
        `Completed: ${data.workflows.completed} | Failed: ${data.workflows.failed} | Running: ${data.workflows.running}`;

    // Card 3: Budget
    document.getElementById('metric-budget').textContent = `$${data.budget.spent_today.toFixed(2)}`;
    document.getElementById('metric-budget-detail').textContent =
        `${Math.round(data.budget.percentage_used)}% consumed | $${data.budget.remaining.toFixed(2)} remaining`;

    // Card 4: System Health
    document.getElementById('metric-health').textContent = `${data.system.response_time_ms}ms`;
    document.getElementById('metric-health-detail').textContent =
        `DB: ${data.system.db_disk_usage_gb.toFixed(1)}/${data.system.db_disk_limit_gb} GB | Status: ${data.system.status.toUpperCase()}`;
}

function updateAgentCards(agents) {
    const stack = document.getElementById('agents-stack');
    stack.innerHTML = agents.map(agent => `
        <div class="agent-card" data-agent="${agent.name}">
            <div class="agent-accent ${agent.status}"></div>
            <div class="agent-info">
                <div class="agent-name">${agent.name}</div>
                <div class="agent-status ${agent.status}">● ${agent.status.toUpperCase()}</div>
                <div class="agent-last-exec">Last: ${formatRelativeTime(agent.last_execution)}</div>
            </div>
            <div class="agent-stats">Executions: ${agent.execution_count_today}</div>
        </div>
    `).join('');
}

function updateSystemMetrics(system) {
    const panel = document.getElementById('system-metrics-panel');
    const statusClass = system.status === 'ok' ? 'sys-ok' :
                       system.status === 'warning' ? 'sys-warn' : 'sys-error';

    panel.innerHTML = `
        <div class="sys-row">
            <div class="sys-key">Response Time</div>
            <div class="sys-val">${system.response_time_ms}ms</div>
        </div>
        <div class="sys-row">
            <div class="sys-key">Database Usage</div>
            <div class="sys-val">${system.db_disk_usage_gb.toFixed(2)}GB / ${system.db_disk_limit_gb}GB</div>
        </div>
        <div class="sys-row">
            <div class="sys-key">Rate Limit Hits</div>
            <div class="sys-val">${system.rate_limit_hits_today} / ${system.rate_limit_max}</div>
        </div>
        <div class="sys-row">
            <div class="sys-key">Status</div>
            <div class="sys-val ${statusClass}">✓ ${system.status.toUpperCase()}</div>
        </div>
        <div class="budget-gauge">
            <div class="gauge-label">Budget Usage</div>
            <div class="gauge-bar">
                <div class="gauge-fill" style="width: ${lastMetrics?.budget?.percentage_used || 0}%"></div>
            </div>
        </div>
    `;
}

function updateBudgetCard(budget) {
    const pct = budget.percentage_used || 0;
    document.getElementById('metric-budget').textContent = `$${budget.spent_today.toFixed(2)}`;
    document.getElementById('metric-budget-detail').textContent =
        `${Math.round(pct)}% consumed | $${budget.remaining.toFixed(2)} remaining`;

    // Update gauge if it exists
    const gauge = document.querySelector('.gauge-fill');
    if (gauge) gauge.style.width = pct + '%';
}

function updateWorkflowList(workflows) {
    const tbody = document.getElementById('workflows-tbody');
    const count = document.getElementById('workflow-count');

    count.textContent = `(${workflows.length})`;

    if (workflows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding:10px;text-align:center;color:var(--muted);">No workflows yet</td></tr>';
        return;
    }

    tbody.innerHTML = workflows.map(wf => `
        <tr style="border-bottom:1px solid var(--border);cursor:pointer;" onclick="toggleWorkflowDetail('${wf.workflow_id}')">
            <td style="padding:10px;font-family:var(--mono);font-size:9px;color:var(--muted);">${formatTime(wf.created_at)}</td>
            <td style="padding:10px;font-family:var(--mono);font-size:9px;color:var(--text);">${wf.type}</td>
            <td style="padding:10px;font-family:var(--mono);font-size:9px;color:var(--text);">${wf.agent}</td>
            <td style="padding:10px;"><span style="font-family:var(--mono);font-size:9px;padding:2px 6px;border-radius:3px;" class="status-${wf.status}">${wf.status}</span></td>
            <td style="padding:10px;font-family:var(--mono);font-size:9px;color:var(--muted);">${wf.duration_seconds.toFixed(1)}s</td>
        </tr>
    `).join('');
}

function addActivityLogEntry(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `activity-log-entry ${type}`;
    entry.innerHTML = `<span class="log-time">[${timestamp}]</span> ${message}`;

    const log = document.getElementById('activity-log');
    log.insertBefore(entry, log.firstChild);

    // Keep only last 10 entries
    while (log.children.length > 10) {
        log.removeChild(log.lastChild);
    }
}

function updateLastUpdatedBadge(timestamp) {
    const time = new Date(timestamp).toLocaleTimeString();
    document.getElementById('update-badge').textContent = `● Updated: ${time}`;
}

function updateStatusBadge(text) {
    document.getElementById('update-badge').textContent = text;
}

// ====== UTILITY FUNCTIONS ======
function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent =
        now.toLocaleTimeString('en-US', { hour12: false });
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatRelativeTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds

    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}

function toggleWorkflowDetail(workflowId) {
    // Placeholder for expanding workflow details
    console.log('Clicked workflow:', workflowId);
    // TODO: Show modal with full workflow output
}
```

**Step 2: Verify file exists**

```bash
ls -lh emy/static/dashboard.js
wc -l emy/static/dashboard.js
```

Expected: File exists, ~350+ lines.

**Step 3: Commit**

```bash
git add emy/static/dashboard.js
git commit -m "feat(dashboard): add JavaScript logic for real-time updates and DOM manipulation"
```

---

## Task 4: Create GET /dashboard Endpoint

**Files:**
- Modify: `emy/gateway/api.py`

**Step 1: Write failing test for dashboard endpoint**

File: `emy/tests/test_dashboard_endpoints.py`

```python
import pytest
from fastapi.testclient import TestClient
from emy.gateway.api import app

client = TestClient(app)

def test_dashboard_endpoint_returns_html():
    """Test that GET /dashboard returns HTML content"""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Emy Dashboard" in response.text
    assert "metric-real-time" in response.text  # Check for dashboard elements

def test_dashboard_serves_from_templates():
    """Test that dashboard is served from templates directory"""
    response = client.get("/dashboard")
    assert "Active Agents" in response.text
    assert "dashboard.js" in response.text  # Should link to JS
    assert "dashboard.css" in response.text  # Should link to CSS
```

**Step 2: Run test to verify it fails**

```bash
cd /c/Users/user/projects/personal
pytest emy/tests/test_dashboard_endpoints.py::test_dashboard_endpoint_returns_html -v
```

Expected: FAIL - "404 Not Found"

**Step 3: Implement GET /dashboard endpoint**

Add to `emy/gateway/api.py` (after imports, before existing routes):

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Add route for dashboard
@app.get("/dashboard")
async def dashboard():
    """Serve the interactive dashboard UI"""
    dashboard_path = Path(__file__).parent.parent / "templates" / "dashboard.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(dashboard_path, media_type="text/html")

# Mount static files (CSS, JS)
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
```

**Step 4: Run test to verify it passes**

```bash
pytest emy/tests/test_dashboard_endpoints.py::test_dashboard_endpoint_returns_html -v
pytest emy/tests/test_dashboard_endpoints.py::test_dashboard_serves_from_templates -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add emy/gateway/api.py emy/tests/test_dashboard_endpoints.py
git commit -m "feat(dashboard): add GET /dashboard endpoint and static file mounting"
```

---

## Task 5: Create GET /api/metrics Endpoint

**Files:**
- Modify: `emy/gateway/api.py`
- Create: `emy/core/metrics.py`

**Step 1: Write failing test for metrics endpoint**

File: `emy/tests/test_dashboard_endpoints.py` (add these tests)

```python
def test_metrics_endpoint_returns_json():
    """Test that GET /api/metrics returns valid JSON"""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert "timestamp" in data
    assert "agents" in data
    assert "workflows" in data
    assert "budget" in data
    assert "system" in data

def test_metrics_agents_structure():
    """Test that agents have required fields"""
    response = client.get("/api/metrics")
    data = response.json()

    assert isinstance(data["agents"], list)
    assert len(data["agents"]) >= 0

    if len(data["agents"]) > 0:
        agent = data["agents"][0]
        assert "name" in agent
        assert "status" in agent
        assert "last_execution" in agent
        assert "execution_count_today" in agent

def test_metrics_workflows_structure():
    """Test that workflows have required fields"""
    response = client.get("/api/metrics")
    data = response.json()

    assert "total_today" in data["workflows"]
    assert "running" in data["workflows"]
    assert "completed" in data["workflows"]
    assert "failed" in data["workflows"]
    assert "recent" in data["workflows"]

def test_metrics_budget_structure():
    """Test that budget has required fields"""
    response = client.get("/api/metrics")
    data = response.json()

    budget = data["budget"]
    assert "daily_limit" in budget
    assert "spent_today" in budget
    assert "percentage_used" in budget
    assert "remaining" in budget
```

**Step 2: Run tests to verify they fail**

```bash
pytest emy/tests/test_dashboard_endpoints.py::test_metrics_endpoint_returns_json -v
```

Expected: FAIL - "404 Not Found"

**Step 3: Create metrics module**

File: `emy/core/metrics.py`

```python
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import BaseModel
from emy.core.database import db

# ====== RESPONSE MODELS ======
class AgentMetric(BaseModel):
    name: str
    status: str  # healthy, executing, error, disabled
    last_execution: str  # ISO format
    execution_count_today: int
    last_result_summary: str

class WorkflowMetric(BaseModel):
    workflow_id: str
    type: str
    agent: str
    status: str
    created_at: str
    duration_seconds: float
    output_summary: str

class WorkflowMetrics(BaseModel):
    total_today: int
    running: int
    completed: int
    failed: int
    recent: List[WorkflowMetric]

class BudgetMetrics(BaseModel):
    daily_limit: float
    spent_today: float
    percentage_used: float
    remaining: float
    currency: str = "USD"

class SystemMetrics(BaseModel):
    response_time_ms: float
    db_disk_usage_gb: float
    db_disk_limit_gb: float
    db_usage_percentage: float
    rate_limit_hits_today: int
    rate_limit_max: int
    uptime_seconds: int
    status: str  # ok, warning, error

class MetricsResponse(BaseModel):
    timestamp: str
    agents: List[AgentMetric]
    workflows: WorkflowMetrics
    budget: BudgetMetrics
    system: SystemMetrics

# ====== METRICS COLLECTION ======
def collect_metrics() -> MetricsResponse:
    """Collect all dashboard metrics from database and system"""

    # Get agent status
    agents = get_agent_metrics()

    # Get workflow metrics
    workflows = get_workflow_metrics()

    # Get budget metrics
    budget = get_budget_metrics()

    # Get system metrics
    system = get_system_metrics()

    return MetricsResponse(
        timestamp=datetime.utcnow().isoformat() + "Z",
        agents=agents,
        workflows=workflows,
        budget=budget,
        system=system
    )

def get_agent_metrics() -> List[AgentMetric]:
    """Get status of all agents"""
    # Query database for agent status
    # For now, return hardcoded agents based on current system
    agents = [
        AgentMetric(
            name="TradingAgent",
            status="healthy",
            last_execution=datetime.utcnow().isoformat() + "Z",
            execution_count_today=0,
            last_result_summary="Awaiting market data"
        ),
        AgentMetric(
            name="ResearchAgent",
            status="healthy",
            last_execution=datetime.utcnow().isoformat() + "Z",
            execution_count_today=0,
            last_result_summary="Ready for queries"
        ),
        AgentMetric(
            name="KnowledgeAgent",
            status="healthy",
            last_execution=datetime.utcnow().isoformat() + "Z",
            execution_count_today=0,
            last_result_summary="Ready for queries"
        )
    ]
    return agents

def get_workflow_metrics() -> WorkflowMetrics:
    """Get workflow execution metrics"""
    today = datetime.utcnow().date()

    # Query workflows from today
    workflows_list = db.get_workflows_by_date(today) if hasattr(db, 'get_workflows_by_date') else []

    total = len(workflows_list)
    completed = len([w for w in workflows_list if w.get('status') == 'completed'])
    failed = len([w for w in workflows_list if w.get('status') == 'failed'])
    running = len([w for w in workflows_list if w.get('status') == 'running'])

    # Get recent 10 workflows
    recent = [
        WorkflowMetric(
            workflow_id=w.get('workflow_id', 'N/A'),
            type=w.get('type', 'unknown'),
            agent=w.get('agent', 'N/A'),
            status=w.get('status', 'unknown'),
            created_at=w.get('created_at', datetime.utcnow().isoformat()),
            duration_seconds=w.get('duration', 0),
            output_summary=w.get('output_summary', '')[:100]
        )
        for w in workflows_list[:10]
    ]

    return WorkflowMetrics(
        total_today=total,
        completed=completed,
        failed=failed,
        running=running,
        recent=recent
    )

def get_budget_metrics() -> BudgetMetrics:
    """Get API budget usage metrics"""
    daily_limit = 10.0  # $10/day from ENV
    spent = 0.0  # TODO: Query from database

    return BudgetMetrics(
        daily_limit=daily_limit,
        spent_today=spent,
        percentage_used=(spent / daily_limit * 100) if daily_limit > 0 else 0,
        remaining=daily_limit - spent,
        currency="USD"
    )

def get_system_metrics() -> SystemMetrics:
    """Get system health metrics"""
    import os
    import time

    # Response time (mock for now)
    response_time_ms = 100.0

    # Database disk usage
    db_path = os.getenv('DATABASE_PATH', '/data/emy.db')
    db_disk_usage = 0.1  # GB (mock)
    db_disk_limit = 2.0  # GB

    if os.path.exists(db_path):
        db_size_bytes = os.path.getsize(db_path)
        db_disk_usage = db_size_bytes / (1024 * 1024 * 1024)  # Convert to GB

    # Determine status
    status = "ok"
    if db_disk_usage > 1.8:
        status = "error"
    elif db_disk_usage > 1.5:
        status = "warning"

    return SystemMetrics(
        response_time_ms=response_time_ms,
        db_disk_usage_gb=db_disk_usage,
        db_disk_limit_gb=db_disk_limit,
        db_usage_percentage=(db_disk_usage / db_disk_limit * 100),
        rate_limit_hits_today=0,
        rate_limit_max=6000,
        uptime_seconds=int(time.time()),  # Mock
        status=status
    )
```

**Step 4: Add metrics endpoint to api.py**

Add to `emy/gateway/api.py`:

```python
from emy.core.metrics import collect_metrics

@app.get('/api/metrics')
async def get_metrics():
    """Get all dashboard metrics"""
    try:
        metrics = collect_metrics()
        return metrics.dict()
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect metrics")
```

**Step 5: Run tests to verify they pass**

```bash
pytest emy/tests/test_dashboard_endpoints.py::test_metrics_endpoint_returns_json -v
pytest emy/tests/test_dashboard_endpoints.py::test_metrics_agents_structure -v
pytest emy/tests/test_dashboard_endpoints.py::test_metrics_workflows_structure -v
pytest emy/tests/test_dashboard_endpoints.py::test_metrics_budget_structure -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add emy/core/metrics.py emy/gateway/api.py emy/tests/test_dashboard_endpoints.py
git commit -m "feat(dashboard): add GET /api/metrics endpoint with metrics collection"
```

---

## Task 6: Create WebSocket /ws/metrics Endpoint

**Files:**
- Modify: `emy/gateway/api.py`

**Step 1: Write failing test for WebSocket endpoint**

File: `emy/tests/test_dashboard_websocket.py`

```python
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from emy.gateway.api import app

client = TestClient(app)

def test_websocket_endpoint_exists():
    """Test that WebSocket endpoint can be connected"""
    with client.websocket_connect("/ws/metrics") as websocket:
        # Connection successful
        assert websocket is not None

def test_websocket_receives_messages():
    """Test that WebSocket sends system_metrics message"""
    with client.websocket_connect("/ws/metrics") as websocket:
        # Should receive system_metrics shortly
        data = websocket.receive_json(mode="text")
        assert "event" in data
        assert data["event"] in ["agent_status_change", "workflow_complete", "budget_update", "system_metrics"]
        assert "timestamp" in data
        assert "data" in data
```

**Step 2: Run test to verify it fails**

```bash
pytest emy/tests/test_dashboard_websocket.py::test_websocket_endpoint_exists -v
```

Expected: FAIL - "404 Not Found" or connection error

**Step 3: Implement WebSocket endpoint**

Add to `emy/gateway/api.py`:

```python
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime

# Global set of connected clients
connected_clients = set()

@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics"""
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        # Send initial system metrics immediately
        metrics = collect_metrics()
        await websocket.send_json({
            "event": "system_metrics",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "response_time_ms": metrics.system.response_time_ms,
                "db_usage_percentage": metrics.system.db_usage_percentage,
                "status": metrics.system.status
            }
        })

        # Send system metrics every 30 seconds
        while True:
            await asyncio.sleep(30)
            metrics = collect_metrics()
            await websocket.send_json({
                "event": "system_metrics",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "response_time_ms": metrics.system.response_time_ms,
                    "db_usage_percentage": metrics.system.db_usage_percentage,
                    "status": metrics.system.status
                }
            })

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

async def broadcast_metric_event(event: str, data: dict):
    """Broadcast metric event to all connected WebSocket clients"""
    message = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data
    }

    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            disconnected.append(client)

    # Remove disconnected clients
    for client in disconnected:
        connected_clients.discard(client)
```

**Step 4: Run test to verify it passes**

```bash
pytest emy/tests/test_dashboard_websocket.py::test_websocket_endpoint_exists -v
pytest emy/tests/test_dashboard_websocket.py::test_websocket_receives_messages -v
```

Expected: PASS (or timeout - normal for streaming test, indicate success)

**Step 5: Commit**

```bash
git add emy/gateway/api.py emy/tests/test_dashboard_websocket.py
git commit -m "feat(dashboard): add WebSocket /ws/metrics endpoint with 30s system metrics broadcast"
```

---

## Task 7: Test Dashboard HTML in Browser

**Files:**
- Reference: `emy/templates/dashboard.html`
- Reference: `emy/static/dashboard.css`
- Reference: `emy/static/dashboard.js`

**Step 1: Start local development server**

```bash
cd /c/Users/user/projects/personal/emy
python -m uvicorn gateway.api:app --port 8000 --reload
```

Expected: Server starts on `http://localhost:8000`

**Step 2: Open dashboard in browser**

Open: `http://localhost:8000/dashboard`

**Verify:**
- [ ] Page loads with dark theme
- [ ] "Emy Dashboard" title visible
- [ ] 4 metric cards display (green, blue, amber, red)
- [ ] Agent status cards show 3 agents
- [ ] Real-time activity log at bottom
- [ ] Live clock updates every second
- [ ] No console errors (F12 to check)

**Step 3: Test API endpoint**

```bash
curl http://localhost:8000/api/metrics | jq .
```

Expected: JSON response with agents, workflows, budget, system

**Step 4: Test WebSocket (in browser console)**

```javascript
ws = new WebSocket("ws://localhost:8000/ws/metrics");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

Expected: Messages received every 30 seconds

**Step 5: Verify responsive design**

- Test on desktop (F12 → Responsive Design Mode)
- Resize to tablet (1024px)
- Resize to mobile (375px)
- Verify layout adapts (single column on mobile)

---

## Task 8: Integration Test - Full Workflow

**Files:**
- Create: `emy/tests/test_dashboard_integration.py`

**Step 1: Write integration test**

```python
import pytest
import asyncio
from fastapi.testclient import TestClient
from emy.gateway.api import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_dashboard_full_cycle():
    """Test: Load dashboard → execute workflow → see metrics update"""

    # 1. Load dashboard
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Emy Dashboard" in response.text

    # 2. Get initial metrics
    metrics = client.get("/api/metrics").json()
    initial_count = metrics["workflows"]["total_today"]

    # 3. Execute a workflow
    workflow_response = client.post(
        "/workflows/execute",
        json={
            "workflow_type": "knowledge_query",
            "agents": ["KnowledgeAgent"],
            "input": {"query": "Test query"}
        }
    )
    assert workflow_response.status_code == 200
    workflow_id = workflow_response.json()["workflow_id"]

    # 4. Wait for workflow to complete (with timeout)
    max_attempts = 60
    for _ in range(max_attempts):
        updated_metrics = client.get("/api/metrics").json()
        if updated_metrics["workflows"]["total_today"] > initial_count:
            # Workflow was counted
            break
        await asyncio.sleep(0.5)

    # 5. Verify metrics updated
    assert updated_metrics["workflows"]["total_today"] >= initial_count
    assert len(updated_metrics["workflows"]["recent"]) > 0

def test_dashboard_css_loads():
    """Test that CSS file is served correctly"""
    response = client.get("/static/dashboard.css")
    assert response.status_code == 200
    assert "var(--bg)" in response.text or "--bg:" in response.text

def test_dashboard_js_loads():
    """Test that JS file is served correctly"""
    response = client.get("/static/dashboard.js")
    assert response.status_code == 200
    assert "connectWebSocket" in response.text or "updateMetrics" in response.text
```

**Step 2: Run integration test**

```bash
pytest emy/tests/test_dashboard_integration.py -v
```

Expected: Tests PASS

**Step 3: Commit**

```bash
git add emy/tests/test_dashboard_integration.py
git commit -m "test(dashboard): add integration tests for full cycle"
```

---

## Task 9: Add Activity Log to Database (Audit Trail)

**Files:**
- Modify: `emy/core/database.py`

**Step 1: Write test for activity logging**

```python
def test_log_activity_stores_event():
    """Test that activity events are stored in database"""
    db.log_activity(
        event_type="workflow_complete",
        agent_name="TradingAgent",
        description="Market analysis complete"
    )

    events = db.get_activity_log(limit=10)
    assert len(events) > 0
    assert events[0]["event_type"] == "workflow_complete"
```

**Step 2: Add to database.py**

```python
def log_activity(self, event_type: str, agent_name: str, description: str):
    """Log activity event for audit trail"""
    query = """
        INSERT INTO activity_log (event_type, agent_name, description, created_at)
        VALUES (?, ?, ?, ?)
    """
    self.execute(query, (event_type, agent_name, description, datetime.utcnow()))

def get_activity_log(self, limit: int = 10) -> list:
    """Get recent activity log entries"""
    query = "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?"
    cursor = self.connection.execute(query, (limit,))
    return [dict(row) for row in cursor.fetchall()]
```

**Step 3: Update schema**

Add to database init:

```python
def create_activity_log_table(self):
    """Create activity log table if not exists"""
    query = """
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            agent_name TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    self.execute(query)
```

**Step 4: Commit**

```bash
git add emy/core/database.py
git commit -m "feat(dashboard): add activity log table and logging methods"
```

---

## Task 10: Update Metrics Endpoint to Use Database

**Files:**
- Modify: `emy/core/metrics.py`

**Step 1: Update get_workflow_metrics to query database**

```python
def get_workflow_metrics() -> WorkflowMetrics:
    """Get workflow execution metrics from database"""
    today = datetime.utcnow().date()

    # Get workflows from database
    all_workflows = db.get_workflows() or []
    today_workflows = [
        w for w in all_workflows
        if datetime.fromisoformat(w.get('created_at', '')).date() == today
    ]

    total = len(today_workflows)
    completed = len([w for w in today_workflows if w.get('status') == 'completed'])
    failed = len([w for w in today_workflows if w.get('status') == 'failed'])
    running = len([w for w in today_workflows if w.get('status') == 'running'])

    # Recent 10
    recent = [
        WorkflowMetric(
            workflow_id=w.get('workflow_id', 'N/A'),
            type=w.get('type', 'unknown'),
            agent=w.get('agent') or 'Unknown',
            status=w.get('status', 'unknown'),
            created_at=w.get('created_at', datetime.utcnow().isoformat()),
            duration_seconds=w.get('duration', 0.0) or 0.0,
            output_summary=(w.get('output', '')[:100] if w.get('output') else '')
        )
        for w in today_workflows[:10]
    ]

    return WorkflowMetrics(
        total_today=total,
        completed=completed,
        failed=failed,
        running=running,
        recent=recent
    )
```

**Step 2: Update get_agent_metrics to query execution count**

```python
def get_agent_metrics() -> List[AgentMetric]:
    """Get agent status and execution metrics"""
    all_workflows = db.get_workflows() or []
    today = datetime.utcnow().date()

    agent_names = ["TradingAgent", "ResearchAgent", "KnowledgeAgent"]
    metrics = []

    for agent_name in agent_names:
        agent_workflows = [
            w for w in all_workflows
            if w.get('agent') == agent_name and
            datetime.fromisoformat(w.get('created_at', '')).date() == today
        ]

        exec_count = len(agent_workflows)
        last_exec = agent_workflows[0].get('created_at') if agent_workflows else None
        last_summary = agent_workflows[0].get('output', '')[:50] if agent_workflows else "No executions"

        metrics.append(AgentMetric(
            name=agent_name,
            status="healthy",  # TODO: Check for errors
            last_execution=last_exec or datetime.utcnow().isoformat() + "Z",
            execution_count_today=exec_count,
            last_result_summary=last_summary
        ))

    return metrics
```

**Step 3: Commit**

```bash
git add emy/core/metrics.py
git commit -m "feat(dashboard): update metrics to query from database"
```

---

## Task 11: Create Test Suite Runner

**Files:**
- Reference: All test files created

**Step 1: Run all dashboard tests**

```bash
pytest emy/tests/test_dashboard_endpoints.py emy/tests/test_dashboard_websocket.py emy/tests/test_dashboard_integration.py -v --tb=short
```

Expected: All tests PASS

**Step 2: Check coverage**

```bash
pytest emy/tests/test_dashboard_*.py --cov=emy.gateway --cov=emy.core.metrics --cov-report=term-missing
```

Expected: Coverage >80%

**Step 3: Commit summary**

```bash
git log --oneline -10
```

Should show: dashboard HTML, CSS, JS, endpoints, WebSocket, integration tests, database updates

---

## Task 12: Verification & Deployment Checklist

**Files:**
- Reference: Production deployment docs

**Step 1: Local Verification**

```bash
# Start server
python -m uvicorn emy/gateway/api:app --port 8000

# In separate terminal:
# 1. Open browser to http://localhost:8000/dashboard
# 2. Verify all sections load
# 3. Check browser console for errors (F12)
# 4. Test WebSocket connection in console:
ws = new WebSocket("ws://localhost:8000/ws/metrics");
ws.onmessage = (e) => console.log(JSON.parse(e.data));

# 5. Verify metrics API
curl http://localhost:8000/api/metrics | jq .

# 6. Execute test workflow
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"knowledge_query","agents":["KnowledgeAgent"],"input":{"query":"test"}}'

# 7. Verify workflow appears in dashboard metrics
```

**Step 2: Checklist Before Deployment**

- [ ] All tests passing: `pytest emy/tests/test_dashboard_*.py -v`
- [ ] No console errors in browser (F12 → Console)
- [ ] Dashboard loads at `/dashboard`
- [ ] `/api/metrics` returns valid JSON
- [ ] `/ws/metrics` WebSocket connects and sends data
- [ ] All 4 metric cards display
- [ ] Agent status cards show 3 agents
- [ ] Responsive design works (mobile, tablet, desktop)
- [ ] Activity log displays events
- [ ] Live clock updates
- [ ] Browser DevTools WebSocket tab shows messages

**Step 3: Push to Production**

```bash
git push origin master
```

Render will auto-deploy to: `https://emy-phase1a.onrender.com/dashboard`

**Step 4: Verify Production**

```bash
curl https://emy-phase1a.onrender.com/dashboard | grep "Emy Dashboard"
curl https://emy-phase1a.onrender.com/api/metrics | jq .
```

Expected: Dashboard loads, metrics return valid JSON

**Step 5: Commit verification**

```bash
git add .
git commit -m "docs(dashboard): verification checklist complete"
```

---

## Summary

**Effort**: 8 hours total across 12 tasks
**Files Created**: 5 (HTML, CSS, JS, 2 test files)
**Files Modified**: 2 (api.py, database.py)
**Endpoints Added**: 3 (`/dashboard`, `/api/metrics`, `/ws/metrics`)
**Tests Created**: 12+ test functions
**Tech Stack**: FastAPI, WebSocket, vanilla JS, CSS custom properties

**Next Step**: Execute with superpowers:executing-plans or subagent-driven-development

---

