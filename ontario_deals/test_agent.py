"""
Test script for Ontario Deals Agent
Demonstrates basic functionality with sample data
"""

from ontario_deals_agent import OntarioDealCurator, UserProfile, Deal
from utils import (
    extract_discount_percentage,
    categorize_deal,
    normalize_location,
    parse_expiry_date
)


def test_utils():
    """Test utility functions"""
    print("\n" + "=" * 70)
    print("Testing Utility Functions")
    print("=" * 70)
    
    # Test discount extraction
    print("\n1. Discount Extraction:")
    test_texts = [
        "30% off",
        "Save 50%",
        "Was $100, now $70",
        "Regular price $50, sale price $25"
    ]
    for text in test_texts:
        discount = extract_discount_percentage(text)
        print(f"   '{text}' -> {discount}%")
    
    # Test categorization
    print("\n2. Category Detection:")
    test_deals = [
        "Samsung 55\" QLED 4K TV",
        "Loblaws grocery sale",
        "Cineplex movie tickets",
        "Python certification course"
    ]
    for deal in test_deals:
        category = categorize_deal(deal)
        print(f"   '{deal}' -> {category}")
    
    # Test location normalization
    print("\n3. Location Normalization:")
    test_locations = [
        "toronto",
        "BRAMPTON, ONTARIO",
        "Waterloo"
    ]
    for location in test_locations:
        normalized = normalize_location(location)
        print(f"   '{location}' -> '{normalized}'")
    
    # Test expiry parsing
    print("\n4. Expiry Date Parsing:")
    test_expiries = [
        "Expires Dec 31",
        "Valid until tomorrow",
        "Ends in 3 days"
    ]
    for expiry in test_expiries:
        parsed = parse_expiry_date(expiry)
        print(f"   '{expiry}' -> {parsed}")


def test_agent_basic():
    """Test basic agent functionality"""
    print("\n" + "=" * 70)
    print("Testing Agent Basic Functions")
    print("=" * 70)
    
    # Initialize agent
    print("\n1. Initializing agent...")
    agent = OntarioDealCurator(db_path="test_deals.db")
    print("   ✓ Agent initialized")
    
    # Create user profile
    print("\n2. Creating user profile...")
    profile = UserProfile(
        interests=["Home & Electronics", "Groceries"],
        location="Toronto",
        postal_code="M5V 3A8",
        notification_preferences=["Email"]
    )
    agent.save_user_profile(profile)
    print("   ✓ Profile created")
    print(f"      Location: {profile.location}")
    print(f"      Interests: {', '.join(profile.interests)}")
    
    # Load profile
    print("\n3. Loading user profile...")
    loaded_profile = agent.load_user_profile()
    print("   ✓ Profile loaded")
    print(f"      Location: {loaded_profile.location}")
    print(f"      Interests: {', '.join(loaded_profile.interests)}")


