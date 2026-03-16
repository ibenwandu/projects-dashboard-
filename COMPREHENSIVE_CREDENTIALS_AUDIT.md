# Comprehensive Credentials Audit & Remediation Plan
**Date**: March 16, 2026
**Status**: 🔴 COMPROMISED - REMEDIATION IN PROGRESS

---

## Executive Summary

**Three platforms have compromised credentials:**
1. **ChatGPT (OpenAI)** — "My cursor project" (sk-pro...L4A)
2. **Anthropic** — Two keys exposed:
   - Primary: Emy-Anthropic-Key (sk-ant-api03-XPz...fAAA)
   - Secondary: My email summary (sk-ant-api03-m0P...MAAA)
3. **Google OAuth2** — Full OAuth2 credentials with client_id/secret

---

## PLATFORM 1: ChatGPT / OpenAI API

### Compromised Details
- **Service**: Cursor "My cursor project"
- **Key Format**: sk-pro...L4A (partial view)
- **Exposure**: Git history + potentially Render environment
- **Status**: 🔴 COMPROMISED

### Active Usage Locations
| Location | Component | Type | Notes |
|----------|-----------|------|-------|
| **Trade-Alerts** | Main Trade-Alerts service | Render env var | PRIMARY DEPLOYMENT |
| Local machine | Development/testing | .env file | If present |
| Backup folders | Various backup versions | Git history | Multiple backups contain references |

### Files to Update
- `Trade-Alerts` Render service environment variables
- `.env` file (local machine) - if contains OpenAI key
- Any documentation with hardcoded references

### Rotation Steps (See Section: Step-by-Step Credential Generation)

---

## PLATFORM 2: Anthropic API

### Compromised Details - PRIMARY KEY
- **Key Name**: Emy-Anthropic-Key
- **Key ID**: 312eb107-a105-420e-9598-826c06884026
- **Key Hint**: sk-ant-api03-XPz...fAAA
- **Exposure**: Git history + Render environment variables
- **Status**: 🔴 COMPROMISED

### Compromised Details - SECONDARY KEY
- **Key Name**: My email summary
- **Key ID**: 679fca02-aa38-451b-996c-87d314cb7800
- **Key Hint**: sk-ant-api03-m0P...MAAA
- **Exposure**: Git history + potentially Render environment
- **Status**: 🔴 COMPROMISED

### Active Usage Locations
| Location | Component | Service Type | Environment Variable(s) |
|----------|-----------|--------------|-------------------------|
| **Emy-Phase1a** | Primary Emy service | Render service | ANTHROPIC_API_KEY |
| **Emy-Brain** | Brain component | Render service | ANTHROPIC_API_KEY |
| **Emy-Scheduler** | Scheduler service | Render service | ANTHROPIC_API_KEY |
| Local machine | Development/testing | CLI/Scripts | ANTHROPIC_API_KEY (if in .env) |

### Code References
- `emy/core/cli_handler.py` — reads ANTHROPIC_API_KEY environment variable
- `emy/core/skill_improver.py` — Anthropic client initialization
- `emy/tests/test_knowledge_agent_real_claude.py` — Test file with credential checks
- Job search projects (LinkedIn, Glassdoor) — May use Anthropic for analysis

### Files/Scripts That Reference These Keys
- `get_refresh_token.py` (in Trade-Alerts) — Historical reference
- Various `.md` documentation files with API key hints
- `Emy-Anthropic-Key.txt` — Standalone file with key information

### Rotation Steps (See Section: Step-by-Step Credential Generation)

---

## PLATFORM 3: Google OAuth2 (Gmail + Google Drive)

### Compromised Details
```json
{
  "installed": {
    "client_id": "650371239489-n5slvo6u2t802ugfvdmf5tabmrpq7fl7.apps.googleusercontent.com",
    "client_secret": "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",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
  }
}
```

### Exposure
- **Status**: 🔴 COMPROMISED
- **Locations**: Git history, Render environment variables, Local config files
- **Scope**: Gmail + Google Drive access across multiple services

