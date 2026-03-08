#!/usr/bin/env python3
"""
Verify Google Drive credentials JSON structure
Compare with working programs to ensure they match
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("GOOGLE DRIVE CREDENTIALS VERIFICATION")
print("=" * 80)
print()

# Get credentials JSON
credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')
refresh_token = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')

if not credentials_json:
    print("[ERROR] GOOGLE_DRIVE_CREDENTIALS_JSON is not set")
    exit(1)

if not refresh_token:
    print("[ERROR] GOOGLE_DRIVE_REFRESH_TOKEN is not set")
    exit(1)

try:
    creds_data = json.loads(credentials_json)
except json.JSONDecodeError as e:
    print(f"[ERROR] Invalid JSON: {e}")
    exit(1)

print("[OK] Credentials JSON is valid")
print()

# Extract client info
installed = creds_data.get('installed', {})
client_id = installed.get('client_id') or creds_data.get('client_id')
client_secret = installed.get('client_secret') or creds_data.get('client_secret')

print("Credentials Structure:")
print(f"  Has 'installed' key: {bool(installed)}")
print(f"  Client ID: {client_id[:30]}... (length: {len(client_id) if client_id else 0})")
print(f"  Client Secret: {client_secret[:10]}... (length: {len(client_secret) if client_secret else 0})")
print(f"  Refresh Token: {refresh_token[:20]}... (length: {len(refresh_token)})")
print()

# Check for required fields
if not client_id:
    print("[ERROR] Missing client_id")
    exit(1)

if not client_secret:
    print("[ERROR] Missing client_secret")
    exit(1)

print("[OK] All required fields present")
print()

# Show full structure (masked)
print("Full JSON structure (values masked):")
def mask_sensitive(obj, depth=0):
    if depth > 3:
        return "..."
    if isinstance(obj, dict):
        masked = {}
        for key, value in obj.items():
            if 'secret' in key.lower() or 'token' in key.lower() or 'id' in key.lower():
                if isinstance(value, str) and len(value) > 10:
                    masked[key] = value[:10] + "..." + f" (length: {len(value)})"
                else:
                    masked[key] = "***"
            else:
                masked[key] = mask_sensitive(value, depth + 1)
        return masked
    elif isinstance(obj, list):
        return [mask_sensitive(item, depth + 1) for item in obj[:3]]
    else:
        return obj

masked_creds = mask_sensitive(creds_data)
print(json.dumps(masked_creds, indent=2))
print()

print("=" * 80)
print("[OK] Credentials structure looks valid")
print("=" * 80)
print()
print("Next step: Run 'python test_drive_auth.py' to test authentication")

