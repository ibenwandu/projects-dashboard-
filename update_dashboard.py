#!/usr/bin/env python3
"""
Update mission control dashboard from dashboard_data.json
Regenerates mission_control.html with current data
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / 'dashboard_data.json'
HTML_FILE_ROOT = SCRIPT_DIR / 'mission_control.html'
HTML_FILE_DOCS = SCRIPT_DIR / 'docs' / 'index.html'

# Static HTML template - CSS and JS are fixed
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mission Control</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Monaco', 'Courier New', monospace;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #00ff88;
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
            font-size: 16px;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        /* ===== VISION BANNER ===== */
        .vision-banner {
            background: linear-gradient(135deg, rgba(255, 68, 102, 0.1) 0%, rgba(0, 255, 136, 0.05) 100%);
            border-left: 4px solid #ff4466;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 68, 102, 0.2);
        }

        .vision-label {
            font-size: 1.2em;
            color: #ff4466;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: bold;
            margin-bottom: 12px;
        }

        .vision-text {
            font-size: 1.3em;
            color: #00ff88;
            line-height: 1.7;
        }

        /* ===== HEADER ===== */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0, 255, 136, 0.05);
            border: 1px solid rgba(0, 255, 136, 0.2);
            border-radius: 8px;
        }

        .header h1 {
            font-size: 2.5em;
            font-weight: bold;
            color: #00ff88;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        }

        .header-right {
            display: flex;
            gap: 30px;
            align-items: center;
        }

        .agents-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.9em;
        }

        .pulse-dot {
            width: 12px;
            height: 12px;
            background: #00ff88;
            border-radius: 50%;
            animation: pulse 1.5s ease-in-out infinite;
            box-shadow: 0 0 10px #00ff88;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 10px #00ff88; }
            50% { opacity: 0.3; box-shadow: 0 0 5px #00ff88; }
        }

        .clock {
            font-size: 1.3em;
            font-weight: bold;
            color: #00ff88;
            min-width: 150px;
        }

        .last-event-badge {
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid #00ff88;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 0.85em;
            color: #00ff88;
        }

        /* ===== METRICS ROW ===== */
        .metrics-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: rgba(0, 255, 136, 0.08);
            border: 1px solid rgba(0, 255, 136, 0.3);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .metric-card:hover {
            background: rgba(0, 255, 136, 0.15);
            border-color: rgba(0, 255, 136, 0.6);
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.2), transparent);
            transition: left 0.5s ease;
        }

        .metric-card:hover::before {
            left: 100%;
        }

        .metric-label {
            font-size: 0.95em;
            color: #00aa66;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .metric-value {
            font-size: 3em;
            font-weight: bold;
            color: #00ff88;
        }

        .metric-tooltip {
            opacity: 0;
            position: absolute;
            top: -40px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.9);
            color: #00ff88;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 0.75em;
            white-space: nowrap;
            border: 1px solid #00ff88;
            transition: opacity 0.3s ease;
            pointer-events: none;
        }

        .metric-card:hover .metric-tooltip {
            opacity: 1;
        }

        /* ===== FILTER BAR ===== */
        .filter-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .filter-btn {
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid rgba(0, 255, 136, 0.3);
            color: #00ff88;
            padding: 10px 18px;
            border-radius: 4px;
            cursor: pointer;
            font-family: 'Monaco', monospace;
            font-size: 1em;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .filter-btn:hover {
            background: rgba(0, 255, 136, 0.2);
            border-color: #00ff88;
        }

        .filter-btn.active {
            background: #00ff88;
            color: #0a0e27;
            border-color: #00ff88;
            font-weight: bold;
        }

        /* ===== MAIN LAYOUT ===== */
        .main-layout {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 30px;
            margin-bottom: 30px;
        }

        /* ===== PROJECT CARDS (LEFT) ===== */
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }

        .project-card {
            background: rgba(0, 255, 136, 0.05);
            border-left: 4px solid #00ff88;
            padding: 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .project-card.pj-g {
            border-left-color: #00ff88;
        }

        .project-card.pj-b {
            border-left-color: #0099ff;
        }

        .project-card.pj-a {
            border-left-color: #ffaa00;
        }

        .project-card.pj-r {
            border-left-color: #ff4466;
        }

        .project-card:hover {
            background: rgba(0, 255, 136, 0.12);
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.2);
        }

        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }

        .project-name {
            font-size: 1.4em;
            font-weight: bold;
            color: #00ff88;
        }

        .status-pill {
            background: rgba(0, 255, 136, 0.15);
            color: #00ff88;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: 1px solid rgba(0, 255, 136, 0.3);
        }

        .status-pill.live {
            background: rgba(0, 255, 136, 0.2);
            border-color: #00ff88;
            color: #00ff88;
        }

        .status-pill.complete {
            background: rgba(0, 255, 136, 0.2);
            border-color: #00ff88;
            color: #00ff88;
        }

        .status-pill.running {
            background: rgba(0, 255, 136, 0.2);
            border-color: #00ff88;
            color: #00ff88;
        }

        .status-pill.ready {
            background: rgba(0, 153, 255, 0.2);
            border-color: #0099ff;
            color: #0099ff;
        }

        .status-pill.configured {
            background: rgba(0, 153, 255, 0.2);
            border-color: #0099ff;
            color: #0099ff;
        }

        .status-pill.pending {
            background: rgba(255, 170, 0, 0.2);
            border-color: #ffaa00;
            color: #ffaa00;
        }

        .status-pill.disabled {
            background: rgba(255, 68, 102, 0.2);
            border-color: #ff4466;
            color: #ff4466;
        }

        .project-phase {
            font-size: 1em;
            color: #00aa66;
            margin-bottom: 10px;
        }

        .project-description {
            font-size: 1em;
            color: rgba(0, 255, 136, 0.7);
            margin-bottom: 15px;
            display: none;
        }

        .project-card.expanded .project-description {
            display: block;
        }

        .project-milestone {
            font-size: 0.85em;
            color: rgba(0, 255, 136, 0.6);
            display: none;
            padding-top: 15px;
            border-top: 1px solid rgba(0, 255, 136, 0.1);
        }

        .project-card.expanded .project-milestone {
            display: block;
        }

        .milestone-label {
            color: #00aa66;
            font-size: 0.75em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }

        /* ===== SIDEBAR (RIGHT) ===== */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .sidebar-panel {
            background: rgba(0, 255, 136, 0.05);
            border: 1px solid rgba(0, 255, 136, 0.2);
            padding: 15px;
            border-radius: 8px;
        }

        .sidebar-title {
            font-size: 1.1em;
            color: #00ff88;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
            font-weight: bold;
            border-bottom: 1px solid rgba(0, 255, 136, 0.2);
            padding-bottom: 10px;
        }

        .priority-item {
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
            font-size: 1em;
            align-items: flex-start;
        }

        .priority-num {
            color: #00aa66;
            font-weight: bold;
            min-width: 40px;
        }

        .priority-text {
            flex: 1;
            color: rgba(0, 255, 136, 0.8);
        }

        .priority-status {
            font-size: 0.7em;
            color: #00ff88;
            text-transform: uppercase;
        }

        .priority-complete {
            color: #00ff88;
        }

        .priority-active {
            color: #ffaa00;
        }

        .priority-pending {
            color: rgba(0, 255, 136, 0.5);
        }

        .status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            font-size: 1em;
            padding: 8px;
            background: rgba(0, 255, 136, 0.02);
            border-radius: 4px;
        }

        .status-name {
            color: rgba(0, 255, 136, 0.7);
        }

        .status-value {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .status-indicator.green {
            background: #00ff88;
            box-shadow: 0 0 8px #00ff88;
        }

        .status-indicator.amber {
            background: #ffaa00;
            box-shadow: 0 0 8px #ffaa00;
        }

        .status-indicator.red {
            background: #ff4466;
            box-shadow: 0 0 8px #ff4466;
        }

        /* ===== LOG BAR ===== */
        .log-bar {
            background: rgba(0, 255, 136, 0.08);
            border: 1px solid rgba(0, 255, 136, 0.3);
            padding: 15px 20px;
            border-radius: 8px;
            font-size: 1em;
            color: #00ff88;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .log-message {
            flex: 1;
        }

        .log-timestamp {
            color: #00aa66;
            font-weight: bold;
        }

        .last-updated {
            display: flex;
            flex-direction: column;
            align-items: center;
            font-size: 0.9em;
            color: #00aa66;
            text-align: center;
        }

        .updated-timestamp {
            font-weight: bold;
            color: #00ff88;
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 1200px) {
            .main-layout {
                grid-template-columns: 1fr;
            }

            .sidebar {
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                display: grid;
            }
        }

        @media (max-width: 768px) {
            .projects-grid {
                grid-template-columns: 1fr;
            }

            .header {
                flex-direction: column;
                gap: 15px;
            }

            .header-right {
                flex-direction: column;
                width: 100%;
            }

            .clock, .last-event-badge, .agents-indicator, .last-updated {
                width: 100%;
                justify-content: center;
            }

            .sidebar {
                grid-template-columns: 1fr;
            }
        }

        /* ===== HIDDEN BY FILTER ===== */
        .project-card.hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- VISION BANNER -->
        <div class="vision-banner">
            <div class="vision-label">Vision</div>
            <div class="vision-text">VISION_TEXT</div>
        </div>

        <!-- HEADER -->
        <div class="header">
            <h1>⚡ MISSION CONTROL</h1>
            <div class="header-right">
                <div class="agents-indicator">
                    <div class="pulse-dot"></div>
                    <span>Agents Active</span>
                </div>
                <div class="clock" id="clock">--:-- --</div>
                <div class="last-updated">
                    <span class="updated-label">Updated</span>
                    <span class="updated-timestamp">LAST_SESSION</span>
                </div>
                <div class="last-event-badge" id="lastEvent">Last Event: LASTEVENTH</div>
            </div>
        </div>

        <!-- METRICS ROW -->
        <div class="metrics-row">
            <div class="metric-card">
                <div class="metric-label">Systems Running</div>
                <div class="metric-value" id="systemsCount">SYSTEMS</div>
                <div class="metric-tooltip">Trade-Alerts, Scalp-Engine, Emy</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Emy Agents</div>
                <div class="metric-value" id="agentsCount">AGENTS</div>
                <div class="metric-tooltip">Trading, Knowledge, Monitor, Research, Gemini, Analysis</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Scheduled Jobs</div>
                <div class="metric-value" id="jobsCount">JOBS</div>
                <div class="metric-tooltip">15m, 1h, 4h, 24h intervals</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Active Automations</div>
                <div class="metric-value" id="automationsCount">AUTOMATIONS</div>
                <div class="metric-tooltip">Job-search paused (API preservation)</div>
            </div>
        </div>

        <!-- FILTER BAR -->
        <div class="filter-bar">
            <button class="filter-btn active" data-filter="all">All Projects</button>
            <button class="filter-btn" data-filter="live">Live</button>
            <button class="filter-btn" data-filter="ready">Ready</button>
            <button class="filter-btn" data-filter="pending">Pending</button>
            <button class="filter-btn" data-filter="disabled">Disabled</button>
        </div>

        <!-- MAIN LAYOUT -->
        <div class="main-layout">
            <!-- PROJECTS GRID (LEFT) -->
            <div class="projects-grid" id="projectsGrid">
PROJECTS_HTML
            </div>

            <!-- SIDEBAR (RIGHT) -->
            <div class="sidebar">
                <!-- PRIORITIES PANEL -->
                <div class="sidebar-panel">
                    <div class="sidebar-title">📋 Priorities</div>
                    <div id="prioritiesList">
PRIORITIES_HTML
                    </div>
                </div>

                <!-- SYSTEM STATUS PANEL -->
                <div class="sidebar-panel">
                    <div class="sidebar-title">🟢 System Status</div>
                    <div id="statusList">
STATUS_HTML
                    </div>
                </div>
            </div>
        </div>

        <!-- LOG BAR -->
        <div class="log-bar">
            <div class="log-message">
                <span class="log-timestamp" id="logTimestamp">LOGTIMESTAMP</span>
                <span> — </span>
                <span id="logMessage">LOGMESSAGE</span>
            </div>
        </div>
    </div>

    <script>
        // Setup filter functionality
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const filter = btn.dataset.filter;
                document.querySelectorAll('.project-card').forEach(card => {
                    card.classList.remove('hidden');
                    if (filter !== 'all') {
                        const status = card.getAttribute('data-status');
                        if (!status.includes(filter)) {
                            card.classList.add('hidden');
                        }
                    }
                });
            });
        });

        // Setup project card expansion
        document.querySelectorAll('.project-card').forEach(card => {
            card.addEventListener('click', () => {
                card.classList.toggle('expanded');
            });
        });

        // Update live clock
        function updateClock() {
            const clock = document.getElementById('clock');
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const ampm = now.getHours() >= 12 ? 'PM' : 'AM';
            clock.textContent = hours + ':' + minutes + ' ' + ampm;
            setTimeout(updateClock, 1000);
        }
        updateClock();
    </script>
</body>
</html>
'''


def generate_projects_html(projects):
    """Generate project cards HTML"""
    html = ""
    for project in projects:
        status_key = project['status'].lower().replace(' ', '').replace('/', '')
        html += f'''            <div class="project-card {project['color']}" data-status="{status_key}">
                <div class="project-header">
                    <div class="project-name">{project['name']}</div>
                    <div class="status-pill {status_key}">{project['status']}</div>
                </div>
                <div class="project-phase">→ {project['phase']}</div>
                <div class="project-description">{project['description']}</div>
                <div class="project-milestone">
                    <div class="milestone-label">Next Milestone</div>
                    <div>{project['nextMilestone']}</div>
                </div>
            </div>
'''
    return html.rstrip()


def generate_priorities_html(priorities):
    """Generate priorities list HTML"""
    html = ""
    for p in priorities:
        status_class = f"priority-{p['status']}"
        status_text = "✓ Done" if p['status'] == 'complete' else ("› Active" if p['status'] == 'active' else "○ Pending")
        html += f'''                    <div class="priority-item">
                        <div class="priority-num">#{p['num']}</div>
                        <div style="flex: 1;">
                            <div class="priority-text">{p['text']}</div>
                            <div style="margin-top: 4px;">
                                <span class="priority-status {status_class}">{status_text}</span>
                            </div>
                        </div>
                    </div>
'''
    return html.rstrip()


def generate_status_html(statuses):
    """Generate system status HTML"""
    html = ""
    for s in statuses:
        html += f'''                    <div class="status-row">
                        <div class="status-name">{s['name']}</div>
                        <div class="status-value">
                            <span>{s['value']}</span>
                            <div class="status-indicator {s['status']}"></div>
                        </div>
                    </div>
'''
    return html.rstrip()


def update_dashboard():
    """Main function to update dashboard"""
    try:
        # Load data
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Generate HTML components
        projects_html = generate_projects_html(data['projects'])
        priorities_html = generate_priorities_html(data['priorities'])
        status_html = generate_status_html(data['systemStatus'])

        # Format timestamps
        last_event = data['metadata']['lastSession']
        log_timestamp = last_event
        log_message = data['logMessage']

        # Prepare template replacements
        vision = data.get('vision', 'Building autonomous systems with AI')
        replacements = {
            'VISION_TEXT': vision,
            'LASTEVENTH': last_event,
            'LAST_SESSION': last_event,
            'SYSTEMS': str(data['metrics']['systemsRunning']),
            'AGENTS': str(data['metrics']['eachAgents']),
            'JOBS': str(data['metrics']['scheduledJobs']),
            'AUTOMATIONS': str(data['metrics']['activeAutomations']),
            'PROJECTS_HTML': projects_html,
            'PRIORITIES_HTML': priorities_html,
            'STATUS_HTML': status_html,
            'LOGTIMESTAMP': log_timestamp,
            'LOGMESSAGE': log_message,
        }

        # Generate HTML
        html_content = HTML_TEMPLATE
        for key, value in replacements.items():
            html_content = html_content.replace(key, value)

        # Create docs folder if it doesn't exist
        HTML_FILE_DOCS.parent.mkdir(parents=True, exist_ok=True)

        # Write HTML to both locations
        with open(HTML_FILE_ROOT, 'w', encoding='utf-8') as f:
            f.write(html_content)

        with open(HTML_FILE_DOCS, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print("[OK] Dashboard updated: " + str(HTML_FILE_ROOT))
        print("[OK] GitHub Pages updated: " + str(HTML_FILE_DOCS))
        print("  Last updated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("  Projects: " + str(len(data['projects'])))
        print("  Priorities: " + str(len(data['priorities'])))

        return True

    except Exception as e:
        print("[ERROR] Error updating dashboard: " + str(e))
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    update_dashboard()
