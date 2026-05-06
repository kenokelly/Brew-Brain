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
