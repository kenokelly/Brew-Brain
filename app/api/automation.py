from flask import Blueprint, jsonify, request
from app.core.decorators import api_safe
from app.services import scout, calculator, water, alerts
import io
import logging

automation_bp = Blueprint('automation', __name__)
logger = logging.getLogger(__name__)

@automation_bp.route('/api/qat/run_suite', methods=['POST'])
@api_safe
def run_qat_suite():
    from app.qat.runner import QATRunner
    runner = QATRunner()
    report = runner.run_suite()
    return jsonify(report)

@automation_bp.route('/api/automation/scout', methods=['POST'])
def search_ingredients():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "Query required"}), 400
    
    results = scout.search_ingredients(query)
    return jsonify(results)

@automation_bp.route('/api/automation/calc_ibu', methods=['POST'])
def calc_ibu():
    data = request.json
    try:
        ibu = calculator.calculate_tinseth_ibu(
            float(data.get('amount', 0)),
            float(data.get('alpha', 0)),
            float(data.get('time', 0)),
            float(data.get('volume', 0)),
            float(data.get('gravity', 1.050))
        )
        return jsonify({"ibu": ibu})
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numbers"}), 400

@automation_bp.route('/api/automation/water/<profile>', methods=['GET'])
def get_water(profile):
    if profile == 'all':
        return jsonify(water.get_all_profiles())
    
    p = water.get_profile(profile)
    if not p:
        return jsonify({"error": "Profile not found"}), 404
        
    return jsonify(p)

@automation_bp.route('/api/automation/alerts', methods=['POST'])
def check_alerts():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    f = request.files['file']
    target = float(request.form.get('target', 20.0))
    
    res = alerts.check_temp_stability(f, target, is_dataframe=False)
    return jsonify(res)

@automation_bp.route('/api/automation/brewfather/batches', methods=['GET'])
def get_bf_batches():
    res = alerts.fetch_brewfather_batches()
    if isinstance(res, dict) and res.get("error"):
        return jsonify(res), 500
    return jsonify(res)

@automation_bp.route('/api/automation/brewfather/analyze', methods=['POST'])
def analyze_bf_batch():
    data = request.json
    batch_id = data.get('batch_id')
    target = float(data.get('target', 20.0))
    
    if not batch_id: return jsonify({"error": "Batch ID required"}), 400
    
    readings = alerts.fetch_batch_readings(batch_id)
    if not readings: return jsonify({"error": "No readings found or API error"}), 404
    
    # Convert to DataFrame
    import pandas as pd
    df = pd.DataFrame(readings)
    
    # Ensure 'temp' column exists and is numeric
    if 'temp' in df.columns:
        df['temp'] = pd.to_numeric(df['temp'], errors='coerce')
        
    res = alerts.check_temp_stability(df, target, is_dataframe=True)
    return jsonify(res)

@automation_bp.route('/api/automation/sourcing/list', methods=['POST'])
def sourcing_list():
    data = request.json
    hops = data.get('hops', [])
    fermentables = data.get('fermentables', [])
    from app.services import sourcing
    res = sourcing.generate_shopping_list(hops, fermentables)
    return jsonify(res)

@automation_bp.route('/api/automation/sourcing/search', methods=['POST'])
def sourcing_search():
    data = request.json
    from app.services import sourcing
    res = sourcing.search_ingredient(data.get('query'))
    return jsonify(res)

@automation_bp.route('/api/automation/sourcing/watch', methods=['POST'])
def sourcing_watch():
    from app.services import sourcing
    # Trigger the check manually for now (can be cron'd)
    res = sourcing.check_price_watch()
    return jsonify(res)

@automation_bp.route('/api/automation/brewfather/recipes', methods=['GET'])
def get_bf_recipes():
    from app.services import alerts
    return jsonify(alerts.fetch_brewfather_recipes())

@automation_bp.route('/api/automation/sourcing/compare', methods=['POST'])
def compare_prices():
    data = request.json
    recipe_id = data.get('recipe_id')
    
    from app.services import alerts, sourcing
    
    # 1. Get Recipe
    recipe = alerts.fetch_recipe_details(recipe_id)
    if 'error' in recipe: return jsonify(recipe), 400
    
    # 2. Compare
    res = sourcing.compare_recipe_prices(recipe)
    return jsonify(res)

@automation_bp.route('/api/automation/pizza', methods=['GET'])
def get_pizza():
    from app.services import calculator
    return jsonify(calculator.get_pizza_schedule())

@automation_bp.route('/api/automation/logger/create', methods=['POST'])
def create_log():
    data = request.json
    from app.services import brew_logger
    content = brew_logger.generate_log_content(
        data.get('name', 'Brew Day'),
        data.get('batch', {}),
        data.get('water', {}),
        data.get('sourcing', {})
    )
    res = brew_logger.save_log(data.get('name', 'brew'), content)
    return jsonify(res)

@automation_bp.route('/api/automation/calcs/save_profile', methods=['POST'])
def save_profile():
    data = request.json
    import json
    import os
    
    # Simple JSON Store
    PROFILE_FILE = 'data/profiles.json'
    profiles = {}
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, 'r') as f:
                profiles = json.load(f)
        except: pass
        
    profiles[data.get('name')] = data.get('data')
    
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profiles, f, indent=2)
        
    return jsonify({"status": "success"})

