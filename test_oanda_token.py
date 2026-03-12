#!/usr/bin/env python3
"""
Test OANDA token validity and authorization.

This script tests:
1. Can we connect to OANDA API?
2. Is the token valid?
3. Does the token have permission for the account?
4. What account info can we retrieve?
"""

import sys
import os
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv('emy/.env')

OANDA_TOKEN = os.getenv('OANDA_ACCESS_TOKEN')
OANDA_ACCOUNT = os.getenv('OANDA_ACCOUNT_ID')
OANDA_ENV = os.getenv('OANDA_ENV', 'practice')

print("=" * 70)
print("OANDA Token Test")
print("=" * 70)
print("\nTest Date/Time: " + datetime.now().isoformat())
print("Environment: " + OANDA_ENV)
print("Account ID: " + OANDA_ACCOUNT)
print("Token: " + OANDA_TOKEN[:20] + "..." + OANDA_TOKEN[-20:])

# Test 1: Check if oandapyV20 is installed
print("\n[TEST 1] Checking oandapyV20 library...")
try:
    import oandapyV20
    import oandapyV20.endpoints.accounts as accounts
    print("[OK] oandapyV20 library is installed")
except ImportError as e:
    print("[FAIL] oandapyV20 not installed: " + str(e))
    print("   Fix: pip install oandapyV20")
    sys.exit(1)

# Test 2: Initialize client
print("\n[TEST 2] Initializing OANDA client...")
try:
    client = oandapyV20.API(
        access_token=OANDA_TOKEN,
        environment=OANDA_ENV
    )
    print("[OK] Client initialized successfully")
except Exception as e:
    print("[FAIL] Client initialization failed: " + str(e))
    sys.exit(1)

# Test 3: Test account authorization
print("\n[TEST 3] Testing authorization for account " + OANDA_ACCOUNT + "...")
try:
    r = accounts.AccountSummary(accountID=OANDA_ACCOUNT)
    client.request(r)

    if r.status == 200:
        print("[OK] Authorization successful!")

        account = r.response.get('account', {})
        print("\nAccount Information:")
        print("   Account ID:       " + str(account.get('id', 'N/A')))
        print("   Alias:            " + str(account.get('alias', 'N/A')))
        print("   Balance:          $" + str(account.get('balance', 'N/A')))
        print("   Currency:         " + str(account.get('currency', 'N/A')))
        print("   Margin Available: $" + str(account.get('marginAvailable', 'N/A')))
        print("   Margin Used:      $" + str(account.get('marginUsed', 'N/A')))
        print("   Unrealized P&L:   $" + str(account.get('unrealizedPL', 'N/A')))
        print("   Open Trade Count: " + str(account.get('openTradeCount', 'N/A')))

        # Overall status
        print("\n" + "=" * 70)
        print("[SUCCESS] TOKEN IS VALID AND AUTHORIZED")
        print("=" * 70)
        sys.exit(0)
    else:
        print("[FAIL] Unexpected status code: " + str(r.status))
        print("   Response: " + str(r.response))
        sys.exit(1)

except Exception as e:
    error_str = str(e)

    print("[FAIL] Authorization failed!")
    print("   Error: " + error_str)

    # Diagnose the error
    print("\nDiagnosis:")

    if "401" in error_str or "Insufficient authorization" in error_str:
        print("   Issue: 401 Unauthorized")
        print("   Possible causes:")
        print("   1. Token is expired or revoked")
        print("   2. Token doesn't have permission for this account")
        print("   3. Token is from a different OANDA workspace")
        print("   4. Account ID is incorrect")

    elif "404" in error_str:
        print("   Issue: 404 Not Found")
        print("   Possible causes:")
        print("   1. Account ID doesn't exist")
        print("   2. Account has been closed")
        print("   3. Wrong environment (should be 'practice' or 'live')")

    elif "Connection" in error_str or "timeout" in error_str.lower():
        print("   Issue: Connection error")
        print("   Possible causes:")
        print("   1. Network connectivity issue")
        print("   2. OANDA API is down")
        print("   3. Firewall blocking connection")

    else:
        print("   Unknown error: " + error_str)

    print("\nSolutions:")
    print("   1. Generate a new token at: https://developer.oanda.com/")
    print("   2. Verify account ID matches your OANDA account")
    print("   3. Check if token is still active (not expired/revoked)")
    print("   4. Verify environment setting (practice vs live)")

    print("\n" + "=" * 70)
    print("[FAILED] TOKEN TEST FAILED")
    print("=" * 70)
    sys.exit(1)
