# RedFlagDeals Web Scraper - Documentation

## 🎉 What's New

Your Ontario Deals Agent now has a **working web scraper** that automatically fetches real deals from RedFlagDeals.com!

## 🚀 How to Use

### Option 1: Through the CLI (Easiest)

1. Run the CLI app:
   ```bash
   python cli.py
   ```

2. Choose **Option 4: 🌐 Fetch new deals from web (RedFlagDeals)**

3. Enter how many deals you want to fetch (recommended: 10-20)

4. Wait while the scraper works (takes about 30-60 seconds for 15 deals)

5. Done! Now you can view, search, and filter the deals using other menu options

### Option 2: Test the Scraper First

Before using it in the app, you can test that it's working:

```bash
python test_scraper.py
```

This will fetch 5 deals and show you the results.

### Option 3: Use in Your Own Code

```python
from ontario_deals_agent import OntarioDealCurator

# Create agent
agent = OntarioDealCurator()

# Fetch 20 deals from web
saved_count = agent.fetch_deals_from_web(max_deals=20)

print(f"Fetched {saved_count} deals!")

# Now view them
deals = agent.get_deals()
for deal in deals:
    print(f"{deal.title} - {deal.store}")
```

## 📋 What the Scraper Does

1. **Connects to RedFlagDeals.com** - Canada's largest deal-sharing community
2. **Extracts deal information**:
   - Title
   - Store/Merchant
   - Price/Discount
   - Category (auto-detected)
   - Link to full deal
   - Discount percentage (when available)

3. **Saves to your database** - All deals are stored locally in `deals_memory.db`

4. **Respects the website**:
   - 2-second delay between requests
   - Proper User-Agent headers
   - Rate limiting to avoid overwhelming the server

## 🎯 Features

### Automatic Categorization
The scraper automatically categorizes deals into:
- Home & Electronics
- Groceries
- Entertainment
- Courses/Certifications
- Fashion & Beauty
- Health & Wellness
- Automotive

### Smart Extraction
- Extracts discount percentages from titles
- Identifies store names automatically
- Cleans HTML and formats text properly
- Handles various deal formats

## ⚙️ Configuration

### Adjust Number of Deals
Default: 15 deals
Recommended: 10-20 deals (faster)
Maximum: 50 deals (takes several minutes)

### Rate Limiting
The scraper includes built-in delays:
- 2 seconds between page requests
- 0.5 seconds between individual deals
- Exponential backoff on errors

### Error Handling
The scraper handles:
- Network timeouts
- Connection errors
- Page structure changes
- Missing data gracefully

## 🛠️ Troubleshooting

### No deals were scraped

**Possible reasons:**
1. **Website structure changed** - Most common! Websites update frequently
2. **Internet connection issue** - Check your connection
3. **Website blocking** - RedFlagDeals may be blocking automated access
4. **Missing dependencies** - Run `pip install -r requirements.txt`

**Solutions:**
- Try again later
- Use sample deals (Option 9 in CLI)
- Check if RedFlagDeals.com is accessible in your browser

### Scraper is slow

**This is normal!** Web scraping requires:
- Respecting rate limits (2+ seconds per request)
- Downloading and parsing HTML
- Processing each deal individually

For 15 deals, expect: **30-60 seconds**

### Some deals missing information

**This happens when:**
- Deal listings have unusual formats
- Information is in images instead of text
- Deal is expired or removed

The scraper will still save the deal with whatever information it can extract.

## 📊 Technical Details

### Files Involved

1. **`redflagdeals_scraper.py`** - Main scraper implementation
   - `RedFlagDealsScraperWorking` class
   - Web fetching and parsing logic
   - Deal extraction methods

2. **`ontario_deals_agent.py`** - Integration
   - `fetch_deals_from_web()` method
   - Converts scraped data to Deal objects
   - Saves to database

3. **`cli.py`** - User interface
   - `fetch_new_deals()` function
   - Menu option 4
   - User prompts and feedback

### Dependencies Used

- **requests** - HTTP requests to fetch pages
- **BeautifulSoup4** - Parse HTML and extract data
- **utils.py** - Helper functions for categorization, formatting

### How It Works

```
1. User requests deals
   ↓
2. Scraper fetches RedFlagDeals.com HTML
   ↓
3. BeautifulSoup parses the page structure
   ↓
4. Extract deal cards/containers
   ↓
5. For each deal:
   - Extract title, store, price, link
   - Auto-categorize
   - Calculate discount percentage
   ↓
6. Convert to Deal objects
   ↓
7. Save to SQLite database
   ↓
8. Show results to user
```

## 🔮 Future Enhancements

Potential improvements:
- [ ] Add more sources (Groupon, Flipp, etc.)
- [ ] Filter deals by user interests before saving
- [ ] Add deal expiry tracking
- [ ] Implement automatic daily scraping
- [ ] Add image downloading
- [ ] Email notifications for new deals
- [ ] Location-based filtering during scraping

## ⚖️ Legal & Ethical Notes

**Important:**
- Only scrapes publicly available information
- Respects rate limits to avoid server overload
- Includes proper User-Agent identification
- For personal use only
- Always check website Terms of Service
- Commercial use may require permission

## 🤝 Contributing

To improve the scraper:
1. Update CSS selectors in `redflagdeals_scraper.py`
2. Add error handling for edge cases
3. Implement additional sources
4. Improve categorization logic

## 📞 Support

If the scraper stops working:
1. Check if RedFlagDeals.com is accessible
2. Run `python test_scraper.py` to diagnose
3. Website structure may have changed - CSS selectors need updating
4. Use sample deals as fallback

---

**Happy deal hunting! 🎉**



