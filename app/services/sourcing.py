import logging
import requests
import json
import math
import re
from app.core.config import get_config
from serpapi import GoogleSearch

logger = logging.getLogger(__name__)

# Helper to extract price from text (e.g. "£13.95" or "13.95")
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
    except:
        pass
        
    return None

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
    except:
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
        
    results = []
    total_tmm = 0.0
    total_geb = 0.0
    
    api_key = get_config("serp_api_key")
    if not api_key: return {"error": "Missing SerpApi Key"}
    
    def search_price(query):
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

             for i, res in enumerate(organic):
                 logger.info(f"DEBUG: Result {i} Snippet: {res.get('snippet')}")
                 logger.info(f"DEBUG: Result {i} Rich: {res.get('rich_snippet')}")
                 
                 # 1. Try Rich Snippet (if available)
                 rich = res.get("rich_snippet", {}).get("top", {}).get("detected_extensions", {})
                 if rich.get("price"):
                     p = extract_price(f"£{rich['price']}") # often just number
                     if p: return p
                 
                 # 2. Try Snippet
                 snippet = res.get("snippet", "")
                 p = extract_price(snippet)
                 if p: return p
                 
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
            "best_vendor": "None"
        }
        
        # Search TMM
        p_tmm = search_price(f"{item['name']} site:themaltmiller.co.uk")
        if p_tmm:
            row['tmm_price'] = p_tmm
            total_tmm += p_tmm
            
        # Search GEB
        p_geb = search_price(f"{item['name']} site:geterbrewed.com")
        if p_geb:
            row['geb_price'] = p_geb
            total_geb += p_geb
        
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