@automation_bp.route('/api/automation/calcs/profiles', methods=['GET'])
def get_profiles():
    import json
    import os
    PROFILE_FILE = 'data/profiles.json'
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, 'r') as f:
            return jsonify(json.load(f))

    return jsonify({})

@automation_bp.route('/api/automation/inventory', methods=['GET'])
def get_inventory():
    import json
    import os
    try:
        with open('data/inventory.json', 'r') as f:
            return jsonify(json.load(f))
    except: return jsonify({})

@automation_bp.route('/api/automation/inventory/save', methods=['POST'])
def save_inventory():
    import json
    data = request.json
    try:
        with open('data/inventory.json', 'w') as f:
            json.dump(data, f, indent=4)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)})

@automation_bp.route('/api/automation/inventory/sync', methods=['POST'])
def sync_inventory():
    from app.services import alerts
    import json
    
    # 1. Fetch from BF
    bf_inv = alerts.fetch_brewfather_inventory()
    if "error" in bf_inv:
        return jsonify(bf_inv)
        
    # 2. Save locally (Overwrite or Merge? Let's Overwrite for "Sync")
    try:
        with open('data/inventory.json', 'w') as f:
            json.dump(bf_inv, f, indent=4)
        return jsonify({"status": "success", "inventory": bf_inv})
    except Exception as e:
        return jsonify({"error": str(e)})

@automation_bp.route('/api/automation/learning/save', methods=['POST'])
def learn_save():
    from app.services import learning
    res = learning.save_brew_outcome(request.json)
    return jsonify(res)

@automation_bp.route('/api/automation/learning/audit', methods=['POST'])
def learn_audit():
    from app.services import learning
    # recipe: {style, og, ibu, abv, name}
    res = learning.audit_recipe(request.json)
    return jsonify(res)

@automation_bp.route('/api/automation/learning/simulate', methods=['POST'])
def learn_simulate():
    data = request.json
    from app.services import learning, calculator
    
    # Pre-Validation
    grains = data.get('grains', [])
    total_grain = sum(g.get('weight_kg', 0) for g in grains)
    volume = float(data.get('volume', 23))
    
    # Check Hardware
    hw_check = calculator.validate_equipment(volume, total_grain)
    
    # grains: list of {weight_kg, potential}
    res = learning.simulate_brew_day(
        grains,
        volume,
        data.get('efficiency', 75)
    )
    
    # Inject Hardware Warnings
    if not hw_check['valid']:
        res['hardware_error'] = " | ".join(hw_check['warnings'])
    elif hw_check['warnings']:
        res['hardware_warning'] = " | ".join(hw_check['warnings'])
    
    # Add Fermentation Prediction if yeast provided
    if data.get('yeast'):
        ferm_pred = learning.predict_fg_from_history(data.get('yeast'), res['predicted_og'])
        res.update(ferm_pred)
        
    return jsonify(res)

@automation_bp.route('/api/automation/learning/import_log', methods=['POST'])
def learn_import():
    data = request.json
    from app.services import learning
    # Expects: csv_content, recipe_name, yeast_name
    res = learning.learn_from_logs(
        data.get('csv_content'),
        data.get('recipe_name', 'Unknown Brew'),
        data.get('yeast_name', 'Unknown Yeast')
    )
    return jsonify(res)

@automation_bp.route('/api/automation/monitoring/check', methods=['POST'])
def monitor_check():
    data = request.json
    from app.services import learning
    # Expects: current_sg, original_gravity, yeast_name, days_in, temp, style, batch_name, stability
    res = learning.check_batch_health(
        data.get('current_sg'),
        data.get('original_gravity'),
        data.get('yeast_name'),
        data.get('days_in', 0),
        data.get('temp'),
        data.get('style'),
        data.get('batch_name', 'Current Batch'),
        data.get('stability') # New param
    )
    return jsonify(res)

@automation_bp.route('/api/automation/github/save', methods=['POST'])
def github_save():
    # Placeholder for actual save logic wrapper
    return jsonify({"status": "not implemented yet"})

@automation_bp.route('/api/automation/monitoring/scan', methods=['POST'])
def monitoring_scan():
    """
    Triggers the full R&D pipeline scan:
    Brewfather -> Tilt Data -> Health Check -> Telegram
    """
    from app.services import alerts
    res = alerts.monitor_active_batches()
    return jsonify(res)

@automation_bp.route('/api/automation/recipes', methods=['POST'])
def search_recipes():
    data = request.json
    from app.services import scout
    return jsonify(scout.search_recipes(data.get('query')))

@automation_bp.route('/api/automation/recipes/analyze', methods=['POST'])
def exp_analyze_recipes():
    data = request.json
    from app.services import scout
    return jsonify(scout.analyze_xml_recipes(data.get('query')))

@automation_bp.route('/api/automation/recipes/scale', methods=['POST'])
def scale_recipe():
    data = request.json
    from app.services import calculator
    return jsonify(calculator.scale_recipe_to_equipment(data))

@automation_bp.route('/api/automation/brewfather/import', methods=['POST'])
def exp_import_recipe():
    # Placeholder for import
    return jsonify({"status": "success", "message": "Recipe imported to Brewfather (Simulation)"})
