import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

# ============================================
# HOP FRESHNESS & ALPHA ACID DEGRADATION
# ============================================

# Hop Storage Index (HSI) - % alpha acid loss per 6 months at 20°C
# Lower HSI = better storage characteristics
HOP_HSI = {
    # High HSI (poor storage) - 35-50%
    "cascade": 50, "centennial": 45, "chinook": 40, "columbus": 40,
    "crystal": 50, "fuggle": 45, "glacier": 50, "hallertau": 40,
    "mt hood": 45, "sterling": 45, "tettnang": 45, "willamette": 50,
    
    # Medium HSI (moderate storage) - 25-35%
    "amarillo": 30, "citra": 30, "el dorado": 28, "galaxy": 30,
    "mosaic": 25, "nelson sauvin": 30, "simcoe": 25, "warrior": 25,
    
    # Low HSI (good storage) - 15-25%
    "apollo": 20, "bravo": 20, "magnum": 20, "nugget": 20,
    "summit": 15, "target": 20, "zeus": 20,
    
    # Default for unknown varieties
    "default": 35
}

# Temperature factor - multiplier for storage temp
STORAGE_TEMP_FACTORS = {
    "freezer": 0.15,     # -18°C - minimal degradation
    "fridge": 0.35,      # 4°C - slow degradation  
    "cool": 0.70,        # 10-15°C - moderate degradation
    "ambient": 1.00,     # 20°C - baseline (HSI rating)
    "warm": 1.50         # 25°C+ - accelerated degradation
}


def calculate_hop_freshness(
    hop_name: str,
    original_alpha: float,
    purchase_date: str,
    storage_condition: str = "freezer",
    current_date: str = None
) -> dict:
    """
    Calculates degraded alpha acid using Hop Storage Index (HSI) formula.
    """
    try:
        # Parse dates
        if isinstance(purchase_date, str):
            purchase = datetime.strptime(purchase_date, "%Y-%m-%d").date()
        else:
            purchase = purchase_date
            
        today = date.today() if not current_date else datetime.strptime(current_date, "%Y-%m-%d").date()
        
        # Calculate age in months
        days_old = (today - purchase).days
        months_old = days_old / 30.44  # Average days per month
        
        # Get HSI for this hop variety
        hop_lower = hop_name.lower().strip()
        hsi = HOP_HSI.get(hop_lower, HOP_HSI["default"])
        
        # Get temperature factor
        temp_factor = STORAGE_TEMP_FACTORS.get(storage_condition.lower(), 1.0)
        
        # Calculate degradation
        # HSI is % loss per 6 months at 20°C
        degradation_pct = (hsi / 100) * temp_factor * (months_old / 6)
        degradation_pct = min(degradation_pct, 0.95)  # Cap at 95% loss
        
        remaining_pct = 1 - degradation_pct
        current_alpha = original_alpha * remaining_pct
        
        # Freshness rating
        if remaining_pct >= 0.90:
            freshness = "Excellent"
            status = "✅"
        elif remaining_pct >= 0.75:
            freshness = "Good"
            status = "✅"
        elif remaining_pct >= 0.60:
            freshness = "Fair"
            status = "⚠️"
        elif remaining_pct >= 0.40:
            freshness = "Poor"
            status = "⚠️"
        else:
            freshness = "Bad - Consider Replacing"
            status = "❌"
        
        return {
            "hop_name": hop_name,
            "original_alpha": original_alpha,
            "current_alpha": round(current_alpha, 2),
            "alpha_loss_pct": round(degradation_pct * 100, 1),
            "remaining_pct": round(remaining_pct * 100, 1),
            "age_months": round(months_old, 1),
            "storage": storage_condition,
            "hsi": hsi,
            "freshness_rating": freshness,
            "status": status,
            "recommendation": f"Use {round(original_alpha / current_alpha, 2)}x more to compensate" if current_alpha > 0 else "Replace hops"
        }
        
    except Exception as e:
        logger.error(f"Hop freshness calculation error: {e}")
        return {"error": str(e)}

# ============================================
# IBU CALCULATIONS (TINSETH FORMULA)
# ============================================

# G40 Utilization Coefficient: 
# G40 has high recirculation efficiency but moderate boil-off.
# Research suggests ~10% higher hop utilization than standard stovetop pots.
G40_UTILIZATION_BOOST = 1.10

def calculate_tinseth_ibu(
    alpha_acid: float,
    weight_grams: float,
    boil_time_mins: float,
    boil_gravity: float,
    batch_volume_liters: float,
    is_g40: bool = True
) -> float:
    """
    Calculates IBU using the Tinseth formula.
    
    Formula: IBU = (Decimal Alpha Acid Utilization) * (mg/l of Alpha Acids)
    Decimal Utilization = Bigness Factor * Time Factor
    """
    try:
        # 1. Calculate Bigness Factor
        # accounts for lower utilization in high-gravity worts
        bigness_factor = 1.65 * (0.000125 ** (boil_gravity - 1.0))
        
        # 2. Calculate Time Factor
        # accounts for alpha acid isomerization over time
        time_factor = (1 - (2.71828 ** (-0.04 * boil_time_mins))) / 4.15
        
        # 3. Calculate Utilization
        utilization = bigness_factor * time_factor
        
        # Apply G40 Hardware Coefficient if applicable
        if is_g40:
            utilization *= G40_UTILIZATION_BOOST
            
        # 4. Calculate mg/L of Alpha Acids
        # alpha_acid is e.g. 12.5 (%), weight in grams
        alpha_mg_l = (alpha_acid / 100.0) * (weight_grams * 1000) / batch_volume_liters
        
        return round(utilization * alpha_mg_l, 1)
        
    except Exception as e:
        logger.error(f"IBU calculation error: {e}")
        return 0.0

# ============================================
# GRAIN SCALING & EFFICIENCY
# ============================================

def calculate_grain_scaling(
    total_grain_kg: float,
    target_og: float,
    base_efficiency: float = 75.0,
    is_g40: bool = True
) -> dict:
    """
    Calculates the expected efficiency drop for high-gravity batches on G40 hardware.
    G40 mash efficiency drops as grain bill approaches the 12kg limit.
    """
    try:
        current_efficiency = base_efficiency
        
        # G40-specific scaling:
        # After 7kg of grain, efficiency drops by ~2% per kg
        if is_g40 and total_grain_kg > 7.0:
            drop_factor = (total_grain_kg - 7.0) * 2.0
            current_efficiency -= drop_factor
            
        # Hard floor for sanity
        current_efficiency = max(current_efficiency, 55.0)
        
        return {
            "total_grain_kg": total_grain_kg,
            "target_og": target_og,
            "estimated_efficiency": round(current_efficiency, 1),
            "efficiency_drop": round(base_efficiency - current_efficiency, 1),
            "is_high_gravity": total_grain_kg > 8.0
        }
    except Exception as e:
        logger.error(f"Grain scaling error: {e}")
        return {"error": str(e)}
