# Mission Control Dashboard

**Live status dashboard for your autonomous AI projects.** Real-time monitoring of Emy, Trade-Alerts, Scalp-Engine, and job-search automation with deployment status, priorities, and system health.

---

## Quick Access

### 📱 Mobile Access
Copy this link to your phone or tablet:
```
https://ibenwandu.github.io/projects/personal/docs/
```

### 💻 Desktop Access
Open in any browser:
```
https://ibenwandu.github.io/projects/personal/docs/
```

**Note:** Same URL works on mobile, tablet, or desktop. All features are fully responsive.

---

## What You're Looking At

### Vision
Autonomous AI Chief of Staff managing trading, job search, and knowledge systems — with real-time visibility into operations, decisions, and system health.

### Systems Running
- **Emy** — Multi-agent orchestration system (5 agents, 11 skills, 24/7)
- **Trade-Alerts** — LLM-based market analysis (Render)
- **Scalp-Engine** — Automated trading execution (Render)
- **job-search** — Cross-platform job discovery (disabled, credits preserved)

### Agents Active
| Agent | Domain | Role |
|-------|--------|------|
| TradingAgent | trading | OANDA monitoring, Render health, log analysis |
| JobSearchAgent | job_search | Multi-platform scraping, scoring, resume tailoring |
| KnowledgeAgent | knowledge | Obsidian updates, MEMORY.md, git commits |
| ProjectMonitorAgent | project_monitor | Monitor all Render services |
| ResearchAgent | research | Evaluate new project feasibility |

### Projects Tracked
- **Emy** (Production, Phase 3 Week 3 Complete) — 40/40 tests passing
- **Trade-Alerts** (Testing, Phase 1) — SL/TP verification in progress
- **Scalp-Engine** (Production) — Real trading on Render
- **job-search** (Disabled) — API credits preserved
- **Indicator-Alerts** (Development) — Real-time price alerts
- **sentiment-monitor** (Development) — Market sentiment analysis

### Priorities
1. **Emy Production Stability** — All features validated, ready for scale
2. **Trade-Alerts Phase 1** — Complete 48+ hour SL/TP verification testing
3. **Dashboard Performance** — Optimize responsive design for mobile/tablet
4. **Job Search Resume Tailoring** — Improve resume scoring algorithm
5. **Multi-Platform Deployment** — Consider AWS Lambda for Scalp-Engine

### System Health Status
- 🟢 **Green** — All systems operational, no alerts
- 🟡 **Amber** — Warning detected, manual review recommended
- 🔴 **Red** — System offline or critical error, immediate attention required

**Status Check Frequency:** Dashboard updates every 1-2 minutes during active sessions.

---

## How This Updates

### Automatic Updates (Zero Manual Intervention)
The dashboard updates automatically when you close a working session:

1. **Trigger**: Run `/close-session` in Claude Code
2. **What Happens**:
   - All session decisions are captured
   - Project status is refreshed
   - Git commits any changes
   - Dashboard HTML is regenerated
   - Changes pushed to GitHub
3. **Publishing**: GitHub Pages auto-publishes within 1 minute
4. **Frequency**: Typically 1-2 times per working day (whenever you end a session)

**Between Sessions:** The dashboard shows the last-known state from the previous
session close. For real-time information (trading positions, current alerts, live
market data), check the individual systems directly rather than relying on the
dashboard snapshot.

### Last Updated
Check the dashboard header for the last update timestamp. This reflects when the dashboard HTML was last regenerated.

### Real-Time Elements
- **Live Clock** — Updates every second
- **Project Status** — Reflects latest database snapshots
- **System Health Indicators** — Real-time color status
- **Priority Rankings** — Dynamically ordered by urgency

---

## Embedding This Dashboard

### iFrame Embedding
Add this code to any documentation or external site to embed the dashboard:

```html
<!-- Mission Control Dashboard Embed -->
<div style="position: relative; width: 100%; padding-bottom: 56.25%;">
  <iframe
    src="https://ibenwandu.github.io/projects/personal/docs/"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 1px solid #ddd; border-radius: 8px;"
    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
    allowfullscreen>
  </iframe>
</div>
```

### Link Embedding
Or simply link to the dashboard:

```markdown
[Mission Control Dashboard](https://ibenwandu.github.io/projects/personal/docs/)
```

### Mobile-Optimized Link
For mobile bookmarks:

```html
<a href="https://ibenwandu.github.io/projects/personal/docs/"
   style="display: inline-block; padding: 12px 24px; background: #0366d6; color: white; border-radius: 6px; text-decoration: none; font-weight: bold;">
  Open Dashboard
</a>
```

