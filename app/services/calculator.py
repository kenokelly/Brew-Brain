import logging

logger = logging.getLogger(__name__)

def calculate_tinseth_ibu(amount_g, alpha_acid, boil_time_min, boil_volume_l, original_gravity):
    """
    Calculates IBU using the Tinseth formula.
    """
    if boil_volume_l <= 0: return 0
    
    # Utilization factor
    bigness_factor = 1.65 * (0.000125 ** (original_gravity - 1))
    boil_time_factor = (1 - (2.71828 ** (-0.04 * boil_time_min))) / 4.15
    utilization = bigness_factor * boil_time_factor

    # IBU Calculation
    alpha_mass_mg = amount_g * (alpha_acid / 100) * 1000
    concentration_mg_l = alpha_mass_mg / boil_volume_l
    
    ibu = concentration_mg_l * utilization
    return round(ibu, 2)

def calculate_batch_cost(items):
    """
    Calculates the total cost.
    items: list of dicts {'cost': float}
    """
    total = sum(i.get('cost', 0.0) for i in items)
    return round(total, 2)

def calculate_hop_adjustment(target_ibu, current_gravity, volume_l, boil_time_min, alpha_acid):
    """
    Calculates the required hop weight (g) to hit a target IBU given current conditions.
    Reverse Tinseth.
    """
    try:
        target_ibu = float(target_ibu)
        current_gravity = float(current_gravity)
        volume_l = float(volume_l)
        boil_time_min = float(boil_time_min)
        alpha_acid = float(alpha_acid)

        if volume_l <= 0 or alpha_acid <= 0: return {}

        # 1. Calculate Utilization Factor for CURRENT conditions
        bigness_factor = 1.65 * (0.000125 ** (current_gravity - 1))
        boil_time_factor = (1 - (2.71828 ** (-0.04 * boil_time_min))) / 4.15
        utilization = bigness_factor * boil_time_factor

        # 2. Reverse IBU Calc: IBU = (Concentration_mg_l * Utilization)
        # Concentration_mg_l = IBU / Utilization
        if utilization == 0: return {"error": "Zero utilization"}
        
        required_concentration_mg_l = target_ibu / utilization
        
        # 3. Required Alpha Mass
        # Concentration = Mass_mg / Vol_l  => Mass_mg = Concentration * Vol_l
        required_alpha_mass_mg = required_concentration_mg_l * volume_l
        
        # 4. Required Hop Weight (g)
        # Mass_mg = Weight_g * (Alpha/100) * 1000
        # Weight_g = Mass_mg / ((Alpha/100) * 1000)
        required_grams = required_alpha_mass_mg / ((alpha_acid / 100) * 1000)
        
        return {
            "required_grams": round(required_grams, 1),
            "utilization": round(utilization, 3)
        }
    except Exception as e:
        return {"error": str(e)}

def get_pizza_schedule():
    """
    Returns a pizza dough schedule relative to a hypothetical brew day (today/tomorrow).
    Assuming Biga 100% (Requires 24-48h).
    """
    return [
        {"time": "T-24h", "step": "Mix Biga (Flour + Water + Minute amount of yeast)"},
        {"time": "T-16h", "step": "Biga Fermentation (18C)"},
        {"time": "T-4h", "step": "Refresh Biga (Add remaining water/salt/malt)"},
        {"time": "T-3h", "step": "Bulk Ferment"},
        {"time": "T-2h", "step": "Ball Dough"},
        {"time": "Brew Day", "step": "Bake in Gozney Dome (450C) while Boil is rolling!"}
    ]

def validate_equipment(volume, grain_weight):
    """
    Checks parameters against G40 limits.
    """
    import json
    import os
    
    eq_file = 'data/equipment.json'
    if not os.path.exists(eq_file):
        return {"valid": True, "warnings": []} # No profile
        
    try:
        with open(eq_file, 'r') as f:
            specs = json.load(f)
            
        warnings = []
        valid = True
        
        # Check Grain
        max_grain = specs.get('max_grain_weight_kg', 13)
        if grain_weight > max_grain:
            warnings.append(f"CRITICAL: Grain bill ({grain_weight}kg) exceeds G40 limit ({max_grain}kg). Mash Overflow Risk!")
            valid = False
            
        # Check Volume
        max_vol = specs.get('pre_boil_vol_max_l', 46)
        if volume > max_vol:
            warnings.append(f"CRITICAL: Volume ({volume}L) exceeds G40 limit ({max_vol}L).")
            valid = False
            
        min_vol = specs.get('min_vol_l', 10)
        if volume < min_vol:
            warnings.append(f"WARNING: Volume ({volume}L) is below safe minimum ({min_vol}L).")
            
        # Check Fermentation (Unitanks)
        ferm = specs.get('fermentation', {})
        if ferm:
            safe_limit = ferm.get('safe_vol_l', 24)
            count = ferm.get('vessels', 1)
            total_cap = safe_limit * count
            
            if volume > total_cap:
                 warnings.append(f"CRITICAL: Volume ({volume}L) exceeds total capacity of {count}x Unitanks ({total_cap}L).")
                 valid = False
            elif volume > safe_limit:
                 warnings.append(f"WARNING: Volume ({volume}L) exceeds single Unitank ({safe_limit}L). Requires Split Batch.")
            
        return {"valid": valid, "warnings": warnings}
        
    except Exception as e:
        return {"valid": False, "warnings": [f"Error reading equipment profile: {str(e)}"]}

def scale_recipe_to_equipment(recipe):
    """
    Scales a recipe dict to fit G40 constraints (Max Grain 13kg).
    Scaling is done by reducing Batch Size to fit the grain limit.
    """
    import json
    import os
    
    eq_file = 'data/equipment.json'
    if not os.path.exists(eq_file):
        return {"error": "No equipment profile"}
        
    try:
        with open(eq_file, 'r') as f:
            specs = json.load(f)
            
        max_grain = specs.get('max_grain_weight_kg', 13.0)
        current_grain = recipe.get('total_grain_kg', 0)
        
        if current_grain <= max_grain:
            return recipe # No scaling needed
            
        # Calc Ratio
        ratio = max_grain / current_grain
        
        # Apply Scaling
        scaled = recipe.copy()
        scaled['original_grain'] = current_grain
        scaled['original_batch_size'] = scaled.get('batch_size_l', 23)
        
        scaled['total_grain_kg'] = round(current_grain * ratio, 2)
        scaled['batch_size_l'] = round(scaled.get('batch_size_l', 23) * ratio, 2)
        
        # Hops usually scale by volume/boil gravity, simple linear is fine for this estimation
        # We don't have individual hop items here, just the summary string, so we'll append a note
        scaled['notes'] = f"Scaled to Fit G40 (Ratio {round(ratio, 2)}). Reduce all ingredients by factor {round(ratio, 3)}"
        
        # Valid now
        scaled['hardware_valid'] = True
        scaled['hardware_warnings'] = [] # Clear warnings
        scaled['is_scaled'] = True
        
        return scaled
        
    except Exception as e:
        return {"error": str(e)}
