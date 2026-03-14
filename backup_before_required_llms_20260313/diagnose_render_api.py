"""
Diagnostic script for Render API log endpoints
Tests all endpoints and provides detailed diagnostics
"""
import requests
import json
from datetime import datetime

API_BASE = "https://config-api-8n37.onrender.com"

def test_endpoint(name, url):
    """Test an API endpoint and return results"""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                data = response.json()
                print(f"Response (JSON):")
                print(json.dumps(data, indent=2))
            else:
                # Plain text response
                text = response.text
                lines = text.split('\n')
                print(f"Response (Text, first 20 lines):")
                for i, line in enumerate(lines[:20], 1):
                    print(f"  {i:3}: {line}")
                if len(lines) > 20:
                    print(f"  ... ({len(lines) - 20} more lines)")
        else:
            print(f"Error Response:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text[:500])
        
        return response.status_code == 200
        
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT - Request took longer than 10 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR - {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR - {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("RENDER API DIAGNOSTIC TOOL")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*70)
    
    # Test health endpoint first
    health_ok = test_endpoint("Health Check", f"{API_BASE}/health")
    
    if not health_ok:
        print("\n⚠️  Health endpoint failed - API may be down or deploying")
        print("   Check Render dashboard for service status")
        return
    
    # Test log listing endpoint
    test_endpoint("List Logs", f"{API_BASE}/logs")
    
    # Test individual log endpoints
    components = ['engine', 'oanda', 'ui']
    results = {}
    
    for component in components:
        results[component] = test_endpoint(
            f"Log Content - {component.upper()}",
            f"{API_BASE}/logs/{component}"
        )
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Health Check: {'OK' if health_ok else 'FAILED'}")
    for component, success in results.items():
        status = 'OK' if success else 'FAILED'
        print(f"Logs/{component}: {status}")
    
    print(f"\n{'='*70}")
    print("RECOMMENDATIONS")
    print(f"{'='*70}")
    
    if not all(results.values()):
        print("WARNING: Some log endpoints are failing")
        print("\nPossible causes:")
        print("1. Services aren't writing logs yet")
        print("2. Log files don't exist (services need to run first)")
        print("3. API fix hasn't been deployed yet")
        print("4. Services are logging to different location")
        print("\nNext steps:")
        print("1. Check Render dashboard - are services running?")
        print("2. Check Render logs for Scalp-Engine service")
        print("3. Wait for API deployment to complete")
        print("4. Verify services are writing to /var/data/logs/")
    else:
        print("SUCCESS: All endpoints working correctly!")

if __name__ == '__main__':
    main()

