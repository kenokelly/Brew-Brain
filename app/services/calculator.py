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

def calculate_batch_cost(items, batch_size_l=23):
    """
    Calculates the total cost and cost per pint.
    items: list of dicts {'cost': float}
    batch_size_l: batch volume in liters (default: G40 standard 23L)
    Returns: dict with total_cost and cost_per_pint
    """
    total = sum(i.get('cost', 0.0) for i in items)
    
    # UK pint = 568ml, so pints = liters * 1000 / 568
    pints = (batch_size_l * 1000) / 568
    cost_per_pint = total / pints if pints > 0 else 0
    
    return {
        "total_cost": round(total, 2),
        "cost_per_pint": round(cost_per_pint, 2),
        "pints": round(pints, 1)
    }

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
    from app.core.config import DATA_DIR
    
    eq_file = os.path.join(DATA_DIR, 'equipment.json')
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
    from app.core.config import DATA_DIR
    
    eq_file = os.path.join(DATA_DIR, 'equipment.json')
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


# ============================================
# CARBONATION CALCULATOR
# ============================================

def calculate_carbonation_psi(temp_c: float, target_volumes_co2: float) -> dict:
    """
    Calculates required PSI for forced carbonation at given temperature.
    Uses a polynomial approximation of Henry's Law for CO2 in beer.
    
    Args:
        temp_c: Beer temperature in Celsius
        target_volumes_co2: Target CO2 volumes (e.g., 2.4 for English Ale, 2.8 for Lager)
    
    Returns:
        dict with psi, bar, kpa values and style recommendations
    
    Common CO2 Volumes:
        - British Cask Ale: 1.5-2.0
        - American Ale: 2.2-2.7
        - Belgian Ales: 2.5-4.0
        - Lagers: 2.5-2.8
        - Hefeweizen: 3.0-4.0
    """
    try:
        temp_c = float(temp_c)
        target_volumes_co2 = float(target_volumes_co2)
        
        # Approximation formula (from Brewer's Friend / Zahm & Nagel)
        # PSI = -16.6999 - 0.0101059*T + 0.00116512*T² + (0.173354*T + 4.24267)*V
        # where T is in Fahrenheit and V is volumes CO2
        
        temp_f = (temp_c * 9/5) + 32
        
        psi = (
            -16.6999 
            - (0.0101059 * temp_f) 
            + (0.00116512 * temp_f * temp_f) 
            + ((0.173354 * temp_f + 4.24267) * target_volumes_co2)
        )
        
        # Convert to other units
        bar = psi * 0.0689476
        kpa = psi * 6.89476
        
        # Style suggestions based on volumes
        if target_volumes_co2 < 2.0:
            style_match = "British Cask / Real Ale"
        elif target_volumes_co2 < 2.5:
            style_match = "American Ale / IPA"
        elif target_volumes_co2 < 3.0:
            style_match = "Lager / Pilsner"
        elif target_volumes_co2 < 3.5:
            style_match = "Belgian Ale / Hefeweizen"
        else:
            style_match = "High Carbonation (Saison, Lambic)"
        
        return {
            "psi": round(max(0, psi), 1),
            "bar": round(max(0, bar), 2),
            "kpa": round(max(0, kpa), 1),
            "temp_c": temp_c,
            "temp_f": round(temp_f, 1),
            "volumes_co2": target_volumes_co2,
            "style_suggestion": style_match,
            "equilibrium_days": "2-3 days at this pressure for full carbonation"
        }
        
    except Exception as e:
        logger.error(f"Carbonation calc error: {e}")
        return {"error": str(e)}


# ============================================
# REFRACTOMETER CORRECTION (POST-FERMENTATION)
# ============================================

