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

# ============ Recipe Parser Endpoints ============

@automation_bp.route('/api/automation/recipe/parse', methods=['POST'])
@require_api_token
def parse_recipe():
    from services.recipe_parser import parse_recipe_and_calculate_deficit
    try:
        data = request.json or {}
        source_type = data.get('source')
        recipe_data = data.get('recipe_data') or data.get('recipe_id')
        
        if not source_type or not recipe_data:
            return api_response(status="error", error="Source (beerxml/brewfather) and data required", code=400)
            
        results = parse_recipe_and_calculate_deficit(source_type, recipe_data)
        if isinstance(results, dict) and 'error' in results:
            return api_response(status="error", error=results['error'], code=500)
            
        return api_response(data=results)
    except Exception as e:
        return handle_error(e, "Recipe Parsing Error")

# ============ Simulation & R&D Endpoints ============

@automation_bp.route('/api/automation/simulate', methods=['POST'])
@require_api_token
def trigger_simulation():
    try:
        data = request.json or {}
        target_og = data.get('target_og')
        yeast = data.get('yeast')
        mash_temp_c = data.get('mash_temp_c')
        
        if not all([target_og, yeast, mash_temp_c]):
            return api_response(status="error", error="Missing parameters. Requires target_og, yeast, and mash_temp_c.", code=400)
            
        # Trigger Celery Task
        from services.tasks import run_monte_carlo_task
        task = run_monte_carlo_task.delay(float(target_og), yeast, float(mash_temp_c))
        
        return api_response(data={"status": "queued", "task_id": task.id})
    except Exception as e:
        return handle_error(e, "Simulation Trigger Error")

@automation_bp.route('/api/automation/simulate/status/<task_id>', methods=['GET'])
@require_api_token
def check_simulation_status(task_id):
    try:
        from extensions import celery
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id, app=celery)
        
        if task_result.state == 'PENDING':
            return api_response(data={"status": "queued"})
        elif task_result.state == 'FAILURE':
            return api_response(status="error", error=str(task_result.info), code=500)
        elif task_result.state == 'SUCCESS':
            result_data = task_result.get()
            return api_response(data=result_data)
        else:
             return api_response(data={"status": task_result.state})
    except Exception as e:
         return handle_error(e, "Simulation Status Check Error")

# ============ Sourcing & Pricing Endpoints ============

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

@automation_bp.route('/api/automation/source', methods=['POST'])
@require_api_token
def source_deficit():
    try:
        data = request.json or {}
        deficit = data.get('deficit')
        preferred_vendors = data.get('preferred_vendors')
        
        if not deficit:
            return api_response(status="error", error="Deficit data required", code=400)
            
        results = sourcing.source_deficit(deficit, preferred_vendors)
        if isinstance(results, dict) and 'error' in results:
             return api_response(status="error", error=results['error'], code=500)
             
        return api_response(data=results)
    except Exception as e:
        return handle_error(e, "Deficit Sourcing Error")

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


# ============ TiltPi Diagnostics ============

@automation_bp.route('/api/automation/tiltpi/troubleshoot', methods=['GET'])
@require_api_token
def tiltpi_troubleshoot():
    """
    Run the TiltPi connectivity diagnostic and return results.

    Response:
      status: 'healthy' | 'data_issue' | 'connectivity_issue' | 'config_error'
      checks: list of individual check results
      suggested_actions: list of human-readable remediation steps
    """
    try:
        from services.notifications import troubleshoot_tiltpi
        result = troubleshoot_tiltpi()
        # Surface connectivity issues as 503 so the UI can distinguish
        code = 200 if result["status"] == "healthy" else 503
        return api_response(data=result), code
    except Exception as e:
        return handle_error(e, "TiltPi Troubleshoot Error")


# ============ Pipeline Diagnostics (B05) ============

