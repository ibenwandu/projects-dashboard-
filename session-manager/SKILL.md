---
name: session-manager
description: Manages persistent session memory by saving and loading interaction logs to GEMINI.md. Use when the user wants to close a session (summarize and persist) or start a session (restore context from GEMINI.md).
---

# Session Manager

This skill implements a persistent memory pattern using the `GEMINI.md` file in the project root. It allows for seamless context transfer between different AI sessions.

## Workflows

### 1. Close Session (`/close-session`)
When the user requests to close the session, follow these steps:
1. **Summarize**: Create a concise summary of the key findings, technical decisions, and actions taken during this session.
2. **Identify Next Steps**: List any pending tasks or planned future actions.
3. **Persist**: Append the summary to `GEMINI.md` under a new section for the current date. 
4. **Clean up**: Ensure the `manual_logs` or other temporary workspaces are noted if they need to be kept or removed.

### 2. Start Session (`/start-session`)
When the user requests to start a session:
1. **Read Log**: Read the `GEMINI.md` file to understand the current state of the project and previous work.
2. **Restore Context**: Summarize the most recent session's state to ensure immediate readiness for the current task.
3. **Verify Environment**: Check if critical files mentioned in the logs are still present.

## Key Files
- `GEMINI.md`: The primary file for cross-session persistent memory.

## Guidelines
- **Brevity**: Keep summaries high-signal and technical. Avoid conversational filler.
- **Accuracy**: Ensure that trade-offs and "why" decisions are captured, not just "what" was done.
- **Git State**: Note if changes were committed or left in the working tree.
