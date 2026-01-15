import logging
import requests
import json
import math
import re
from bs4 import BeautifulSoup
from app.core.config import get_config
from serpapi import GoogleSearch

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
def _get_inventory():
    """Fetches inventory from Brewfather (cached for duration of request)."""
    from app.services import alerts
    return alerts.fetch_brewfather_inventory()

# Ingredient name aliases - maps Brewfather names to simpler search terms
INGREDIENT_ALIASES = {
    # Common malts with origin/supplier info
    "pilsner (2 row) ger": ["pilsner malt", "german pilsner malt"],
    "pilsner (2 row) bel": ["pilsner malt", "belgian pilsner malt"],
    "pale malt (2 row) uk": ["pale malt", "maris otter"],
    "pale malt (2 row) us": ["pale malt", "2 row malt"],
    "best chit malt (bestmalz)": ["chit malt"],
    "wheat, flaked": ["flaked wheat"],
    "white wheat malt": ["wheat malt"],
    "oats, flaked": ["flaked oats"],
    "barley, flaked": ["flaked barley"],
    "caramunich i": ["caramunich malt"],
    "caramunich ii": ["caramunich malt"],
    "caramunich iii": ["caramunich malt"],
    "carafa special i": ["carafa malt"],
    "carafa special ii": ["carafa malt"],
    "carafa special iii": ["carafa malt"],
    # Hops with codes
    "mosaic (hbc 369)": ["mosaic hops"],
    "sabro (hbc 438)": ["sabro hops"],
    "strata (x-331)": ["strata hops"],
    "idaho 7 (a07270)": ["idaho 7 hops"],
    "nelson sauvin (hop)": ["nelson sauvin hops"],
}

def normalize_ingredient_name(name):
    """
    Normalizes ingredient name for better search results.
    - Removes parenthetical content (origin, supplier, codes)
    - Strips common suffixes
    """
    if not name:
        return name
    
    # Lowercase for matching
    normalized = name.lower().strip()
    
    # Check aliases first
    if normalized in INGREDIENT_ALIASES:
        return INGREDIENT_ALIASES[normalized][0]  # Return primary alias
    
    # Remove parenthetical content like "(2 Row)", "(HBC 369)", "(BESTMALZ)"
    normalized = re.sub(r'\s*\([^)]*\)', '', normalized)
    
    # Remove trailing origin codes like "Ger", "UK", "US", "Bel"
    normalized = re.sub(r'\s+(ger|uk|us|bel|aus|nz)$', '', normalized, flags=re.IGNORECASE)
    
    return normalized.strip()

def extract_price(text):
    if not text: return None
    # Clean text
    text = text.replace(',', '') # Handle 1,000.00
    
    # 1. Look for £ followed by digits (e.g. £13.95)
    match = re.search(r'[£$€]\s?(\d+(?:\.\d{2})?)', text)
    if match:
            return float(match.group(1))

    # 2. Look for digits followed by GBP (e.g. 7.50 GBP)
    match = re.search(r'(\d+(?:\.\d{2})?)\s?GBP', text, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # 3. Look for "Price/Cost:" followed by digits (e.g. Price: 10.00)
    match = re.search(r'(?:Price|Cost):\s?£?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
            
    # 4. Fallback: Pure number if context suggests (simplified)
    # Be careful not to pick up "2023" or "100g" as price blindly, but for snippets often the price field is clean.
    try:
        # If text is just a number (common in rich snippet 'price' field)
        return float(text)
    except Exception as e:
        logger.debug(f"Price parse fallback failed: {e}")
        
    return None

# Rate limiting - track last request time per domain
_last_request_time = {}
_MIN_REQUEST_INTERVAL = 2.0  # Minimum 2 seconds between requests to same domain

def get_page_content(url, retries=2, use_browser=False):
    """
    Fetches page HTML. Tries requests first, falls back to Playwright if blocked.
    Set use_browser=True to force Playwright (slower but bypasses anti-bot).
    Includes rate limiting to be respectful to vendor sites.
    """
    import time as _time
    from urllib.parse import urlparse
    
    # Rate limiting - wait if we've requested this domain recently
    domain = urlparse(url).netloc
    now = _time.time()
    if domain in _last_request_time:
        elapsed = now - _last_request_time[domain]
        if elapsed < _MIN_REQUEST_INTERVAL:
            wait_time = _MIN_REQUEST_INTERVAL - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.1f}s before requesting {domain}")
            _time.sleep(wait_time)
    _last_request_time[domain] = _time.time()
    
    # Try requests first (fast path)
    if not use_browser:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
        }
        
        for attempt in range(retries + 1):
            try:
                r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                r.raise_for_status()
                return r.text
            except requests.exceptions.RequestException as e:
                if attempt < retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Retry {attempt + 1}/{retries} for {url} after {wait_time}s: {e}")
                    _time.sleep(wait_time)
                else:
                    # If requests fails with 403, try Playwright
                    if "403" in str(e):
                        logger.info(f"403 detected, falling back to Playwright for {url}")
                        return get_page_content_browser(url)
                    logger.error(f"Failed to fetch {url} after {retries + 1} attempts: {e}")
                    return None
    else:
        return get_page_content_browser(url)

