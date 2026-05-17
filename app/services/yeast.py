import requests
from bs4 import BeautifulSoup
import logging
import re
from serpapi import GoogleSearch
from core.config import get_config

logger = logging.getLogger(__name__)

# Local Database of common yeast strains for offline-first intelligence
YEAST_DATABASE = {
    "us-05": {
        "name": "SafAle US-05",
        "attenuation": "78-82%",
        "flocculation": "Medium",
        "temp_range": "18-28°C",
        "styles": ["American Ale", "IPA", "Stout"],
        "notes": "Neutral flavor, clean finish. Very robust and reliable."
    },
    "s-04": {
        "name": "SafAle S-04",
        "attenuation": "72-75%",
        "flocculation": "High",
        "temp_range": "15-20°C",
        "styles": ["English Ale", "Porter", "Stout"],
        "notes": "Fast fermentation, compact sediment. Slight fruity esters."
    },
    "w-34/70": {
        "name": "Saflager W-34/70",
        "attenuation": "80-84%",
        "flocculation": "High",
        "temp_range": "12-15°C",
        "styles": ["Lager", "Pilsner"],
        "notes": "Clean lager profile. High pressure tolerance."
    },
    "be-256": {
        "name": "SafAle BE-256",
        "attenuation": "82-85%",
        "flocculation": "High",
        "temp_range": "15-25°C",
        "styles": ["Abbey Style", "Belgian Strong"],
        "notes": "Fast, high alcohol tolerance, spicy/phenolic."
    },
    "wlp001": {
        "name": "White Labs California Ale",
        "attenuation": "73-80%",
        "flocculation": "Medium",
        "temp_range": "20-23°C",
        "styles": ["American Style Ale"],
        "notes": "Standard clean ale yeast. Balanced."
    },
    "london ale iii": {
        "name": "Wyeast 1318 London Ale III",
        "attenuation": "71-75%",
        "flocculation": "High",
        "temp_range": "18-23°C",
        "styles": ["NEIPA", "English Pale"],
        "notes": "Fruit-forward, great for hazy IPAs. Soft finish."
    }
}

def search_yeast_meta(yeast_name: str) -> dict:
    """
    Searches for yeast metadata, prioritizing the local expert database.
    """
    if not yeast_name:
        return {"error": "No yeast name provided"}

    # 1. Check local expert database (fuzzy-ish match)
    lower_name = yeast_name.lower()
    for key, data in YEAST_DATABASE.items():
        if key in lower_name or lower_name in key:
            logger.info(f"Found yeast '{yeast_name}' in local expert database as '{data['name']}'")
            return data

    # 2. Fallback to SerpApi Search if local DB fails
    api_key = get_config("serp_api_key")
    if not api_key:
        return {"error": "Missing SerpApi Key"}

    # 1. Search for the manufacturer page
    query = f"{yeast_name} yeast specifications site:whitelabs.com OR site:wyeastlab.com OR site:imperialyeast.com OR site:lallemandbrewing.com OR site:fermentis.com OR site:omegayeast.com"
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 3
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        organic = results.get("organic_results", [])
        
        if not organic:
            return {"error": "No manufacturer page found"}
            
        target_url = organic[0].get("link")
        title = organic[0].get("title")
        
        # 2. Fetch and Parse
        return scrape_yeast_page(target_url, title)
        
    except Exception as e:
        logger.error(f"Yeast Search Error: {e}")
        return {"error": str(e)}

def scrape_yeast_page(url, title):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code != 200:
            return {"error": f"Failed to fetch page: {r.status_code}"}
            
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text().lower()
        
        # 3. Heuristic Extraction (Naive approach)
        data = {
            "name": title,
            "url": url,
            "attenuation": extract_range(text, "attenuation"),
            "flocculation": extract_keyword(text, "flocculation", ["low", "medium", "high", "med-high", "high-low"]),
            "temp_range": extract_temp_range(text),
            "abv_tolerance": extract_range(text, "tolerance")
        }
        
        return data
        
    except Exception as e:
        return {"error": f"Scrape Error: {e}"}

def extract_range(text, keyword):
    # Regex to find patterns like "Attenuation: 70-80%" or "Attenuation: 75%"
    # Look for keyword followed by numbers
    try:
        # Simple pattern: keyword ... number ... %
        match = re.search(f"{keyword}.*?(\\d+(?:-\\d+)?)\\s*%", text)
        if match:
            return match.group(1) + "%"
    except (re.error, IndexError, ValueError):
        pass
    return "Unknown"

def extract_keyword(text, keyword, options):
    try:
        # Find context around keyword
        idx = text.find(keyword)
        if idx == -1: return "Unknown"
        
        snippet = text[idx:idx+50]
        for opt in options:
            if opt in snippet:
                return opt.capitalize()
    except (IndexError, ValueError):
        pass
    return "Unknown"

def extract_temp_range(text):
    # Look for patterns like 65-72 F or 18-22 C
    try:
        # F search
        f_match = re.search(r"(\d{2})\s*-\s*(\d{2})\s*°?f", text)
        if f_match:
            return f"{f_match.group(1)}-{f_match.group(2)}°F"
            
        # C search
        c_match = re.search(r"(\d{2})\s*-\s*(\d{2})\s*°?c", text)
        if c_match:
            return f"{c_match.group(1)}-{c_match.group(2)}°C"
    except (re.error, IndexError, ValueError):
        pass
    return "Unknown"
