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

    // Update agent count
    const agentCount = document.getElementById('agent-count');
    if (agentCount) {
        agentCount.textContent = `(${agents.length})`;
    }

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

function updateAgentCard(agentName, data) {
    const card = document.querySelector(`[data-agent="${agentName}"]`);
    if (!card) return;

    card.querySelector('.agent-status').className = `agent-status ${data.status}`;
    card.querySelector('.agent-status').textContent = `● ${data.status.toUpperCase()}`;
    card.querySelector('.agent-last-exec').textContent = `Last: ${formatRelativeTime(data.last_execution)}`;
    card.querySelector('.agent-stats').textContent = `Executions: ${data.execution_count_today}`;
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
