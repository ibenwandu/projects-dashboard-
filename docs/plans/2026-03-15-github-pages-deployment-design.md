# GitHub Pages Deployment for Mission Control Dashboard

**Date**: March 15, 2026
**Status**: ✅ DESIGN APPROVED
**Implementation Complexity**: Low (~20 minutes)
**Maintenance Overhead**: Zero (automated at session close)

---

## Executive Summary

Deploy the Mission Control dashboard to GitHub Pages for mobile access and embedding in documentation. Use the `docs/` folder approach with automatic updates triggered at session close. No build process, external dependencies, or branch switching needed.

**Primary use cases**:
1. Quick status check from phone (anywhere, anytime)
2. Embed dashboard in documentation, GitHub profile, or other platforms

**Success criteria**:
- ✅ Dashboard accessible via GitHub Pages URL
- ✅ Updates automatically when `/close-session` runs
- ✅ "Last Updated" timestamp visible to users
- ✅ Responsive design works on mobile
- ✅ Can be embedded in iframes

---

## Architecture & Data Flow

### File Structure

```
C:\Users\user\projects\personal\
├── dashboard_data.json           (source of truth)
├── mission_control.html          (local version)
├── update_dashboard.py           (generator - MODIFIED)
├── docs/                         (NEW - GitHub Pages root)
│   ├── index.html               (generated from Python script)
│   ├── dashboard.json           (optional: backup of data)
│   └── README.md                (NEW - documentation)
└── ~/.claude/session-decisions-end.sh (MODIFIED - git commit)
```

### Data Flow Pipeline

```
User runs /close-session
        ↓
session-decisions-end.sh executes
        ↓
update_dashboard.py runs
        ↓
Regenerates docs/index.html from dashboard_data.json
        ↓
session-decisions-end.sh: git add docs/
        ↓
git commit (includes docs/ folder)
        ↓
git push to origin/main
        ↓
GitHub Pages auto-publishes from docs/index.html
        ↓
Dashboard live at: https://github.com/username/projects/personal/docs/
```

### Why This Architecture Works

