import requests
from bs4 import BeautifulSoup
import logging
import re
from serpapi import GoogleSearch
from core.config import get_config

logger = logging.getLogger(__name__)

def search_yeast_meta(yeast_name):
    """
    Searches spec sheets for a yeast strain and attempts to scrape metadata.
    """
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
    except:
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
    except:
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
    except:
        pass
    return "Unknown"