### Active Usage Locations
| Location | Service | Component | Env Variable(s) |
|----------|---------|-----------|-----------------|
| **Trade-Alerts** | Render service | Market state tracking, Google Drive uploads | GMAIL_CREDENTIALS_JSON, GOOGLE_DRIVE_CREDENTIALS_JSON |
| **Forex-Trends-Tracker** | Render service | Historical data tracking | GOOGLE_DRIVE_CREDENTIALS_JSON |
| **Asset-Tracker** | Render service | Asset monitoring | GOOGLE_DRIVE_CREDENTIALS_JSON |
| **Job Search Projects** | Various (LinkedIn, Glassdoor) | Job matching, email integration | GMAIL_CREDENTIALS_JSON (may be in code or config) |
| **Job-Matching-System** | Local/experimental | Config-based credentials | Credentials in: `config/credentials/drive_token.json`, `config/credentials/gmail_token.json` |
| **Job-Evaluation** | Local/experimental | Config-based credentials | Credentials in: `config/credentials/drive_token.json`, `config/credentials/gmail_token.json` |

### Token Files That Need Rotation
- `Trade-Alerts/token.json` — Refresh token for Trade-Alerts service
- `Trade-Alerts/google_oauth_credentials_trade_alerts.json` — OAuth credentials
- `Forex/token.json` — Refresh token for Forex service
- `Forex/credentials.json.json` — OAuth credentials (duplicate extension?)
- `job-matching-system/config/credentials/sheets_token.json`
- `job-matching-system/config/credentials/drive_token.json`
- `job-matching-system/config/credentials/gmail_token.json`
- `job-matching-system/config/credentials/gmail_credentials.json`
- `Job_evaluation/config/credentials/drive_token.json`
- `Job_evaluation/config/credentials/gmail_token.json`
- `Job_evaluation/config/credentials/drive_credentials.json`
- `Job_evaluation/config/credentials/gmail_credentials.json`

### Code/Config References
- `get_refresh_token.py` (Trade-Alerts) — Script for generating new tokens
- Multiple backup folders with similar patterns
- Render deployment guides with credential setup instructions
- Various `.md` files documenting OAuth setup

---

## SUMMARY TABLE: ALL COMPROMISED CREDENTIALS

| Platform | Key Name | Status | Active Services | Files to Rotate |
|----------|----------|--------|-----------------|-----------------|
| **OpenAI** | "My cursor project" (sk-pro...L4A) | 🔴 COMPROMISED | Trade-Alerts | `.env`, Render environment |
| **Anthropic** | Emy-Anthropic-Key (sk-ant-api03-XPz...fAAA) | 🔴 COMPROMISED | Emy-Phase1a, Emy-Brain, Emy-Scheduler | Render environment (3 services) |
| **Anthropic** | My email summary (sk-ant-api03-m0P...MAAA) | 🔴 COMPROMISED | Unknown/Secondary | Render environment (verify usage) |
| **Google OAuth2** | client_id: 650371239489-... | 🔴 COMPROMISED | Trade-Alerts, Forex-Trends, Asset-Tracker, Job projects | OAuth2 console, Render (3+ services), Local token files |

---

## NEXT ACTIONS BY PLATFORM

### ⚠️ HIGHEST PRIORITY: Rotate All Three
1. **OpenAI** — Generate new API key in Cursor project
2. **Anthropic** — Generate new API keys (primary + secondary)
3. **Google OAuth2** — Revoke old credentials, generate new OAuth2 credentials

Then update all services in order:
1. Render services (deployment will restart automatically)
2. Local .env files
3. Git history cleanup (force-push after credential rotation complete)

See "STEP-BY-STEP CREDENTIAL GENERATION" section below for detailed instructions.

---

## STEP-BY-STEP CREDENTIAL GENERATION GUIDE

### A. OPENAI API KEY ROTATION (Cursor Project)

**Step 1: Revoke Current Key in Cursor Settings**
1. Go to https://www.cursor.com/settings (or your Cursor account dashboard)
2. Navigate to **API Keys** or **Project Settings**
3. Find "My cursor project"
4. Click **Revoke** or **Delete** on the compromised key (sk-pro...L4A)
5. Confirm revocation

