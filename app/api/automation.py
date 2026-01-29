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
    """Compare recipe ingredient prices between TMM and GEB.
    DIAGNOSTIC MODE: Returns full stack trace for debugging.
    """
    import traceback
    
    try:
        data = request.json or {}
        recipe_id = data.get('recipe_id')
        
        if not recipe_id:
            return jsonify({
                "error": "Missing recipe_id",
                "breakdown": [],
                "total_tmm": 0,
                "total_geb": 0,
                "winner": ""
            }), 400
        
        from app.services import alerts, sourcing
        
        # 1. Get Recipe with detailed error
        logger.info(f"[DIAG] Fetching recipe: {recipe_id}")
        recipe = alerts.fetch_recipe_details(recipe_id)
        
        if not recipe:
            return jsonify({
                "error": "Recipe not found (null response from Brewfather)",
                "breakdown": [],
                "total_tmm": 0,
                "total_geb": 0,
                "winner": ""
            }), 404
            
        if isinstance(recipe, dict) and 'error' in recipe:
            return jsonify({
                "error": f"Recipe fetch error: {recipe.get('error', 'Unknown')}",
                "breakdown": [],
                "total_tmm": 0,
                "total_geb": 0,
                "winner": ""
            }), 400
        
        # 2. Compare prices with FULL stack trace on error
        logger.info(f"[DIAG] Starting price comparison for: {recipe.get('name', 'Unknown')}")
        try:
            result = sourcing.compare_recipe_prices(recipe)
            logger.info(f"[DIAG] Price comparison complete. Result keys: {list(result.keys()) if isinstance(result, dict) else 'NOT A DICT'}")
        except Exception as scrape_error:
            tb = traceback.format_exc()
            logger.error(f"[DIAG] Price scraping CRASHED:\n{tb}")
            return jsonify({
                "error": f"Price scraping failed: {str(scrape_error)}",
                "stack_trace": tb,
                "breakdown": [],
                "total_tmm": 0,
                "total_geb": 0,
                "winner": ""
            }), 500
            
        # Ensure result has expected structure
        if not isinstance(result, dict):
            return jsonify({
                "error": f"Invalid response type from price comparison: {type(result).__name__}",
                "breakdown": [],
                "total_tmm": 0,
                "total_geb": 0,
                "winner": ""
            }), 500
            
        return jsonify(result)
        
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[DIAG] Unexpected error in compare_prices:\n{tb}")
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "stack_trace": tb,
            "breakdown": [],
            "total_tmm": 0,
            "total_geb": 0,
            "winner": ""
        }), 500

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


# ============================================
# NEW BREWING CALCULATORS API
# ============================================

@automation_bp.route('/api/automation/calc/water_chemistry', methods=['POST'])
@api_safe
def calc_water_chemistry():
    """
    Calculate salt additions to transform source water to target profile.
    
    Body: {
        "source_water": {"calcium": 0, "magnesium": 0, ...} or null for RO,
        "target_profile": "neipa" | "west_coast" | "balanced" | etc,
        "volume_liters": 23
    }
    """
    from app.services import water_chemistry
    data = request.json
    
    # Default to RO water if not specified
    source = data.get('source_water') or water_chemistry.get_ro_water_source()
    target = data.get('target_profile', 'balanced')
    volume = float(data.get('volume_liters', 23))
    
    result = water_chemistry.calculate_salt_additions(source, target, volume)
    return jsonify(result)


@automation_bp.route('/api/automation/calc/carbonation', methods=['POST'])
@api_safe
def calc_carbonation():
    """
    Calculate PSI for forced carbonation.
    
    Body: {
        "temp_c": 4,
        "volumes_co2": 2.4
    }
    """
    data = request.json
    result = calculator.calculate_carbonation_psi(
        float(data.get('temp_c', 4)),
        float(data.get('volumes_co2', 2.4))
    )
    return jsonify(result)


@automation_bp.route('/api/automation/calc/refractometer', methods=['POST'])
@api_safe
def calc_refractometer():
    """
    Correct refractometer reading for alcohol presence.
    
    Body: {
        "original_brix": 15.0,
        "final_brix": 8.0,
        "wort_correction_factor": 1.04 (optional)
    }
    """
    data = request.json
    result = calculator.correct_refractometer_reading(
        float(data.get('final_brix', 0)),
        float(data.get('original_brix', 0)),
        float(data.get('wort_correction_factor', 1.04))
    )
    return jsonify(result)


@automation_bp.route('/api/automation/calc/priming', methods=['POST'])
@api_safe
def calc_priming():
    """
    Calculate priming sugar for bottle conditioning.
    
    Body: {
        "volume_liters": 20,
        "temp_c": 20,
        "target_co2": 2.4,
        "sugar_type": "corn_sugar" (optional)
    }
    """
    data = request.json
    result = calculator.calculate_priming_sugar(
        float(data.get('volume_liters', 20)),
        float(data.get('temp_c', 20)),
        float(data.get('target_co2', 2.4)),
        data.get('sugar_type', 'corn_sugar')
    )
    return jsonify(result)


@automation_bp.route('/api/automation/water/profiles', methods=['GET'])
@api_safe
def get_all_water_profiles():
    """Get all available water profiles for the chemistry calculator."""
    return jsonify(water.get_all_profiles())


