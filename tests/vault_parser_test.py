import sys
sys.path.insert(0, r'C:\Users\user\.claude\scripts')
from vault_parser import parse_session_log_section, extract_project_status

def test_parse_session_overview():
    """Should extract session overview from log"""
    log_content = """
## Current Session Status

### Trade-Alerts System State
- ✅ New Google Drive OAuth credentials created (Trade-Alerts-OAuth app)
- ✅ Trade-Alerts running on Render in AUTO mode (continuous since Mar 9)

### PHASE 1: Verify Stop Loss & Take Profit
**Status**: 🟡 TESTING COMPLETE — AWAITING ANALYSIS
"""

    sections = parse_session_log_section(log_content, "## Current Session Status")
    assert sections is not None
    assert "Trade-Alerts System State" in sections
    assert "PHASE 1" in sections

def test_extract_project_status():
    """Should extract status, blockers, next milestone from project log"""
    log_content = """
## Status
- Phase: Phase 1 Testing
- Last updated: 2026-03-09

## Current Blockers
- Manual close rate still at 80% (need to reduce)
- Need to analyze P1 test logs

## Next Milestone
- Review all Phase 1 logs and publish findings
"""

    status = extract_project_status(log_content)

    assert status["phase"] == "Phase 1 Testing"
    assert status["last_updated"] == "2026-03-09"
    assert "Manual close rate" in status["blockers"]
    assert "Review all Phase 1 logs" in status["next_milestone"]

def test_format_markdown_link():
    """Should format wiki-links correctly"""
    from vault_parser import format_wiki_link

    link = format_wiki_link("Trade-Alerts")
    assert link == "[[Trade-Alerts]]"

def test_sanitize_filename():
    """Should convert text to safe filename"""
    from vault_parser import sanitize_filename

    # Test with special characters
    result = sanitize_filename("Trade-Alerts — Phase 1 (Testing)")
    assert result == "Trade-Alerts_Phase_1_Testing"