**Step 2: Generate New API Key**
1. In Cursor settings, click **Create New API Key** or **+ New Key**
2. Name it: `"OpenAI API Key - Trade-Alerts (Rotated Mar 16 2026)"`
3. Copy the full key (format: sk-pro...)
4. Store it temporarily in a secure location

**Step 3: Update Trade-Alerts Render Service**
1. Go to https://dashboard.render.com
2. Select **Trade-Alerts** service
3. Go to **Environment** tab
4. Find `CHATGPT_API_KEY` or `OPENAI_API_KEY` variable
5. Update with new key
6. Click **Save** (Render will auto-deploy)
7. Verify service starts successfully (check logs)

**Step 4: Update Local .env (if present)**
1. Edit `.env` file in project root
2. Update or add: `OPENAI_API_KEY=sk-pro...` (new key)
3. Save file (do NOT commit to git)

✅ **Verification**: Trade-Alerts service should restart and be operational

---

### B. ANTHROPIC API KEY ROTATION (Primary Key)

**Step 1: Revoke Compromised Key**
1. Go to https://console.anthropic.com (Anthropic dashboard)
2. Navigate to **API Keys**
3. Find key name: **"Emy-Anthropic-Key"** (ID: 312eb107-a105-420e-9598-826c06884026)
4. Click **Revoke** or **Delete**
5. Confirm revocation

**Step 2: Generate New API Key**
1. In Anthropic console, click **Create New API Key**
2. Name it: `"Anthropic API Key - Emy (Rotated Mar 16 2026)"`
3. Copy the full key (format: sk-ant-api03-...)
4. Store it temporarily in a secure location

**Step 3: Update Three Render Services**
Repeat for each service:

**Service 1: emy-phase1a**
1. Go to https://dashboard.render.com
2. Select **emy-phase1a** service
3. Go to **Environment** tab
4. Find `ANTHROPIC_API_KEY` variable
5. Update with new key
6. Click **Save** (Render will auto-deploy)
7. Wait for deployment to complete
8. Check logs: `curl https://emy-phase1a.onrender.com/health` should return 200

**Service 2: emy-brain**
1. Repeat same steps for **emy-brain** service
2. Verify deployment successful

**Service 3: emy-scheduler**
1. Repeat same steps for **emy-scheduler** service
2. Verify deployment successful

**Step 4: Update Local .env (if present)**
1. Edit `.env` file in project root
2. Update: `ANTHROPIC_API_KEY=sk-ant-api03-...` (new key)
3. Save file (do NOT commit to git)

✅ **Verification**: All three services should restart and respond to health checks

---

### C. ANTHROPIC API KEY ROTATION (Secondary Key - "My email summary")

**⚠️ ACTION REQUIRED**: First identify where this key is actively used

**Step 1: Identify Active Usage**
1. Search Render services for "My email summary" reference
2. Check if any services are using this key
3. If found, note the service name(s)
4. If NOT found, skip to Step 2 (revoke only)

**Step 2: Revoke Compromised Key**
1. Go to https://console.anthropic.com
2. Navigate to **API Keys**
3. Find key name: **"My email summary"** (ID: 679fca02-aa38-451b-996c-87d314cb7800)
4. Click **Revoke** or **Delete**
5. Confirm revocation

**Step 3: If Key Is In Use, Generate & Deploy New Key**
(Only if Step 1 found active usage)
1. Generate new Anthropic API key (follow steps from Section B, Step 2)
2. Name it: `"Anthropic API Key - Email Summary (Rotated Mar 16 2026)"`
3. Update the identified Render service(s) with new key
4. Verify deployment

---

### D. GOOGLE OAUTH2 CREDENTIALS ROTATION (Most Complex)

**⚠️ IMPORTANT**: Google OAuth2 rotation requires multiple steps across platforms

**Step 1: Create New OAuth2 Application in Google Cloud Console**

1. Go to https://console.cloud.google.com/
2. Select or create project
3. Go to **APIs & Services** > **Credentials**
4. Click **+ Create Credentials** > **OAuth client ID**
5. Select **Desktop application** (or **Web application** if applicable)
6. For Redirect URIs, use:
   - `urn:ietf:wg:oauth:2.0:oob` (for desktop/CLI apps)
   - `http://localhost:8080/callback` (for web apps if needed)
