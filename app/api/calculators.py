from flask import Blueprint, request, jsonify
from services.hop_math import calculate_tinseth_ibu, calculate_grain_scaling
from pydantic import BaseModel, Field
from typing import Optional

calc_bp = Blueprint('calculator', __name__)

class IBURequest(BaseModel):
    alpha_acid: float = Field(..., gt=0)
    weight_grams: float = Field(..., gt=0)
    boil_time_mins: float = Field(..., gt=0)
    boil_gravity: float = Field(..., gt=1.0)
    batch_volume_liters: float = Field(..., gt=0)
    is_g40: bool = True

class GrainScalingRequest(BaseModel):
    total_grain_kg: float = Field(..., gt=0)
    target_og: float = Field(..., gt=1.0)
    base_efficiency: float = 75.0
    is_g40: bool = True

@calc_bp.route('/ibu', methods=['POST'])
def get_ibu():
    """Calculate IBU for a hop addition."""
    try:
        data = IBURequest(**request.json)
        ibu = calculate_tinseth_ibu(
            data.alpha_acid,
            data.weight_grams,
            data.boil_time_mins,
            data.boil_gravity,
            data.batch_volume_liters,
            data.is_g40
        )
        return jsonify({"status": "success", "ibu": ibu})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@calc_bp.route('/grain-scaling', methods=['POST'])
def get_grain_scaling():
    """Calculate expected efficiency drop."""
    try:
        data = GrainScalingRequest(**request.json)
        result = calculate_grain_scaling(
            data.total_grain_kg,
            data.target_og,
            data.base_efficiency,
            data.is_g40
        )
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