def test_deal_management():
    """Test deal creation and retrieval"""
    print("\n" + "=" * 70)
    print("Testing Deal Management")
    print("=" * 70)
    
    agent = OntarioDealCurator(db_path="test_deals.db")
    
    # Create sample deals
    sample_deals = [
        Deal(
            category="Home & Electronics",
            title="Samsung 55\" QLED 4K TV – 30% off",
            store="Best Buy",
            price_discount="$699 (Was $999)",
            location="Toronto, ON",
            link="https://www.bestbuy.ca/",
            relevance="Matches your interest in electronics",
            discount_percentage=30.0,
            distance_km=2.5,
            expiry_date="2025-12-31"
        ),
        Deal(
            category="Groceries",
            title="Loblaws – 20% off produce and dairy",
            store="Loblaws",
            price_discount="Various prices",
            location="Toronto, ON",
            link="https://www.loblaws.ca/",
            relevance="Weekly grocery savings",
            discount_percentage=20.0,
            distance_km=1.2,
            expiry_date="2025-10-19"
        ),
        Deal(
            category="Entertainment",
            title="Cineplex Movie Tickets – 2 for $20",
            store="Cineplex",
            price_discount="$20 for 2 (Save 30%)",
            location="Mississauga, ON",
            link="https://www.cineplex.com/",
            relevance="Weekend entertainment deal",
            discount_percentage=30.0,
            distance_km=15.0,
            expiry_date="2025-10-31"
        ),
        Deal(
            category="Groceries",
            title="No Frills – Buy one get one free",
            store="No Frills",
            price_discount="BOGO on selected items",
            location="Brampton, ON",
            link="https://www.nofrills.ca/",
            relevance="Great for bulk shopping",
            discount_percentage=50.0,
            distance_km=20.0,
            expiry_date="2025-10-20"
        ),
        Deal(
            category="Home & Electronics",
            title="Apple AirPods Pro – $50 off",
            store="Amazon",
            price_discount="$199 (Was $249)",
            location="Online - Ships to Ontario",
            link="https://www.amazon.ca/",
            relevance="Popular electronics deal",
            discount_percentage=20.0,
            expiry_date="2025-11-15"
        )
    ]
    
    # Save deals
    print("\n1. Saving sample deals...")
    for i, deal in enumerate(sample_deals, 1):
        deal_id = agent.save_deal(deal)
        print(f"   ✓ Saved deal {i}: {deal.title[:40]}... (ID: {deal_id})")
    
    # Retrieve all deals
    print("\n2. Retrieving all deals...")
    all_deals = agent.get_deals()
    print(f"   ✓ Found {len(all_deals)} total deals")
    
    # Filter by category
    print("\n3. Filtering by category (Groceries)...")
    grocery_deals = agent.get_deals(category="Groceries")
    print(f"   ✓ Found {len(grocery_deals)} grocery deals:")
    for deal in grocery_deals:
        print(f"      - {deal.title}")
    
    # Filter by location
    print("\n4. Filtering by location (Toronto)...")
    toronto_deals = agent.get_deals(location="Toronto")
    print(f"   ✓ Found {len(toronto_deals)} deals in Toronto:")
    for deal in toronto_deals:
        print(f"      - {deal.title}")
    
    # Test ranking
    print("\n5. Testing deal ranking...")
    
    print("\n   a) Ranked by discount:")
    ranked_by_discount = agent.rank_deals(all_deals, sort_by="discount")
    for i, deal in enumerate(ranked_by_discount[:3], 1):
        print(f"      {i}. {deal.title} - {deal.discount_percentage}% off")
    
    print("\n   b) Ranked by distance:")
    ranked_by_distance = agent.rank_deals(all_deals, sort_by="distance")
    for i, deal in enumerate(ranked_by_distance[:3], 1):
        print(f"      {i}. {deal.title} - {deal.distance_km} km away")
    
    print("\n   c) Ranked by category:")
    ranked_by_category = agent.rank_deals(all_deals, sort_by="category")
    for i, deal in enumerate(ranked_by_category[:3], 1):
        print(f"      {i}. {deal.title} - {deal.category}")


def test_user_interactions():
    """Test user interaction logging"""
    print("\n" + "=" * 70)
    print("Testing User Interactions")
    print("=" * 70)
    
    agent = OntarioDealCurator(db_path="test_deals.db")
    
    # Log some interactions
    print("\n1. Logging user interactions...")
    interactions = [
        (1, "clicked"),
        (1, "saved"),
        (2, "clicked"),
        (3, "dismissed"),
        (4, "clicked")
    ]
    
    for deal_id, action in interactions:
        agent.log_user_interaction(deal_id, action)
        print(f"   ✓ Logged: Deal {deal_id} - {action}")
    
    print("\n   ✓ All interactions logged")
    print("   (In a full implementation, these would inform future recommendations)")


def test_profile_updates():
    """Test profile update functionality"""
    print("\n" + "=" * 70)
    print("Testing Profile Updates")
    print("=" * 70)
    
    agent = OntarioDealCurator(db_path="test_deals.db")
    
    # Load existing profile
    profile = agent.load_user_profile()
    print(f"\n1. Current interests: {', '.join(profile.interests)}")
    
    # Update interests
    print("\n2. Updating interests...")
    new_interests = ["Entertainment", "Courses/Certifications"]
    agent.update_user_interests(new_interests)
    print(f"   ✓ Updated to: {', '.join(agent.user_profile.interests)}")
    
    # Update location
    print("\n3. Current location:", profile.location)
    print("   Updating location...")
    agent.update_user_location("Brampton", postal_code="L6T 1A1")
    print(f"   ✓ Updated to: {agent.user_profile.location}")
    print(f"      Postal code: {agent.user_profile.postal_code}")


def test_output_formatting():
    """Test deal output formatting"""
    print("\n" + "=" * 70)
    print("Testing Output Formatting")
    print("=" * 70)
    
    agent = OntarioDealCurator(db_path="test_deals.db")
    
    # Get a deal and format it
    deals = agent.get_deals(limit=1)
    if deals:
        deal = deals[0]
        formatted = agent.format_deal_output(deal)
        
        print("\n1. Formatted deal output:")
        for key, value in formatted.items():
            print(f"   {key}: {value}")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 Ontario Deals Agent - Test Suite")
    print("=" * 70)
    
    try:
        test_utils()
        test_agent_basic()
        test_deal_management()
        test_user_interactions()
        test_profile_updates()
        test_output_formatting()
        
        print("\n" + "=" * 70)
        print("✅ All tests completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()



