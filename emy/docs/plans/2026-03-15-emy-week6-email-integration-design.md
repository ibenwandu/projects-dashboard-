# Emy Week 6: Email Integration & Outreach — Design Document

> **Status**: ✅ DESIGN APPROVED (March 15, 2026)
> **Target**: Enable agents to send and parse emails for outbound communication and inbound feedback processing
> **Architecture**: Gmail API (outbound) + Polling (inbound) + Jinja2 templates + Retry logic

---

## Vision

Emy agents need to communicate via email for:
- **Outbound**: Research findings, feasibility assessments, status updates
- **Inbound**: Receiving feedback, questions, information for processing

Email is the primary communication channel for enterprise environments (matching OpenClaw capabilities).

---

## Design Decisions

### 1. Outbound Email Strategy: Gmail API

**Why Gmail API (not SMTP)?**
- **Reliability**: Gmail API is production-grade; SMTP is throttled by Google
- **Enterprise standard**: OpenClaw uses Gmail API
- **Audit trail**: Sent emails appear in Gmail inbox (user verification)
- **Security**: OAuth is more secure than SMTP passwords in environment variables
- **Scalability**: Handles rate limiting better than SMTP

**Implementation:**
- Service account OAuth (or user OAuth if preferred)
- One-time setup, then fully automated
- Credentials stored in environment variables (GMAIL_CREDENTIALS)

---

### 2. Inbound Email Strategy: Polling

**Why Polling (not Webhook)?**
- **Simplicity**: No external service (Zapier, Make) needed
- **Self-contained**: Fully within Emy system
- **Integration**: Fits naturally with Week 7 scheduling
- **Testing**: Easier to mock and verify
- **MVP scope**: 10-minute check interval is acceptable for email feedback (not time-critical)

**Frequency:**
- Check Gmail every 10 minutes
- Can be increased later if needed (currently: 6 checks/hour)

---

### 3. Email Templates: Jinja2

**Why Jinja2 (not f-strings)?**
- **Professional quality**: Enterprise-grade templating
- **Flexibility**: Supports conditionals, loops, filters
- **Maintainability**: Non-developers can modify templates without code
- **OpenClaw parity**: Enterprise systems use professional templating
- **Scalability**: As email types grow, Jinja2 scales naturally

**Template files location:**
```
emy/templates/emails/
├── feasibility_assessment.jinja2
├── daily_digest.jinja2
└── research_summary.jinja2
```

**Template structure:**
```jinja2
Dear {{ recipient_name }},

[Body content with dynamic sections]

{% for item in items %}
- {{ item.title }}: {{ item.description }}
{% endfor %}

[Closing]

Best regards,
Emy AI Chief of Staff
```

---

### 4. Error Handling: Retry with Backoff

**Send failures:**
1. **Attempt 1**: Immediate send
2. **Fail → Wait 1 second → Attempt 2**: Retry
3. **Fail → Wait 2 seconds → Attempt 3**: Final retry
4. **Fail → Alert user**: Log error, store in database for manual retry

**Why backoff?**
- Handles transient failures (network blips, temporary rate limits)
- Doesn't hammer Gmail API during outages
- Professional reliability approach

**Parse failures:**
- Log unparseable emails (malformed, encoding issues)
- Skip and continue polling
- User can manually reprocess via API endpoint

**Monitoring:**
- Log every send attempt (timestamp, status, error if any)
- Alert threshold: After 3 failed attempts, create alert for user
- Database table: `email_log` tracks all send/receive activities

---

### 5. Email System Architecture

