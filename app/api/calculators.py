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

class CarbonationRequest(BaseModel):
    temp_c: float
    volumes_co2: float

class RefractometerRequest(BaseModel):
    original_brix: float
    final_brix: float
    wort_correction_factor: float = 1.04

class PrimingRequest(BaseModel):
    volume_liters: float
    temp_c: float
    target_co2: float
    sugar_type: str = 'corn_sugar'

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

@calc_bp.route('/carbonation', methods=['POST'])
def calc_carbonation():
    try:
        data = CarbonationRequest(**request.json)
        # Simplified formula for keg carbonation PSI
        # P = -16.6999 - (0.0101059 * T) + (0.00116512 * T^2) + (0.173354 * T * V) + (4.24267 * V) - (0.0684226 * V^2)
        # where T is temp in F, V is volumes
        t_f = (data.temp_c * 9/5) + 32
        v = data.volumes_co2
        psi = -16.6999 - (0.0101059 * t_f) + (0.00116512 * t_f**2) + (0.173354 * t_f * v) + (4.24267 * v) - (0.0684226 * v**2)
        
        if psi < 0: psi = 0
        
        style = "General Ale"
        if v > 3.0: style = "Hefeweizen / Belgian"
        elif v < 2.0: style = "British Cask Ale"
        elif v >= 2.5: style = "Lager / Pilsner"
        
        return jsonify({
            "psi": round(psi, 1),
            "bar": round(psi * 0.0689476, 2),
            "kpa": round(psi * 6.89476, 1),
            "style_suggestion": style
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@calc_bp.route('/refractometer', methods=['POST'])
def calc_refractometer():
    try:
        data = RefractometerRequest(**request.json)
        # Standard refractometer correction formula
        ob = data.original_brix / data.wort_correction_factor
        fb = data.final_brix / data.wort_correction_factor
        
        sg_orig = 1.0000 + 0.0038661 * ob + 1.3488e-5 * (ob**2) + 4.3074e-7 * (ob**3)
        sg_final = 1.0000 - 0.00085683 * ob + 0.0034941 * fb
        
        abv = (sg_orig - sg_final) * 131.25
        attenuation = ((sg_orig - sg_final) / (sg_orig - 1)) * 100 if sg_orig > 1 else 0
        
        return jsonify({
            "original_gravity": round(sg_orig, 3),
            "corrected_final_gravity": round(sg_final, 3),
            "abv": round(abv, 1),
            "apparent_attenuation": round(attenuation, 1),
            "formula": "Standard Brix to SG (Novotny)"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@calc_bp.route('/priming', methods=['POST'])
def calc_priming():
    try:
        data = PrimingRequest(**request.json)
        # Residual CO2 based on temp
        t_f = (data.temp_c * 9/5) + 32
        residual = 3.0378 - (0.050062 * t_f) + (0.00026555 * t_f**2)
        if residual < 0: residual = 0
        
        needed_co2 = data.target_co2 - residual
        if needed_co2 < 0: needed_co2 = 0
        
        # Grams per liter for 1 volume of CO2 depends on sugar type
        # Corn sugar: ~4.15g/L per vol. Table sugar: ~3.8g/L per vol.
        factors = {
            'corn_sugar': 4.15,
            'table_sugar': 3.8,
            'honey': 5.2,
            'dme': 5.8,
            'brown_sugar': 4.0,
            'maple_syrup': 4.9
        }
        factor = factors.get(data.sugar_type, 4.15)
        
        total_grams = data.volume_liters * needed_co2 * factor
        
        return jsonify({
            "total_grams": round(total_grams, 1),
            "sugar_type": data.sugar_type.replace('_', ' ').title(),
            "per_500ml_bottle": round(total_grams / (data.volume_liters / 0.5), 1) if data.volume_liters > 0 else 0,
            "per_330ml_bottle": round(total_grams / (data.volume_liters / 0.33), 1) if data.volume_liters > 0 else 0,
            "residual_co2": round(residual, 2),
            "added_co2": round(needed_co2, 2),
            "conditioning_time": "Allow 2 weeks at room temperature"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

