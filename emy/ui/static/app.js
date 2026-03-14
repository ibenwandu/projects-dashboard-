// Emy Dashboard Frontend Logic

const API_BASE = '';  // Relative URLs (same domain)
const HISTORY_REFRESH_INTERVAL = 30000;  // 30 seconds
const HEALTH_CHECK_INTERVAL = 60000;  // 60 seconds

// DOM Elements
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const agentCount = document.getElementById('agentCount');
const queryInput = document.getElementById('queryInput');
const workflowSelect = document.getElementById('workflowSelect');
const submitBtn = document.getElementById('submitBtn');
const resultContent = document.getElementById('resultContent');
const resultTime = document.getElementById('resultTime');
const loadingOverlay = document.getElementById('loadingOverlay');
const historyList = document.getElementById('historyList');

// State
let isConnected = false;
let isLoading = false;

// ============================================================================
// API Functions
// ============================================================================

/**
 * Check API health status
 */
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`, { method: 'GET' });
        const data = await response.json();

        isConnected = response.ok && data.status === 'ok';
        updateHealthIndicator();
        return isConnected;
    } catch (error) {
        console.error('Health check failed:', error);
        isConnected = false;
        updateHealthIndicator();
        return false;
    }
}

/**
 * Load agent status and update header
 */
async function loadAgents() {
    try {
        const response = await fetch(`${API_BASE}/agents/status`, { method: 'GET' });
        if (!response.ok) throw new Error('Failed to load agents');

        const data = await response.json();
        const count = data.agents.length;
        agentCount.textContent = `${count} agent${count !== 1 ? 's' : ''} ready`;
        return count;
    } catch (error) {
        console.error('Failed to load agents:', error);
        agentCount.textContent = '? agents';
    }
}

/**
 * Load recent workflow history
 */
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/workflows?limit=10&offset=0`, { method: 'GET' });
        if (!response.ok) throw new Error('Failed to load history');

        const data = await response.json();
        const workflows = data.workflows || [];

        if (workflows.length === 0) {
            historyList.innerHTML = '<p class="placeholder">No queries yet</p>';
            return;
        }

        // Reverse to show newest first
        workflows.reverse();

        historyList.innerHTML = workflows.map(wf => {
            const created = new Date(wf.created_at);
            const timeAgo = getTimeAgo(created);
            const statusClass = `status-${wf.status}`;
            const statusLabel = wf.status.charAt(0).toUpperCase() + wf.status.slice(1);

            return `
                <div class="history-item ${statusClass}">
                    <div class="history-main">
                        <span class="history-type">${wf.type}</span>
                        <span class="history-status">${statusLabel}</span>
                    </div>
                    <span class="history-time">${timeAgo}</span>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

/**
 * Submit a new query to the workflow engine
 */
async function submitQuery() {
    const query = queryInput.value.trim();
    if (!query) {
        alert('Please enter a query');
        return;
    }

    if (!isConnected) {
        alert('Emy is not connected. Please try again.');
        return;
    }

    const [workflowType, agent] = workflowSelect.value.split(':');

    try {
        isLoading = true;
        showLoading(true);
        submitBtn.disabled = true;
        queryInput.disabled = true;
        workflowSelect.disabled = true;

        const startTime = Date.now();

        const response = await fetch(`${API_BASE}/workflows/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                workflow_type: workflowType,
                agents: [agent],
                input: {
                    query: query
                }
            })
        });

        if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
        }

        const result = await response.json();
        const duration = ((Date.now() - startTime) / 1000).toFixed(1);

        // Format and display result
        displayResult(result, duration);

        // Refresh history to show new query
        setTimeout(loadHistory, 500);

        // Clear input
        queryInput.value = '';

    } catch (error) {
        console.error('Workflow execution failed:', error);
        resultContent.innerHTML = `<p class="error">Error: ${error.message}</p>`;
        resultTime.textContent = '';
    } finally {
        isLoading = false;
        showLoading(false);
        submitBtn.disabled = false;
        queryInput.disabled = false;
        workflowSelect.disabled = false;
        queryInput.focus();
    }
}

// ============================================================================
// UI Functions
// ============================================================================

/**
 * Update health status indicator and text
 */
function updateHealthIndicator() {
    if (isConnected) {
        statusDot.className = 'status-indicator connected';
        statusText.textContent = 'Connected';
    } else {
        statusDot.className = 'status-indicator disconnected';
        statusText.textContent = 'Disconnected';
    }
}

/**
 * Show/hide loading spinner
 */
function showLoading(show) {
    if (show) {
        loadingOverlay.style.display = 'flex';
    } else {
        loadingOverlay.style.display = 'none';
    }
}

/**
 * Format and display workflow result
 */
function displayResult(workflow, duration) {
    const output = workflow.output || '';

    // Parse the output - try JSON first
    let formatted = '';
    try {
        const parsed = JSON.parse(output);
        formatted = formatWorkflowOutput(parsed, workflow.type);
    } catch (e) {
        // If not JSON, display as text
        formatted = output || '(No output)';
    }

    resultContent.innerHTML = `
        <div class="result-formatted">
            ${formatted}
        </div>
    `;

    resultTime.textContent = `⏱ ${duration}s`;
}

/**
 * Format workflow output based on type and content
 */
function formatWorkflowOutput(data, workflowType) {
    // Handle different agent response types
    if (data.response) {
        // Knowledge or Research agent response
        return `<p>${escapeHtml(data.response)}</p>`;
    }

    if (data.analysis) {
        // Trading agent analysis
        return `<pre>${escapeHtml(JSON.stringify(data.analysis, null, 2))}</pre>`;
    }

    if (data.message) {
        return `<p>${escapeHtml(data.message)}</p>`;
    }

    // Default: pretty-print JSON
    if (typeof data === 'object') {
        return `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
    }

    return `<p>${escapeHtml(String(data))}</p>`;
}

/**
 * Get human-readable time ago string
 */
function getTimeAgo(date) {
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hour${Math.floor(seconds / 3600) > 1 ? 's' : ''} ago`;
    return `${Math.floor(seconds / 86400)} day${Math.floor(seconds / 86400) > 1 ? 's' : ''} ago`;
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// Event Listeners
// ============================================================================

submitBtn.addEventListener('click', submitQuery);
queryInput.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
        submitQuery();
    }
});

// ============================================================================
// Initialization
// ============================================================================

/**
 * Initialize dashboard on page load
 */
async function initialize() {
    // Check health and load initial data
    await checkHealth();
    await loadAgents();
    await loadHistory();

    // Set up auto-refresh intervals
    setInterval(loadHistory, HISTORY_REFRESH_INTERVAL);
    setInterval(checkHealth, HEALTH_CHECK_INTERVAL);

    // Focus query input
    queryInput.focus();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}
