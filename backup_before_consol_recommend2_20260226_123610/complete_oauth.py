#!/usr/bin/env python3
"""
Complete OAuth flow using an authorization code from the redirect URL
Use this if you already have the code from the browser redirect
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    print("Error: .env file not found")
    exit(1)

credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')
if not credentials_json:
    print("Error: GOOGLE_DRIVE_CREDENTIALS_JSON not set in .env")
    exit(1)

try:
    creds_data = json.loads(credentials_json)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON in GOOGLE_DRIVE_CREDENTIALS_JSON: {e}")
    exit(1)

# Write credentials.json file
credentials_file = Path(__file__).parent / "credentials.json"
with open(credentials_file, 'w') as f:
    json.dump(creds_data, f)

print("=" * 80)
print("Complete OAuth Flow with Authorization Code")
print("=" * 80)
print()
print("If you have the authorization code from the browser URL,")
print("paste it here (or the full URL with the code parameter).")
print()
print("Example URL: http://localhost:8080/?code=4/0ATX87IPTPw_af8YbLh9xHYRduxb4LoT06OXY6ttpfsBG6mAXzuSahR-H4YMWLLcbXhcWRw&scope=...")
print()
print("Or just the code: 4/0ATX87IPTPw_af8YbLh9xHYRduxb4LoT06OXY6ttpfsBG6mAXzuSahR-H4YMWLLcbXhcWRw")
print()

user_input = input("Paste URL or code here: ").strip()

# Extract code from URL if full URL provided
if 'code=' in user_input:
    code = user_input.split('code=')[1].split('&')[0].split('?')[0]
else:
    code = user_input

if not code:
    print("Error: No authorization code found")
    exit(1)

print()
print(f"[*] Using authorization code: {code[:30]}...")
print()

try:
    from pydrive2.auth import GoogleAuth
    from oauth2client.client import OAuth2WebServerFlow
    import urllib.parse
    
    # Get client credentials
    installed = creds_data.get('installed', {})
    client_id = installed.get('client_id') or creds_data.get('client_id')
    client_secret = installed.get('client_secret') or creds_data.get('client_secret')
    
    if not client_id or not client_secret:
        print("Error: Missing client_id or client_secret in credentials")
        exit(1)
    
    # Exchange code for token
    flow = OAuth2WebServerFlow(
        client_id=client_id,
        client_secret=client_secret,
        scope='https://www.googleapis.com/auth/drive',
        redirect_uri='http://localhost'
    )
    
    credentials = flow.step2_exchange(code)
    
    if credentials.refresh_token:
        print()
        print("=" * 80)
        print("[SUCCESS] Refresh token obtained:")
        print("=" * 80)
        print()
        print(credentials.refresh_token)
        print()
        print("=" * 80)
        print("Copy this token and update GOOGLE_DRIVE_REFRESH_TOKEN in your .env file")
        print("=" * 80)
        
        # Save to token.json
        token_file = Path(__file__).parent / "token.json"
        with open(token_file, 'w') as f:
            json.dump({
                'access_token': credentials.access_token,
                'refresh_token': credentials.refresh_token,
                'token_expiry': credentials.token_expiry.isoformat() if credentials.token_expiry else None,
                'client_id': client_id,
                'client_secret': client_secret
            }, f, indent=2)
        print(f"[OK] Also saved to {token_file} for reference")
    else:
        print("[ERROR] No refresh token in response. Make sure you granted offline access.")
        
except ImportError:
    print("Error: PyDrive2 or oauth2client not installed.")
    print("Install with: pip install PyDrive2 oauth2client")
    exit(1)
except Exception as e:
    print(f"Error during token exchange: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

