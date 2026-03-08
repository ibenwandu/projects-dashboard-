"""
Example web scraper for Ontario deals
This is a template/example showing how to scrape deals from various sources
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import time
from datetime import datetime
from utils import (
    extract_discount_percentage,
    parse_price,
    categorize_deal,
    clean_html,
    validate_url,
    normalize_location
)


class DealScraper:
    """Base class for deal scrapers"""
    
    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_page(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Fetch a web page with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch {url}: {e}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        return None
    
    def parse_deals(self, html: str) -> List[dict]:
        """Parse deals from HTML - to be implemented by subclasses"""
        raise NotImplementedError


class RedFlagDealsScraper(DealScraper):
    """Scraper for RedFlagDeals (example implementation)"""
    
    def __init__(self):
        super().__init__("RedFlagDeals", "https://www.redflagdeals.com")
    
    def parse_deals(self, html: str) -> List[dict]:
        """
        Parse deals from RedFlagDeals HTML
        This is a simplified example - actual implementation would need to be adjusted
        based on the current site structure
        """
        soup = BeautifulSoup(html, 'html.parser')
        deals = []
        
        # Example: Find deal containers (this selector would need to match actual site)
        deal_elements = soup.find_all('div', class_='deal_container')
        
        for element in deal_elements:
            try:
                # Extract deal information
                title_elem = element.find('h3', class_='deal_title')
                title = clean_html(title_elem.get_text()) if title_elem else "Unknown Deal"
                
                store_elem = element.find('span', class_='merchant_name')
                store = clean_html(store_elem.get_text()) if store_elem else "Unknown Store"
                
                price_elem = element.find('span', class_='price')
                price_text = clean_html(price_elem.get_text()) if price_elem else ""
                
                link_elem = element.find('a', class_='deal_link')
                link = link_elem.get('href', '') if link_elem else ""
                if link and not link.startswith('http'):
                    link = self.base_url + link
                
                # Extract discount
                discount = extract_discount_percentage(title + " " + price_text)
                
                # Categorize
                category = categorize_deal(title)
                
                deal = {
                    'category': category,
                    'title': title,
                    'store': store,
                    'price_discount': price_text or "See website",
                    'location': "Ontario",  # Default to Ontario
                    'link': link if validate_url(link) else self.base_url,
                    'relevance': f"Trending deal from {self.source_name}",
                    'discount_percentage': discount,
                    'timestamp': datetime.now().isoformat()
                }
                
                deals.append(deal)
                
            except Exception as e:
                print(f"Error parsing deal: {e}")
                continue
        
        return deals
    
    def scrape_hot_deals(self, location: str = "Ontario") -> List[dict]:
        """Scrape hot deals from RedFlagDeals"""
        url = f"{self.base_url}/deals/canada/{location.lower()}/"
        html = self.fetch_page(url)
        
        if html:
            deals = self.parse_deals(html)
            print(f"Found {len(deals)} deals from {self.source_name}")
            return deals
        
        return []


class GrouponScraper(DealScraper):
    """Scraper for Groupon (example implementation)"""
    
    def __init__(self):
        super().__init__("Groupon", "https://www.groupon.com")
    
    def parse_deals(self, html: str) -> List[dict]:
        """Parse deals from Groupon HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        deals = []
        
        # This is a simplified example - actual selectors would need to match site structure
        deal_elements = soup.find_all('div', class_='deal-tile')
        
        for element in deal_elements[:20]:  # Limit to first 20
            try:
                title_elem = element.find('h3')
                title = clean_html(title_elem.get_text()) if title_elem else "Unknown Deal"
                
                price_elem = element.find('span', class_='deal-price')
                price_text = clean_html(price_elem.get_text()) if price_elem else "See website"
                
                discount_elem = element.find('span', class_='discount-percentage')
                discount_text = clean_html(discount_elem.get_text()) if discount_elem else ""
                discount = extract_discount_percentage(discount_text)
                
                link_elem = element.find('a')
                link = link_elem.get('href', '') if link_elem else ""
                if link and not link.startswith('http'):
                    link = self.base_url + link
                
                category = categorize_deal(title)
                
                deal = {
                    'category': category,
                    'title': title,
                    'store': self.source_name,
                    'price_discount': price_text,
                    'location': "Ontario",
                    'link': link if validate_url(link) else self.base_url,
                    'relevance': f"Popular deal from {self.source_name}",
                    'discount_percentage': discount,
                    'timestamp': datetime.now().isoformat()
                }
                
                deals.append(deal)
                
            except Exception as e:
                print(f"Error parsing deal: {e}")
                continue
        
        return deals
    
    def scrape_local_deals(self, city: str = "Toronto") -> List[dict]:
        """Scrape local deals from Groupon"""
        url = f"{self.base_url}/local/{city.lower()}"
        html = self.fetch_page(url)
        
        if html:
            deals = self.parse_deals(html)
            print(f"Found {len(deals)} deals from {self.source_name} in {city}")
            return deals
        
        return []


class MultiSourceScraper:
    """Orchestrate scraping from multiple sources"""
    
    def __init__(self):
        self.scrapers = [
            RedFlagDealsScraper(),
            GrouponScraper()
        ]
    
    def scrape_all(self, location: str = "Ontario") -> List[dict]:
        """Scrape deals from all sources"""
        all_deals = []
        
        print(f"\n🔍 Scraping deals for {location}...")
        print("=" * 60)
        
        for scraper in self.scrapers:
            print(f"\nScraping from {scraper.source_name}...")
            try:
                if isinstance(scraper, RedFlagDealsScraper):
                    deals = scraper.scrape_hot_deals(location)
                elif isinstance(scraper, GrouponScraper):
                    deals = scraper.scrape_local_deals(location)
                else:
                    deals = []
                
                all_deals.extend(deals)
                
                # Be nice to servers
                time.sleep(2)
                
            except Exception as e:
                print(f"Error scraping {scraper.source_name}: {e}")
        
        print("\n" + "=" * 60)
        print(f"✓ Total deals scraped: {len(all_deals)}")
        
        return all_deals


def main():
    """Example usage of the scrapers"""
    print("Ontario Deals Scraper - Example")
    print("=" * 60)
    print("\nNOTE: This is an example implementation.")
    print("Actual web scraping requires:")
    print("1. Respecting robots.txt")
    print("2. Proper rate limiting")
    print("3. Terms of service compliance")
    print("4. Up-to-date CSS selectors for each site")
    print("=" * 60)
    
    # Example: Scrape from multiple sources
    scraper = MultiSourceScraper()
    deals = scraper.scrape_all("Toronto")
    
    # Display first few deals
    if deals:
        print("\n📦 Sample Deals:")
        print("=" * 60)
        for i, deal in enumerate(deals[:5], 1):
            print(f"\n[{i}] {deal['title']}")
            print(f"    Store: {deal['store']}")
            print(f"    Category: {deal['category']}")
            print(f"    Price: {deal['price_discount']}")
            if deal.get('discount_percentage'):
                print(f"    Discount: {deal['discount_percentage']}% off")
            print(f"    Link: {deal['link']}")


if __name__ == "__main__":
    main()



