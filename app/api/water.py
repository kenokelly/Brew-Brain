from flask import Blueprint, request, jsonify
from services.water_chemistry import calculate_salt_additions, get_all_profiles, get_ro_water_source
from pydantic import BaseModel, Field
from typing import Dict, Optional

water_bp = Blueprint('water', __name__)

class WaterAdjustmentRequest(BaseModel):
    source_water: Dict[str, float] = Field(default_factory=get_ro_water_source)
    target_profile: str
    volume_liters: float = 23.0

@water_bp.route('/profiles', methods=['GET'])
def list_profiles():
    """List all available target water profiles."""
    return jsonify({"status": "success", "data": get_all_profiles()})

@water_bp.route('/calculate', methods=['POST'])
@water_bp.route('/<target_profile>', methods=['GET'])
def adjust_water(target_profile: Optional[str] = None):
    """Calculate salt additions to reach a target profile."""
    try:
        if request.method == 'GET' and target_profile:
            # Handle legacy GET request from frontend
            result = calculate_salt_additions(
                get_ro_water_source(),
                target_profile,
                23.0
            )
        else:
            data = WaterAdjustmentRequest(**request.json)
            result = calculate_salt_additions(
                data.source_water,
                data.target_profile,
                data.volume_liters
            )
        
        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 400
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
