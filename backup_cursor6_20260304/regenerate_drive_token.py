#!/usr/bin/env python3
"""
Regenerate Google Drive Refresh Token

This script helps you generate a new refresh token for Google Drive API access.
Run this locally (not on Render) to get a new refresh token.

Usage:
1. Set GOOGLE_DRIVE_CREDENTIALS_JSON environment variable, OR
2. Place credentials.json file in the same directory
3. Run: python regenerate_drive_token.py
4. Copy the refresh token and update it in Render Dashboard
"""

import os
import json
import sys
from pathlib import Path

try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
except ImportError:
    print("❌ PyDrive2 not installed. Install with: pip install PyDrive2")
    sys.exit(1)

def main():
    print("=" * 80)
    print("Google Drive Refresh Token Generator")
    print("=" * 80)
    print()
    
    # Get credentials
    credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')
    credentials_file = 'credentials.json'
    client_secrets_file = 'client_secrets.json'
    
    if credentials_json:
        print("✅ Found GOOGLE_DRIVE_CREDENTIALS_JSON in environment")
        try:
            creds_data = json.loads(credentials_json)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in GOOGLE_DRIVE_CREDENTIALS_JSON: {e}")
            sys.exit(1)
    elif os.path.exists(credentials_file):
        print(f"✅ Found {credentials_file}")
        with open(credentials_file, 'r') as f:
            creds_data = json.load(f)
    else:
        print("❌ No credentials found!")
        print("   Options:")
        print("   1. Set GOOGLE_DRIVE_CREDENTIALS_JSON environment variable")
        print("   2. Place credentials.json file in current directory")
        sys.exit(1)
    
    # Write client_secrets.json (required by PyDrive2)
    with open(client_secrets_file, 'w') as f:
        json.dump(creds_data, f)
    print(f"✅ Created {client_secrets_file}")
    
    # Authenticate
    print()
    print("🔐 Starting authentication...")
    print("   A browser window will open for you to sign in.")
    print()
    
    gauth = GoogleAuth()
    
    # Try to load existing credentials
    creds_file = "mycreds.txt"
    if os.path.exists(creds_file):
        try:
            gauth.LoadCredentialsFile(creds_file)
            if gauth.credentials and not gauth.access_token_expired:
                print("✅ Found valid saved credentials")
                refresh_token = gauth.credentials.refresh_token
                if refresh_token:
                    print()
                    print("=" * 80)
                    print("✅ REFRESH TOKEN (from saved credentials):")
                    print("=" * 80)
                    print(refresh_token)
                    print("=" * 80)
                    print()
                    print("📋 Copy this token and update GOOGLE_DRIVE_REFRESH_TOKEN in Render Dashboard")
                    return
        except Exception as e:
            print(f"⚠️  Could not load saved credentials: {e}")
            print("   Will generate new token...")
    
    # Need to authenticate
    print("🌐 Opening browser for authentication...")
    print("   Please sign in and grant permissions.")
    print()
    
    try:
        gauth.LocalWebserverAuth()  # Opens browser
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Authentication failed: {e}")
        print()
        
        if "redirect_uri_mismatch" in error_msg.lower():
            print("🔧 REDIRECT URI MISMATCH ERROR:")
            print("   The script uses http://localhost:8080/ but it's not authorized in Google Cloud Console.")
            print()
            print("   Option 1 (Recommended): Use OAuth2 Playground instead (no redirect URI needed):")
            print("   1. Go to: https://developers.google.com/oauthplayground/")
            print("   2. Click ⚙️ (Settings) → Check 'Use your own OAuth credentials'")
            print("   3. Enter Client ID and Secret from GOOGLE_DRIVE_CREDENTIALS_JSON")
            print("   4. Select 'Drive API v3' → scope: https://www.googleapis.com/auth/drive")
            print("   5. Click 'Authorize APIs' → Sign in → 'Exchange authorization code for tokens'")
            print("   6. Copy the refresh_token from response")
            print()
            print("   Option 2: Add redirect URI to Google Cloud Console:")
            print("   1. Go to: https://console.cloud.google.com/apis/credentials")
            print("   2. Click your OAuth 2.0 Client ID")
            print("   3. Under 'Authorized redirect URIs', add: http://localhost:8080/")
            print("   4. Save and try this script again")
        else:
            print("💡 Alternative: Use Google OAuth2 Playground:")
            print("   1. Go to: https://developers.google.com/oauthplayground/")
            print("   2. Configure with your Client ID and Secret")
            print("   3. Authorize Drive API scope")
            print("   4. Exchange code for tokens")
        sys.exit(1)
    
    # Save credentials
    gauth.SaveCredentialsFile(creds_file)
    print(f"✅ Saved credentials to {creds_file}")
    
    # Get refresh token
    if gauth.credentials and gauth.credentials.refresh_token:
        refresh_token = gauth.credentials.refresh_token
        print()
        print("=" * 80)
        print("✅ NEW REFRESH TOKEN:")
        print("=" * 80)
        print(refresh_token)
        print("=" * 80)
        print()
        print("📋 Next Steps:")
        print("   1. Copy the refresh token above")
        print("   2. Go to Render Dashboard → trade-alerts → Environment")
        print("   3. Update GOOGLE_DRIVE_REFRESH_TOKEN with the new token")
        print("   4. Save and wait for redeploy")
        print()
    else:
        print("❌ No refresh token found in credentials")
        print("   This might happen if:")
        print("   - You didn't grant offline access")
        print("   - The OAuth flow didn't complete")
        print()
        print("💡 Try using Google OAuth2 Playground instead (see FIX_GOOGLE_DRIVE_TOKEN.md)")

if __name__ == "__main__":
    main()