---

## Features & Functionality

### Live Clock
- Updates every second
- Displays current time in your local timezone
- Useful for checking task scheduling and run times

### Expandable Project Cards
- Click any project to expand/collapse details
- Shows current status, phase, test results, and priority
- One-click access to project repositories (GitHub links)

### Filterable Projects
Filter dashboard by project status:
- **All** — Show all projects
- **Live** — Production systems (running 24/7)
- **Ready** — Fully tested, ready for deployment
- **Pending** — In development, awaiting testing
- **Disabled** — Currently paused (API credits, manual maintenance)

### System Status Indicators
Color-coded visual indicators:
- 🟢 **Green** — Operational, all tests passing
- 🟡 **Amber** — Warning detected, review recommended
- 🔴 **Red** — Offline or critical error, action required

### Priority Tracking
- Ranked by importance and urgency
- Shows completion percentage for multi-phase projects
- Links to detailed task lists and blockers

### Responsive Design
- **Desktop** — Full-featured multi-column layout
- **Tablet** — Optimized 2-column grid
- **Mobile** — Single-column stack with collapsible sections
- Touch-friendly buttons and expandable cards
- Auto-scaling fonts and spacing

---

## QR Code for Mobile

Scan this QR code with your phone to open the dashboard instantly:

![QR Code - Scan with your phone to open dashboard on mobile](https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=https%3A%2F%2Fibenwandu.github.io%2Fprojects%2Fpersonal%2Fdocs%2F)

---

## Questions & Documentation

### Need More Information?
- **[Main Project README](https://github.com/ibenwandu/projects-personal/blob/main/README.md)** — Complete Emy documentation, architecture, CLI commands
- **[Global Working Guidelines](https://github.com/ibenwandu/projects-personal/blob/main/CLAUDE.md)** — Development approach, working style, career context
- **[Deployment Guide](https://github.com/ibenwandu/projects-personal/blob/main/RENDER_DEPLOYMENT.md)** — Production setup, configuration, monitoring

### Project Specifics
For project-specific documentation, each project directory includes:
- `CLAUDE.md` — Project working guidelines
- `CLAUDE_SESSION_LOG.md` — Session history and progress
- `README.md` — Detailed project documentation

### Full Documentation
Ask for comprehensive documentation of any project:
```bash
# Request documentation
Ask Emy to provide full documentation for [project-name]

# Examples:
Ask Emy to provide full documentation for Trade-Alerts
Ask Emy to provide full documentation for Scalp-Engine
Ask Emy to provide full documentation for Emy
```

---

## Browser Compatibility

**Recommended Browsers:**
- Chrome 90+ (Desktop & Mobile)
- Firefox 88+
- Safari 14+
- Edge 90+

**Mobile Browsers:**
- Safari on iOS 14+
- Chrome for Android

**Progressive Enhancement:**
The dashboard works with or without JavaScript enabled, though interactive features (filtering, clock updates) require JavaScript.

---

## Performance Notes

- **First Load**: ~2-3 seconds (includes assets and data)
- **Subsequent Loads**: <1 second (browser caching)
- **Mobile Data**: ~200 KB on first load, ~50 KB for refreshes
- **Auto-Refresh**: Every 1-2 minutes during active session

---

## Troubleshooting

### Dashboard Not Loading?
1. Clear browser cache: Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
2. Try a different browser
3. Check internet connection
4. Wait 2 minutes (GitHub Pages may take time to publish)

### Project Status Outdated?
- Dashboard updates when you run `/close-session`
- Manual updates can be triggered by running dashboard generation scripts
- Check the timestamp in the dashboard header

### Mobile Display Issues?
1. Rotate device to landscape
2. Zoom out slightly (pinch gesture)
3. Try a different mobile browser
4. Check that JavaScript is enabled in browser settings

### iFrame Embedding Not Working?
- Ensure you're using HTTPS (not HTTP)
- Check browser console for security warnings
- Verify the URL hasn't changed
- Some corporate firewalls may block external iframes

---

## Footer

**Dashboard Version:** 1.0
**Last Updated:** March 15, 2026
**Platform:** GitHub Pages + Static HTML
**Repository:** [ibenwandu/projects-personal](https://github.com/ibenwandu/projects-personal)

---

**Questions about your systems?** Check the [main README](https://github.com/ibenwandu/projects-personal/blob/main/README.md) or view the [global guidelines](https://github.com/ibenwandu/projects-personal/blob/main/CLAUDE.md).

**Want to access your projects directly?** Navigate to the repository root or check the GitHub organization.
