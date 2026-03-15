// Emy Dashboard Frontend Logic

const API_BASE = '';  // Relative URLs (same domain)
const HISTORY_REFRESH_INTERVAL = 30000;  // 30 seconds
const HEALTH_CHECK_INTERVAL = 60000;  // 60 seconds

// Workflow mapping: agentName -> [[workflowType, label], ...]
const WORKFLOW_MAP = {
    'TradingAgent': [
        ['trading_health', 'Trading Health'],
        ['trading_analysis', 'Trading Analysis']
    ],
    'KnowledgeAgent': [
        ['knowledge_query', 'Knowledge Query'],
        ['knowledge_synthesis', 'Knowledge Synthesis']
    ],
    'ResearchAgent': [
        ['research_query', 'Research Query'],
        ['research_evaluation', 'Research Evaluation']
    ],
    'ProjectMonitorAgent': [
        ['project_status', 'Project Status'],
        ['project_analysis', 'Project Analysis']
    ],
};

// DOM Elements
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const agentCount = document.getElementById('agentCount');
const queryInput = document.getElementById('queryInput');
const workflowSelect = document.getElementById('workflowSelect');
const workflowSelect2 = document.getElementById('workflowSelect2');
const compareMode = document.getElementById('compareMode');
const compareAgentRow = document.getElementById('compareAgentRow');
const submitBtn = document.getElementById('submitBtn');
const resultContent = document.getElementById('resultContent');
const resultTime = document.getElementById('resultTime');
const resultActions = document.getElementById('resultActions');
const exportBtn = document.getElementById('exportBtn');
const copyBtn = document.getElementById('copyBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const historyList = document.getElementById('historyList');
const comparisonSection = document.getElementById('comparisonSection');
const compareContent1 = document.getElementById('compareContent1');
const compareContent2 = document.getElementById('compareContent2');
const compareLabel1 = document.getElementById('compareLabel1');
const compareLabel2 = document.getElementById('compareLabel2');

// State
let isConnected = false;
let isLoading = false;
let lastResult = null;
let historyCache = [];

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
 * Load agent status and populate workflow dropdowns dynamically
 */
async function loadAgents() {
    try {
        const response = await fetch(`${API_BASE}/agents/status`, { method: 'GET' });
        if (!response.ok) throw new Error('Failed to load agents');

        const data = await response.json();
        const count = data.agents.length;
        agentCount.textContent = `${count} agent${count !== 1 ? 's' : ''} ready`;

        // Populate both dropdowns dynamically
        const agents = data.agents || [];
        populateWorkflowSelects(agents);
        return count;
    } catch (error) {
        console.error('Failed to load agents:', error);
        agentCount.textContent = '? agents';
    }
}

/**
 * Populate both workflow select dropdowns from available agents
 */
function populateWorkflowSelects(agents) {
    workflowSelect.innerHTML = '';
    workflowSelect2.innerHTML = '';

    agents.forEach(agent => {
        const workflows = WORKFLOW_MAP[agent.agent_name] || [];
        workflows.forEach(([type, label]) => {
            const opt1 = document.createElement('option');
            opt1.value = `${type}:${agent.agent_name}`;
            opt1.textContent = label;
            workflowSelect.appendChild(opt1);

            const opt2 = document.createElement('option');
            opt2.value = `${type}:${agent.agent_name}`;
            opt2.textContent = label;
            workflowSelect2.appendChild(opt2);
        });
    });
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

        // Store full workflow objects for click handlers
        historyCache = workflows;
        // Reverse to show newest first
        workflows.reverse();

        historyList.innerHTML = workflows.map((wf, index) => {
            const created = new Date(wf.created_at);
            const timeAgo = getTimeAgo(created);
            const statusClass = `status-${wf.status}`;
            const statusLabel = wf.status.charAt(0).toUpperCase() + wf.status.slice(1);

            return `
                <div class="history-item ${statusClass}" data-index="${index}" role="button" tabindex="0">
                    <div class="history-main">
                        <span class="history-type">${wf.type}</span>
                        <span class="history-status">${statusLabel}</span>
                    </div>
                    <span class="history-time">${timeAgo}</span>
                </div>
            `;
        }).join('');

        // Attach click handlers to history items
        historyList.querySelectorAll('.history-item').forEach((item, index) => {
            item.addEventListener('click', () => loadHistoryItem(index));
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    loadHistoryItem(index);
                }
            });
        });
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

/**
 * Load and display a historical workflow result
 */
function loadHistoryItem(index) {
    const wf = historyCache[index];
    if (!wf) return;

    // Try to parse input to get the query
    try {
        const input = JSON.parse(wf.input || '{}');
        queryInput.value = input.query || '';
    } catch (e) {
        queryInput.value = '';
    }

    // Display the cached result
    if (wf.output) {
        lastResult = wf;
        displayResult(wf, '(cached)');
    }
}

/**
 * Execute a single workflow and return result
 */