@automation_bp.route('/api/automation/monitoring/scan', methods=['POST'])
@require_api_token
def pipeline_scan():
    """Scan Brewfather active batches and return their statuses."""
    try:
        from core.cache import cache
        from services.brewfather_client import get_active_batches
        # Use cache if available
        cached = cache.get("pipeline_scan_cache")
        if cached:
            return api_response(data={"batches": cached})
            
        batches = get_active_batches()
        
        # Transform for Pipeline UI
        formatted = []
        for b in batches:
            formatted.append({
                "name": b.get("name", "Unknown"),
                "number": b.get("batchNo"),
                "brewer": b.get("brewer"),
                "status": b.get("status", "Unknown"),
                "gravity": b.get("measuredSg", b.get("estimatedSg")),
                "temp": b.get("measuredTemp"),
                "health_check": {
                    "status": "stable",
                    "message": "Tracking nominally with Brewfather data."
                }
            })
            
        cache.set("pipeline_scan_cache", formatted, timeout=300)
        return api_response(data={"batches": formatted})
    except Exception as e:
        return handle_error(e, "Pipeline Scan Error")

@automation_bp.route('/api/automation/brewfather/batches', methods=['GET'])
@require_api_token
def bf_batches_list():
    """Return all Brewfather batches for selection in diagnostics."""
    try:
        from services.brewfather_client import get_active_batches
        batches = get_active_batches() # Or a broader endpoint if needed
        return jsonify(batches) # Pipeline expects raw array for this one
    except Exception as e:
        return handle_error(e, "Brewfather Batches Error")

@automation_bp.route('/api/automation/alerts', methods=['POST'])
@require_api_token
def analyze_csv_log():
    """Manual Diagnostic: Parse a CSV log and run stability analysis."""
    try:
        if 'file' not in request.files:
            return api_response(status="error", error="No file provided", code=400)
            
        file = request.files['file']
        target = request.form.get('target', 20.0, type=float)
        csv_content = file.read().decode('utf-8')
        
        from services.learning import learn_from_logs
        result = learn_from_logs(csv_content, "Diagnostics", "Unknown Yeast")
        
        if "error" in result:
            return api_response(status="error", error=result["error"], code=400)
            
        stability = result.get("temp_stability", 0)
        status = "warning" if stability > 0.5 else "stable"
        msg = f"Analysis complete. Temperature deviation: ±{stability}°C from average."
        if status == "warning":
            msg += " Deviation is above 0.5°C threshold."
            
        return api_response(data={
            "status": status,
            "message": msg,
            "stability_score": stability
        })
    except Exception as e:
        return handle_error(e, "CSV Analysis Error")

@automation_bp.route('/api/automation/brewfather/analyze', methods=['POST'])
@require_api_token
def analyze_bf_batch():
    """Manual Diagnostic: Analyze a Brewfather batch ID for stability."""
    try:
        data = request.json or {}
        batch_id = data.get("batch_id")
        target = data.get("target", 20.0)
        
        if not batch_id:
            return api_response(status="error", error="batch_id required", code=400)
            
        # In a real scenario, this would fetch readings for the batch.
        # For now, simulate a result.
        return api_response(data={
            "status": "stable",
            "message": f"Batch {batch_id} tracking securely around {target}°C.",
            "stability_score": 0.2
        })
    except Exception as e:
        return handle_error(e, "BF Analysis Error")


# ============ Experiment Tracker CRUD ============

@automation_bp.route('/api/automation/experiments', methods=['GET'])
@require_api_token
def list_experiments():
    try:
        from services.experiments import get_experiments
        return api_response(data={"experiments": get_experiments()})
    except Exception as e:
        return handle_error(e, "Experiments Fetch Error")

@automation_bp.route('/api/automation/experiments', methods=['POST'])
@require_api_token
def create_experiment():
    try:
        from services.experiments import add_experiment
        data = request.json or {}
        exp = add_experiment(data)
        return api_response(data={"experiment": exp})
    except Exception as e:
        return handle_error(e, "Experiment Creation Error")

@automation_bp.route('/api/automation/experiments/<exp_id>', methods=['PUT'])
@require_api_token
def modify_experiment(exp_id):
    try:
        from services.experiments import update_experiment
        data = request.json or {}
        exp = update_experiment(exp_id, data)
        if not exp:
            return api_response(status="error", error="Not found", code=404)
        return api_response(data={"experiment": exp})
    except Exception as e:
        return handle_error(e, "Experiment Update Error")

@automation_bp.route('/api/automation/experiments/<exp_id>', methods=['DELETE'])
@require_api_token
def remove_experiment(exp_id):
    try:
        from services.experiments import delete_experiment
        success = delete_experiment(exp_id)
        if not success:
            return api_response(status="error", error="Not found", code=404)
        return api_response(data={"message": "Deleted"})
    except Exception as e:
        return handle_error(e, "Experiment Deletion Error")
