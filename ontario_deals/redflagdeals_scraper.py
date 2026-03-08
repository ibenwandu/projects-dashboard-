"""
RedFlagDeals Scraper - Working Implementation
Fetches real deals from RedFlagDeals.com for Ontario
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import List, Dict, Optional
import re
from utils import (
    extract_discount_percentage,
    categorize_deal,
    clean_html,
    validate_url,
    normalize_location,
    parse_expiry_date
)


class RedFlagDealsScraperWorking:
    """Working scraper for RedFlagDeals.com"""
    
    def __init__(self):
        self.base_url = "https://www.redflagdeals.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.deals_scraped = 0
    
    def fetch_page(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Fetch a web page with retry logic and rate limiting"""
        for attempt in range(max_retries):
            try:
                print(f"  Fetching: {url}")
                time.sleep(2)  # Be respectful - 2 second delay
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                print(f"  ✓ Page fetched successfully (Status: {response.status_code})")
                return response.text
                
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    print(f"  ✗ Failed to fetch {url} after {max_retries} attempts: {e}")
                    return None
                print(f"  ⚠ Attempt {attempt + 1} failed, retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def extract_deal_from_card(self, deal_elem) -> Optional[Dict]:
        """Extract deal information from a deal card element"""
        try:
            deal_data = {}
            
            # If deal_elem is itself a link, extract from it
            if deal_elem.name == 'a':
                deal_data['title'] = clean_html(deal_elem.get_text()).strip()
                link = deal_elem.get('href', '')
                if link:
                    if not link.startswith('http'):
                        link = self.base_url + link
                    deal_data['link'] = link
                
                # If we got a title from the link, continue
                if not deal_data.get('title'):
                    return None
            else:
                # Title - multiple possible selectors
                title_elem = (
                    deal_elem.find('h3') or
                    deal_elem.find('h2') or
                    deal_elem.find('a', class_=re.compile(r'title')) or
                    deal_elem.find('a', href=re.compile(r'/deal')) or
                    deal_elem.find('a')
                )
                
                if title_elem:
                    deal_data['title'] = clean_html(title_elem.get_text()).strip()
                    # Get link
                    link = title_elem.get('href', '')
                    if link:
                        if not link.startswith('http'):
                            link = self.base_url + link
                        deal_data['link'] = link
                else:
                    return None
            
            # Store/Merchant
            merchant_elem = (
                deal_elem.find('span', class_='merchant_name') or
                deal_elem.find('a', class_='merchant') or
                deal_elem.find('div', class_='offer_merchant')
            )
            
            if merchant_elem:
                deal_data['store'] = clean_html(merchant_elem.get_text()).strip()
            else:
                # Try to extract from title
                deal_data['store'] = self._extract_store_from_title(deal_data['title'])
            
            # Price/Discount
            price_elem = (
                deal_elem.find('span', class_='offer_price') or
                deal_elem.find('div', class_='price') or
                deal_elem.find('span', class_='sale_price')
            )
            
            if price_elem:
                deal_data['price_discount'] = clean_html(price_elem.get_text()).strip()
            else:
                # Extract from title if price is mentioned
                deal_data['price_discount'] = self._extract_price_from_title(deal_data['title'])
            
            # Extract discount percentage
            full_text = deal_data['title'] + " " + deal_data.get('price_discount', '')
            deal_data['discount_percentage'] = extract_discount_percentage(full_text)
            
            # Category
            deal_data['category'] = categorize_deal(deal_data['title'])
            
            # Location - default to Ontario for now
            deal_data['location'] = "Ontario, Canada"
            
            # Relevance
            deal_data['relevance'] = f"Trending deal from RedFlagDeals"
            
            # Timestamp
            deal_data['timestamp'] = datetime.now().isoformat()
            
            # Set default link if not found
            if 'link' not in deal_data:
                deal_data['link'] = self.base_url
            
            return deal_data
            
        except Exception as e:
            print(f"  ⚠ Error parsing deal card: {e}")
            return None
    
    def _extract_store_from_title(self, title: str) -> str:
        """Try to extract store name from title"""
        common_stores = [
            'Amazon', 'Best Buy', 'Walmart', 'Costco', 'Canadian Tire',
            'Home Depot', 'Loblaws', 'No Frills', 'Metro', 'Sobeys',
            'Target', 'Staples', 'eBay', 'AliExpress', 'Newegg'
        ]
        
        title_lower = title.lower()
        for store in common_stores:
            if store.lower() in title_lower:
                return store
        
        # Try to extract from @ or "at" patterns
        match = re.search(r'(?:@|at)\s*([A-Z][A-Za-z\s&]+?)(?:\s|$|\[|\()', title)
        if match:
            return match.group(1).strip()
        
        return "Various Retailers"
    
    def _extract_price_from_title(self, title: str) -> str:
        """Extract price information from title"""
        # Look for price patterns
        price_patterns = [
            r'\$[\d,]+(?:\.\d{2})?',
            r'[\d]+%\s*off',
            r'save\s*\$?[\d,]+',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return "See deal for pricing"
    
    def scrape_hot_deals(self, max_deals: int = 20) -> List[Dict]:
        """Scrape hot deals from RedFlagDeals"""
        print("\n" + "=" * 70)
        print("🔍 Scraping RedFlagDeals Hot Deals")
        print("=" * 70)
        
        # Try multiple URL patterns
        urls_to_try = [
            f"{self.base_url}/deals/",
            f"{self.base_url}/deals/hot/",
            f"{self.base_url}/",
        ]
        
        html = None
        url = None
        
        for try_url in urls_to_try:
            print(f"\n  Trying URL: {try_url}")
            html = self.fetch_page(try_url)
            if html:
                url = try_url
                break
        
        if not html:
            print("✗ Could not fetch deals page")
            return []
        
        print(f"\n✓ Successfully fetched page, parsing content...")
        soup = BeautifulSoup(html, 'html.parser')
        deals = []
        
        # Try multiple selectors for deal containers - updated for 2024 structure
        deal_containers = []
        
        # Try various selectors
        selectors_to_try = [
            ('li', {'class': 'thread'}),
            ('div', {'class': 'thread'}),
            ('li', {'class': 'offer_container'}),
            ('div', {'class': 'offer_container'}),
            ('article', {}),
            ('div', {'class': re.compile(r'deal')}),
            ('li', {'class': re.compile(r'deal')}),
            ('a', {'class': re.compile(r'thread')}),
        ]
        
        for tag, attrs in selectors_to_try:
            containers = soup.find_all(tag, attrs, limit=max_deals * 2)
            if containers:
                deal_containers = containers
                print(f"  Found {len(containers)} containers using {tag} with {attrs}")
                break
        
        print(f"\n📦 Found {len(deal_containers)} potential deal containers")
        
        if not deal_containers:
            # Fallback: try to find any links with deal-like patterns
            print("  ⚠ No standard containers found, trying fallback method...")
            deal_containers = soup.find_all('a', href=re.compile(r'/deal'))[:max_deals * 2]
            print(f"  Fallback found {len(deal_containers)} links")
        
        for i, deal_elem in enumerate(deal_containers[:max_deals], 1):
            print(f"\n  Processing deal {i}/{min(len(deal_containers), max_deals)}...")
            
            deal_data = self.extract_deal_from_card(deal_elem)
            
            if deal_data and deal_data.get('title'):
                deals.append(deal_data)
                print(f"    ✓ {deal_data['title'][:60]}...")
                self.deals_scraped += 1
            else:
                print(f"    ✗ Could not extract deal data")
            
            # Be respectful with rate limiting
            if i < len(deal_containers):
                time.sleep(0.5)
        
        print("\n" + "=" * 70)
        print(f"✓ Successfully scraped {len(deals)} deals from RedFlagDeals")
        print("=" * 70)
        
        return deals
    
    def scrape_category_deals(self, category: str, max_deals: int = 15) -> List[Dict]:
        """Scrape deals from a specific category"""
        print(f"\n🔍 Scraping {category} deals from RedFlagDeals")
        
        # Map categories to RedFlagDeals URLs
        category_urls = {
            'electronics': '/deals/electronics/',
            'computers': '/deals/computers/',
            'home': '/deals/home/',
            'grocery': '/deals/grocery/',
            'entertainment': '/deals/entertainment/',
            'apparel': '/deals/apparel/'
        }
        
        category_lower = category.lower()
        category_path = category_urls.get(category_lower, '/deals/canada/')
        
        url = f"{self.base_url}{category_path}"
        html = self.fetch_page(url)
        
        if not html:
            print(f"✗ Could not fetch {category} deals")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        deals = []
        
        deal_containers = (
            soup.find_all('li', class_='thread') or
            soup.find_all('div', class_='deal')
        )
        
        print(f"📦 Found {len(deal_containers)} {category} deals")
        
        for i, deal_elem in enumerate(deal_containers[:max_deals], 1):
            deal_data = self.extract_deal_from_card(deal_elem)
            
            if deal_data and deal_data.get('title'):
                deals.append(deal_data)
                print(f"  ✓ [{i}] {deal_data['title'][:60]}...")
                self.deals_scraped += 1
            
            time.sleep(0.5)
        
        print(f"✓ Scraped {len(deals)} {category} deals")
        return deals


def main():
    """Test the scraper"""
    print("\n" + "=" * 70)
    print("RedFlagDeals Scraper - Test Run")
    print("=" * 70)
    
    scraper = RedFlagDealsScraperWorking()
    
    # Scrape hot deals
    deals = scraper.scrape_hot_deals(max_deals=10)
    
    # Display results
    if deals:
        print("\n" + "=" * 70)
        print("📋 Scraped Deals Summary")
        print("=" * 70)
        
        for i, deal in enumerate(deals[:5], 1):
            print(f"\n[{i}] {deal['title']}")
            print(f"    Store: {deal['store']}")
            print(f"    Category: {deal['category']}")
            print(f"    Price: {deal['price_discount']}")
            if deal.get('discount_percentage'):
                print(f"    Discount: {deal['discount_percentage']}% off")
            print(f"    Link: {deal['link'][:80]}...")
        
        if len(deals) > 5:
            print(f"\n... and {len(deals) - 5} more deals")
    else:
        print("\n⚠ No deals were scraped. The website structure may have changed.")
        print("This is common with web scraping - sites update frequently.")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

