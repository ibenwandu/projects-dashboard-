# Diagnostic: Test RL Parser Directly on Render

Since the `data/recommendations/` directory is ephemeral on Render, we can't check files directly. Instead, let's test the parser with the actual `gemini_final` text that's being generated.

## Step 1: Run Analysis and Capture gemini_final Text

Run this command to trigger an analysis and test the parser directly:

```bash
cd /opt/render/project/src
python -c "
import sys
sys.path.insert(0, '.')
from run_immediate_analysis import run_immediate_analysis
from src.trade_alerts_rl import RecommendationParser
import json

# Run analysis
print('Running analysis...')
success = run_immediate_analysis()

# The analysis already logs the result, but let's also test the parser directly
# We need to get the gemini_final text from the latest run
# Since we can't access files, let's check the database to see if anything was logged
from src.trade_alerts_rl import RecommendationDatabase
import sqlite3

db = RecommendationDatabase()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM recommendations')
total = cursor.fetchone()[0]
print(f'\n📊 Total Recommendations in Database: {total}')

if total > 0:
    cursor.execute('SELECT pair, direction, entry_price, stop_loss, llm_source FROM recommendations ORDER BY timestamp DESC LIMIT 5')
    for row in cursor.fetchall():
        print(f'  {row[4]}: {row[0]} {row[1]} @ {row[2]} SL: {row[3]}')
else:
    print('❌ Still 0 recommendations in database')
    print('   The parser is not extracting recommendations from the text')

conn.close()
"
```

## Step 2: Alternative - Test Parser with Sample Text

If the above doesn't work, we can test the parser directly with a sample of the actual Gemini Final format:

```bash
cd /opt/render/project/src
python -c "
from src.trade_alerts_rl import RecommendationParser
import re

# Sample text matching the actual format
sample_text = '''### **Trade Recommendation 1: Short GBP/USD (High Conviction)**

*   **Currency Pair:** GBP/USD
*   **Entry Price (Sell Limit):** **1.3450**
*   **Stop Loss:** **1.3520**
*   **Take Profit Target 1:** **1.3380**
*   **Take Profit Target 2:** **1.3300**
'''

parser = RecommendationParser()
recs = parser._parse_recommendations(sample_text, 'SYNTHESIS', '2026-01-12T01:54:31', 'test.json')
print(f'Parsed {len(recs)} recommendations from sample text')

if len(recs) > 0:
    for rec in recs:
        print(f'  {rec[\"pair\"]} {rec[\"direction\"]} @ {rec[\"entry_price\"]} SL: {rec[\"stop_loss\"]}')
else:
    print('❌ Parser returned 0 recommendations')
    print('Testing Pattern 5 match...')
    pattern_5 = r'###\s+\*\*Trade\s+Recommendation\s+\d+:\s+(?:Short|Long)\s+([A-Z]{3})[/\s]([A-Z]{3})'
    matches = list(re.finditer(rf'{pattern_5}(.*?)(?=\n###\s+\*\*Trade\s+Recommendation|\n---\n|$)', sample_text, re.IGNORECASE | re.DOTALL))
    print(f'Pattern 5 matches: {len(matches)}')
    if matches:
        m = matches[0]
        print(f'  Base: {m.group(1)}, Quote: {m.group(2)}')
        section = m.group(3) if len(m.groups()) >= 3 else ''
        print(f'  Section length: {len(section)}')
        print(f'  Section preview: {section[:200]}')
        
        # Test price extraction
        entry = parser._extract_price(section, ['Entry Price', 'Entry Price (Sell Limit)'])
        stop = parser._extract_price(section, ['Stop Loss'])
        print(f'  Entry extracted: {entry}')
        print(f'  Stop Loss extracted: {stop}')
"
```

## Step 3: Check Current Working Directory

The parser might be looking for files in the wrong location. Check where files are actually being saved:

```bash
cd /opt/render/project/src
python -c "
import os
print(f'Current directory: {os.getcwd()}')
print(f'Directory exists: {os.path.exists(\"data/recommendations\")}')
if os.path.exists('data/recommendations'):
    files = os.listdir('data/recommendations')
    print(f'Files in directory: {files[:10]}')
else:
    print('Directory does not exist (ephemeral filesystem)')
"
```
