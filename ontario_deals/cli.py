"""
Command-line interface for the Ontario Deals Agent
"""

import sys
from ontario_deals_agent import OntarioDealCurator, UserProfile, Deal
from utils import format_currency, is_deal_expired
import json


def print_banner():
    """Print welcome banner"""
    print("\n" + "=" * 70)
    print("🎯 Ontario AI Deal Curator Agent")
    print("=" * 70)


def print_menu():
    """Print main menu"""
    print("\n📋 Main Menu:")
    print("  1. View my profile")
    print("  2. Update interests")
    print("  3. Update location")
    print("  4. 🌐 Fetch new deals from web (RedFlagDeals)")
    print("  5. Search deals")
    print("  6. View all deals")
    print("  7. View deals by category")
    print("  8. View deals by location")
    print("  9. Add a sample deal (for testing)")
    print(" 10. View supported sources")
    print("  0. Exit")
    print()


def print_profile(profile: UserProfile):
    """Print user profile"""
    print("\n" + "=" * 70)
    print("👤 Your Profile")
    print("=" * 70)
    print(f"📍 Location: {profile.location}")
    if profile.postal_code:
        print(f"📮 Postal Code: {profile.postal_code}")
    print(f"❤️  Interests: {', '.join(profile.interests)}")
    if profile.notification_preferences:
        print(f"🔔 Notifications: {', '.join(profile.notification_preferences)}")
    print("=" * 70)


def print_deal(deal: Deal, index: int = None):
    """Print a single deal"""
    prefix = f"[{index}] " if index is not None else ""
    expired = " ⚠️ EXPIRED" if deal.expiry_date and is_deal_expired(deal.expiry_date) else ""
    
    print(f"\n{prefix}🏷️  {deal.title}{expired}")
    print(f"   Category: {deal.category}")
    print(f"   Store: {deal.store}")
    print(f"   Price: {deal.price_discount}")
    if deal.discount_percentage:
        print(f"   Discount: {deal.discount_percentage}% off")
    print(f"   Location: {deal.location}")
    if deal.distance_km:
        print(f"   Distance: {deal.distance_km} km away")
    if deal.expiry_date:
        print(f"   Expires: {deal.expiry_date}")
    print(f"   Link: {deal.link}")
    print(f"   Why relevant: {deal.relevance}")


def get_input(prompt: str, options: list = None) -> str:
    """Get user input with optional validation"""
    while True:
        response = input(prompt).strip()
        if not options or response in options:
            return response
        print(f"Invalid input. Please choose from: {', '.join(options)}")


def update_interests(agent: OntarioDealCurator):
    """Interactive interest update"""
    print("\n📝 Update Your Interests")
    print("-" * 70)
    
    current_interests = agent.user_profile.interests if agent.user_profile else []
    print(f"Current interests: {', '.join(current_interests)}")
    
    print("\nAvailable categories:")
    categories = [
        "Home & Electronics",
        "Groceries",
        "Entertainment",
        "Courses/Certifications",
        "Fashion & Beauty",
        "Health & Wellness",
        "Automotive"
    ]
    
    for i, category in enumerate(categories, 1):
        marker = "✓" if category in current_interests else " "
        print(f"  [{marker}] {i}. {category}")
    
    print("\nEnter category numbers separated by commas (e.g., 1,2,4)")
    print("Or press Enter to keep current interests")
    
    response = input("➤ ").strip()
    
    if response:
        try:
            indices = [int(x.strip()) for x in response.split(',')]
            new_interests = [categories[i-1] for i in indices if 1 <= i <= len(categories)]
            
            if new_interests:
                agent.update_user_interests(new_interests)
                print(f"\n✓ Interests updated to: {', '.join(new_interests)}")
            else:
                print("\n⚠️  No valid categories selected")
        except (ValueError, IndexError):
            print("\n⚠️  Invalid input")


