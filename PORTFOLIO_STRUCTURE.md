# Personal Portfolio Structure

**Status**: ✅ Initialized February 22, 2026
**Architecture**: Multi-repo with portfolio-level coordination

---

## Repository Hierarchy

```
personal/                              ← MAIN REPO (Portfolio-level)
├── .git/                              ← Version control (root)
├── .gitignore                         ← Exclude nested repos
├── CLAUDE_SESSION_LOG.md              ← Cross-project session history
├── PORTFOLIO_STRUCTURE.md             ← This file
│
├── job-search/                        ← SUB-REPO (Independent)
│   ├── .git/                          ← Separate version control
│   ├── CLAUDE_SESSION_LOG.md          ← Project-specific history
│   ├── daily_workflow.py              ← Automation scripts
│   └── [project files...]
│
├── Trade-Alerts/                      ← SUB-REPO (Independent)
│   ├── .git/                          ← Separate version control
│   ├── CLAUDE_SESSION_LOG.md          ← Project-specific history
│   ├── scalp_engine.py                ← Trading system
│   └── [project files...]
│
└── [other directories...]             ← Not yet version controlled
```

---

## Version Control Strategy

### Personal (Root Repository)
- **Purpose**: Portfolio-level coordination and history
- **Tracks**: Session logs, cross-project decisions, coordination notes
- **Frequency**: Updated at end of each root-level session
- **Branch**: `master`
- **Initial Commit**: `3ed0987` (Feb 22, 2026)

### job-search (Sub-Repository)
- **Purpose**: Independent version control for job automation
- **Tracks**: All project-specific code, configs, and sessions
- **Frequency**: Commits as work is done
- **Branch**: `master`
- **Latest Commit**: `855e737` (Task Scheduler setup)

### Trade-Alerts (Sub-Repository)
- **Purpose**: Independent version control for trading system
- **Tracks**: All project-specific code, configs, and sessions
- **Frequency**: Commits as work is done
- **Branch**: `master`
- **Latest Commit**: `dd53d38` (Session 19)

---

## How It Works

### Root-Level Sessions
When working across projects:
1. Start session with `/start-session-root`
2. Review cross-project status from CLAUDE_SESSION_LOG.md files
3. Work on tasks (may touch multiple projects)
4. End session with `/close-session-root`
   - Updates `personal/CLAUDE_SESSION_LOG.md`
   - Updates each touched project's session log
   - Creates commit in `personal/` with portfolio summary
   - Shows summary dashboard

### Project-Level Sessions
When working within a project:
1. Start session with `/start-session`
2. Work on project tasks
3. End session with `/close-session`
   - Updates project's CLAUDE_SESSION_LOG.md
   - Creates commit in that project's repo
   - Documents decisions and learnings

### .gitignore Rules

**Excludes**:
- `job-search/.git/` ← Don't track nested repo
- `Trade-Alerts/.git/` ← Don't track nested repo

**Includes**:
- `job-search/**` ← Track all content
- `Trade-Alerts/**` ← Track all content

This prevents git from trying to manage nested repositories while still tracking all content.

---

## Session Log Organization

### Root Level (`personal/CLAUDE_SESSION_LOG.md`)
Documents:
- Cross-project work
- Portfolio-level decisions
- Project coordination
- Dependencies and patterns
- Overall progress

**Updated**: End of each root-level session

### Project Level (`project/CLAUDE_SESSION_LOG.md`)
Documents:
- Project-specific work
- Technical decisions
- Code changes and commits
- Learnings and patterns

**Updated**: End of each project-level session

---

## Example Workflow

### Scenario 1: Root-Level Session
```
Start: /start-session-root
  ↓
Review: personal/CLAUDE_SESSION_LOG.md
Review: job-search/CLAUDE_SESSION_LOG.md
Review: Trade-Alerts/CLAUDE_SESSION_LOG.md
  ↓
Work: Set up job-search automation
  ↓
Create commits: in job-search/ (2 commits)
  ↓
End: /close-session-root
  ↓
Action: Updates personal/CLAUDE_SESSION_LOG.md
Action: Updates job-search/CLAUDE_SESSION_LOG.md
Action: Creates commit in personal/ (portfolio-level)
```

### Scenario 2: Project-Level Session
```
Start: /start-session
  ↓
Work: Modify job-search code
  ↓
Create commits: in job-search/ (1+ commits)
  ↓
End: /close-session
  ↓
Action: Updates job-search/CLAUDE_SESSION_LOG.md
Action: Creates commit in job-search/
```

---

## Git Commands Reference

### View Portfolio History
```bash
cd personal
git log --oneline          # Portfolio commits
git log -p                 # With details
```

### View Project History
```bash
cd personal/job-search
git log --oneline          # Project commits
```

### Check What Will Commit
```bash
cd personal
git status                 # Staged files
git diff --cached          # What will be committed
```

### Multi-Project View
```bash
# From personal/ root
cd personal && git log --oneline
cd job-search && git log --oneline
cd ../Trade-Alerts && git log --oneline
```

---

## Benefits of This Structure

✅ **Portfolio-Level Memory**
- Central location for cross-project decisions
- Full history of how projects evolved together
- Easy to see portfolio progress

✅ **Project Independence**
- Each project can move at its own pace
- Independent version control histories
- No conflicts between project repos

✅ **Clear Coordination Trail**
- Root session logs document dependencies
- Easy to understand interactions
- Searchable history of decisions

✅ **Persistent Knowledge**
- Session logs are version controlled
- Full audit trail of work
- Accessible from any future session

---

## Future Additions

As new projects are created, add them following the same pattern:
```bash
cd /path/to/new-project
git init
# Create .git, CLAUDE_SESSION_LOG.md, etc.
git add .
git commit -m "Initialize project-level repository"
```

Then reference them in `personal/CLAUDE_SESSION_LOG.md` for cross-project tracking.

---

## Key Principles

1. **Persistent Memory**: All significant work is documented and version controlled
2. **Clear Ownership**: Root tracks portfolio, projects track themselves
3. **Independent Progress**: Projects can evolve independently
4. **Searchable History**: Git log provides full audit trail
5. **Sustainable**: Easy to continue sessions and understand prior work

---

**Initialized**: February 22, 2026
**Status**: ✅ Operational and ready for use
