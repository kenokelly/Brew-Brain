import logging
import json
import difflib
import math
import re
import time as std_time
import threading
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from core.config import get_config
from serpapi import GoogleSearch

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
def _get_inventory():
    """Fetches inventory from Brewfather (cached for duration of request)."""
    from services import alerts
    return alerts.fetch_brewfather_inventory()
from services.hop_math import calculate_hop_freshness
from services.scraper_utils import (
    get_page_content, 
    parse_product_page, 
    extract_weight_in_grams, 
    extract_json_ld_products, 
    extract_price
)
from core.cache import cache
import os

# SERP API Key
def get_serpapi_key():
    return os.environ.get("SERPAPI_KEY") or get_config("serp_api_key")

def check_inventory_hop_freshness(inventory: dict = None) -> list:
    """
    Checks all hops in inventory for freshness.
    Requires inventory items to have purchase_date and storage fields.
    """
    if inventory is None:
        inventory = get_inventory()
    
    if not inventory or isinstance(inventory, str):
        return []
    
    results = []
    hops = inventory.get("hops", {})
    
    for hop_name, hop_data in hops.items():
        if isinstance(hop_data, dict):
            purchase_date = hop_data.get("purchase_date")
            original_alpha = hop_data.get("alpha_acid", 10.0)
            storage = hop_data.get("storage", "freezer")
            
            if purchase_date:
                freshness = calculate_hop_freshness(
                    hop_name,
                    original_alpha,
                    purchase_date,
                    storage
                )
                results.append(freshness)
    
    return results



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
    "crisp extra pale malt": ["extra pale malt", "crisp extra pale"],
    "weyermann vienna malt": ["vienna malt"],
    "weyermann munich i": ["munich malt", "munich i"],
    "weyermann munich ii": ["munich malt", "munich ii"],
    "simpsons golden promise": ["golden promise", "golden promise malt"],
    "simpsons maris otter": ["maris otter", "maris otter malt"],
    # Hops
    "mosaic (hbc 369)": ["mosaic hops"],
    "sabro (hbc 438)": ["sabro hops"],
    "strata (x-331)": ["strata hops"],
    "idaho 7 (a07270)": ["idaho 7 hops"],
    "nelson sauvin (hop)": ["nelson sauvin hops"],
    "citra crg": ["citra hops", "citra cryo"],
    "mosaic crg": ["mosaic hops", "mosaic cryo"],
    "simcoe crg": ["simcoe hops", "simcoe cryo"],
    "cascade (us)": ["cascade hops"],
    "centennial (us)": ["centennial hops"],
    "columbus (us)": ["columbus hops", "ctz hops"],
    "magnum (ger)": ["magnum hops"],
}

def get_fuzzy_match(name, choices, threshold=0.6):
    """Returns the best fuzzy match from a list of choices."""
    matches = difflib.get_close_matches(name, choices, n=1, cutoff=threshold)
    return matches[0] if matches else None

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
    normalized = re.sub(r'\s+(ger|uk|us|bel|aus|nz|crg)$', '', normalized, flags=re.IGNORECASE)
    
    # Strip common pellet indicators
    normalized = re.sub(r'\s+(t90|t-90|pellets|pellet)$', '', normalized, flags=re.IGNORECASE)
    
    return normalized.strip()

def search_ingredient(name, ingredient_type="hop"):
    """
    Searches for an ingredient on The Malt Miller and Get Er Brewed.
    """
    api_key = get_serpapi_key()
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
        
        api_key = get_serpapi_key()
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
                except (ValueError, TypeError):
                    continue
        except Exception as e:
            logger.error(f"Price Watch Error for {name}: {e}")
            
    if alerts:
        full_msg = "🛒 *Weekly Ingredient Watch*\n\n" + "\n\n".join(alerts)
        send_telegram_message(full_msg)
        return {"status": "alerts_sent", "count": len(alerts)}
        
    return {"status": "no_alerts"}

