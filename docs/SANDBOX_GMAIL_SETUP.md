# Sandbox Gmail Account Setup Guide

## Objective

Create and configure a sandbox Gmail account (`emy.test@gmail.com`) for integration testing of email workflows without affecting production systems.

## Setup Steps

### Step 1: Create Sandbox Gmail Account

1. Go to [Google Accounts - Sign Up](https://accounts.google.com/signup)
2. Create a new account with:
   - **Email**: `emy.test@gmail.com`
   - **Password**: [Strong password - store securely in password manager]
   - **Recovery Email**: [Your personal email address]
   - **Phone**: [Optional but recommended]

3. Verify the account and complete security setup

### Step 2: Enable Gmail API Access

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or use existing project
3. Enable Gmail API:
   - Search for "Gmail API" in the API Library
   - Click "Enable"
4. Create OAuth2 Service Account (same as production):
   - Go to "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Fill in service account details
   - Create key as JSON
   - Download and save the JSON file securely

### Step 3: Grant Service Account Access to Sandbox Email

1. Go to [Google Workspace Admin Console](https://admin.google.com/)
2. In "Security" → "API controls":
   - Select "Domain-wide delegation"
   - Add the service account client ID
   - Grant required scopes:
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/gmail.readonly`

3. Alternatively, enable "Less secure app access" on the sandbox account:
   - Sign in to `emy.test@gmail.com`
   - Go to [myaccount.google.com/security](https://myaccount.google.com/security)
   - Enable "Less secure app access"

### Step 4: Configure Environment Variables

Add to your `.env` file:

```bash
# Sandbox Gmail Configuration
SANDBOX_ENABLED=true
SANDBOX_EMAIL=emy.test@gmail.com
SANDBOX_SERVICE_ACCOUNT_JSON=/path/to/service-account-key.json

# Or if using the same credentials as production:
GMAIL_CREDENTIALS_JSON=<json-credentials-from-step-2>
```

**Security Note**: Never commit credentials to git. Store in:
- `.env` file (git-ignored)
- Environment variables (CI/CD)
- Secure credential vault

### Step 5: Verify Configuration

Run the configuration test:

```bash
# Check if sandbox is properly configured
python -c "from emy.config.test_config import SandboxConfig; print(f'Configured: {SandboxConfig.is_configured()}')"
```

Expected output: `Configured: True`

## Running Sandbox Tests

### Run All Sandbox Tests

```bash
# Run all sandbox Gmail integration tests
pytest emy/tests/test_email_sandbox_integration.py -v

# Run specific test
pytest emy/tests/test_email_sandbox_integration.py::TestEmailSandboxIntegration::test_sandbox_send_email_to_test_account -v

# Run with output
pytest emy/tests/test_email_sandbox_integration.py -v -s
```

### Expected Test Behavior

All tests will be **SKIPPED** if sandbox is not configured:

```
test_email_sandbox_integration.py::TestEmailSandboxIntegration::test_sandbox_send_email_to_test_account SKIPPED
  Sandbox Gmail not configured (set SANDBOX_EMAIL and SANDBOX_SERVICE_ACCOUNT_JSON)
```

Once configured, tests will run and verify:

✅ **test_sandbox_send_email_to_test_account**
- Send test email to sandbox account
- Verify successful delivery

✅ **test_sandbox_parse_received_email**
- Retrieve unread emails from sandbox inbox
- Verify parsing succeeds

✅ **test_sandbox_intent_classification**
- Test intent detection on sample emails
- Verify 'research' intent correctly identified

✅ **test_sandbox_intent_question_classification**
- Test question intent classification
- Verify 'question' intent correctly identified

✅ **test_sandbox_end_to_end_workflow**
- Send email to sandbox
- Parse received email
- Classify intent
- Generate and verify response

✅ **test_sandbox_polling_and_classification_loop**
- Poll inbox for unread emails
- Parse each email
- Classify intent for each

✅ **test_sandbox_config_validation**
- Verify sandbox config is set correctly
- Verify environment variables present

✅ **TestEmailSandboxErrorHandling**
- Test graceful error handling
- Verify invalid emails rejected
- Verify large emails processed
- Verify empty fields handled

✅ **TestEmailSandboxIntegrationWithMocks**
- Test response generation with mocks
- Test agent interaction with mocks
- Verify end-to-end flow without API calls

## Monitoring & Troubleshooting

### Check Sandbox Inbox

Sign in to `emy.test@gmail.com` and verify emails are arriving.

### Common Issues

**Issue**: Tests skip with "Sandbox Gmail not configured"

**Solution**:
```bash
# Verify environment variables
echo $SANDBOX_EMAIL
echo $SANDBOX_SERVICE_ACCOUNT_JSON

# Set manually if needed
export SANDBOX_EMAIL=emy.test@gmail.com
export SANDBOX_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
export SANDBOX_ENABLED=true
```

**Issue**: "Gmail service not initialized" error

**Solution**:
- Verify credentials JSON is valid
- Check that service account has Gmail API scope
- Verify Gmail API is enabled in Google Cloud Console
- Check that credentials aren't expired

**Issue**: 401 Authorization errors

**Solution**:
- Verify service account has domain-wide delegation enabled
- Check that scopes include `gmail.send` and `gmail.readonly`
- Verify credentials are for correct Google Cloud project
- Check that `emy.test@gmail.com` has access to service account

### View Logs

```bash
# Enable debug logging
export LOGLEVEL=DEBUG
pytest emy/tests/test_email_sandbox_integration.py -v -s --log-cli-level=DEBUG
```

### Test Quota & Limits

**Gmail API Quotas** (per 100 seconds):
- Send: 2 requests per user
- Get: Unlimited (for testing, ~1000 per day practical limit)
- List: Unlimited (but reasonable usage)

**Recommendations**:
- Run tests during off-peak hours for shared credentials
- Don't run all tests in parallel (use `-n 1` with pytest-xdist)
- Monitor quota usage in Google Cloud Console
- Rotate credentials every 90 days

## Security Best Practices

✅ **DO**:
- Store credentials in `.env` (git-ignored) or secure vault
- Use service account credentials (not personal account)
- Rotate credentials every 90 days
- Review API access logs regularly
- Use separate sandbox account from production

❌ **DON'T**:
- Commit credentials to git
- Share credentials across teams
- Use personal email account for testing
- Leave test emails in sandbox inbox indefinitely
- Enable "Less secure app access" in production

## Cleaning Up

### Archive Old Test Emails

Periodically clean the sandbox inbox to avoid quota issues:

```bash
# Sign in to emy.test@gmail.com and delete old emails
# Or use Gmail API to delete:
python -c "from emy.tools.email_parser import EmailParser; parser = EmailParser(); emails = parser.check_inbox(); print(f'Unread: {len(emails)}')"
```

### Disable Sandbox (if needed)

Set environment variable:
```bash
export SANDBOX_ENABLED=false
```

Tests will automatically skip.

## Integration with CI/CD

### GitHub Actions Example

```yaml
env:
  SANDBOX_ENABLED: true
  SANDBOX_EMAIL: emy.test@gmail.com
  SANDBOX_SERVICE_ACCOUNT_JSON: ${{ secrets.SANDBOX_CREDENTIALS }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest emy/tests/test_email_sandbox_integration.py -v
```

### Local Testing

```bash
# Set credentials locally
export SANDBOX_EMAIL=emy.test@gmail.com
export SANDBOX_SERVICE_ACCOUNT_JSON=$(cat /path/to/creds.json)
export SANDBOX_ENABLED=true

# Run tests
pytest emy/tests/test_email_sandbox_integration.py -v
```

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api/guides)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Service Account Setup](https://cloud.google.com/docs/authentication/getting-started)
- [Gmail API Python Library](https://github.com/googleapis/google-api-python-client)

---

**Last Updated**: 2026-03-15
**Status**: Implementation Ready
