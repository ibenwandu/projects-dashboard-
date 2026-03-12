# SESSION_DECISIONS_SYSTEM - Skill Integration Hooks

**Purpose**: Configure `start-session-root` and `close-session-root` skills to automatically load and capture session decisions

**Status**: INTEGRATION CONFIGURATION READY
**Date**: March 12, 2026

---

## How Skills Integration Works

The `start-session-root` and `close-session-root` skills can be configured to automatically execute our scripts by reading this integration file.

---

## START-SESSION-ROOT Hook

**Trigger**: At every session start via `start-session-root` skill

**What to Add**: After existing CLAUDE.md and session log loading, add:

```bash
# Auto-load session decisions
if [ -f "$HOME/.claude/session-decisions-start.sh" ]; then
    bash "$HOME/.claude/session-decisions-start.sh"
fi
```

**Or in Python**:
```python
import subprocess
import os

# Auto-load session decisions
start_script = os.path.expanduser('~/.claude/session-decisions-start.sh')
if os.path.exists(start_script):
    try:
        subprocess.run(['bash', start_script], check=False, timeout=10)
    except Exception as e:
        print(f"Warning: Could not load session decisions: {e}")
```

**Effect**: User automatically sees all prior decisions at session start

---

## CLOSE-SESSION-ROOT Hook

**Trigger**: When closing session via `close-session-root` skill

**What to Add**: After existing documentation and dashboard updates, add:

```bash
# Auto-capture session decisions
if [ -f "$HOME/.claude/session-decisions-end.sh" ]; then
    bash "$HOME/.claude/session-decisions-end.sh"
fi
```

**Or in Python**:
```python
import subprocess
import os
from datetime import datetime

# Auto-capture session decisions
end_script = os.path.expanduser('~/.claude/session-decisions-end.sh')
if os.path.exists(end_script):
    try:
        subprocess.run(['bash', end_script], check=False, timeout=30)
    except Exception as e:
        print(f"Warning: Could not capture session decisions: {e}")
```

**Effect**: Decisions automatically captured when session closes

---

## Integration Verification

After integration, verify with:

### Check 1: Session Start
```
Expected output at session start:
📋 SESSION DECISIONS & CONTEXT (Auto-Loaded)
🎯 DECISION INDEX & CRITICAL ITEMS:
[Shows prior decisions]
```

### Check 2: Session End
```
Expected output at session close:
💾 CAPTURING SESSION DECISIONS (Auto)
[OK] Session decisions captured: ...
[OK] JSON backup created: ...
```

### Check 3: Files Exist
```bash
ls ~/.claude/session-decisions/
# Should show timestamped decision files
```

---

## Configuration Files

### Primary Configuration
**File**: `~/.claude/session-decisions-config.json`
**Purpose**: Main configuration for the system
**Auto-read by**: Integration scripts

### Start-Session Integration
**File**: `~/.claude/session-decisions-start.sh`
**Purpose**: Display decisions at session start
**Executable**: Yes (chmod +x)
**Status**: Ready to run

### End-Session Integration
**File**: `~/.claude/session-decisions-end.sh`
**Purpose**: Capture decisions at session end
**Executable**: Yes (chmod +x)
**Status**: Ready to run

---

## Integration Checklist

- [ ] Add start-session hook to `start-session-root` skill
- [ ] Add end-session hook to `close-session-root` skill
- [ ] Test session start (verify auto-load works)
- [ ] Test session end (verify auto-capture works)
- [ ] Verify decision files created
- [ ] Verify next session shows loaded decisions
- [ ] Confirm zero manual recall needed

---

## Manual Testing (Until Integrated)

If skill integration isn't available yet, you can manually trigger:

### At Session Start
```bash
bash ~/.claude/session-decisions-start.sh
```

### At Session End
```bash
bash ~/.claude/session-decisions-end.sh
```

This will provide the same functionality as automatic skill integration.

---

**Status**: 🟢 READY FOR INTEGRATION
**Next**: Integrate hooks into skill system
**Timeline**: Can be integrated immediately

