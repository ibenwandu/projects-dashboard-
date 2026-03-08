"""
Ontario AI Deal Curator Agent

An autonomous AI agent that curates, ranks, and recommends the best deals,
discounts, and offers in Ontario, Canada, based on user interests, preferences, and location.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import sqlite3


@dataclass
class Deal:
    """Represents a single deal"""
    category: str
    title: str
    store: str
    price_discount: str
    location: str
    link: str
    relevance: str
    expiry_date: Optional[str] = None
    discount_percentage: Optional[float] = None
    distance_km: Optional[float] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class UserProfile:
    """Represents user profile with interests and preferences"""
    interests: List[str]
    location: str
    postal_code: Optional[str] = None
    budget_thresholds: Optional[Dict[str, float]] = None
    notification_preferences: Optional[List[str]] = None
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)


class OntarioDealCurator:
    """Main agent class for curating Ontario deals"""
    
    SYSTEM_PROMPT = """You are an autonomous Ontario Deals Curator AI. Your objectives:
- Curate deals in Ontario from multiple online sources and APIs.
- Remember user interests, history, and regional preferences.
- Provide categorized, map-based, and personalized recommendations.
- Schedule weekly summaries and offer on-demand alerts.
- Adapt dynamically to new user interests and trending deals.

When fetching deals, output for each:
- Category, Deal Title, Store, Price/Discount, Location, Link, Relevance.

