# Quick Start Guide - Ontario Deals Agent

## 🚀 Get Started in 4 Steps

### Step 1: Install Dependencies

```bash
cd personal/ontario_deals
pip install -r requirements.txt
```

### Step 2: Test the Web Scraper (Optional but Recommended)

```bash
python test_scraper.py
```

This will verify that the RedFlagDeals scraper is working correctly.

### Step 3: Run the Agent

#### Option A: Interactive CLI (Recommended for beginners)
```bash
python cli.py
```

This will launch an interactive menu where you can:
- View and update your profile
- Search for deals
- Browse deals by category or location
- Add sample deals for testing

#### Option B: Basic Agent
```bash
python ontario_deals_agent.py
```

This will initialize the agent and show your profile and configuration.

#### Option C: Run Tests
```bash
python test_agent.py
```

This will run a comprehensive test suite demonstrating all features.

### Step 4: Start Using the Agent

#### First Time Setup
The agent will automatically:
1. Create a user profile on first run
2. Set up a local database (`deals_memory.db`)
3. Load default interests and preferences

#### Fetching Real Deals
Once you're in the CLI, choose **Option 4** to fetch real deals from RedFlagDeals.com! The scraper will:
- Search RedFlagDeals for hot Canadian deals
- Automatically categorize them based on your interests
- Save them to your local database
- Make them available for searching and filtering

## 📖 Quick Examples

### Using the Agent in Your Code

```python
from ontario_deals_agent import OntarioDealCurator, UserProfile, Deal

# Initialize
agent = OntarioDealCurator()

# Create/load profile
profile = agent.load_user_profile() or agent.create_default_profile()

# Update your preferences
agent.update_user_interests(["Home & Electronics", "Groceries"])
agent.update_user_location("Toronto", postal_code="M5V 3A8")

# Add a deal
deal = Deal(
    category="Groceries",
    title="Loblaws – 20% off produce",
    store="Loblaws",
    price_discount="Various prices",
    location="Toronto, ON",
    link="https://www.loblaws.ca/",
    relevance="Weekly savings",
    discount_percentage=20.0
)
agent.save_deal(deal)

# Search deals
deals = agent.get_deals(category="Groceries", location="Toronto")

# Rank by discount
ranked = agent.rank_deals(deals, sort_by="discount")

# Display
for deal in ranked[:5]:
    output = agent.format_deal_output(deal)
    print(f"{output['Category']}: {output['Deal']}")
    print(f"  {output['Price/Discount']} at {output['Store/Website']}")
    print(f"  {output['Link']}")
```

## 🎯 Common Tasks

### Update Your Interests

```python
agent.update_user_interests([
    "Home & Electronics",
    "Groceries",
    "Entertainment",
    "Courses/Certifications"
])
```

### Update Your Location

```python
agent.update_user_location("Brampton", postal_code="L6T 1A1")
```

### Search Deals

```python
# All deals
all_deals = agent.get_deals()

# By category
grocery_deals = agent.get_deals(category="Groceries")

# By location
toronto_deals = agent.get_deals(location="Toronto")

# Both
specific_deals = agent.get_deals(category="Entertainment", location="Toronto")
```

### Sort Deals

```python
deals = agent.get_deals()

# By discount percentage (highest first)
by_discount = agent.rank_deals(deals, sort_by="discount")

# By distance (closest first)
by_distance = agent.rank_deals(deals, sort_by="distance")

# By category
by_category = agent.rank_deals(deals, sort_by="category")

# By relevance (default)
by_relevance = agent.rank_deals(deals, sort_by="relevance")
```

### Log User Actions

```python
# Track what users do with deals
agent.log_user_interaction(deal_id=1, action="clicked")
agent.log_user_interaction(deal_id=2, action="saved")
agent.log_user_interaction(deal_id=3, action="dismissed")
```

## 🛠️ Customization

### Modify Configuration

Edit `config.json` to change:
- Supported sources
- Update frequency
- Default interests
- Notification preferences
- And more...

### Add API Keys

1. Copy `env_template.txt` to `.env`
2. Fill in your API keys:
   - OpenAI (for AI recommendations)
   - SendGrid (for email notifications)
   - Groupon, Amazon, etc. (for deal sources)

### Implement Custom Scrapers

See `example_scraper.py` for templates. Create your own scrapers by:

```python
from example_scraper import DealScraper

class MyCustomScraper(DealScraper):
    def __init__(self):
        super().__init__("MySource", "https://example.com")
    
    def parse_deals(self, html):
        # Your parsing logic here
        return deals
```

## 📊 Database Structure

The agent uses SQLite with three main tables:

1. **deals**: All discovered deals
2. **user_profile**: Your preferences and settings
3. **user_interactions**: History of your actions

Database file: `deals_memory.db` (auto-created)

## 🔧 Troubleshooting

### "No module named 'X'"
```bash
pip install -r requirements.txt
```

### "No deals found"
Add sample deals using the CLI or test script:
```bash
python cli.py  # Then choose option 8
```

### Database errors
Delete the database and restart:
```bash
rm deals_memory.db  # or del deals_memory.db on Windows
python ontario_deals_agent.py
```

## 📚 Next Steps

1. **Run the tests**: `python test_agent.py` to see all features in action
2. **Try the CLI**: `python cli.py` for interactive usage
3. **Implement scrapers**: Customize `example_scraper.py` for real deal sources
4. **Add notifications**: Set up SendGrid for email alerts
5. **Build a UI**: Create a web interface using Flask/FastAPI

## 🤝 Need Help?

- Read the full `README.md` for detailed documentation
- Check the `test_agent.py` for usage examples
- Explore `utils.py` for helper functions
- Examine `config.json` for all settings

---

**Happy deal hunting! 🎉**

