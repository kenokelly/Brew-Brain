from flask import Blueprint, jsonify, request
from app.core.decorators import api_safe
from app.core.auth import require_api_token
from app.services import scout, calculator, water, alerts
import io
import json
import os
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
def scout_ingredients():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "Query required"}), 400
    
    results = scout.search_ingredients(query)
    return jsonify(results)

@automation_bp.route('/api/automation/calculator/strike', methods=['POST'])
def calc_strike():
    data = request.json
    res = calculator.calculate_strike_water(
        float(data.get('grain_temp', 20)),
        float(data.get('target_mash_temp', 65)),
        float(data.get('grain_weight_kg', 5)),
        float(data.get('water_ratio', 3))
    )
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

@automation_bp.route('/api/automation/sourcing/compare-async', methods=['POST'])
def compare_prices_async():
    """Trigger an async price comparison job for a recipe."""
    data = request.json
    from app.services import sourcing
    job_id = sourcing.trigger_comparison_job(data.get('recipe_details', {}))
    return jsonify({"job_id": job_id, "status": "accepted"}), 202

@automation_bp.route('/api/automation/sourcing/job/<job_id>', methods=['GET'])
def get_sourcing_job(job_id):
    """Poll for the result of an async price comparison job."""
    from app.services import sourcing
    result = sourcing.get_job_status(job_id)
    if result is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(result)

@automation_bp.route('/api/automation/brewfather/recipes', methods=['GET'])
def get_bf_recipes():
    from app.services import alerts
    return jsonify(alerts.fetch_brewfather_recipes())

@automation_bp.route('/api/automation/sourcing/compare', methods=['POST'])
def compare_prices():
    """Compare recipe ingredient prices between TMM and GEB.
    
    Body: {
        "recipe_details": {
            "hops": [{"name": "Citra", "amount": 100}, ...],
            "fermentables": [{"name": "Maris Otter", "amount": 5000}, ...]
        }
    }
    """
    data = request.json
    from app.services import sourcing
    try:
        result = sourcing.compare_recipe_prices(data.get('recipe_details', {}))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@automation_bp.route('/api/automation/inventory/sync', methods=['POST'])
def sync_inventory():
    from app.services import alerts
    
    # 1. Fetch from BF
    bf_inv = alerts.fetch_brewfather_inventory()
    if "error" in bf_inv:
        return jsonify(bf_inv)
    
    # 2. Map to local DB (Simplified for now)
    return jsonify({"status": "synced", "items_fetched": len(bf_inv.get('inventory', []))})

@automation_bp.route('/api/automation/inventory/hop_freshness', methods=['GET'])
@api_safe
def inventory_hop_freshness():
    """Check freshness of all hops in inventory."""
    from app.services import sourcing
    results = sourcing.check_inventory_hop_freshness()
    return jsonify({"hops": results})

@automation_bp.route('/api/automation/hop/freshness', methods=['POST'])
def calculate_hop_freshness():
    """Calculate the remaining alpha acids for a hop based on storage.
    
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
        data.get('purchase_date'),
        data.get('storage', 'freezer')
    )
    return jsonify(result)

@automation_bp.route('/api/automation/yeast/search', methods=['POST'])
def search_yeast():
    """Search for yeast metadata and compatibility.
    
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

@automation_bp.route('/api/automation/sourcing/labels', methods=['POST'])
def print_ingredient_labels():
    """Generate labels for new hop/malt purchases."""
    from app.services import sourcing
    data = request.json
    # Placeholder for Dymo/Brother integration
    return jsonify({"status": "Labels sent to print queue", "count": len(data.get('items', []))})

@automation_bp.route('/api/automation/scan', methods=['POST'])
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
    """Search community recipes (HomebrewTalk, Brewfather Library)."""
    from app.services import scout
    data = request.json
    res = scout.search_recipes(data.get('query'))
    return jsonify(res)

@automation_bp.route('/api/automation/calculator/pizza', methods=['GET'])
def pizza_calc():
    """Returns a pizza dough schedule based on brew day timing."""
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
    # Return as markdown
    return jsonify({"markdown": content})

# ============ WATER & CHEMISTRY ============

@automation_bp.route('/api/automation/water/optimize', methods=['POST'])
def optimize_water():
    """Optimize water additions for a target profile.
    
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
    
    result = water_chemistry.optimize_additions(source, target, float(data.get('volume_liters', 20)))
    return jsonify(result)

@automation_bp.route('/api/automation/mash/ph', methods=['POST'])
def predict_mash_ph():
    """Predict mash pH based on grain bill and water profile.
    
    Body: {
        "grains": [{"name": "Pilsner", "amount_kg": 5, "color_ebc": 3}, ...],
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
    
    result = mash_chemistry.predict_ph_and_acid_additions(grains, water_profile, target_ph, float(data.get('mash_volume_l', 20)))
    return jsonify(result)

# ============ ANOMALY DETECTION ============

@automation_bp.route('/api/automation/anomaly/check', methods=['POST'])
@api_safe
def run_anomaly_check():
    """
    Manual trigger for anomaly check.
    
    Body: {
        "batch_name": "Optional name override"
    },
    Returns: {
        "anomaly_score": 0.45,
        "results": {
            "temp_stable": true,
            "fermentation_active": true
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
def trigger_training():
    """Trigger a manual retraining of the ML gravity models."""
    from app.ml.prediction import train_models
    result = train_models()
    return jsonify(result)

@automation_bp.route('/api/ml/predict/fg', methods=['POST'])
@api_safe
def predict_fg():
    """Predict Final Gravity using real-time batch features.
    
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
        return jsonify({"error": "OG and Attenuation required"}), 400
        
    result = ml_predict_fg(
        float(og), 
        0.0, # Velocity placeholder
        0.0, # Variance placeholder
        float(data.get('avg_temp', 20.0))
    )
    return jsonify({"predicted_fg": result})

@automation_bp.route('/api/ml/predict/time', methods=['POST'])
@api_safe
def predict_time():
    """Predict Time to FG completion.
    
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
        return jsonify({"error": "OG, Current SG and Attenuation required"}), 400
        
    result = predict_time_to_fg(
        float(og),
        0.0, # Velocity placeholder
        0.0, # Variance placeholder
        20.0, # Temp placeholder
        float(data.get('days_elapsed', 0.0))
    )
    return jsonify({"days_to_fg": result})

@automation_bp.route('/api/ml/info', methods=['GET'])
@api_safe
def ml_model_info():
    """Get information about trained ML models."""
    from app.ml.prediction import get_model_info
    return jsonify(get_model_info())