def compare_recipe_prices(recipe_details, recipe_tag=None, debug_mode=False):
    """
    Compares prices for a recipe's ingredients.
    """
    if debug_mode:
        logger.info("DEBUG MODE: Returning mock comparison results.")
        return {
            "breakdown": [
                {"name": "Debug Hop", "tmm_cost": 10.0, "geb_cost": 12.0, "best_vendor": "TMM"}
            ],
            "total_tmm": 10.0,
            "total_geb": 12.0,
            "winner": "The Malt Miller",
            "debug": True
        }
    """
    Takes full recipe object (from BF) OR a tag to fetch it, and compares basket cost.
    Uses Google Organic Search + Snippet Parsing for broader coverage than Google Shopping.
    """
    # 1. Resolve Recipe if Tag provided
    if recipe_tag:
        from services import alerts
        logger.info(f"Fetching recipe by tag: {recipe_tag}")
        recipe = alerts.fetch_recipe_by_tag(recipe_tag)
        if not recipe or 'error' in recipe:
            return {"error": f"Could not find recipe with tag '{recipe_tag}': {recipe.get('error')}"}
        recipe_details = recipe

    # DEBUG: Log incoming recipe structure
    logger.info(f"DEBUG compare_recipe_prices: Received recipe. Keys: {list(recipe_details.keys()) if isinstance(recipe_details, dict) else 'NOT A DICT'}")
    
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
        # Convert kg to g for standardized cost calc
        items_to_check.append({"name": name, "amount": amount, "unit": unit, "type": "Malt"})
        
    # Yeasts
    for yeast in recipe_details.get('yeasts', []):
        name = yeast.get('name')
        items_to_check.append({"name": name, "amount": 1, "unit": "pack", "type": "Yeast"})
    
    # Deduplicate items to check (merge amounts for same name/unit/type)
    deduped = {}
    for item in items_to_check:
        key = (item['name'], item['unit'], item['type'])
        if key in deduped:
            deduped[key]['amount'] += item['amount']
        else:
            deduped[key] = item
    items_to_check = list(deduped.values())
    
    # Fetch inventory to check stock levels
    inventory = {}
    try:
        inventory = _get_inventory()
    except Exception as e:
        logger.warning(f"Could not fetch inventory: {e}")
        
    results = []
    total_tmm = 0.0
    total_geb = 0.0
    
    api_key = get_serpapi_key()
    use_serp = bool(api_key)  # SerpAPI is now OPTIONAL
    
    logger.info(f"[PRICE-CMP] Mode: {'SerpAPI' if use_serp else 'Direct Scraping'}")
    
    def search_vendor_direct(ingredient_name, vendor):
        """
        Searches vendor site directly via their site search.
        Returns {"price": float|None, "link": str, "title": str}
        """
        from urllib.parse import quote_plus
        
        try:
            query = quote_plus(ingredient_name)
            
            if vendor == "tmm":
                # The Malt Miller uses WooCommerce - search via ?s= parameter
                search_url = f"https://www.themaltmiller.co.uk/?s={query}&post_type=product"
                source_name = "The Malt Miller"
            else:
                # Get Er Brewed uses custom search
                search_url = f"https://www.geterbrewed.com/?s={query}&post_type=product"
                source_name = "Get Er Brewed"
            
            logger.debug(f"[DIRECT] Searching {source_name}: {search_url}")
            html = get_page_content(search_url)
            
            if not html:
                logger.warning(f"[DIRECT] No response from {source_name}")
                return None
                
            # 1. Try JSON-LD Extraction first
            products = extract_json_ld_products(html)
            best_match = None
            best_confidence = 0.0
            target_clean = ingredient_name.lower().strip()
            
            for p in products:
                p_name = p.get('name', '')
                if not p_name: continue
                
                conf = difflib.SequenceMatcher(None, target_clean, p_name.lower()).ratio()
                if target_clean in p_name.lower(): conf = max(conf, 0.8)
                
                if conf > best_confidence:
                    best_confidence = conf
                    best_match = p

            if best_match and best_confidence >= 0.5:
                price = None
                offers = best_match.get('offers', {})
                if isinstance(offers, dict): offers = [offers]
                for offer in offers:
                    if offer.get('@type') == 'Offer' and offer.get('price'):
                        try:
                            price = float(offer['price'])
                            break
                        except ValueError:
                            pass
                            
                if price:
                    title = best_match.get('name')
                    link = best_match.get('url') or search_url
                    if link == search_url and isinstance(offers, list) and len(offers) > 0:
                        link = offers[0].get('url', search_url)
                        
                    return {
                        "price": price,
                        "link": link,
                        "title": title,
                        "weight_g": extract_weight_in_grams(title),
                        "confidence": best_confidence
                    }

            # 2. Fallback to HTML/CSS Parsing
            soup = BeautifulSoup(html, 'html.parser')
            
            product = soup.select_one('.product, .products .product, li.product, .item, .product-item')
            if not product:
                logger.debug(f"[DIRECT] No product found for '{ingredient_name}' on {source_name}")
                return None
            
            title_tag = product.select_one('.woocommerce-loop-product__title, h2, .product-title, .product-name')
            title = title_tag.get_text().strip() if title_tag else ingredient_name
            
            conf = difflib.SequenceMatcher(None, target_clean, title.lower()).ratio()
            if target_clean in title.lower(): conf = max(conf, 0.8)
            
            if conf < 0.4:
                logger.debug(f"[DIRECT] Rejected '{title}' for '{ingredient_name}'. Low confidence: {conf:.2f}")
                return None
            
            price_tag = product.select_one('.price .amount bdi, .price ins .amount bdi, .price .amount, .price ins .amount, .woocommerce-Price-amount, .product-price')
            price = None
            if price_tag:
                price = extract_price(price_tag.get_text())
            
            link_tag = product.select_one('a[href*="/product/"], a[href*="/item/"], a.woocommerce-LoopProduct-link')
            link = link_tag.get('href') if link_tag else search_url
            
            return {
                "price": price,
                "link": link,
                "title": title,
                "weight_g": extract_weight_in_grams(title),
                "confidence": conf
            }
            
        except Exception as e:
            logger.warning(f"[DIRECT] Error searching {vendor}: {e}")
            return None
    
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
             
             # Best Candidate
             for i, res in enumerate(organic):
                 link = res.get("link")
                 title = res.get("title", "")
                 
                 # 1. VISITING PAGE
                 if i == 0: 
                     html = get_page_content(link)
                     page_data = parse_product_page(html, source_name)
                     
                     if page_data and page_data['price']:
                         # Improvement: If page parse didn't get weight, try title/snippet
                         w_g = page_data.get('weight_g')
                         if not w_g:
                              w_g = extract_weight_in_grams(title) or extract_weight_in_grams(res.get("snippet", ""))
                              
                         return {
                             "price": page_data['price'],
                             "weight": page_data.get('weight') or "Unknown",
                             "weight_g": w_g,
                             "link": link
                         }

                 # 2. Rich Snippet (Fallback) - Requires extra regex for weight
                 rich = res.get("rich_snippet", {})
                 box = rich.get("top", {}) or rich.get("bottom", {})
                 extensions = box.get("detected_extensions", {})
                 
                 if extensions.get("price"):
                     p = extract_price(f"£{extensions['price']}")
                     # Try to guess weight from title
                     w_g = extract_weight_in_grams(title)
                     if p: 
                         return {"price": p, "weight": "Snippet", "weight_g": w_g, "link": link}
                 
                 # 3. Snippet (Fallback)
                 snippet = res.get("snippet", "")
                 p = extract_price(snippet)
                 w_g = extract_weight_in_grams(snippet) or extract_weight_in_grams(title)
                 if p:
                      return {"price": p, "weight": "Snippet", "weight_g": w_g, "link": link}
                  
        except Exception as e:
            logger.error(f"Search Error: {e}")
        return None

    def process_item(item):
        row = {
            "name": item['name'],
            "type": item['type'],
            "amount": f"{item['amount']} {item['unit']}",
            "amount_g": item['amount'] * 1000 if item['unit'] == 'kg' else item['amount'],
            "tmm_price": "N/A", "tmm_cost": 0.0, "tmm_cost_raw": 0.0, "tmm_link": "#",
            "geb_price": "N/A", "geb_cost": 0.0, "geb_cost_raw": 0.0, "geb_link": "#",
            "best_vendor": "None",
            "in_stock": False,
            "stock_qty": 0
        }
        
        names_to_try = [item['name']]
        normalized_name = normalize_ingredient_name(item['name'])
        if normalized_name:
             names_to_try.append(normalized_name)
        
        def get_cached_or_fetch(vendor, names):
            for try_name in names:
                cache_key = f"sourcing_{vendor}_{try_name.lower().replace(' ', '_')}"
                
                cached_data = cache.get(cache_key)
                if cached_data:
                    return cached_data
                        
                res = search_vendor_direct(try_name, vendor)
                if res and res.get('price'):
                    cache.set(cache_key, res, ttl=86400) # 24 hours TTL
                    return res
            return None

        def fetch_tmm_price():
            res = get_cached_or_fetch("tmm", names_to_try)
            if use_serp and not res:
                for try_name in names_to_try:
                     res = search_price(f"{try_name} site:themaltmiller.co.uk", "The Malt Miller")
                     if res: break
            return res

        def fetch_geb_price():
            res = get_cached_or_fetch("geb", names_to_try)
            if use_serp and not res:
                for try_name in names_to_try:
                     res = search_price(f"{try_name} site:geterbrewed.com", "Get Er Brewed")
                     if res: break
            return res

        with ThreadPoolExecutor(max_workers=2) as inner_executor:
            f_tmm = inner_executor.submit(fetch_tmm_price)
            f_geb = inner_executor.submit(fetch_geb_price)
            res_tmm = f_tmm.result()
            res_geb = f_geb.result()

        if res_tmm:
            row['tmm_price'] = res_tmm['price']
            row['tmm_link'] = res_tmm.get('link', '#')
            if res_tmm.get('weight_g') and res_tmm['weight_g'] > 0:
                cost_per_g = res_tmm['price'] / res_tmm['weight_g']
                item_cost = cost_per_g * row['amount_g']
                row['tmm_cost_raw'] = item_cost
                row['tmm_cost'] = round(item_cost, 2)
            else:
                row['tmm_cost'] = "?" 

        if res_geb:
            row['geb_price'] = res_geb['price']
            row['geb_link'] = res_geb.get('link', '#')
            if res_geb.get('weight_g') and res_geb['weight_g'] > 0:
                cost_per_g = res_geb['price'] / res_geb['weight_g']
                item_cost = cost_per_g * row['amount_g']
                row['geb_cost_raw'] = item_cost
                row['geb_cost'] = round(item_cost, 2)
            else:
                row['geb_cost'] = "?"
        
        # Determine Winner
        try:
            t = float(row['tmm_price']) if row['tmm_price'] != "N/A" else 9999
            g = float(row['geb_price']) if row['geb_price'] != "N/A" else 9999
            if t < g and t != 9999: row['best_vendor'] = "TMM"
            elif g < t and g != 9999: row['best_vendor'] = "GEB"
            elif t == g and t != 9999: row['best_vendor'] = "Tie"
        except (ValueError, TypeError): pass
        
        return row

    # Process all items concurrently using ThreadPoolExecutor (max 3 workers to prevent overwhelming)
    with ThreadPoolExecutor(max_workers=3) as executor:
        for row in executor.map(process_item, items_to_check):
            if row:
                results.append(row)
                if isinstance(row.get('tmm_cost_raw'), float) and row['tmm_cost_raw'] > 0:
                    total_tmm += row['tmm_cost_raw']
                if isinstance(row.get('geb_cost_raw'), float) and row['geb_cost_raw'] > 0:
                    total_geb += row['geb_cost_raw']
        
    return {
        "breakdown": results,
        "total_tmm": round(total_tmm, 2) if total_tmm > 0 else "Inc",
        "total_geb": round(total_geb, 2) if total_geb > 0 else "Inc",
        "winner": "The Malt Miller" if (total_tmm < total_geb and total_tmm > 0) else "Get Er Brewed" if (total_geb < total_tmm and total_geb > 0) else "Inconclusive"
    }