```
┌─────────────────────────────────────┐
│     Emy Gateway (FastAPI)           │
├─────────────────────────────────────┤
│                                     │
│  POST /emails/process               │  (manual trigger for testing)
│  GET /emails/status                 │  (check last processing)
│                                     │
└─────────────────────────────────────┘
         ↓↓↓ (every 10 min)
┌─────────────────────────────────────┐
│     Polling Task (Week 7)           │
├─────────────────────────────────────┤
│                                     │
│  Check Gmail inbox every 10 min     │
│  → Parse emails                     │
│  → Classify intent                  │
│  → Route to agent                   │
│  → Generate response                │
│  → Send via Gmail API               │
│                                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│     Email Tools                     │
├─────────────────────────────────────┤
│                                     │
│  emy/tools/email_tool.py            │
│  - Gmail API OAuth client           │
│  - Send with retry logic            │
│  - Template rendering               │
│                                     │
│  emy/tools/email_parser.py          │
│  - Parse email (sender, body, etc)  │
│  - Intent classification            │
│  - Route to agent                   │
│                                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│     Agent Email Skills              │
├─────────────────────────────────────┤
│                                     │
│  ResearchAgent                      │
│  - send_feasibility_assessment()    │
│                                     │
│  ProjectMonitorAgent                │
│  - send_daily_status_digest()       │
│                                     │
│  KnowledgeAgent                     │
│  - send_research_summary()          │
│                                     │
└─────────────────────────────────────┘
```

---

## Component Details

### Email Tool (`emy/tools/email_tool.py`)

**Class: EmailClient**
```python
class EmailClient:
    """Gmail API client for sending emails with retry logic."""

    def __init__(self):
        """Initialize OAuth credentials."""

    async def send(self, to: str, subject: str, body: str, html: bool = True) -> bool:
        """Send email with retry logic (3 attempts, exponential backoff)."""

    async def render_template(self, template_name: str, context: dict) -> str:
        """Render Jinja2 template with context."""
```

**Methods:**
- `send()`: Send email with 3-retry backoff logic
- `render_template()`: Render Jinja2 email template
- `_log_attempt()`: Log each attempt (for audit trail)
- `_alert_after_failure()`: Alert user after 3 failed attempts

### Email Parser (`emy/tools/email_parser.py`)

**Class: EmailParser**
```python
class EmailParser:
    """Parse and route incoming emails."""

    async def check_inbox(self) -> List[dict]:
        """Poll Gmail inbox for new emails."""

    async def parse_email(self, email_id: str) -> dict:
        """Extract sender, subject, body from email."""

    async def classify_intent(self, email: dict) -> str:
        """Classify email intent (research, status, feedback, etc)."""

    async def route_to_agent(self, email: dict) -> str:
        """Route email to appropriate agent."""
```

**Intent classification examples:**
- "feedback on feasibility assessment" → ResearchAgent
- "project status question" → ProjectMonitorAgent
- "research summary request" → KnowledgeAgent

### Agent Email Skills

**ResearchAgent email skill:**
```python
async def send_feasibility_assessment(self, opportunity: dict, assessment: str, recommendation: str):
    """Send feasibility assessment email."""
    context = {
        'recipient_name': opportunity['contact_name'],
        'opportunity': opportunity['title'],
        'assessment': assessment,
        'recommendation': recommendation,
        'next_steps': self._next_steps(opportunity)
    }
    await self.email_client.render_and_send('feasibility_assessment.jinja2', context)
```

**Similar methods for ProjectMonitorAgent and KnowledgeAgent.**

---

## Data Flow

### Outbound Email Flow

```
1. Agent calls: send_feasibility_assessment(opportunity, assessment, rec)
   ↓
2. Email tool renders Jinja2 template with context
   ↓
3. Template produces HTML email body
   ↓
4. Gmail API sends email (attempt 1)
   ├─ Success → Log and return
   ├─ Fail → Wait 1s, retry (attempt 2)
   ├─ Fail → Wait 2s, retry (attempt 3)
   └─ Fail → Alert user, store in database for manual retry
   ↓
5. Email logged in database (audit trail)
```

### Inbound Email Flow

