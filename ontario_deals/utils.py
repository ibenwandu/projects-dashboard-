"""
Utility functions for the Ontario Deals Agent
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib


def extract_discount_percentage(text: str) -> Optional[float]:
    """
    Extract discount percentage from text
    
    Examples:
        "30% off" -> 30.0
        "Save 50%" -> 50.0
        "Was $100, now $70" -> 30.0
    """
    # Look for percentage pattern
    percentage_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if percentage_match:
        return float(percentage_match.group(1))
    
    # Look for price comparison pattern
    price_match = re.search(r'(?:was|original)\s*\$?(\d+(?:\.\d+)?)[^\d]*(?:now|sale)\s*\$?(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if price_match:
        original = float(price_match.group(1))
        current = float(price_match.group(2))
        if original > 0:
            return ((original - current) / original) * 100
    
    return None


def parse_price(text: str) -> Optional[Tuple[float, str]]:
    """
    Parse price from text, return (amount, currency)
    
    Examples:
        "$49.99" -> (49.99, "CAD")
        "C$100" -> (100.0, "CAD")
        "99" -> (99.0, "CAD")
    """
    # Remove common words
    text = re.sub(r'\b(was|now|sale|reg|regular)\b', '', text, flags=re.IGNORECASE)
    
    # Look for price pattern
    price_match = re.search(r'(?:C?\$|CAD)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
    if price_match:
        amount_str = price_match.group(1).replace(',', '')
        return (float(amount_str), "CAD")
    
    return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula
    Returns distance in kilometers
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return round(distance, 2)


def normalize_location(location: str) -> str:
    """
    Normalize location string
    
    Examples:
        "toronto" -> "Toronto, ON"
        "BRAMPTON, ONTARIO" -> "Brampton, ON"
        "Waterloo" -> "Waterloo, ON"
    """
    location = location.strip()
    
    # Common Ontario cities
    cities = {
        'toronto': 'Toronto',
        'ottawa': 'Ottawa',
        'mississauga': 'Mississauga',
        'brampton': 'Brampton',
        'hamilton': 'Hamilton',
        'london': 'London',
        'markham': 'Markham',
        'vaughan': 'Vaughan',
        'kitchener': 'Kitchener',
        'waterloo': 'Waterloo',
        'windsor': 'Windsor',
        'oshawa': 'Oshawa',
        'barrie': 'Barrie',
        'guelph': 'Guelph',
        'kingston': 'Kingston'
    }
    
    location_lower = location.lower()
    for city_key, city_name in cities.items():
        if city_key in location_lower:
            return f"{city_name}, ON"
    
    # If already has ON or Ontario, just clean it up
    if 'on' in location_lower or 'ontario' in location_lower:
        location = re.sub(r',?\s*(ON|Ontario|ONTARIO)', '', location, flags=re.IGNORECASE)
        return f"{location.strip()}, ON"
    
    return location


def parse_expiry_date(text: str) -> Optional[str]:
    """
    Parse expiry date from text
    
    Examples:
        "Expires Dec 31" -> "2025-12-31"
        "Valid until tomorrow" -> "2025-10-13"
        "Ends in 3 days" -> "2025-10-15"
    """
    text_lower = text.lower()
    today = datetime.now()
    
    # Relative dates
    if 'today' in text_lower:
        return today.strftime('%Y-%m-%d')
    
    if 'tomorrow' in text_lower:
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Days pattern
    days_match = re.search(r'(\d+)\s*days?', text_lower)
    if days_match:
        days = int(days_match.group(1))
        return (today + timedelta(days=days)).strftime('%Y-%m-%d')
    
    # Month and day pattern
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    for month_name, month_num in month_map.items():
        pattern = f'{month_name}[a-z]*\s+(\d{{1,2}})'
        match = re.search(pattern, text_lower)
        if match:
            day = int(match.group(1))
            year = today.year
            # If the date has passed this year, assume next year
            try:
                expiry = datetime(year, month_num, day)
                if expiry < today:
                    expiry = datetime(year + 1, month_num, day)
                return expiry.strftime('%Y-%m-%d')
            except ValueError:
                pass
    
    return None


def generate_deal_id(title: str, store: str, timestamp: str) -> str:
    """
    Generate a unique ID for a deal based on its properties
    """
    content = f"{title}|{store}|{timestamp}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def categorize_deal(title: str, description: str = "") -> str:
    """
    Automatically categorize a deal based on title and description
    """
    text = (title + " " + description).lower()
    
    # Category keywords
    categories = {
        "Home & Electronics": [
            'tv', 'laptop', 'computer', 'phone', 'tablet', 'camera', 'headphone',
            'speaker', 'appliance', 'refrigerator', 'washer', 'dryer', 'microwave',
            'furniture', 'mattress', 'home', 'electronics', 'smart', 'gaming'
        ],
        "Groceries": [
            'grocery', 'food', 'produce', 'meat', 'dairy', 'vegetables', 'fruit',
            'bread', 'snack', 'beverage', 'drink', 'loblaws', 'no frills', 'metro',
            'sobeys', 'organic', 'fresh'
        ],
        "Entertainment": [
            'movie', 'cinema', 'cineplex', 'concert', 'show', 'ticket', 'entertainment',
            'game', 'book', 'music', 'streaming', 'lcbo', 'wine', 'beer', 'restaurant',
            'dining'
        ],
        "Courses/Certifications": [
            'course', 'certification', 'training', 'class', 'workshop', 'seminar',
            'education', 'learning', 'online course', 'certificate', 'degree',
            'professional development', 'skill'
        ],
        "Fashion & Beauty": [
            'clothing', 'shoes', 'fashion', 'beauty', 'makeup', 'skincare',
            'perfume', 'accessories', 'jewelry', 'apparel'
        ],
        "Health & Wellness": [
            'fitness', 'gym', 'health', 'wellness', 'supplement', 'vitamin',
            'pharmacy', 'medical', 'dental', 'yoga', 'spa'
        ],
        "Automotive": [
            'car', 'auto', 'tire', 'oil change', 'vehicle', 'automotive',
            'canadian tire', 'parts', 'service'
        ]
    }
    
    # Score each category
    scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            scores[category] = score
    
    # Return category with highest score, or "Other" if none match
    if scores:
        return max(scores, key=scores.get)
    
    return "Other"


def format_currency(amount: float, currency: str = "CAD") -> str:
    """Format currency amount"""
    if currency == "CAD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def is_deal_expired(expiry_date: Optional[str]) -> bool:
    """Check if a deal has expired"""
    if not expiry_date:
        return False
    
    try:
        expiry = datetime.fromisoformat(expiry_date)
        return expiry < datetime.now()
    except (ValueError, TypeError):
        return False


def clean_html(text: str) -> str:
    """Remove HTML tags and clean text"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    
    return text.strip()


def validate_url(url: str) -> bool:
    """Validate if string is a proper URL"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None