def correct_refractometer_reading(
    final_brix: float, 
    original_brix: float,
    wort_correction_factor: float = 1.04
) -> dict:
    """
    Corrects refractometer readings for alcohol presence post-fermentation.
    Uses the Sean Terrill cubic formula which is more accurate than linear.
    
    Args:
        final_brix: Refractometer reading of fermented beer (uncorrected)
        original_brix: Refractometer reading of original wort (OG in Brix)
        wort_correction_factor: Calibration factor (default 1.04 for most refractometers)
    
    Returns:
        dict with corrected SG, ABV calculation, and apparent/real attenuation
    """
    try:
        fb = float(final_brix)
        ob = float(original_brix)
        wcf = float(wort_correction_factor)
        
        # Apply wort correction factor
        ob_corrected = ob / wcf
        fb_corrected = fb / wcf
        
        # Convert OG from Brix to SG
        og_sg = 1 + (ob_corrected / (258.6 - ((ob_corrected / 258.2) * 227.1)))
        
        # Sean Terrill's Cubic Correction Formula
        # FG = 1.001843 - 0.002318474*OB - 0.000007775*OB² - 0.000000034*OB³ 
        #      + 0.00574*FB + 0.00003344*FB² + 0.000000086*FB³
        fg_sg = (
            1.001843 
            - (0.002318474 * ob_corrected)
            - (0.000007775 * ob_corrected ** 2)
            - (0.000000034 * ob_corrected ** 3)
            + (0.00574 * fb_corrected)
            + (0.00003344 * fb_corrected ** 2)
            + (0.000000086 * fb_corrected ** 3)
        )
        
        # Clamp FG to reasonable range
        fg_sg = max(0.990, min(fg_sg, og_sg))
        
        # Calculate ABV
        abv = (og_sg - fg_sg) * 131.25
        
        # Apparent attenuation
        apparent_attenuation = ((og_sg - fg_sg) / (og_sg - 1)) * 100 if og_sg > 1 else 0
        
        return {
            "original_brix": ob,
            "final_brix": fb,
            "original_gravity": round(og_sg, 4),
            "corrected_final_gravity": round(fg_sg, 4),
            "abv": round(abv, 2),
            "apparent_attenuation": round(apparent_attenuation, 1),
            "formula": "Sean Terrill Cubic",
            "note": "Use hydrometer for critical measurements"
        }
        
    except Exception as e:
        logger.error(f"Refractometer correction error: {e}")
        return {"error": str(e)}


# ============================================
# PRIMING SUGAR CALCULATOR (BOTTLE CONDITIONING)
# ============================================

# Sugar contribution factors (grams per liter per volume CO2)
PRIMING_SUGARS = {
    "table_sugar": {"factor": 4.0, "name": "Table Sugar (Sucrose)"},
    "corn_sugar": {"factor": 4.5, "name": "Corn Sugar (Dextrose)"},
    "honey": {"factor": 5.3, "name": "Honey"},
    "dme": {"factor": 5.6, "name": "Dry Malt Extract"},
    "brown_sugar": {"factor": 4.2, "name": "Brown Sugar"},
    "maple_syrup": {"factor": 5.0, "name": "Maple Syrup"},
}

def calculate_priming_sugar(
    volume_liters: float,
    temp_c: float,
    target_volumes_co2: float,
    sugar_type: str = "corn_sugar"
) -> dict:
    """
    Calculates priming sugar needed for bottle conditioning.
    
    Args:
        volume_liters: Batch volume in liters
        temp_c: Current beer temperature (affects residual CO2)
        target_volumes_co2: Target carbonation level
        sugar_type: Type of priming sugar (corn_sugar, table_sugar, honey, dme, etc.)
    
    Returns:
        dict with total grams needed and per-bottle amounts
    """
    try:
        vol = float(volume_liters)
        temp = float(temp_c)
        target = float(target_volumes_co2)
        
        # Get sugar factor
        sugar_info = PRIMING_SUGARS.get(sugar_type, PRIMING_SUGARS["corn_sugar"])
        factor = sugar_info["factor"]
        
        # Calculate residual CO2 based on temperature
        # Approximation: higher temp = less residual CO2
        # Residual CO2 ≈ 1.57 - 0.0344*T + 0.000372*T²  (where T in Celsius)
        residual_co2 = 1.57 - (0.0344 * temp) + (0.000372 * temp * temp)
        residual_co2 = max(0, residual_co2)
        
        # CO2 volumes needed from priming
        needed_volumes = max(0, target - residual_co2)
        
        # Grams per liter = needed_volumes * factor
        grams_per_liter = needed_volumes * factor
        
        # Total grams
        total_grams = grams_per_liter * vol
        
        # Per 500ml bottle
        per_500ml = grams_per_liter * 0.5
        # Per 330ml bottle  
        per_330ml = grams_per_liter * 0.33
        
        return {
            "sugar_type": sugar_info["name"],
            "total_grams": round(total_grams, 1),
            "grams_per_liter": round(grams_per_liter, 2),
            "per_500ml_bottle": round(per_500ml, 2),
            "per_330ml_bottle": round(per_330ml, 2),
            "residual_co2": round(residual_co2, 2),
            "added_co2": round(needed_volumes, 2),
            "target_co2": target,
            "beer_temp_c": temp,
            "volume_liters": vol,
            "conditioning_time": "2-3 weeks at 18-22°C",
            "available_sugars": list(PRIMING_SUGARS.keys())
        }
        
    except Exception as e:
        logger.error(f"Priming calc error: {e}")
        return {"error": str(e)}

