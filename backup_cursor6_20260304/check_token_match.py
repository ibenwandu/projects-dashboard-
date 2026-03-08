"""Check if refresh token matches the credentials JSON"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

def check_token_match():
    """Verify if refresh token and credentials are from the same OAuth app"""
    
    refresh_token = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')
    credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')
    
    if not refresh_token or not credentials_json:
        print("❌ Missing environment variables")
        return
    
    try:
        creds_data = json.loads(credentials_json)
        installed = creds_data.get('installed', {})
        client_id = installed.get('client_id') or creds_data.get('client_id')
        client_secret = installed.get('client_secret') or creds_data.get('client_secret')
        
        print("="*80)
        print("CHECKING TOKEN AND CREDENTIALS MATCH")
        print("="*80)
        print()
        print(f"Refresh Token (first 30 chars): {refresh_token[:30]}...")
        print(f"Refresh Token length: {len(refresh_token)}")
        print()
        print(f"Client ID: {client_id}")
        print(f"Client Secret: {client_secret[:20]}..." if client_secret else "Client Secret: NOT FOUND")
        print()
        print("="*80)
        print("DIAGNOSIS:")
        print("="*80)
        print()
        print("If this refresh token works for other programs but not this one,")
        print("it likely means:")
        print()
        print("1. The refresh token was generated with DIFFERENT client_id/client_secret")
        print("2. The credentials JSON here has DIFFERENT client_id/client_secret")
        print("3. They need to match for the token to work")
        print()
        print("SOLUTION:")
        print("Use the SAME credentials JSON that was used to generate the refresh token")
        print("OR generate a new refresh token using the current credentials JSON")
        print()
        
    except Exception as e:
        print(f"❌ Error parsing credentials: {e}")

if __name__ == '__main__':
    check_token_match()