7. Click **Create**
8. Click **Download JSON** to save credentials
9. **IMPORTANT**: Copy the full JSON content (you'll need this)

**Step 2: Revoke Old OAuth2 Credentials**

1. In Google Cloud Console, find old credentials (client_id: 650371239489-...)
2. Click the **X** or **Delete** button
3. Confirm deletion
4. Old credentials are now revoked

**Step 3: Update Render Environment Variables**

Update THREE Render services that use Google credentials:

**Service 1: Trade-Alerts**
1. Go to https://dashboard.render.com
2. Select **Trade-Alerts** service
3. Go to **Environment** tab
4. Find/Update these variables:
   - `GMAIL_CREDENTIALS_JSON` — Replace with new OAuth2 JSON
   - `GOOGLE_DRIVE_CREDENTIALS_JSON` — Replace with new OAuth2 JSON
5. Click **Save** (Render auto-deploys)
6. Wait for deployment
7. Check logs for successful start

**Service 2: forex-trends-tracker** (if exists and running)
1. Repeat same steps
2. Update: `GOOGLE_DRIVE_CREDENTIALS_JSON`

**Service 3: asset-tracker** (if exists and running)
1. Repeat same steps
2. Update: `GOOGLE_DRIVE_CREDENTIALS_JSON`

**Step 4: Generate New Refresh Tokens**

For Trade-Alerts and other services that need refresh tokens:

1. Use script: `Trade-Alerts/get_refresh_token.py`
2. Run locally:
   ```bash
   cd /c/Users/user/projects/personal/Trade-Alerts
   python get_refresh_token.py
   ```
3. Follow browser OAuth2 consent flow
4. Copy returned refresh token
5. Update Render services:
   - Add/Update: `GOOGLE_DRIVE_REFRESH_TOKEN=<new_refresh_token>`

**Step 5: Update Local Token Files**

Update all local token.json files with new credentials:

- `Trade-Alerts/token.json` — Run get_refresh_token.py locally
- `Trade-Alerts/google_oauth_credentials_trade_alerts.json` — Replace with new OAuth JSON
- `Forex/token.json` — Update if this service is used
- `Forex/credentials.json.json` — Replace with new OAuth JSON
- `job-matching-system/config/credentials/*.json` — Update all token files
- `Job_evaluation/config/credentials/*.json` — Update all token files

**Step 6: Verify All Services Are Working**

For each updated service, verify:
1. Service is running (check Render dashboard)
2. Service can access Gmail/Drive APIs
3. Check logs for error messages
4. Test API calls if possible

✅ **Verification Complete**: All services should be accessing Gmail/Drive with new credentials

---

## GIT HISTORY CLEANUP (Final Step)

**⚠️ CRITICAL**: Only run AFTER all credentials are rotated and verified

After all three platforms' credentials are updated and services are running successfully:

**Step 1: Use git-filter-repo to Remove Exposed Credentials**

```bash
# Install git-filter-repo if not already installed
pip install git-filter-repo

# Run cleanup (removes specific credential patterns from all commits)
cd /c/Users/user/projects/personal

git-filter-repo --replace-text <(cat <<'EOF'
sk-ant-api03-XPz...fAAA==>ANTHROPIC_API_KEY_REMOVED
sk-ant-api03-m0P...MAAA==>ANTHROPIC_API_KEY_REMOVED
sk-pro...L4A==>OPENAI_API_KEY_REMOVED
650371239489-n5slvo6u2t802ugfvdmf5tabmrpq7fl7.apps.googleusercontent.com==>GOOGLE_CLIENT_ID_REMOVED
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==>GOOGLE_CLIENT_SECRET_REMOVED
EOF
)
```

**Step 2: Force Push to Remote**

```bash
git push origin --force --all
git push origin --force --tags
```

**Step 3: Verify Cleanup**

```bash
# Search git history for any remaining exposed patterns
git log -S "sk-ant-api03" --all -- || echo "✅ No Anthropic keys found"
git log -S "sk-pro" --all -- || echo "✅ No OpenAI keys found"
git log -S "650371239489" --all -- || echo "✅ No Google OAuth IDs found"
```

---

## CHECKLIST: Credential Rotation Completion

### Phase 1: Pre-Rotation Verification
- [ ] This audit document reviewed and understood
- [ ] All active Render services identified (Trade-Alerts, Emy-Phase1a, Emy-Brain, Emy-Scheduler)
- [ ] Backups created (optional but recommended)
- [ ] Secure location prepared for temporary credential storage

### Phase 2: OpenAI Rotation
- [ ] Old Cursor API key revoked in Cursor dashboard
- [ ] New OpenAI API key generated
- [ ] Trade-Alerts Render service updated with new key
- [ ] Trade-Alerts service verified operational (health check passes)
- [ ] Local .env updated (if present)

### Phase 3: Anthropic Rotation (Primary)
- [ ] Old Emy-Anthropic-Key revoked in Anthropic console
- [ ] New Anthropic API key generated
- [ ] emy-phase1a Render service updated and verified
- [ ] emy-brain Render service updated and verified
- [ ] emy-scheduler Render service updated and verified
- [ ] Local .env updated (if present)

### Phase 4: Anthropic Rotation (Secondary)
- [ ] Usage of "My email summary" key identified (if any)
- [ ] Key revoked in Anthropic console
- [ ] If in use: new key generated and deployed
- [ ] Relevant services verified operational

### Phase 5: Google OAuth2 Rotation
- [ ] New OAuth2 credentials created in Google Cloud Console
- [ ] Old OAuth2 credentials revoked
- [ ] Trade-Alerts Render service updated with new OAuth credentials
- [ ] forex-trends-tracker Render service updated (if applicable)
- [ ] asset-tracker Render service updated (if applicable)
- [ ] New refresh tokens generated using get_refresh_token.py
- [ ] Render services updated with new refresh tokens
- [ ] All services verified operational
- [ ] Local token files updated with new credentials

### Phase 6: Git History Cleanup
- [ ] ✅ All services confirmed running with new credentials
- [ ] git-filter-repo installed
- [ ] Git history cleaned of exposed credentials
- [ ] Force push to origin completed
- [ ] Cleanup verified with git log searches

---

## SUMMARY OF LOCATIONS TO UPDATE

### Render Services (Auto-deploy on update)
1. ✅ Trade-Alerts (OPENAI_API_KEY, GMAIL_CREDENTIALS_JSON, GOOGLE_DRIVE_CREDENTIALS_JSON)
2. ✅ emy-phase1a (ANTHROPIC_API_KEY, GMAIL_CREDENTIALS_JSON, GOOGLE_DRIVE_CREDENTIALS_JSON)
3. ✅ emy-brain (ANTHROPIC_API_KEY)
4. ✅ emy-scheduler (ANTHROPIC_API_KEY)
5. ✅ forex-trends-tracker (GOOGLE_DRIVE_CREDENTIALS_JSON) — if running
6. ✅ asset-tracker (GOOGLE_DRIVE_CREDENTIALS_JSON) — if running

### Local Files
1. ✅ `.env` (OPENAI_API_KEY, ANTHROPIC_API_KEY)
2. ✅ `Trade-Alerts/token.json`
3. ✅ `Trade-Alerts/google_oauth_credentials_trade_alerts.json`
4. ✅ `Forex/token.json`
5. ✅ `Forex/credentials.json.json`
6. ✅ Job project token files (multiple)

### Git History
- ✅ Remove all exposed credential patterns before final commit

---

## CRITICAL NOTES

1. **Do NOT hardcode credentials in code** — Always use environment variables
2. **Test After Each Update** — Verify service health before moving to next
3. **Backup Current Credentials** — Keep old credentials accessible for 24h post-rotation
4. **Document Rotation Date** — Mark March 16, 2026 as rotation date
5. **Monitor Logs Post-Rotation** — Watch for auth failures in first hour after each update

---

**Status**: 🔴 AWAITING USER ACTION
**Next Step**: Begin Section A (OpenAI Rotation) when ready
