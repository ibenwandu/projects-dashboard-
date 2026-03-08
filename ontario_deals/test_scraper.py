"""
Quick test script for the RedFlagDeals scraper
Run this to verify the scraper is working before using it in the main app
"""

from redflagdeals_scraper import RedFlagDealsScraperWorking


def test_scraper():
    """Test the RedFlagDeals scraper"""
    print("\n" + "=" * 70)
    print("🧪 Testing RedFlagDeals Scraper")
    print("=" * 70)
    print("\nThis will attempt to fetch 5 deals from RedFlagDeals.com")
    print("Please wait, this may take 10-15 seconds...\n")
    
    try:
        # Create scraper
        scraper = RedFlagDealsScraperWorking()
        
        # Fetch deals
        deals = scraper.scrape_hot_deals(max_deals=5)
        
        # Show results
        if deals:
            print("\n" + "=" * 70)
            print(f"✅ SUCCESS! Scraped {len(deals)} deals")
            print("=" * 70)
            
            for i, deal in enumerate(deals, 1):
                print(f"\n[{i}] {deal['title']}")
                print(f"    Store: {deal['store']}")
                print(f"    Category: {deal['category']}")
                print(f"    Price: {deal['price_discount']}")
                if deal.get('discount_percentage'):
                    print(f"    Discount: {deal['discount_percentage']}% off")
                print(f"    Link: {deal['link']}")
            
            print("\n" + "=" * 70)
            print("✅ Scraper is working! You can now use it in the CLI app.")
            print("=" * 70)
            
        else:
            print("\n" + "=" * 70)
            print("⚠️  WARNING: No deals were scraped")
            print("=" * 70)
            print("\nPossible reasons:")
            print("1. RedFlagDeals.com structure has changed (common with web scraping)")
            print("2. Internet connection issue")
            print("3. Website is blocking automated access")
            print("\nYou can still use sample deals to test the app functionality.")
            print("=" * 70)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERROR during scraping")
        print("=" * 70)
        print(f"\nError: {e}")
        print("\nThis could be due to:")
        print("1. Missing dependencies (run: pip install -r requirements.txt)")
        print("2. Internet connection issues")
        print("3. Website blocking access")
        print("=" * 70)


if __name__ == "__main__":
    test_scraper()



