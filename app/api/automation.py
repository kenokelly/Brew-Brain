from flask import Blueprint, jsonify, request
from core.decorators import api_safe
from core.auth import require_api_token
from services import scout, calculator, water_chemistry, alerts
import io
import json
import os
import logging

automation_bp = Blueprint('automation', __name__)
logger = logging.getLogger(__name__)

# ============ ML Prediction Endpoints ============

# ... rest of automation functions ...
@automation_bp.route('/api/automation/scout', methods=['POST'])
def scout_ingredients():
    data = request.json
    query = data.get('query')
    if not query: return jsonify({"error": "Query required"}), 400
    return jsonify(scout.search_ingredients(query))

@automation_bp.route('/api/automation/calculator/strike', methods=['POST'])
def calc_strike():
    data = request.json
    res = calculator.calculate_strike_water(float(data.get('grain_temp', 20)), float(data.get('target_mash_temp', 65)), float(data.get('grain_weight_kg', 5)), float(data.get('water_ratio', 3)))
    return jsonify(res)
