from services.inventory import get_processed_inventory
from services.alerts import fetch_recipe_details
from lxml import etree
import logging

logger = logging.getLogger(__name__)

def parse_beerxml(xml_string):
    """
    Parses a BeerXML string using lxml and normalizes ingredients.
    """
    try:
        root = etree.fromstring(xml_string.encode('utf-8'))
        recipe = root.find('.//RECIPE')
        
        if recipe is None:
            return {"error": "Invalid BeerXML: No RECIPE tag found"}
            
        normalized = {
            "name": recipe.findtext('NAME', 'Unknown XML Recipe'),
            "batch_size_l": float(recipe.findtext('BATCH_SIZE', 20)),
            "boil_size_l": float(recipe.findtext('BOIL_SIZE', 25)),
            "hops": [],
            "fermentables": []
        }
        
        # Parse Hops (BeerXML stores amount in KG)
        for hop in recipe.findall('.//HOP'):
            name = hop.findtext('NAME', 'Unknown Hop')
            amt_kg = float(hop.findtext('AMOUNT', 0))
            normalized["hops"].append({
                "name": name,
                "amount_g": amt_kg * 1000  # Convert to grams for internal consistency
            })
            
        # Parse Fermentables (BeerXML stores amount in KG)
        for ferm in recipe.findall('.//FERMENTABLE'):
            name = ferm.findtext('NAME', 'Unknown Grain')
            amt_kg = float(ferm.findtext('AMOUNT', 0))
            normalized["fermentables"].append({
                "name": name,
                "amount_kg": amt_kg
            })
            
        return normalized
    except Exception as e:
        logger.error(f"BeerXML Parse Error: {e}")
        return {"error": str(e)}

def parse_brewfather_recipe(recipe_id):
    """
    Fetches and normalizes a Brewfather recipe by ID.
    """
    bf_data = fetch_recipe_details(recipe_id)
    if isinstance(bf_data, dict) and 'error' in bf_data:
        return bf_data
        
    normalized = {
        "name": bf_data.get('name', 'Unknown BF Recipe'),
        "batch_size_l": float(bf_data.get('batchSize', 20)),
        "boil_size_l": float(bf_data.get('boilSize', 25)),
        "hops": [],
        "fermentables": []
    }
    
    # Brewfather API hops are in grams
    for hop in bf_data.get('hops', []):
        normalized["hops"].append({
            "name": hop.get('name', 'Unknown Hop'),
            "amount_g": float(hop.get('amount', 0))
        })
        
    # Brewfather API fermentables are in kg
    for ferm in bf_data.get('fermentables', []):
        normalized["fermentables"].append({
            "name": ferm.get('name', 'Unknown Grain'),
            "amount_kg": float(ferm.get('amount', 0))
        })
        
    return normalized

def calculate_ingredient_deficit(normalized_recipe):
    """
    Cross-references recipe requirements against current inventory
    to generate an actionable deficit report.
    """
    inventory = get_processed_inventory()
    if isinstance(inventory, dict) and 'error' in inventory:
        return {"error": "Could not load inventory to calculate deficit"}
        
    deficit_report = {
        "hops": [],
        "fermentables": []
    }
    
    warnings = []
    
    # Check G40 Physical Limits
    total_grain = sum(f['amount_kg'] for f in normalized_recipe['fermentables'])
    if total_grain > 12.0:
        warnings.append(f"Grain bill ({round(total_grain, 1)}kg) exceeds G40 maximum efficiency threshold (12kg)")
    if normalized_recipe['boil_size_l'] > 40.0:
        warnings.append(f"Boil volume ({round(normalized_recipe['boil_size_l'], 1)}L) exceeds G40 physical capacity (40L)")
        
    # Calculate Hop Deficit
    inv_hops = {h['name'].lower(): h['amount_g'] for h in inventory.get('hops', [])}
    for req_hop in normalized_recipe['hops']:
        name = req_hop['name']
        req_amount = req_hop['amount_g']
        in_stock = inv_hops.get(name.lower(), 0)
        
        if in_stock < req_amount:
            deficit_report["hops"].append({
                "name": name,
                "amount_needed_g": req_amount,
                "amount_in_stock_g": in_stock,
                "deficit_g": round(req_amount - in_stock, 1)
            })
            
    # Calculate Fermentable Deficit
    inv_ferm = {f['name'].lower(): f['amount_kg'] for f in inventory.get('fermentables', [])}
    for req_ferm in normalized_recipe['fermentables']:
        name = req_ferm['name']
        req_amount = req_ferm['amount_kg']
        in_stock = inv_ferm.get(name.lower(), 0)
        
        if in_stock < req_amount:
            deficit_report["fermentables"].append({
                "name": name,
                "amount_needed_kg": req_amount,
                "amount_in_stock_kg": in_stock,
                "deficit_kg": round(req_amount - in_stock, 2)
            })
            
    return {
        "recipe_name": normalized_recipe['name'],
        "warnings": warnings,
        "deficit": deficit_report,
        "has_deficit": len(deficit_report['hops']) > 0 or len(deficit_report['fermentables']) > 0
    }

def parse_recipe_and_calculate_deficit(source_type, source_data):
    """
    Main entrypoint: parses recipe and returns deficit report.
    """
    if source_type == 'beerxml':
        recipe = parse_beerxml(source_data)
    elif source_type == 'brewfather':
        recipe = parse_brewfather_recipe(source_data)
    else:
        return {"error": "Invalid source type. Must be 'beerxml' or 'brewfather'"}
        
    if 'error' in recipe:
        return recipe
        
    report = calculate_ingredient_deficit(recipe)
    report['status'] = "success"
    return report
