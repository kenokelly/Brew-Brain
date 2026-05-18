from flask import Blueprint, request
from core.auth import require_api_token
from services import scout, calculator, alerts, yeast, sourcing, learning, inventory
import logging
from api.routes import api_response, handle_error

automation_bp = Blueprint('automation', __name__)
logger = logging.getLogger(__name__)

# ============ Inventory Endpoints ============

@automation_bp.route('/api/automation/inventory', methods=['GET'])
@require_api_token
def get_inventory():
    try:
        results = inventory.get_processed_inventory()
        if isinstance(results, dict) and 'error' in results:
            return api_response(status="error", error=results['error'], code=500)
        return api_response(data=results)
    except Exception as e:
        return handle_error(e, "Inventory Fetch Error")

@automation_bp.route('/api/automation/inventory/sync', methods=['POST'])
@require_api_token
def sync_inventory():
    # In a full production environment this would trigger a Celery task.
    # For now, we perform a synchronous fetch.
    try:
        results = inventory.fetch_inventory_with_backoff()
        if isinstance(results, dict) and 'error' in results:
            return api_response(status="error", error=results['error'], code=500)
        return api_response(data={"message": "Inventory successfully synced", "raw_data": results})
    except Exception as e:
        return handle_error(e, "Inventory Sync Error")

# ============ Recipe Finder Endpoints ============

@automation_bp.route('/api/automation/recipes', methods=['POST'])
@require_api_token
def search_recipes():
    try:
        data = request.json or {}
        query = data.get('query')
        if not query:
            return api_response(status="error", error="Query required", code=400)
        
        results = scout.search_recipes(query)
        return api_response(data=results)
    except Exception as e:
        return handle_error(e, "Recipe Search Error")

@automation_bp.route('/api/automation/recipes/analyze', methods=['POST'])
@require_api_token
def analyze_recipes():
    try:
        data = request.json or {}
        query = data.get('query')
        if not query:
            return api_response(status="error", error="Query required", code=400)
        
        results = scout.analyze_xml_recipes(query)
        return api_response(data=results)
    except Exception as e:
        return handle_error(e, "Recipe Analysis Error")

# ============ Sourcing & Pricing Endpoints ============

@automation_bp.route('/api/automation/scout', methods=['POST'])
@require_api_token
def scout_ingredients():
    try:
        data = request.json or {}
        query = data.get('query')
        if not query:
            return api_response(status="error", error="Query required", code=400)
        
        results = scout.search_ingredients(query)
        return api_response(data=results)
    except Exception as e:
        return handle_error(e, "Ingredient Scout Error")

@automation_bp.route('/api/automation/sourcing/compare', methods=['POST'])
@require_api_token
def compare_prices():
    try:
        data = request.json or {}
        recipe_id = data.get('recipe_id')
        recipe_details = data.get('recipe_details')
        
        if not recipe_id and not recipe_details:
            return api_response(status="error", error="Recipe ID or details required", code=400)
        
        if recipe_id:
            # Fetch details from Brewfather
            details = alerts.fetch_recipe_details(recipe_id)
            if not details or 'error' in details:
                return api_response(status="error", error=f"Failed to fetch recipe: {details.get('error')}", code=404)
            recipe_details = details

        # Run comparison (Sync for now to simplify, or Async if needed)
        # The frontend seems to expect a direct response or we can implement the async job status route
        result = sourcing.compare_recipe_prices(recipe_details)
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Price Comparison Error")

# ============ Yeast Endpoints ============

@automation_bp.route('/api/automation/yeast/search', methods=['POST'])
@require_api_token
def search_yeast():
    try:
        data = request.json or {}
        query = data.get('query')
        if not query:
            return api_response(status="error", error="Yeast name required", code=400)
        
        result = yeast.search_yeast_meta(query)
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Yeast Search Error")

# ============ R&D Pipeline & Audit ============

@automation_bp.route('/api/automation/learning/audit', methods=['POST'])
@require_api_token
def audit_recipe():
    try:
        data = request.json or {}
        # Expected keys: name, style, og, ibu, abv
        result = learning.audit_recipe(data)
        return api_response(data=result)
    except Exception as e:
        return handle_error(e, "Recipe Audit Error")

# ============ Brewfather Integration ============

@automation_bp.route('/api/automation/brewfather/recipes', methods=['GET'])
@require_api_token
def get_bf_recipes():
    try:
        recipes = alerts.fetch_brewfather_recipes()
        if isinstance(recipes, dict) and 'error' in recipes:
            return api_response(status="error", error=recipes['error'], code=500)
        return api_response(data=recipes)
    except Exception as e:
        return handle_error(e, "Brewfather Recipe Fetch Error")

@automation_bp.route('/api/automation/brewfather/import', methods=['POST'])
@require_api_token
def import_bf_recipe():
    # Placeholder for importing external recipes into Brewfather
    return api_response(data={"message": "Import feature coming soon!"})

# ============ Calculator Endpoints ============

@automation_bp.route('/api/automation/calculator/strike', methods=['POST'])
@require_api_token
def calc_strike():
    try:
        data = request.json or {}
        res = calculator.calculate_strike_water(
            float(data.get('grain_temp', 20)),
            float(data.get('target_mash_temp', 65)),
            float(data.get('grain_weight_kg', 5)),
            float(data.get('water_ratio', 3))
        )
        return api_response(data=res)
    except Exception as e:
        return handle_error(e, "Calculator Error")