def get_page_content_browser(url):
    """
    Fetches page HTML using Playwright headless browser.
    Slower but bypasses Cloudflare/anti-bot protection.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return None
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            # Navigate and wait for network to be idle (Cloudflare challenge completes)
            page.goto(url, wait_until="networkidle", timeout=45000)
            # Extra wait for any JS rendering
            page.wait_for_timeout(3000)
            content = page.content()
            browser.close()
            logger.info(f"Successfully fetched {url} via Playwright ({len(content)} chars)")
            return content
    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {e}")
        return None

def parse_product_page(html, source):
    """
    Extracts price and weight/pack-size from HTML.
    """
    if not html: return None
    
    soup = BeautifulSoup(html, 'html.parser')
    data = {"price": None, "weight": None}
    
    try:
        # Debugging
        # print(f"DEBUG: Parsing {source}...")

        # --- THE MALT MILLER (WooCommerce) ---
        if "malt miller" in str(source).lower() or soup.select('.tmm-logo'):
            # Price
            # Generic WooCommerce Price
            price_tag = soup.select_one('.price .amount')
            if price_tag:
                 # Extract text but handle nested tags like <bdi>
                 data['price'] = extract_price(price_tag.get_text())
            
            # Weight/Size
            # 1. Attribute table
            # 2. Product Title
            title = soup.select_one('h1.product_title') or soup.find('h1')
            title_text = title.get_text() if title else ""
            
            # Extract grams/kg from title

            weight_match = re.search(r'(\d+)\s?(g|kg|ml|l)', title_text, re.IGNORECASE)
            if weight_match:
                data['weight'] = f"{weight_match.group(1)}{weight_match.group(2)}"
                
        # --- GET ER BREWED ---
        elif "get er brewed" in str(source).lower() or "geterbrewed" in str(source).lower():
             # Price
             price_tag = soup.select_one('[itemprop="price"]') or soup.select_one('.product-price')
             if price_tag:
                # content attribute often cleans "12.50"
                 p_text = price_tag.get("content") or price_tag.get_text()
                 data['price'] = extract_price(p_text)
                 
             # Weight
             title = soup.select_one('h1')
             title_text = title.get_text() if title else ""
             weight_match = re.search(r'(\d+)\s?(g|kg|ml|l)', title_text, re.IGNORECASE)
             if weight_match:
                data['weight'] = f"{weight_match.group(1)}{weight_match.group(2)}"

        # --- GENERIC FALLBACK ---
        else:
             # Try generic meta tags
             price_meta = soup.select_one('meta[property="product:price:amount"]') or soup.select_one('meta[property="og:price:amount"]')
             if price_meta:
                 data['price'] = float(price_meta['content'])
                 
    except Exception as e:
        logger.error(f"Page Parsing Error: {e}")
        
    return data

def search_ingredient(name, ingredient_type="hop"):
    """
    Searches for an ingredient on The Malt Miller and Get Er Brewed.
    """
    api_key = get_config("serp_api_key")
    if not api_key: return {"error": "Missing SerpApi Key"}

    # Targeted Search
    query = f"site:themaltmiller.co.uk OR site:geterbrewed.com {name} {ingredient_type}"
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 5
    }

    results = []
    try:
        search = GoogleSearch(params)
        data = search.get_dict()
        organic = data.get("organic_results", [])
        
        for item in organic:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            source = "The Malt Miller" if "themaltmiller" in link else "Get Er Brewed" if "geterbrewed" in link else "Other"
            
            # Basic Price Extraction (Heuristic from snippet if available)
            price = "Check Site"
            # Regex for price could go here, but snippets often lack it. 
            # Real implementation would visit the LINK to scrape proper price.
            # For this agent, we'll return the search hit for the user to click.
            
            results.append({
                "title": title,
                "link": link,
                "source": source,
                "snippet": snippet
            })
            
    except Exception as e:
        logger.error(f"Sourcing Error: {e}")
        return {"error": str(e)}

    return results

def get_inventory():
    try:
        with open("data/inventory.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"Inventory load failed: {e}")
        return {}

def generate_shopping_list(recipe_hops, recipe_fermentables):
    """
    Compares recipe needs vs inventory and estimates cost.
    recipe_hops: list of {'name': str, 'amount_g': float}
    """
    inventory = get_inventory()
    shopping_list = []
    total_est_cost = 0.0
    
    # Process Hops
    for hop in recipe_hops:
        name = hop['name'].lower()
        amount_needed = float(hop['amount_g'])
        
        # Check Inventory
        # Simple string matching for now
        stock = 0
        for k, v in inventory.get("hops", {}).items():
            if k in name or name in k:
                stock = v
                break
        
        amount_to_buy = max(0, amount_needed - stock)
        
        if amount_to_buy > 0:
            # Bagging Logic: Round up to nearest 50g or 100g
            # Standard packs are often 50g, 100g.
            # If > 100, maybe multiple packs.
            
            pack_size = 100 if amount_to_buy > 50 else 50
            packs_needed = math.ceil(amount_to_buy / pack_size)
            buy_weight = packs_needed * pack_size
            
            # Estimated Cost (avg 5.00 GBP per 100g for special hops)
            est_cost = (buy_weight / 100) * 6.50 # conservative estimate
            
            shopping_list.append({
                "type": "Hop",
                "name": hop['name'],
                "need": amount_needed,
                "stock": stock,
                "buy": buy_weight,
                "est_cost": round(est_cost, 2),
                "pack_size": pack_size
            })
            total_est_cost += est_cost
            
    # Process Fermentables (Simplified)
    for ferm in recipe_fermentables:
         name = ferm['name'].lower()
         amount_kg = float(ferm['amount_kg'])
         
         # Check Inventory
         stock_kg = 0 # Assume 0 for simplicity if not found
         
         if amount_kg > 0:
             # Round to nearest kg?
             buy_kg = math.ceil(amount_kg)
             est_cost = buy_kg * 2.50 # Avg malt price
             
             shopping_list.append({
                "type": "Malt",
                "name": ferm['name'],
                "need": f"{amount_kg} kg",
                "stock": f"{stock_kg} kg",
                "buy": f"{buy_kg} kg",
                "est_cost": round(est_cost, 2)
            })
             total_est_cost += est_cost

    return {
        "items": shopping_list,
        "total_est_cost": round(total_est_cost, 2)
    }

def check_price_watch():
    """
    Checks watched ingredients for price drops via SerpApi.
    Triggered by a cron/scheduler (or manual API call for now).
    """
    from services.notifications import send_telegram_message
    
    # Library of "Normal Prices" (Baseline)
    # In a full app, this would be in a DB or ingredient_library.json
    INGREDIENT_LIBRARY = {
        "Citra Hops 100g": {"baseline": 7.50, "search_term": "Citra Hops 100g"},
        "Crisp Extra Pale Malt 25kg": {"baseline": 55.00, "search_term": "Crisp Extra Pale Malt 25kg"},
        "Simcoe Hops 100g": {"baseline": 7.50, "search_term": "Simcoe Hops 100g"},
        "Golden Promise Malt 25kg": {"baseline": 52.00, "search_term": "Golden Promise Malt 25kg"}
    }
    
    alerts = []
    
    for name, data in INGREDIENT_LIBRARY.items():
        baseline = data['baseline']
        query = data['search_term']
        
        # 10% Drop Threshold
        target_price = baseline * 0.90
        
        api_key = get_config("serp_api_key")
        if not api_key: continue
        
        params = {
            "engine": "google_shopping",
            "q": query + " site:themaltmiller.co.uk OR site:geterbrewed.com",
            "api_key": api_key,
            "num": 3,
            "gl": "uk",
            "hl": "en",
            "currency": "GBP"
        }
        
        try:
            search = GoogleSearch(params)
            res_data = search.get_dict()
            shopping_results = res_data.get("shopping_results", [])
            
            for res in shopping_results:
                price_str = res.get("price", "100.00").replace('£', '')
                try:
                    price = float(price_str)
                    
                    # Logic: If Price is 10% lower than baseline
                    if price <= target_price:
                        savings_pct = int(((baseline - price) / baseline) * 100)
                        vendor = res.get("source", "Unknown")
                        link = res.get("link")
                        
                        msg = (
                            f"🚨 *DEAL ALERT: {name}*\n"
                            f"Current Price: £{price}\n"
                            f"Normal Price: £{baseline}\n"
                            f"Savings: {savings_pct}% Off! (Found at {vendor})\n"
                            f"[Buy Now]({link})"
                        )
                        alerts.append(msg)
                        break # Found best deal for this item
                except:
                    continue
        except Exception as e:
            logger.error(f"Price Watch Error for {name}: {e}")
            
    if alerts:
        full_msg = "🛒 *Weekly Ingredient Watch*\n\n" + "\n\n".join(alerts)
        send_telegram_message(full_msg)
        return {"status": "alerts_sent", "count": len(alerts)}
        
    return {"status": "no_alerts"}

def compare_recipe_prices(recipe_details):
    """
    Takes full recipe object (from BF) and compares basket cost.
    Uses Google Organic Search + Snippet Parsing for broader coverage than Google Shopping.
    """
    # DEBUG: Log incoming recipe structure
    logger.info(f"DEBUG compare_recipe_prices: Received recipe keys: {list(recipe_details.keys()) if isinstance(recipe_details, dict) else 'NOT A DICT'}")
    logger.info(f"DEBUG compare_recipe_prices: Hops field: {recipe_details.get('hops', 'MISSING')}")
    logger.info(f"DEBUG compare_recipe_prices: Fermentables field: {recipe_details.get('fermentables', 'MISSING')}")
    logger.info(f"DEBUG compare_recipe_prices: Yeasts field: {recipe_details.get('yeasts', 'MISSING')}")
    
    # Parse Ingredients
    items_to_check = []
    
    # Hops
    for hop in recipe_details.get('hops', []):
        amount = hop.get('amount', 0)
        unit = "g"
        name = hop.get('name')
        items_to_check.append({"name": name, "amount": amount, "unit": unit, "type": "Hop"})
        
    # Fermentables
    for ferm in recipe_details.get('fermentables', []):
        amount = ferm.get('amount', 0)
        unit = "kg"
        name = ferm.get('name')
        items_to_check.append({"name": name, "amount": amount, "unit": unit, "type": "Malt"})
        
    # Yeasts
    for yeast in recipe_details.get('yeasts', []):
        name = yeast.get('name')
        items_to_check.append({"name": name, "amount": 1, "unit": "pack", "type": "Yeast"})
    
    # DEBUG: Log parsed items
    logger.info(f"DEBUG compare_recipe_prices: Parsed {len(items_to_check)} items: {items_to_check}")
    
    # Fetch inventory to check stock levels
    inventory = {}
    try:
        inventory = _get_inventory()
        if isinstance(inventory, dict) and 'error' not in inventory:
            logger.info(f"DEBUG: Loaded inventory with {len(inventory.get('hops', {}))} hops, {len(inventory.get('fermentables', {}))} malts")
    except Exception as e:
        logger.warning(f"Could not fetch inventory: {e}")
        
    results = []
    total_tmm = 0.0
    total_geb = 0.0
    
    api_key = get_config("serp_api_key")
    if not api_key:
        logger.error("Missing SerpApi Key - Cannot perform price comparison")
        return {"error": "Missing SerpApi Key"}
    
    def search_price(query, source_name):
        try:
             params = {
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": 2, # Top 2 organic results
                "gl": "uk",
                "hl": "en"
             }
             search = GoogleSearch(params)
             data = search.get_dict()
             organic = data.get("organic_results", [])
             
             logger.info(f"DEBUG: Found {len(organic)} organic results for query '{query}'")

             # Best Candidate
             best_price = None
             best_weight = None
             best_link = None
             
             for i, res in enumerate(organic):
                 link = res.get("link")
                 title = res.get("title", "")
                 
                 # 1. VISITING PAGE (Highest Accuracy)
                 if i == 0: # Only visit top hit for now to save time/bandwidth
                     logger.info(f"Visiting {link}...")
                     html = get_page_content(link)
                     page_data = parse_product_page(html, source_name)
                     
                     if page_data and page_data['price']:
                         return {
                             "price": page_data['price'],
                             "weight": page_data.get('weight') or "Unknown",
                             "link": link
                         }

                 # 2. Try Rich Snippet (Fallback)
                 rich = res.get("rich_snippet", {})
                 box = rich.get("top", {}) or rich.get("bottom", {})
                 extensions = box.get("detected_extensions", {})
                 
                 if extensions.get("price"):
                     p = extract_price(f"£{extensions['price']}")
                     if p: 
                         return {"price": p, "weight": "Snippet", "link": link}
                 
                 # 3. Try Snippet
                 snippet = res.get("snippet", "")
                 p = extract_price(snippet)
                 if p:
                      return {"price": p, "weight": "Snippet", "link": link}
                  
        except Exception as e:
            logger.error(f"Search Error: {e}")
        return None

    # Limit to top 5 items for speed/cost (Prototype)
    for item in items_to_check[:6]: 
        row = {
            "name": item['name'],
            "type": item['type'],
            "amount": f"{item['amount']} {item['unit']}",
            "tmm_price": "N/A",
            "geb_price": "N/A",
            "best_vendor": "None",
            "searched_as": None,  # Track if we used an alternative name
            "in_stock": False,
            "stock_qty": 0
        }
        
        # Check inventory stock
        item_name_lower = item['name'].lower() if item['name'] else ""
        needed_amount = item.get('amount', 0)
        
        if inventory and not inventory.get('error'):
            # Map type to inventory category
            inv_category = {"Hop": "hops", "Malt": "fermentables", "Yeast": "yeast"}.get(item['type'])
            
            if inv_category and inv_category in inventory:
                # Try exact match first
                stock = inventory[inv_category].get(item_name_lower, 0)
                
                # Partial match fallback
                if stock == 0:
                    for inv_name, inv_qty in inventory[inv_category].items():
                        if item_name_lower in inv_name or inv_name in item_name_lower:
                            stock = inv_qty
                            break
                
                row['stock_qty'] = round(stock, 2)
                row['in_stock'] = stock >= needed_amount
                
                if row['in_stock']:
                    row['best_vendor'] = "In Stock"
        
        original_name = item['name']
        normalized_name = normalize_ingredient_name(original_name)
        
        # Build list of names to try: original first, then normalized, then aliases
        names_to_try = [original_name]
        if normalized_name and normalized_name.lower() != original_name.lower():
            names_to_try.append(normalized_name)
        
        # Add aliases if available
        lower_name = original_name.lower().strip()
        if lower_name in INGREDIENT_ALIASES:
            for alias in INGREDIENT_ALIASES[lower_name]:
                if alias not in [n.lower() for n in names_to_try]:
                    names_to_try.append(alias)
        
        # Search TMM - try each name until we get a result
        res_tmm = None
        used_name_tmm = None
        for try_name in names_to_try:
            res_tmm = search_price(f"{try_name} site:themaltmiller.co.uk", "The Malt Miller")
            if res_tmm:
                used_name_tmm = try_name if try_name != original_name else None
                break
        
        if res_tmm:
            row['tmm_price'] = res_tmm['price']
            row['tmm_weight'] = res_tmm['weight']
            total_tmm += res_tmm['price']
            if used_name_tmm:
                row['searched_as'] = used_name_tmm
            
        # Search GEB - try each name until we get a result
        res_geb = None
        used_name_geb = None
        for try_name in names_to_try:
            res_geb = search_price(f"{try_name} site:geterbrewed.com", "Get Er Brewed")
            if res_geb:
                used_name_geb = try_name if try_name != original_name else None
                break
                
        if res_geb:
            row['geb_price'] = res_geb['price']
            row['geb_weight'] = res_geb.get('weight', 'N/A')
            total_geb += res_geb['price']
            # Only set searched_as if TMM didn't already set it
            if used_name_geb and not row.get('searched_as'):
                row['searched_as'] = used_name_geb
        
        # Determine Winner
        try:
            t = float(row['tmm_price']) if row['tmm_price'] != "N/A" else 9999
            g = float(row['geb_price']) if row['geb_price'] != "N/A" else 9999
            
            if t < g and t != 9999: row['best_vendor'] = "TMM"
            elif g < t and g != 9999: row['best_vendor'] = "GEB"
            elif t == g and t != 9999: row['best_vendor'] = "Tie"
        except: pass
        
        results.append(row)
        
    return {
        "breakdown": results,
        "total_tmm": round(total_tmm, 2) if total_tmm > 0 else "Inc",
        "total_geb": round(total_geb, 2) if total_geb > 0 else "Inc",
        "winner": "The Malt Miller" if (total_tmm < total_geb and total_tmm > 0) else "Get Er Brewed" if (total_geb < total_tmm and total_geb > 0) else "Inconclusive"
    }

def get_restock_suggestions():
    """
    Scans inventory for low items and generates TMM links.
    """
    inventory = get_inventory()
    suggestions = []
    
    # Thresholds
    THRESHOLDS = {
        "hops": 100, # g
        "fermentables": 1000, # g (1kg)
        "yeasts": 1, # packs
        "salts": 50 # g
    }
    
    api_key = get_config("serp_api_key")
    
    def search_tmm_link(query):
        if not api_key: return "#"
        try:
            params = {
                "engine": "google_shopping",
                "q": f"{query} site:themaltmiller.co.uk",
                "api_key": api_key,
                "num": 1,
                "gl": "uk",
                "hl": "en",
                "currency": "GBP"
            }
            res = GoogleSearch(params).get_dict().get("shopping_results", [])
            if res: return res[0].get("link", "#")
        except: pass
        return "#"

    # Scan Categories
    for cat, items in inventory.items():
        limit = THRESHOLDS.get(cat, 0)
        if not items: continue
        
        for name, amount_str in items.items():
            # Parse amount (e.g. "5000g" -> 5000)
            try:
                # Remove unit chars
                clean = str(amount_str).lower().replace('g', '').replace('ml', '').replace('pack', '').strip()
                val = float(clean)
                
                if val <= limit:
                    # Low Stock!
                    link = search_tmm_link(name)
                    suggestions.append({
                        "name": name,
                        "current_stock": amount_str,
                        "category": cat,
                        "link": link,
                        "vendor": "The Malt Miller"
                    })
            except:
                continue
                
    if suggestions:
        # Generate Text Summary for Telegram
        try:
             from services.notifications import send_telegram_message
             msg = "🛒 *AUTO-RESTOCK REPORT*\nFound low stock items:\n\n"
             for item in suggestions:
                 msg += f"• {item['name']} (Current: {item['current_stock']})\n"
             msg += "\nCheck Dashboard for Purchase Links."
             # Only send if meaningful diff? For now just send.
             send_telegram_message(msg)
        except: pass
        
    return suggestions
