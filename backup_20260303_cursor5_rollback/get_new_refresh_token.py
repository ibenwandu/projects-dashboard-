#!/usr/bin/env python3
"""
Generate a new OAuth2 refresh token for Google Drive
This will use the credentials JSON from your .env file
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
print(f"[OK] Created {credentials_file}")

# Create settings.yaml for pydrive2
settings_file = Path(__file__).parent / "settings.yaml"
settings_content = """client_config_backend: file
client_config_file: credentials.json
save_credentials: True
save_credentials_backend: file
save_credentials_file: token.json
get_refresh_token: True
oauth_scope:
  - https://www.googleapis.com/auth/drive
"""
with open(settings_file, 'w') as f:
    f.write(settings_content)
print(f"[OK] Created {settings_file}")

print()
print("=" * 80)
print("Starting OAuth2 authentication...")
print("=" * 80)
print()
print("A browser window will open for you to authorize.")
print("After authorization, the refresh token will be saved to token.json")
print("You can then copy it to your .env file as GOOGLE_DRIVE_REFRESH_TOKEN")
print()

try:
    from pydrive2.auth import GoogleAuth
    
    gauth = GoogleAuth()
    gauth.LoadClientConfigFile(str(credentials_file))
    
    print("[*] Starting authentication flow...")
    print()
    print("Using command-line authentication (more reliable)...")
    print()
    
    # Use command line auth instead of local server
    gauth.CommandLineAuth()
    
    # Get the refresh token
    if gauth.credentials.refresh_token:
        print()
        print("=" * 80)
        print("[SUCCESS] New refresh token generated:")
        print("=" * 80)
        print()
        print(gauth.credentials.refresh_token)
        print()
        print("=" * 80)
        print("Copy this token and update GOOGLE_DRIVE_REFRESH_TOKEN in your .env file")
        print("=" * 80)
        
        # Also save to token.json for reference
        token_file = Path(__file__).parent / "token.json"
        gauth.SaveCredentialsFile(str(token_file))
        print(f"[OK] Also saved to {token_file} for reference")
    else:
        print("[WARNING] No refresh token found. Make sure you granted offline access.")
        
except ImportError:
    print("Error: PyDrive2 not installed. Install with: pip install PyDrive2")
    exit(1)
except Exception as e:
    print(f"Error during authentication: {e}")
    import traceback
    traceback.print_exc()
    exit(1)


