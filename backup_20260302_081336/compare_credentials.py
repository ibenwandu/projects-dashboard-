#!/usr/bin/env python3
"""
Compare Google Drive credentials between programs
Check if client_id matches between working programs and Trade-Alerts
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

print("=" * 80)
print("COMPARING GOOGLE DRIVE CREDENTIALS")
print("=" * 80)
print()

# Get Trade-Alerts credentials
trade_alerts_env = Path("personal/Trade-Alerts/.env")
if trade_alerts_env.exists():
    load_dotenv(trade_alerts_env)
    ta_creds_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')
    ta_refresh = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')
    
    if ta_creds_json:
        try:
            ta_creds = json.loads(ta_creds_json)
            ta_installed = ta_creds.get('installed', {})
            ta_client_id = ta_installed.get('client_id') or ta_creds.get('client_id')
            print(f"Trade-Alerts Client ID: {ta_client_id}")
            print(f"Trade-Alerts Refresh Token: {ta_refresh[:30]}...")
        except:
            print("Trade-Alerts: Could not parse credentials")
    else:
        print("Trade-Alerts: No credentials found")
else:
    print("Trade-Alerts: .env file not found")

print()

# Check other programs
programs = [
    ("Forex", "personal/Forex/.env"),
    ("Assets", "personal/Assets/.env"),
]

for name, env_path in programs:
    if Path(env_path).exists():
        # Clear previous env vars
        for key in list(os.environ.keys()):
            if key.startswith('GOOGLE_DRIVE_'):
                del os.environ[key]
        
        load_dotenv(env_path, override=True)
        creds_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')
        refresh = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')
        
        if creds_json:
            try:
                creds = json.loads(creds_json)
                installed = creds.get('installed', {})
                client_id = installed.get('client_id') or creds.get('client_id')
                print(f"{name} Client ID: {client_id}")
                print(f"{name} Refresh Token: {refresh[:30]}...")
                
                if ta_creds_json and ta_client_id:
                    if client_id == ta_client_id:
                        print(f"  -> MATCHES Trade-Alerts!")
                    else:
                        print(f"  -> DIFFERENT from Trade-Alerts")
                    if refresh == ta_refresh:
                        print(f"  -> Refresh token MATCHES")
                    else:
                        print(f"  -> Refresh token DIFFERENT")
            except Exception as e:
                print(f"{name}: Could not parse credentials: {e}")
        else:
            print(f"{name}: No credentials found")
        print()

print("=" * 80)
print("If client_id values don't match, that's the problem!")
print("The refresh token must be generated from the same OAuth app as the credentials JSON")
print("=" * 80)


