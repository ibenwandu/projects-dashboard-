# Emy Shared Modules

Reusable modules copied from Trade-Alerts (pinned to known-good versions).

## Module Sources

| Module | Source | Last Updated | Purpose |
|--------|--------|--------------|---------|
| `audit_logger.py` | `Trade-Alerts/agents/shared/audit_logger.py` | Feb 26, 2026 | Event audit logging |
| `pushover_notifier.py` | `Trade-Alerts/agents/shared/pushover_notifier.py` | Feb 26, 2026 | Push notifications via Pushover |

## Usage

```python
from emy.shared.audit_logger import AuditLogger
from emy.shared.pushover_notifier import PushoverNotifier

# Audit logging
audit = AuditLogger('agent_name')
audit.log_event('action', {'data': 'value'})

# Notifications
notifier = PushoverNotifier(api_token, user_key)
notifier.send('title', 'message', priority=1)
```

## Maintenance

When updating Trade-Alerts shared modules:
1. Review changes in Trade-Alerts/agents/shared/
2. If breaking changes: copy new version + update this README
3. If compatible: copy new version (no breaking changes expected)
4. Test with existing code after updating
5. Document version/date in table above
