# GEMINI.md - Personal Portfolio & Trading Systems Hub

This directory is a **Portfolio-level repository** that coordinates a collection of independent software projects, primarily focused on AI-powered trading systems and job search automation.

## 🏗️ Architecture & Structure

The workspace follows a **Multi-repo architecture with portfolio-level coordination**, as documented in `PORTFOLIO_STRUCTURE.md`.

- **Root (`personal/`)**: Tracks cross-project decisions, session logs, and coordination notes.
- **Sub-repositories**: Independent projects (e.g., `Trade-Alerts`, `job-search`) with their own `.git` directories.
- **Monorepos**: Some projects are being consolidated (e.g., `trading-systems-monorepo` combining `Fx-engine` and `first-monitor`).

### Key Directories

| Category | Directories |
| :--- | :--- |
| **Trading Systems** | `Trade-Alerts`, `Scalp-Engine`, `Fx-engine`, `first-monitor`, `Assets`, `Forex`, `trading-systems-monorepo` |
| **Job Search** | `job-search`, `Indeed-jobs`, `Linkedin-jobs`, `job_alerts`, `Job_evaluation`, `recruiter_email_automation` |
| **AI Agents** | `agent-project` (Multi-agent ecosystem), `sentiment-monitor-git` |
| **Utilities** | Root scripts (`BackupRenderLogs.ps1`, `gmail_summarizer.py`, `summarize_eml.py`) |

## 🛠️ Development Workflow

### Session Management
The project uses a persistent memory pattern via **Session Logs**:
- `CLAUDE_SESSION_LOG.md` (Root): Documents cross-project work and portfolio decisions.
- `[project]/CLAUDE_SESSION_LOG.md`: Documents project-specific technical decisions and changes.

### Common Commands (PowerShell)
Many root-level tasks are automated with PowerShell scripts:
- **Backup**: `.\RunBackupRenderLogs.ps1` (Executes `BackupRenderLogs.ps1`)
- **Monorepo Management**: `.\create_monorepo.ps1`
- **Job Search**: `python open_job_links.py`, `python gmail_summarizer.py`

## 📈 Trading Systems Overview
Refer to `COMPREHENSIVE_TRADING_SYSTEMS_DOCUMENTATION.md` for full details.

1.  **Trade-Alerts**: AI-powered macro analysis using multiple LLMs.
2.  **Scalp-Engine**: Real-time high-speed execution via OANDA API.
3.  **Fx-Engine**: Institutional-grade decision engine (Python/Streamlit).
4.  **First-Monitor**: Economic first-principles monitoring and dislocation detection.
5.  **Assets/Forex**: Multi-asset trend and news tracking with correlation analysis.

## 🤖 AI Agent Ecosystem (`agent-project`)
A multi-agent system featuring:
- **Primary Agent**: Coordinator & Task Delegation.
- **Sub-Agents**: Research, Analysis, Writing, and Quality Control.

## 📝 Usage Guidelines for Gemini CLI

1.  **Consult the Logs**: Always check `CLAUDE_SESSION_LOG.md` at the root and in the relevant sub-project before starting work to understand the current state.
2.  **Respect the Boundaries**: When working in a sub-project (like `Trade-Alerts`), ensure commits are made within that sub-repo, not just at the root.
3.  **Python Environments**: A root `.venv` exists, but sub-projects often have their own `requirements.txt` and environments. Verify the correct environment before running scripts.
4.  **Deployment**: Many systems are designed for **Render**. Check `render.yaml` files in sub-directories or the root `trading-systems-monorepo-render.yaml` for deployment specs.

---
*Last Updated: March 3, 2026*

## 📓 Session Log: March 3, 2026

### **Session Summary**
Conducted a deep-dive consistency review between **Trade-Alerts**, **Scalp-Engine**, and **Oanda** using manual logs from the user's desktop. Identified critical technical debt and bugs preventing proper trailing stop execution.

### **Key Technical Findings**
1.  **API Bug (auto_trader_core.py)**: The `update_stop_loss` method uses the wrong OANDA endpoint (`TradeClientExtensions`), which updates metadata but not the actual SL order. This must be changed to `TradeOrders`.
2.  **Sync Bug (PositionManager)**: `sync_with_oanda()` fails to match filled pending orders because it only checks by `trade_id`. Pending orders in memory have `trade_id = None`. Matching logic needs to include **Pair + Direction**.
3.  **Performance Issue**: Order "chattering" (excessive replacements) is caused by a low `REPLACE_ENTRY_MIN_PIPS` threshold (5 pips).

### **Actions Taken**
-   Initialized `GEMINI.md` with portfolio architecture.
-   Imported 207 manual log files to `manual_logs/`.
-   Performed logic mapping in `auto_trader_core.py` and `scalp_engine.py`.
-   Created `gemini-suggestions1.md` with the full bug report and fix plan.
-   Established the `session-manager` skill protocol for context persistence.

### **Next Steps**
-   [ ] **Fix API Endpoint**: Update `auto_trader_core.py` (L551-620) to use `TradeOrders` for SL/Trailing Stop updates.
-   [ ] **Patch Sync Logic**: Implement two-stage matching (Trade ID -> Pair/Direction) in `PositionManager.sync_with_oanda()`.
-   [ ] **Stabilize Orders**: Increase `REPLACE_ENTRY_MIN_PIPS` to 10 or 15.
-   [ ] **Clean up**: Review and potentially remove the `manual_logs/` folder once fixes are verified.

