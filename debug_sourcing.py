import sys
import os
import logging

# Setup path
sys.path.append(os.getcwd())

# Setup Logging
logging.basicConfig(level=logging.INFO)

from app.core.config import refresh_config_from_influx, get_config
from app.services.sourcing import extract_price
from serpapi import GoogleSearch

def debug_search():
    print("--- DIAGNOSTIC START ---")
    
    # 1. Load Config
    print("Loading config from InfluxDB...")
    try:
        refresh_config_from_influx()
        key = get_config("serp_api_key")
        if key:
            print(f"API Key Found: {key[:4]}...{key[-4:]}")
        else:
            print("ERROR: API Key 'serp_api_key' is Missing/None!")
            return
    except Exception as e:
        print(f"Config Load Error: {e}")
        return

    # 2. Perform Search
    query = "Citra Hops 100g site:themaltmiller.co.uk"
    print(f"Searching: {query}")
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": key,
        "num": 2,
        "gl": "uk",
        "hl": "en"
    }
    
    try:
        search = GoogleSearch(params)
        data = search.get_dict()
        organic = data.get("organic_results", [])
        
        print(f"Found {len(organic)} results.")
        
        for i, res in enumerate(organic):
            print(f"\n[Result {i}]")
            snippet = res.get("snippet", "NO_SNIPPET")
            rich = res.get("rich_snippet", {})
            print(f"Snippet: {snippet}")
            print(f"Rich Snippet: {rich}")
            
            # Test Extraction
            p_rich = None
            if rich and rich.get("top", {}).get("detected_extensions", {}).get("price"):
                 raw_p = rich['top']['detected_extensions']['price']
                 print(f"Rich Price Raw: {raw_p}")
                 p_rich = extract_price(f"£{raw_p}")
                 
            p_snip = extract_price(snippet)
            
            print(f"Extracted (Rich): {p_rich}")
            print(f"Extracted (Snippet): {p_snip}")
            
    except Exception as e:
        print(f"Search Error: {e}")

if __name__ == "__main__":
    debug_search()
    print("--- DIAGNOSTIC END ---")