def source_deficit(deficit_data, preferred_vendors=None):
    """
    Takes a deficit report and uses ThreadPoolExecutor to find the best prices
    to fulfill the missing ingredients.
    """
    items_to_check = []
    
    for hop in deficit_data.get('hops', []):
        if hop.get('deficit_g', 0) > 0:
            items_to_check.append({
                "name": hop['name'],
                "amount": hop['deficit_g'],
                "unit": "g",
                "type": "Hop"
            })
            
    for ferm in deficit_data.get('fermentables', []):
        if ferm.get('deficit_kg', 0) > 0:
            items_to_check.append({
                "name": ferm['name'],
                "amount": ferm['deficit_kg'],
                "unit": "kg",
                "type": "Malt"
            })

    # For simplicity, we wrap compare_recipe_prices logic
    # but adapt it to just these items. We could refactor compare_recipe_prices
    # to share a core processing function, but for Phase 1 we will construct a dummy recipe
    dummy_recipe = {
        "hops": [{"name": i['name'], "amount": i['amount']} for i in items_to_check if i['type'] == 'Hop'],
        "fermentables": [{"name": i['name'], "amount": i['amount']} for i in items_to_check if i['type'] == 'Malt']
    }
    
    # We call the existing price comparison engine which uses ThreadPoolExecutor
    # and Redis-like in-memory caching.
    cmp_results = compare_recipe_prices(dummy_recipe)
    
    if "error" in cmp_results:
        return cmp_results
        
    # Re-format output to match PRD
    cart = []
    total_cost = 0.0
    
    for row in cmp_results.get('breakdown', []):
        vendor = row.get('best_vendor', 'Unknown')
        
        # Default to TMM if tie or inconclusive
        if vendor == 'TMM' or vendor == 'Tie' or vendor == 'Unknown':
            v_name = "The Malt Miller"
            price = row.get('tmm_cost')
            link = row.get('tmm_link')
        else:
            v_name = "Get Er Brewed"
            price = row.get('geb_cost')
            link = row.get('geb_link')
            
        if price == '?':
            price = 0.0
            
        cart.append({
            "item": f"{row['name']} {row['amount']}",
            "vendor": v_name,
            "price": price,
            "link": link
        })
        total_cost += float(price) if isinstance(price, (int, float)) else 0.0
        
    return {
        "total_estimated_cost": round(total_cost, 2),
        "currency": "GBP",
        "cart": cart
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
    
    api_key = get_serpapi_key()
    
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
        except Exception: pass
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
            except (ValueError, TypeError):
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
        except Exception: pass
        
    return suggestions


# ============================================
# ASYNC JOB INFRASTRUCTURE
# ============================================

import threading
import uuid
import time as _time_module

# In-memory job store. Keys are job_id (str), values are dicts with:
#   status: "pending" | "running" | "done" | "error"
#   result: dict | None
#   error: str | None
#   created_at: float (time.time())
_jobs = {}
_jobs_lock = threading.Lock()
_JOB_TTL_SECONDS = 3600  # Jobs expire after 1 hour


def _cleanup_expired_jobs():
    """Remove jobs older than TTL to prevent unbounded memory growth."""
    now = _time_module.time()
    with _jobs_lock:
        expired = [jid for jid, j in _jobs.items() if now - j["created_at"] > _JOB_TTL_SECONDS]
        for jid in expired:
            del _jobs[jid]


def compare_recipe_prices_async(recipe_details=None, recipe_tag=None):
    """
    Runs compare_recipe_prices in a background thread.
    Returns a job_id immediately (does not block Flask).
    """
    _cleanup_expired_jobs()

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": _time_module.time(),
        }

    def _worker():
        with _jobs_lock:
            _jobs[job_id]["status"] = "running"
        try:
            result = compare_recipe_prices(recipe_details, recipe_tag=recipe_tag)
            with _jobs_lock:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["result"] = result
        except Exception as e:
            logger.error(f"Async price comparison failed (job {job_id}): {e}")
            with _jobs_lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = str(e)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return job_id


def get_job_status(job_id):
    """Returns the current state of an async job, or None if not found."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return None
    return {
        "job_id": job_id,
        "status": job["status"],
        "result": job["result"],
        "error": job["error"],
    }
