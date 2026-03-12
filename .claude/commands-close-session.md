## AUTO-CAPTURE SESSION DECISIONS

Before closing this session, run the SESSION_DECISIONS_SYSTEM auto-capture:

```bash
bash ~/.claude/session-decisions-end.sh
```

This will automatically:
- 💾 Capture all decisions made this session
- 📅 Create timestamped decision file
- 📦 Back up to JSON format
- 🔄 Update DECISION_INDEX.md
- 📝 Commit to git for version control

Then help me document and save all work:

1. **Session Summary**: Create or update CLAUDE_SESSION_LOG.md with:
   - Session date and time
   - What we worked on (main tasks/issues)
   - What was tried (approaches, commands, solutions)
   - What worked and what didn't
   - Current status (completed, in-progress, blocked)
   - Next steps for the next session
   - Any important decisions or discoveries

2. **Update Project Files**:
   - Check if CLAUDE.md needs updates based on this session
   - Check if any new patterns or rules should be documented
   - Update any relevant config files if we learned something new

3. **Git Commit**:
   - Stage all relevant changes: `git add .`
   - Create a descriptive commit message based on what we accomplished
   - Show me the commit message before committing
   - After I approve, commit with: `git commit -m "[message]"`
   - Remind me to push if I want to: `git push`

4. **Session Checklist**:
   - [ ] All code changes saved
   - [ ] CLAUDE_SESSION_LOG.md updated
   - [ ] CLAUDE.md updated if needed
   - [ ] Config files updated if needed
   - [ ] Git changes committed
   - [ ] Next steps documented

5. **Final Summary**:
   Show me:
   - What files were modified
   - What was committed to git
   - What's ready for next session
   - Any urgent todos for next time

Execute all steps and confirm when the session is properly closed out.