1. **Single git workflow**: No branch switching required
2. **Automatic updates**: Happens at session close (when you're already committing)
3. **Self-contained HTML**: Data is already embedded by Python script (no runtime data fetching)
4. **GitHub Pages convention**: Using `docs/` folder is standard, GitHub auto-detects and publishes
5. **Zero external dependencies**: No build tools, APIs, or servers needed
6. **Mobile-friendly**: Responsive design already built into mission_control.html

---

## Design Components

### 1. HTML Enhancement: "Last Updated" Display

**Current state**: Dashboard shows log timestamp in footer, but freshness not obvious

**Change**: Add prominent "Updated" display in header

**Implementation**:
```html
<!-- Add to header-right div (before or after Agents Active) -->
<div class="last-updated">
    <span class="updated-label">Updated</span>
    <span class="updated-timestamp">Mar 15 · 14:33 EDT</span>
</div>
```

**CSS** (add to style section):
```css
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
```

**Result**: Users instantly see "Updated Mar 15 · 14:33 EDT" in header, addressing freshness without requiring real-time updates

**Data source**: Extract from `dashboard_data.json` → `metadata.lastSession` → format as "Mar 15 · 14:33 EDT"

---

### 2. Python Script Modification: Dual Output

**Current**: `update_dashboard.py` generates only `mission_control.html` (root)

**Change**: Generate to both root and `docs/index.html`

**Implementation**:
```python
# At top of update_dashboard() function
HTML_FILE_ROOT = SCRIPT_DIR / 'mission_control.html'       # Local version
HTML_FILE_DOCS = SCRIPT_DIR / 'docs' / 'index.html'        # GitHub Pages

# Ensure docs folder exists
HTML_FILE_DOCS.parent.mkdir(parents=True, exist_ok=True)

# After generating html_content, write to both locations
with open(HTML_FILE_ROOT, 'w', encoding='utf-8') as f:
    f.write(html_content)
print("[OK] Dashboard updated: " + str(HTML_FILE_ROOT))

with open(HTML_FILE_DOCS, 'w', encoding='utf-8') as f:
    f.write(html_content)
print("[OK] GitHub Pages updated: " + str(HTML_FILE_DOCS))
```

**Result**: Single `python update_dashboard.py` call updates both local and GitHub Pages versions

---

### 3. GitHub Pages Configuration

**One-time setup** (no code changes required):

1. Go to: GitHub repo → Settings → Pages
2. Source: "Deploy from a branch"
3. Branch: `main`, Folder: `docs/`
4. Save
5. Wait ~1 minute for GitHub to activate

**Verification**: After first git push, dashboard lives at:
```
https://github.com/username/projects/personal/docs/
```

(Exact URL depends on GitHub account settings; GitHub will display the URL in Settings → Pages)

---

### 4. Session Workflow Integration

**File**: `~/.claude/session-decisions-end.sh`

**Change**: Add git staging for `docs/` folder

After the dashboard update section, add:
```bash
# Stage docs folder for GitHub Pages deployment
if [ -d "$GIT_DIR/docs" ]; then
    echo "📤 Staging docs folder for GitHub Pages..."
    git add docs/ 2>/dev/null || true
    echo "   ✅ docs/ folder staged"
fi
```

**Result**: Every session close automatically:
1. Runs `update_dashboard.py` (updates docs/index.html)
2. Stages `docs/` folder for commit
3. Commits changes
4. When you push, GitHub Pages auto-publishes

---

### 5. Documentation: docs/README.md

**Location**: `C:\Users\user\projects\personal\docs\README.md`

**Content**:
```markdown
# Mission Control Dashboard

Live status dashboard for Ibe's autonomous AI projects.

## Quick Access

📱 **Mobile Link**: [Copy this URL to your phone]
https://github.com/username/projects/personal/docs/

🖥️ **Desktop**: Same URL, works on any browser

## What You're Looking At

- **Vision**: Building a 24/7 autonomous organization
- **Systems Running**: Emy AI, Trade-Alerts, Scalp-Engine
- **Agents Active**: 6 autonomous agents (Trading, Knowledge, Research, Gemini, Analysis, Monitor)
- **Projects**: 8 active projects with status, phases, next milestones
- **Priorities**: Current session priorities with completion tracking
- **System Health**: Real-time status of all components (green/amber/red)

## How This Updates

Dashboard updates when you close your working session (run `/close-session`):
- Captures all decisions and updates status
- Regenerates dashboard HTML
- Commits to git
- GitHub Pages auto-publishes (within 1 minute)

**Last updated**: See timestamp in dashboard header
**Update frequency**: Typically 1-2x per day (when you close sessions)

## Embedding This Dashboard

You can embed this dashboard in documentation, wikis, or other sites:

```html
<iframe src="https://github.com/username/projects/personal/docs/"
        width="100%"
        height="800"
        frameborder="0"></iframe>
```

## Features

- ✅ Live clock (updates every second)
- ✅ Expandable project cards (click to see full details)
- ✅ Filterable projects (All / Live / Ready / Pending / Disabled)
- ✅ System status indicators (green = operational, amber = warning, red = offline)
- ✅ Priority tracking with completion status
- ✅ Responsive design (works on desktop, tablet, mobile)

## Questions?

For full project documentation, see the main [README](../README.md) or [CLAUDE.md](../CLAUDE.md).
```

---

### 6. Mobile Access via QR Code (Optional Enhancement)

**Purpose**: Make it easy to scan and open dashboard on phone

**Implementation**:
1. Use online QR code generator (e.g., qr-server.com)
2. Generate QR code pointing to: `https://github.com/username/projects/personal/docs/`
3. Add to docs/README.md:
   ```markdown
   📱 **Scan to open on your phone**:
   ![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://github.com/username/projects/personal/docs/)
   ```

**Result**: Users can scan QR code in README and instantly access dashboard on phone

---

## Error Handling & Edge Cases

| Scenario | How Handled |
|----------|-------------|
| `docs/` folder doesn't exist on first run | `Python script creates it automatically (mkdir -p)` |
| User opens GitHub Pages on mobile | Responsive design works (already built in mission_control.html) |
| Dashboard data is 2 hours old | "Updated" timestamp shows when it was last generated |
| User embeds in iframe | Self-contained HTML works (no CORS issues, no data fetching) |
| GitHub Pages takes time to publish | Documented in README (typically 1 minute, users can refresh) |
| `git add docs/` fails | Error is caught by `2>/dev/null \|\| true`, doesn't break workflow |

---

## Testing Checklist

Before considering deployment complete:

- [ ] `update_dashboard.py` successfully writes to both `mission_control.html` and `docs/index.html`
- [ ] `docs/index.html` is properly formatted HTML (open locally to verify styling)
- [ ] "Updated" timestamp displays correctly in header
- [ ] GitHub Pages is enabled (Settings → Pages shows correct source)
- [ ] First git push includes `docs/` folder
- [ ] GitHub Pages dashboard is live at GitHub URL (wait ~1 minute after push)
- [ ] Dashboard is responsive on mobile (test in browser device mode)
- [ ] Can view dashboard from different network/device (not just localhost)
- [ ] Embedding works (test iframe in separate HTML file)
- [ ] QR code in docs/README.md works on phone

---

## Rollback Plan

If anything goes wrong:

1. Delete `docs/` folder from local repo
2. Run `git rm -r docs/`
3. Commit and push
4. Go to Settings → Pages, change source to "None"

Everything reverts. The local `mission_control.html` still works as before.

---

## Timeline & Effort

| Task | Time | Effort |
|------|------|--------|
| Modify update_dashboard.py | 5 min | Trivial |
| Add HTML "Updated" display | 5 min | Trivial |
| Create docs/README.md | 5 min | Trivial |
| Modify session-decisions-end.sh | 2 min | Trivial |
| Enable GitHub Pages (one-time) | 1 min | Trivial |
| Test & verify | 2 min | Trivial |
| **Total** | **~20 min** | **Low** |

---

## Success Criteria (Post-Implementation)

✅ Dashboard accessible via GitHub Pages URL from phone
✅ "Last Updated" timestamp visible and accurate
✅ Updates automatically at each session close
✅ Can be embedded in documentation
✅ Works on mobile (responsive)
✅ Zero maintenance overhead

---

## Next Steps

1. ✅ Design approved (this document)
2. → Create detailed implementation plan (writing-plans skill)
3. → Execute implementation
4. → Test & verify
5. → Commit to git

---

**Design Document**: Approved and ready for implementation
**Author**: Claude Haiku 4.5
**Date**: March 15, 2026, 3:15 PM EDT
