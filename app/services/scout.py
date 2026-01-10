import logging
from serpapi import GoogleSearch
from app.core.config import get_config

logger = logging.getLogger(__name__)

PREFERRED_VENDORS = [
    "The Malt Miller",
    "Get Er Brewed"
]

def search_ingredients(query):
    """
    Searches for brewing ingredients using SerpApi Google Shopping.
    Prioritizes results from The Malt Miller and Get Er Brewed.
    """
    api_key = get_config("serp_api_key")
    if not api_key:
        logger.error("SERP_API_KEY not configured.")
        return {"error": "API Key Missing"}

    logger.info(f"Searching for: {query}")

    params = {
        "engine": "google_shopping",
        "q": query,
        "location": "United Kingdom",
        "hl": "en",
        "gl": "uk",
        "api_key": api_key
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        shopping_results = results.get("shopping_results", [])

        filtered_results = []
        
        for item in shopping_results:
            source = item.get("source")
            if any(vendor.lower() in source.lower() for vendor in PREFERRED_VENDORS):
                item['is_preferred'] = True
                filtered_results.insert(0, item)
            else:
                item['is_preferred'] = False
                filtered_results.append(item)
                
        return filtered_results

    except Exception as e:
        logger.error(f"Error executing search: {e}")
        return {"error": str(e)}

def analyze_xml_recipes(query):
    """
    Searches for BeerXML recipes and analyzes them against G40 specs.
    Calculates Brewer's Percentages and Est. Final pH.
    """
    import requests
    from services.calculator import validate_equipment
    
    # Mocking for demo purposes
    # Ideally this parses real XMLs found via Google Search
    
    mock_recipes = []
    
    # helper
    def calc_breakdown_and_ph(ingredients, style_type="ale"):
        total_g = sum(i['amount'] for i in ingredients)
        base_ph = 4.45 # Standard finished beer pH
        
        # pH Modifiers
        if "roast" in str(ingredients).lower() or "chocolate" in str(ingredients).lower():
            base_ph -= 0.15
        if style_type == "neipa" or "citra" in str(ingredients).lower(): # Heavy hop buffering
            base_ph += 0.1
        if "sour" in  style_type or "acid" in str(ingredients).lower():
            base_ph = 3.5
            
        breakdown = []
        for i in ingredients:
            pct = (i['amount'] / total_g) * 100
            breakdown.append(f"{round(pct)}% {i['name']}")
            
        return breakdown, round(base_ph, 2)


        
    consensus = {
        "count": len(mock_recipes),
        "recipes": []
    }
    
    for r in mock_recipes:
        hw = validate_equipment(r['batch_size_l'], r['total_grain_kg'])
        r['hardware_valid'] = hw['valid']
        r['hardware_warnings'] = hw['warnings']
        consensus['recipes'].append(r)
        
    # helper
    def get_style_wisdom(name, ingredients):
        n = name.lower()
        i = str(ingredients).lower()
        
        if "neipa" in n or "hazy" in n or "juicy" in n:
            return {"style": "NEIPA", "ph_range": "4.4-4.6", "desc": "Soft/Juicy Finish"}
        elif "stout" in n or "porter" in n:
             return {"style": "Stout", "ph_range": "4.1-4.3", "desc": "Acidic Cut for Roast"}
        elif "sour" in n or "gose" in n or "berliner" in n:
             return {"style": "Sour", "ph_range": "3.2-3.4", "desc": "Tart/Acidic"}
        elif "lager" in n or "pilsner" in n:
             return {"style": "Lager", "ph_range": "4.2-4.4", "desc": "Crisp Finish"}
        else:
             return {"style": "Ale", "ph_range": "4.3-4.5", "desc": "Standard Balance"}
             
    # Helper to 'parse' notes (Mocking the finding)
    def parse_recipe_notes_for_ph(name):
        if "julius" in name.lower():
            return 4.55 # Julius typically finishes high
        return None

    if "julius" in query.lower():
        # High Adjunct, Heavy Hop
        grains = [
            {"name": "Pale Malt", "amount": 12.0},
            {"name": "Flaked Oats", "amount": 1.5},
            {"name": "Honey Malt", "amount": 1.0}
        ]
        breakdown, ph = calc_breakdown_and_ph(grains, "neipa")
        wisdom = get_style_wisdom("NEIPA", grains)
        target = parse_recipe_notes_for_ph("julius")
        
        mock_recipes.append({
            "name": "Treehouse Julius Clone_V2",
            "source_url": "http://example.com/julius.xml",
            "og": 1.080,
            "ibu": 75,
            "abv": 8.2,
            "hops_summary": "Citra, Mosaic (300g)",
            "total_grain_kg": 14.5,
            "batch_size_l": 23,
            "grain_breakdown": breakdown,
            "est_ph": ph,
            "target_ph": target,
            "wisdom": wisdom
        })
    else:
        # Standard Ale
        grains = [
            {"name": "Maris Otter", "amount": 4.5},
            {"name": "Crystal 60", "amount": 0.5}
        ]
        breakdown, ph = calc_breakdown_and_ph(grains, "ale")
        wisdom = get_style_wisdom("Ale", grains)
        
        mock_recipes.append({
            "name": f"{query.title()} Standard",
            "source_url": "http://example.com/recipe.xml",
            "og": 1.050,
            "ibu": 40,
            "abv": 5.0,
            "hops_summary": "Cascade (100g)",
            "total_grain_kg": 5.0,
            "batch_size_l": 23,
            "grain_breakdown": breakdown,
            "est_ph": ph,
            "target_ph": None, # No explicit target in this mock
            "wisdom": wisdom
        })
        
    consensus = {
        "count": len(mock_recipes),
        "recipes": []
    }
    
    for r in mock_recipes:
        hw = validate_equipment(r['batch_size_l'], r['total_grain_kg'])
        r['hardware_valid'] = hw['valid']
        r['hardware_warnings'] = hw['warnings']
        consensus['recipes'].append(r)
        
    return consensus