def update_location(agent: OntarioDealCurator):
    """Interactive location update"""
    print("\n📍 Update Your Location")
    print("-" * 70)
    
    current_location = agent.user_profile.location if agent.user_profile else "Ontario"
    print(f"Current location: {current_location}")
    
    print("\nPopular Ontario cities:")
    cities = [
        "Toronto", "Ottawa", "Mississauga", "Brampton", "Hamilton",
        "London", "Markham", "Vaughan", "Kitchener", "Waterloo"
    ]
    
    for i, city in enumerate(cities, 1):
        print(f"  {i}. {city}")
    
    print("\nEnter city number or type a custom location:")
    response = input("➤ ").strip()
    
    if response:
        try:
            # Try as number first
            index = int(response)
            if 1 <= index <= len(cities):
                new_location = cities[index - 1]
            else:
                print("Invalid number")
                return
        except ValueError:
            # Use as custom location
            new_location = response
        
        postal_code = input("Postal code (optional, press Enter to skip): ").strip() or None
        
        agent.update_user_location(new_location, postal_code)
        print(f"\n✓ Location updated to: {new_location}")
        if postal_code:
            print(f"  Postal code: {postal_code}")


def search_deals(agent: OntarioDealCurator):
    """Interactive deal search"""
    print("\n🔍 Search Deals")
    print("-" * 70)
    
    print("Filter by category? (press Enter to skip)")
    if agent.user_profile and agent.user_profile.interests:
        for i, interest in enumerate(agent.user_profile.interests, 1):
            print(f"  {i}. {interest}")
        category_input = input("➤ ").strip()
        
        if category_input:
            try:
                cat_index = int(category_input)
                category = agent.user_profile.interests[cat_index - 1]
            except (ValueError, IndexError):
                category = None
        else:
            category = None
    else:
        category = None
    
    print("\nFilter by location? (press Enter to skip)")
    location = input("➤ ").strip() or None
    
    print("\nSort by:")
    print("  1. Relevance (default)")
    print("  2. Discount percentage")
    print("  3. Distance")
    print("  4. Category")
    sort_input = input("➤ ").strip()
    
    sort_map = {
        "1": "relevance",
        "2": "discount",
        "3": "distance",
        "4": "category"
    }
    sort_by = sort_map.get(sort_input, "relevance")
    
    # Get deals
    deals = agent.get_deals(category=category, location=location)
    
    if not deals:
        print("\n😔 No deals found matching your criteria")
        return
    
    # Rank deals
    ranked_deals = agent.rank_deals(deals, sort_by=sort_by)
    
    print(f"\n✨ Found {len(ranked_deals)} deal(s)")
    print("=" * 70)
    
    for i, deal in enumerate(ranked_deals[:10], 1):  # Show top 10
        print_deal(deal, i)
    
    if len(ranked_deals) > 10:
        print(f"\n... and {len(ranked_deals) - 10} more deals")


def view_all_deals(agent: OntarioDealCurator):
    """View all active deals"""
    print("\n📦 All Active Deals")
    print("=" * 70)
    
    deals = agent.get_deals()
    
    if not deals:
        print("\n😔 No deals found. Try adding some first!")
        return
    
    for i, deal in enumerate(deals[:20], 1):  # Show top 20
        print_deal(deal, i)
    
    if len(deals) > 20:
        print(f"\n... and {len(deals) - 20} more deals")


def fetch_new_deals(agent: OntarioDealCurator):
    """Fetch new deals from RedFlagDeals"""
    print("\n🌐 Fetching Deals from RedFlagDeals")
    print("-" * 70)
    
    print("\nHow many deals would you like to fetch? (recommended: 10-20)")
    max_deals_input = input("Enter number (press Enter for 15): ").strip()
    
    try:
        max_deals = int(max_deals_input) if max_deals_input else 15
        max_deals = min(max(max_deals, 1), 50)  # Limit between 1-50
    except ValueError:
        max_deals = 15
    
    print(f"\n⏳ Fetching up to {max_deals} deals from RedFlagDeals...")
    print("This may take a minute. Please wait...\n")
    
    saved_count = agent.fetch_deals_from_web(max_deals=max_deals)
    
    if saved_count > 0:
        print(f"\n✅ Successfully fetched and saved {saved_count} deals!")
        print("You can now view them using the menu options.")
    else:
        print("\n⚠️  No deals were fetched. Please check your internet connection.")
        print("The website structure may have changed, or there was a connection issue.")