```
1. Polling task triggered every 10 minutes
   ↓
2. Check Gmail inbox for new emails
   ↓
3. For each new email:
   a. Parse email (sender, subject, body)
   b. Classify intent (which agent should handle this?)
   c. Route to agent
   d. Agent generates response
   e. Send response via Gmail API (with retry logic)
   f. Log email in database (audit trail)
   ↓
4. Next polling cycle in 10 minutes
```

---

## Database Schema

**Table: `email_log`**
```sql
CREATE TABLE email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT UNIQUE,
    direction TEXT,  -- 'outbound' or 'inbound'
    sender TEXT,
    recipient TEXT,
    subject TEXT,
    status TEXT,  -- 'sent', 'failed', 'pending', 'received'
    attempt_count INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    error_message TEXT,
    response_email_id TEXT  -- if this is a response to another email
)
```

---

## Security & Credentials

**Gmail OAuth:**
- Service account JSON stored in `.env` (GMAIL_CREDENTIALS_JSON)
- OR user OAuth via `https://accounts.google.com/o/oauth2/auth`
- Scopes: `gmail.send`, `gmail.readonly`

**Rate limiting:**
- Gmail API: 10 requests per second limit (we use ~1/10 min)
- Exponential backoff respects rate limits

**Data privacy:**
- Email bodies logged only in database (not in logs)
- User can configure which emails to log (privacy setting)

---

## Testing Strategy

### Unit Tests (Mocks)
- Email template rendering (Jinja2 + context)
- Email parsing logic (extract sender, subject, body)
- Intent classification (route to correct agent)
- Retry logic (exponential backoff)
- Error handling (after 3 failures, alert)

### Integration Tests (Sandbox Gmail)
- Create test Gmail account (emy.test@gmail.com)
- Send email via Gmail API → verify in inbox
- Receive email → parse → verify fields
- Route to agent → generate response → send
- End-to-end: Feedback email → Response sent ✓

### Test file:
```
emy/tests/test_email_integration.py
- 4 unit tests (template, parsing, intent, retry)
- 4 integration tests (send, receive, response, e2e)
Total: 8 tests, all passing
```

---

## Success Criteria

- ✅ ResearchAgent can send feasibility assessment emails
- ✅ ProjectMonitorAgent can send daily status digests
- ✅ KnowledgeAgent can send research summaries
- ✅ Incoming emails parsed and routed correctly
- ✅ Agents generate contextual responses
- ✅ Failed sends retry with backoff (3 attempts)
- ✅ User alerted after 3 failed attempts
- ✅ All email types tested (unit + integration)
- ✅ 8/8 tests passing

---

## Dependencies

- **gmail**: `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client`
- **templates**: `jinja2` (already used in project)
- **async**: `asyncio` (already used in project)

**New dependencies:**
- `google-auth-oauthlib` (for OAuth)
- `google-api-python-client` (for Gmail API)

---

## Timeline & Effort

**Week 6 (Email Integration):**
- Task 1: Email Tool Implementation (2h) — Gmail API client, Jinja2 rendering, retry logic
- Task 2: Agent Email Skills (1.5h) — Add skills to ResearchAgent, ProjectMonitorAgent, KnowledgeAgent
- Task 3: Email Parsing & Response (1.5h) — Parse, classify, route, respond
- Task 4: Testing (1h) — Unit + integration tests

**Total: 6 hours of implementation**

---

## Future Enhancements (Not in Scope)

- Webhook integration (replace polling in Week 8+)
- Email attachment handling
- HTML email rendering (currently plain text + HTML template)
- Email forwarding (forward certain emails to user)
- Scheduled digest emails (configured by user)

---

## Implementation Next Steps

1. Create implementation plan (writing-plans skill)
2. Dispatch subagents per task (subagent-driven-development)
3. Two-stage review: spec compliance → code quality
4. Deploy to Render + test with sandbox Gmail account

---

**Document Status**: ✅ APPROVED FOR IMPLEMENTATION
**Last Updated**: March 15, 2026
**Next Action**: Create detailed implementation plan