Always ask user if interests or locations need updating."""
    
    def __init__(self, config_path: str = "config.json", db_path: str = "deals_memory.db"):
        """Initialize the deal curator agent"""
        self.config = self._load_config(config_path)
        self.db_path = db_path
        self._init_database()
        self.user_profile: Optional[UserProfile] = None
        
    def _load_config(self, config_path: str) -> Dict:
        """Load agent configuration from JSON file"""
        config_file = os.path.join(os.path.dirname(__file__), config_path)
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _init_database(self):
        """Initialize SQLite database for storing deals and user history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create deals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                store TEXT,
                price_discount TEXT,
                location TEXT,
                link TEXT,
                relevance TEXT,
                expiry_date TEXT,
                discount_percentage REAL,
                distance_km REAL,
                timestamp TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Create user interactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id INTEGER,
                action TEXT,
                timestamp TEXT,
                FOREIGN KEY (deal_id) REFERENCES deals(id)
            )
        ''')
        
        # Create user profile table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                interests TEXT,
                location TEXT,
                postal_code TEXT,
                budget_thresholds TEXT,
                notification_preferences TEXT,
                last_updated TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_user_profile(self) -> Optional[UserProfile]:
        """Load user profile from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_profile WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            profile_data = {
                'interests': json.loads(row[1]),
                'location': row[2],
                'postal_code': row[3],
                'budget_thresholds': json.loads(row[4]) if row[4] else None,
                'notification_preferences': json.loads(row[5]) if row[5] else None
            }
            self.user_profile = UserProfile.from_dict(profile_data)
            return self.user_profile
        return None
    
    def save_user_profile(self, profile: UserProfile):
        """Save user profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_profile 
            (id, interests, location, postal_code, budget_thresholds, notification_preferences, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            1,
            json.dumps(profile.interests),
            profile.location,
            profile.postal_code,
            json.dumps(profile.budget_thresholds) if profile.budget_thresholds else None,
            json.dumps(profile.notification_preferences) if profile.notification_preferences else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        self.user_profile = profile
    
    def create_default_profile(self) -> UserProfile:
        """Create a default user profile based on config"""
        profile = UserProfile(
            interests=self.config['user_profile']['interests'],
            location=self.config['location_preferences']['default_region'],
            notification_preferences=['Email']
        )
        self.save_user_profile(profile)
        return profile
    
    def save_deal(self, deal: Deal) -> int:
        """Save a deal to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO deals 
            (category, title, store, price_discount, location, link, relevance, 
             expiry_date, discount_percentage, distance_km, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            deal.category, deal.title, deal.store, deal.price_discount,
            deal.location, deal.link, deal.relevance, deal.expiry_date,
            deal.discount_percentage, deal.distance_km, deal.timestamp
        ))
        
        deal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return deal_id
    
    def get_deals(self, category: Optional[str] = None, 
                  location: Optional[str] = None,
                  limit: int = 50) -> List[Deal]:
        """Retrieve deals from database with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM deals WHERE is_active = 1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        if location:
            query += ' AND location LIKE ?'
            params.append(f'%{location}%')
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        deals = []
        for row in rows:
            deal = Deal(
                category=row[1],
                title=row[2],
                store=row[3],
                price_discount=row[4],
                location=row[5],
                link=row[6],
                relevance=row[7],
                expiry_date=row[8],
                discount_percentage=row[9],
                distance_km=row[10],
                timestamp=row[11]
            )
            deals.append(deal)
        
        return deals
    
    def log_user_interaction(self, deal_id: int, action: str):
        """Log user interaction with a deal (clicked, dismissed, saved, etc.)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_interactions (deal_id, action, timestamp)
            VALUES (?, ?, ?)
        ''', (deal_id, action, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def rank_deals(self, deals: List[Deal], sort_by: str = "relevance") -> List[Deal]:
        """Rank deals based on sorting criteria"""
        if sort_by == "discount":
            return sorted(deals, key=lambda x: x.discount_percentage or 0, reverse=True)
        elif sort_by == "distance":
            return sorted(deals, key=lambda x: x.distance_km or float('inf'))
        elif sort_by == "category":
            return sorted(deals, key=lambda x: x.category)
        else:  # relevance or default
            return deals
    
    def format_deal_output(self, deal: Deal) -> Dict[str, Any]:
        """Format a deal for output according to config specification"""
        return {
            "Category": deal.category,
            "Deal": deal.title,
            "Store/Website": deal.store,
            "Price/Discount": deal.price_discount,
            "Location": deal.location,
            "Link": deal.link,
            "Relevance": deal.relevance
        }
    
    def generate_session_prompt(self) -> str:
        """Generate session start prompt for user"""
        prompts = self.config['interaction_logic']['session_start_prompts']
        return "\n".join(prompts)
    
    def get_supported_sources(self) -> List[str]:
        """Get list of supported deal sources"""
        return self.config['scope']['supported_sources']
    
    def get_session_modes(self) -> List[str]:
        """Get available session modes"""
        return self.config['interaction_logic']['session_modes']
    
    def update_user_interests(self, new_interests: List[str]):
        """Update user interests dynamically"""
        if self.user_profile:
            self.user_profile.interests = new_interests
            self.save_user_profile(self.user_profile)
    
    def update_user_location(self, new_location: str, postal_code: Optional[str] = None):
        """Update user location preferences"""
        if self.user_profile:
            self.user_profile.location = new_location
            if postal_code:
                self.user_profile.postal_code = postal_code
            self.save_user_profile(self.user_profile)
    
    def fetch_deals_from_web(self, max_deals: int = 20) -> int:
        """Fetch deals from RedFlagDeals and save them to database"""
        try:
            from redflagdeals_scraper import RedFlagDealsScraperWorking
            
            scraper = RedFlagDealsScraperWorking()
            deals_data = scraper.scrape_hot_deals(max_deals=max_deals)
            
            saved_count = 0
            for deal_data in deals_data:
                deal = Deal(
                    category=deal_data['category'],
                    title=deal_data['title'],
                    store=deal_data['store'],
                    price_discount=deal_data['price_discount'],
                    location=deal_data['location'],
                    link=deal_data['link'],
                    relevance=deal_data['relevance'],
                    discount_percentage=deal_data.get('discount_percentage'),
                    timestamp=deal_data['timestamp']
                )
                self.save_deal(deal)
                saved_count += 1
            
            return saved_count
            
        except ImportError as e:
            print(f"Error: Could not import scraper: {e}")
            return 0
        except Exception as e:
            print(f"Error fetching deals: {e}")
            return 0


def main():
    """Main entry point for the agent"""
    print("=" * 60)
    print("Ontario AI Deal Curator Agent")
    print("=" * 60)
    
    # Initialize agent
    agent = OntarioDealCurator()
    
    # Load or create user profile
    profile = agent.load_user_profile()
    if not profile:
        print("\nWelcome! Setting up your profile...")
        profile = agent.create_default_profile()
        print(f"Profile created with default interests: {', '.join(profile.interests)}")
        print(f"Default location: {profile.location}")
    else:
        print(f"\nWelcome back!")
        print(f"Your interests: {', '.join(profile.interests)}")
        print(f"Your location: {profile.location}")
    
    # Display session prompts
    print("\n" + agent.generate_session_prompt())
    
    # Display available sources
    print(f"\n📍 Supported sources ({len(agent.get_supported_sources())}):")
    sources = agent.get_supported_sources()
    for i in range(0, len(sources), 4):
        print("  " + ", ".join(sources[i:i+4]))
    
    # Display session modes
    print(f"\n🔧 Available modes: {', '.join(agent.get_session_modes())}")
    
    print("\n" + "=" * 60)
    print("Agent is ready to curate deals!")
    print("=" * 60)


if __name__ == "__main__":
    main()