@automation_bp.route('/api/automation/calc/mash_ph', methods=['POST'])
@api_safe
def calc_mash_ph():
    """
    Predict mash pH from grain bill and water chemistry.
    
    Body: {
        "grains": [
            {"name": "Pale Malt", "weight_kg": 5.0, "lovibond": 2.5},
            {"name": "Crystal 60", "weight_kg": 0.5, "lovibond": 60}
        ],
        "water_profile": {"bicarbonate": 100, "calcium": 50, "magnesium": 10},
        "target_ph": 5.4,
        "mash_volume_l": 20
    }
    """
    from app.services import mash_chemistry
    data = request.json
    
    grains = data.get('grains', [])
    water_profile = data.get('water_profile', {"bicarbonate": 0, "calcium": 0, "magnesium": 0})
    target_ph = float(data.get('target_ph', 5.4))
    mash_volume = float(data.get('mash_volume_l', 20))
    
    result = mash_chemistry.predict_mash_ph(grains, water_profile, target_ph, mash_volume)
    return jsonify(result)


@automation_bp.route('/api/automation/calc/hop_freshness', methods=['POST'])
@api_safe
def calc_hop_freshness():
    """
    Calculate hop freshness and alpha acid degradation.
    
    Body: {
        "hop_name": "Citra",
        "original_alpha": 12.0,
        "purchase_date": "2025-06-01",
        "storage": "freezer"
    }
    """
    from app.services import sourcing
    data = request.json
    
    result = sourcing.calculate_hop_freshness(
        data.get('hop_name', 'Unknown'),
        float(data.get('original_alpha', 10.0)),
        data.get('purchase_date', '2025-01-01'),
        data.get('storage', 'freezer')
    )
    return jsonify(result)


@automation_bp.route('/api/automation/inventory/hop_freshness', methods=['GET'])
@api_safe
def get_inventory_hop_freshness():
    """Check freshness of all hops in inventory."""
    from app.services import sourcing
    results = sourcing.check_inventory_hop_freshness()
    return jsonify({"hops": results})


@automation_bp.route('/api/automation/yeast/search', methods=['POST'])
@api_safe
def search_yeast():
    """
    Search for yeast strain metadata (attenuation, flocculation, temp range).
    
    Body: {
        "query": "WLP001"
    }
    """
    from app.services import yeast
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "Query required"}), 400
    result = yeast.search_yeast_meta(query)
    return jsonify(result)


@automation_bp.route('/api/automation/anomaly/check', methods=['POST'])
@api_safe
def check_anomalies():
    """
    Run anomaly detection checks manually.
    
    Body (optional): {
        "batch_name": "My IPA"
    }
    
    Returns: {
        "timestamp": "...",
        "checks": {
            "stalled": {...},
            "temp_deviation": {...},
            "runaway": {...},
            "signal_loss": {...}
        },
        "alerts_sent": 0,
        "status": "ok"
    }
    """
    from app.services.anomaly import run_all_anomaly_checks
    from app.core.config import get_config
    
    data = request.json or {}
    batch_name = data.get('batch_name') or get_config("batch_name") or "Current Batch"
    
    result = run_all_anomaly_checks(batch_name)
    return jsonify(result)


@automation_bp.route('/api/automation/anomaly/stalled', methods=['GET'])
@api_safe
def check_stalled():
    """Check for stalled fermentation only."""
    from app.services.anomaly import check_stalled_fermentation
    from app.core.config import get_config
    batch_name = get_config("batch_name") or "Current Batch"
    return jsonify(check_stalled_fermentation(batch_name))


@automation_bp.route('/api/automation/anomaly/temp', methods=['GET'])
@api_safe
def check_temp():
    """Check for temperature deviation only."""
    from app.services.anomaly import check_temperature_deviation
    from app.core.config import get_config
    batch_name = get_config("batch_name") or "Current Batch"
    return jsonify(check_temperature_deviation(batch_name=batch_name))


# ============ ML Prediction Endpoints ============

@automation_bp.route('/api/ml/train', methods=['POST'])
@api_safe
def train_ml_models():
    """
    Train ML prediction models using historical batch data.
    
    Returns: {
        "status": "success",
        "batches_used": 15,
        "fg_model": {"mae": 0.003},
        "time_model": {"mae": 1.2}
    }
    """
    from app.ml.prediction import train_models
    result = train_models()
    return jsonify(result)


@automation_bp.route('/api/ml/predict/fg', methods=['POST'])
@api_safe
def predict_fg():
    """
    Predict Final Gravity for a batch.
    
    Body: {
        "og": 1.055,
        "attenuation": 78.0,
        "avg_temp": 20.0  (optional)
    }
    """
    from app.ml.prediction import predict_fg as ml_predict_fg
    data = request.json or {}
    
    og = data.get('og')
    attenuation = data.get('attenuation')
    
    if not og or not attenuation:
        return jsonify({"error": "og and attenuation required"}), 400
    
    result = ml_predict_fg(
        float(og),
        float(attenuation),
        float(data.get('avg_temp', 20.0))
    )
    return jsonify(result)


@automation_bp.route('/api/ml/predict/time', methods=['POST'])
@api_safe
def predict_time():
    """
    Predict days remaining until FG is reached.
    
    Body: {
        "og": 1.055,
        "current_sg": 1.025,
        "attenuation": 78.0,
        "days_elapsed": 3  (optional)
    }
    """
    from app.ml.prediction import predict_time_to_fg
    data = request.json or {}
    
    og = data.get('og')
    current_sg = data.get('current_sg')
    attenuation = data.get('attenuation')
    
    if not og or not current_sg or not attenuation:
        return jsonify({"error": "og, current_sg, and attenuation required"}), 400
    
    result = predict_time_to_fg(
        float(og),
        float(current_sg),
        float(attenuation),
        float(data.get('days_elapsed', 0))
    )
    return jsonify(result)


@automation_bp.route('/api/ml/info', methods=['GET'])
@api_safe
def ml_model_info():
    """Get information about trained ML models."""
    from app.ml.prediction import get_model_info
    return jsonify(get_model_info())
