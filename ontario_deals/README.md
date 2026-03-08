# Ontario AI Deal Curator Agent

An autonomous AI agent that curates, ranks, and recommends the best deals, discounts, and offers in Ontario, Canada, based on user interests, preferences, and location.

## 🎯 Overview

The Ontario AI Deal Curator is an intelligent agent designed to help you discover and track the best deals across Ontario. It learns from your preferences, remembers your interactions, and provides personalized recommendations based on your interests and location.

## ✨ Features

### Core Capabilities
- **Smart Deal Curation**: Automatically discovers and curates deals from trusted sources
- **Personalized Recommendations**: Learns from your behavior and preferences
- **Location-Aware**: Filters deals by city, postal code, or region
- **Category-Based Organization**: Organizes deals by your interests
- **Intelligent Ranking**: Ranks deals by relevance, discount percentage, expiry, and proximity
- **Memory-Enabled**: Remembers your past interactions and preferences
- **Proactive Alerts**: Notifies you about new or expiring deals

### Supported Categories
- Home & Electronics
- Groceries
- Entertainment
- Courses/Certifications

### Supported Sources
The agent can curate deals from 18+ sources including:
- **Deal Aggregators**: RedFlagDeals, Groupon, WagJag, RetailMeNot
- **Grocery**: Loblaws, No Frills, Metro, Sobeys
- **Retail**: Amazon, Costco, Walmart, Canadian Tire, Best Buy, Staples
- **Entertainment**: Cineplex, LCBO
- **Flyer Services**: Flipp, Reebee
- **Education**: Local training institutes

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Navigate to the agent directory:
```bash
cd personal/ontario_deals
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Run the agent:
```bash
python ontario_deals_agent.py
```

## 📖 Usage

### Basic Usage

```python
from ontario_deals_agent import OntarioDealCurator, UserProfile, Deal

# Initialize the agent
agent = OntarioDealCurator()

# Create or load user profile
profile = agent.load_user_profile()
if not profile:
    profile = agent.create_default_profile()

# Update interests
agent.update_user_interests([
    "Home & Electronics",
    "Groceries",
    "Entertainment"
])

# Update location
agent.update_user_location("Toronto", postal_code="M5V 3A8")

# Get deals
deals = agent.get_deals(category="Groceries", location="Toronto")

# Rank deals
ranked_deals = agent.rank_deals(deals, sort_by="discount")

# Format for display
for deal in ranked_deals[:5]:
    print(agent.format_deal_output(deal))
```

### Session Modes

The agent supports three modes of operation:

1. **Weekly Summary**: Get a curated list of deals every Sunday at 9:00 AM
2. **On-Demand Search**: Search for deals whenever you need them
3. **Location-Based Search**: Find deals near your current location

### Sorting Options

Deals can be sorted by:
- **Category**: Group by interest category
- **Location**: Show deals near you first
- **Trending Relevance**: Based on popularity and your interests
- **Discount**: Highest discount percentage first
- **Distance**: Closest deals first

## 🔧 Configuration

The agent behavior is controlled by `config.json`. Key settings include:

- **Region**: Default is Ontario, Canada
- **Update Frequency**: Weekly digest on Sunday 9:00 AM + on-demand
- **Notification Channels**: Email, Chat, Push
- **API Integration**: Support for Flipp, Reebee, Groupon, Amazon APIs
- **Memory**: Vector memory enabled for learning user preferences

## 📊 Data Storage

The agent uses SQLite to store:
- **Deals**: All discovered deals with metadata
- **User Profile**: Your interests, location, and preferences
- **Interactions**: Your clicks, dismissals, and saves for learning

Database file: `deals_memory.db`

## 🔒 Privacy & Ethics

- **Data Privacy**: User preferences are stored locally; no personal identifiers shared
- **Content Scope**: Only publicly available deals are curated
- **Verification**: Deals are verified before recommendation
- **Bias Disclosure**: Transparent about deal sources and ranking criteria

## 📱 Alert Triggers

The agent can send alerts for:
- New deals under your specified budget
- High discount threshold met (e.g., >50% off)
- Deals within 5km of your location
- Deals about to expire in your favorite categories

## 🎓 Example Use Cases

### Example 1: Grocery Shopping
```python
agent.update_user_interests(["Groceries"])
agent.update_user_location("Brampton")
deals = agent.get_deals(category="Groceries", location="Brampton")
```

Expected output:
- Loblaws – 20% off on produce and dairy items
- No Frills – Buy one get one free on selected items
- Metro – Weekly specials on meat and seafood

### Example 2: Electronics Hunt
```python
agent.update_user_interests(["Home & Electronics"])
deals = agent.get_deals(category="Home & Electronics")
ranked = agent.rank_deals(deals, sort_by="discount")
```

Expected output:
- Samsung 55" QLED 4K TV – 30% off at Best Buy
- Apple AirPods Pro – $50 off at Amazon
- Gaming laptops – Up to 40% off at Costco

### Example 3: Weekend Entertainment
```python
agent.update_user_interests(["Entertainment"])
agent.update_user_location("Toronto")
deals = agent.get_deals(category="Entertainment", location="Toronto")
```

Expected output:
- Cineplex Movie Tickets – 2 for $20 (Save 30%)
- LCBO – Special pricing on wine selection
- Local concert tickets – Early bird pricing

## 🛠️ Development

### Project Structure
```
ontario_deals/
├── config.json                  # Agent configuration
├── ontario_deals_agent.py       # Main agent implementation
├── deals_memory.db             # SQLite database (auto-generated)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── scrapers/                   # Deal scrapers (future)
    ├── redflagdeals_scraper.py
    ├── groupon_scraper.py
    └── flipp_scraper.py
```

### Future Enhancements
- [ ] Implement web scrapers for each deal source
- [ ] Add API integrations (Flipp, Reebee, Groupon, Amazon)
- [ ] Build web interface for easier interaction
- [ ] Add email notification system
- [ ] Implement map visualization for nearby deals
- [ ] Add mobile app support
- [ ] Integrate with calendar for deal expiry reminders
- [ ] Add collaborative filtering for better recommendations

## 📄 License

This project is part of a personal agent collection.

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

## 📧 Contact

For questions or feedback about this agent, please refer to the main project documentation.

---

**Version**: 2.0  
**Last Updated**: October 2025  
**Region**: Ontario, Canada