async function executeWorkflow(workflowType, agent, query) {
    const response = await fetch(`${API_BASE}/workflows/execute`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            workflow_type: workflowType,
            agents: [agent],
            input: { query: query }
        })
    });

    if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
    }

    return response.json();
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

    // If in comparison mode, execute comparison
    if (compareMode.checked) {
        return submitComparison(query);
    }

    const [workflowType, agent] = workflowSelect.value.split(':');

    try {
        isLoading = true;
        showLoading(true);
        submitBtn.disabled = true;
        queryInput.disabled = true;
        workflowSelect.disabled = true;

        const startTime = Date.now();
        const result = await executeWorkflow(workflowType, agent, query);
        const duration = ((Date.now() - startTime) / 1000).toFixed(1);

        // Store result and display
        lastResult = result;
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

/**
 * Submit query in comparison mode
 */
async function submitComparison(query) {
    const [type1, agent1] = workflowSelect.value.split(':');
    const [type2, agent2] = workflowSelect2.value.split(':');

    try {
        isLoading = true;
        showLoading(true);
        submitBtn.disabled = true;

        comparisonSection.style.display = 'block';
        compareContent1.innerHTML = '<div class="spinner-inline"></div>';
        compareContent2.innerHTML = '<div class="spinner-inline"></div>';
        compareLabel1.textContent = type1;
        compareLabel2.textContent = type2;

        const startTime = Date.now();
        const [result1, result2] = await Promise.all([
            executeWorkflow(type1, agent1, query),
            executeWorkflow(type2, agent2, query)
        ]);
        const duration = ((Date.now() - startTime) / 1000).toFixed(1);

        // Display comparison results - with proper unescaping
        let output1 = (result1.output || '');
        let output2 = (result2.output || '');
        console.log('Result1:', result1, 'Output1 type:', typeof output1, 'Output1:', output1);
        console.log('Result2:', result2, 'Output2 type:', typeof output2, 'Output2:', output2);

        // Ensure they're strings, parse JSON if needed, then unescape
        function cleanOutput(output) {
            if (!output) return '';
            let text = '' + output;  // Force string conversion
            // Try JSON parse
            try {
                const parsed = JSON.parse(text);
                text = '' + parsed;
            } catch (e) {
                // Not JSON, use as-is
            }
            // Ensure text is a string before calling replace
            if (typeof text !== 'string') {
                text = '' + text;
            }
            // Unescape sequences
            text = text.replace(/\\n/g, '\n')
                      .replace(/\\t/g, '\t')
                      .replace(/\\\\/g, '\\')
                      .replace(/^["\\]+|["\\]+$/g, '');
            return text;
        }

        output1 = cleanOutput(output1);
        output2 = cleanOutput(output2);

        compareContent1.innerHTML = `<div style="white-space: pre-wrap; font-family: monospace; font-size: 12px; line-height: 1.6;">${escapeHtml(output1)}</div>`;
        compareContent2.innerHTML = `<div style="white-space: pre-wrap; font-family: monospace; font-size: 12px; line-height: 1.6;">${escapeHtml(output2)}</div>`;

        resultTime.textContent = `⏱ ${duration}s`;

        // Refresh history
        setTimeout(loadHistory, 500);
        queryInput.value = '';

    } catch (error) {
        console.error('Comparison failed:', error);
        compareContent1.innerHTML = `<p class="error">Error: ${error.message}</p>`;
        compareContent2.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    } finally {
        isLoading = false;
        showLoading(false);
        submitBtn.disabled = false;
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
 * Try to parse JSON, return as-is if parsing fails
 */
function tryParseJSON(str) {
    try {
        return JSON.parse(str || '{}');
    } catch (e) {
        return str || '';
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
    resultActions.style.display = 'flex';
    comparisonSection.style.display = 'none';
}

/**
 * Export current result as JSON download
 */
async function exportResult() {
    if (!lastResult) return;
    const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `emy-${lastResult.type}-${lastResult.workflow_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Copy current result to clipboard
 */
async function copyResult() {
    if (!lastResult) return;
    const text = lastResult.output || JSON.stringify(lastResult, null, 2);
    try {
        await navigator.clipboard.writeText(text);
        // Show brief feedback
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✓ Copied!';
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    } catch (error) {
        console.error('Failed to copy:', error);
        alert('Failed to copy to clipboard');
    }
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

    // Handle string data (markdown text)
    if (typeof data === 'string') {
        let text = data;

        // Try to parse as JSON, handling double-encoding
        let parseAttempts = 0;
        while ((text.startsWith('"') || text.startsWith('\\"')) && parseAttempts < 3) {
            try {
                text = JSON.parse(text);
                parseAttempts++;
            } catch (e) {
                // If parsing fails, strip outer quotes
                text = text.replace(/^["\\]/, '').replace(/["\\]$/, '');
                break;
            }
        }

        // Unescape common escape sequences if still present
        text = text.replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\\\/g, '\\');

        // Strip any remaining leading/trailing quotes
        text = text.replace(/^["\\]+/, '').replace(/["\\]+$/, '');

        // If it looks like markdown or structured text, display with proper formatting
        if (text.trim().startsWith('#') || text.includes('##') || text.includes('|')) {
            return `<div style="white-space: pre-wrap; font-family: monospace; font-size: 12px; line-height: 1.6;">${escapeHtml(text)}</div>`;
        }
        return `<p>${escapeHtml(text)}</p>`;
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

compareMode.addEventListener('change', (e) => {
    compareAgentRow.style.display = e.target.checked ? 'flex' : 'none';
    comparisonSection.style.display = 'none';
});

exportBtn.addEventListener('click', exportResult);
copyBtn.addEventListener('click', copyResult);

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
