"""
Test script to verify Dukascopy API is working and data is being received
"""

import requests
from datetime import datetime, timedelta

def test_dukascopy_url():
    """Test a single Dukascopy URL"""
    pair = "EURUSD"
    year = 2024
    month = 11  # December (0-indexed, so 11 = December)
    day = 15
    
    url = f"https://www.dukascopy.com/datafeed/{pair}/{year}/{month:02d}/{day:02d}/1DAY_bid_ask.csv"
    
    print(f"Testing URL: {url}")
    print("-" * 80)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Content Length: {len(response.text)} bytes")
        print(f"Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            print(f"Total Lines: {len(lines)}")
            
            if len(lines) > 0:
                print(f"First Line (Header): {lines[0]}")
                if len(lines) > 1:
                    print(f"Second Line (Data): {lines[1]}")
                    print(f"Third Line (Data): {lines[2] if len(lines) > 2 else 'N/A'}")
                
                # Try to parse a line
                if len(lines) > 1:
                    parts = lines[1].split(',')
                    print(f"\nParsed Second Line:")
                    print(f"  Parts count: {len(parts)}")
                    if len(parts) >= 6:
                        print(f"  Timestamp: {parts[0]}")
                        print(f"  Open: {parts[1]}")
                        print(f"  High: {parts[2]}")
                        print(f"  Low: {parts[3]}")
                        print(f"  Close: {parts[4]}")
                        print(f"  Volume: {parts[5]}")
                    else:
                        print(f"  Warning: Expected 6 parts, got {len(parts)}")
                        print(f"  Actual parts: {parts}")
            else:
                print("Warning: No lines in response!")
                print(f"Response text (first 500 chars): {response.text[:500]}")
        else:
            print(f"Error: Status code {response.status_code}")
            print(f"Response text (first 500 chars): {response.text[:500]}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def test_multiple_dates():
    """Test multiple dates to see if data is available"""
    pair = "EURUSD"
    base_date = datetime(2024, 12, 15)
    
    print("\n" + "=" * 80)
    print("Testing Multiple Dates")
    print("=" * 80)
    
    dates_to_test = [
        base_date,
        base_date - timedelta(days=1),
        base_date - timedelta(days=7),
        base_date - timedelta(days=30),
        base_date - timedelta(days=365),
    ]
    
    results = []
    for test_date in dates_to_test:
        year = test_date.year
        month = test_date.month - 1  # 0-indexed
        day = test_date.day
        
        url = f"https://www.dukascopy.com/datafeed/{pair}/{year}/{month:02d}/{day:02d}/1DAY_bid_ask.csv"
        
        try:
            response = requests.get(url, timeout=5)
            status = response.status_code
            has_data = (status == 200 and len(response.text) > 100)
            
            results.append({
                'date': test_date.strftime('%Y-%m-%d'),
                'url': url,
                'status': status,
                'has_data': has_data,
                'length': len(response.text)
            })
            
            print(f"{test_date.strftime('%Y-%m-%d')}: Status={status}, Has Data={has_data}, Length={len(response.text)}")
            
        except Exception as e:
            results.append({
                'date': test_date.strftime('%Y-%m-%d'),
                'url': url,
                'status': 'ERROR',
                'has_data': False,
                'length': 0,
                'error': str(e)
            })
            print(f"{test_date.strftime('%Y-%m-%d')}: ERROR - {e}")
    
    return results

if __name__ == '__main__':
    print("=" * 80)
    print("Dukascopy API Test")
    print("=" * 80)
    print()
    
    # Test single URL
    test_dukascopy_url()
    
    # Test multiple dates
    results = test_multiple_dates()
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    successful = sum(1 for r in results if r.get('has_data', False))
    print(f"Successful downloads: {successful}/{len(results)}")
    
    if successful == 0:
        print("\n⚠️  WARNING: No data received from Dukascopy API!")
        print("This could mean:")
        print("  1. Dukascopy API format has changed")
        print("  2. Data is not available for these dates")
        print("  3. API endpoint is incorrect")
        print("  4. Network/authentication issue")
    else:
        print(f"\n✅ Successfully received data from {successful} dates")