def add_sample_deal(agent: OntarioDealCurator):
    """Add a sample deal for testing"""
    print("\n➕ Add Sample Deal")
    print("-" * 70)
    
    samples = [
        Deal(
            category="Home & Electronics",
            title="Samsung 55\" QLED 4K TV – 30% off",
            store="Best Buy",
            price_discount="$699 (Was $999)",
            location="Toronto, ON",
            link="https://www.bestbuy.ca/",
            relevance="Matches your interest in electronics",
            discount_percentage=30.0,
            expiry_date="2025-12-31"
        ),
        Deal(
            category="Groceries",
            title="Loblaws – 20% off produce and dairy",
            store="Loblaws",
            price_discount="Various prices",
            location="Brampton, ON",
            link="https://www.loblaws.ca/",
            relevance="Weekly grocery savings",
            discount_percentage=20.0,
            expiry_date="2025-10-19"
        ),
        Deal(
            category="Entertainment",
            title="Cineplex Movie Tickets – 2 for $20",
            store="Cineplex",
            price_discount="$20 for 2 (Save 30%)",
            location="Toronto, ON",
            link="https://www.cineplex.com/",
            relevance="Weekend entertainment deal",
            discount_percentage=30.0,
            expiry_date="2025-10-31"
        )
    ]
    
    print("Select a sample deal to add:")
    for i, deal in enumerate(samples, 1):
        print(f"  {i}. {deal.title}")
    
    choice = input("➤ ").strip()
    
    try:
        index = int(choice) - 1
        if 0 <= index < len(samples):
            deal_id = agent.save_deal(samples[index])
            print(f"\n✓ Deal added successfully (ID: {deal_id})")
        else:
            print("\n⚠️  Invalid choice")
    except ValueError:
        print("\n⚠️  Invalid input")


def main():
    """Main CLI loop"""
    print_banner()
    
    # Initialize agent
    agent = OntarioDealCurator()
    
    # Load or create profile
    profile = agent.load_user_profile()
    if not profile:
        print("\n👋 Welcome! Let's set up your profile...")
        profile = agent.create_default_profile()
        print(f"\n✓ Profile created!")
    else:
        print(f"\n👋 Welcome back!")
    
    print_profile(profile)
    
    # Main loop
    while True:
        print_menu()
        choice = get_input("Choose an option: ", 
                          ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
        
        if choice == "0":
            print("\n👋 Goodbye! Happy deal hunting!")
            break
        
        elif choice == "1":
            print_profile(agent.user_profile)
        
        elif choice == "2":
            update_interests(agent)
        
        elif choice == "3":
            update_location(agent)
        
        elif choice == "4":
            fetch_new_deals(agent)
        
        elif choice == "5":
            search_deals(agent)
        
        elif choice == "6":
            view_all_deals(agent)
        
        elif choice == "7":
            category = input("\nEnter category name: ").strip()
            deals = agent.get_deals(category=category)
            if deals:
                print(f"\n✨ Found {len(deals)} deal(s) in {category}")
                for i, deal in enumerate(deals[:10], 1):
                    print_deal(deal, i)
            else:
                print(f"\n😔 No deals found in {category}")
        
        elif choice == "8":
            location = input("\nEnter location: ").strip()
            deals = agent.get_deals(location=location)
            if deals:
                print(f"\n✨ Found {len(deals)} deal(s) in {location}")
                for i, deal in enumerate(deals[:10], 1):
                    print_deal(deal, i)
            else:
                print(f"\n😔 No deals found in {location}")
        
        elif choice == "9":
            add_sample_deal(agent)
        
        elif choice == "10":
            sources = agent.get_supported_sources()
            print(f"\n📋 Supported Sources ({len(sources)}):")
            print("-" * 70)
            for i in range(0, len(sources), 3):
                print("  " + ", ".join(sources[i:i+3]))
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

