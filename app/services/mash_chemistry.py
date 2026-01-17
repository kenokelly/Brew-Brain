"""
Brew Brain - Mash Chemistry Calculator

Predicts mash pH from grain bill and water chemistry.
Uses the residual alkalinity method with grain color contributions.
"""

import logging
from typing import List, Dict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Grain color to pH contribution (approximate)
# Based on Palmer's How to Brew and Bru'n Water data
# pH contribution per % of grist at distilled water baseline
GRAIN_PH_CONTRIBUTION = {
    # Base malts (0-5 Lovibond) - minimal acidification
    "base": {"lovibond_max": 5, "ph_per_percent": -0.0005},
    # Munich/Vienna (5-15 Lovibond)
    "light_specialty": {"lovibond_max": 15, "ph_per_percent": -0.001},
    # Crystal/Caramel (15-80 Lovibond)
    "crystal": {"lovibond_max": 80, "ph_per_percent": -0.002},
    # Roasted (80-500+ Lovibond) - strong acidification
    "roasted": {"lovibond_max": 600, "ph_per_percent": -0.004},
}

# Distilled water mash pH baseline (typical for pale malt)
DISTILLED_WATER_MASH_PH = 5.7

# Bicarbonate to pH effect (ppm per 0.1 pH shift)
BICARBONATE_PH_FACTOR = 50  # ~50 ppm HCO3 raises pH by 0.1


@dataclass
class MashPHResult:
    """Result of mash pH prediction"""
    predicted_ph: float
    grain_contribution: float
    water_contribution: float
    target_ph: float = 5.4
    adjustment_needed: float = 0.0
    lactic_acid_ml: float = 0.0
    phosphoric_acid_ml: float = 0.0
    calcium_carbite_g: float = 0.0
    notes: str = ""


def get_grain_category(lovibond: float) -> str:
    """Categorizes grain by color"""
    if lovibond <= 5:
        return "base"
    elif lovibond <= 15:
        return "light_specialty"
    elif lovibond <= 80:
        return "crystal"
    else:
        return "roasted"


def predict_mash_ph(
    grains: List[Dict],
    water_profile: Dict,
    target_ph: float = 5.4,
    mash_volume_l: float = 20.0
) -> Dict:
    """
    Predicts mash pH from grain bill and water chemistry.
    
    Args:
        grains: List of dicts with {name, weight_kg, lovibond} 
                lovibond can also be 'srm' or 'ebc'
        water_profile: Dict with {bicarbonate, calcium, magnesium} in ppm
        target_ph: Desired mash pH (default 5.4 for most beers)
        mash_volume_l: Total mash water volume
    
    Returns:
        Dict with predicted pH and acid/base adjustments needed
    
    Example:
        grains = [
            {"name": "Pale Malt", "weight_kg": 5.0, "lovibond": 2.5},
            {"name": "Crystal 60", "weight_kg": 0.5, "lovibond": 60}
        ]
        water = {"bicarbonate": 100, "calcium": 50}
    """
    try:
        # Calculate total grain weight and contributions
        total_weight = sum(g.get("weight_kg", 0) for g in grains)
        if total_weight == 0:
            return {"error": "No grain weight provided"}
        
        # 1. Calculate grain pH contribution
        grain_ph_shift = 0.0
        for grain in grains:
            weight = grain.get("weight_kg", 0)
            percent_of_grist = (weight / total_weight) * 100
            
            # Get lovibond (convert from EBC if needed)
            lovibond = grain.get("lovibond", 0)
            if grain.get("ebc"):
                lovibond = grain["ebc"] / 1.97  # EBC to Lovibond
            if grain.get("srm"):
                lovibond = grain["srm"]  # SRM ≈ Lovibond
            
            category = get_grain_category(lovibond)
            contribution = GRAIN_PH_CONTRIBUTION[category]
            
            # Darker grains contribute more acidity
            color_factor = 1 + (lovibond / 100) * 0.5  # Scale by darkness
            ph_contrib = percent_of_grist * contribution["ph_per_percent"] * color_factor
            grain_ph_shift += ph_contrib
        
        # 2. Calculate water alkalinity contribution
        bicarbonate = water_profile.get("bicarbonate", 0)
        calcium = water_profile.get("calcium", 0)
        magnesium = water_profile.get("magnesium", 0)
        
        # Residual Alkalinity formula (simplified)
        # RA = Alkalinity - (Ca/1.4) - (Mg/1.7)
        alkalinity = bicarbonate / 50 * 50  # Convert to CaCO3 equivalent
        residual_alkalinity = alkalinity - (calcium / 1.4) - (magnesium / 1.7)
        
        # RA to pH shift (approx 0.03 pH per 10 ppm RA)
        water_ph_shift = residual_alkalinity * 0.003
        
        # 3. Combined predicted pH
        predicted_ph = DISTILLED_WATER_MASH_PH + grain_ph_shift + water_ph_shift
        
        # Clamp to reasonable range
        predicted_ph = max(4.0, min(6.5, predicted_ph))
        
        # 4. Calculate adjustments needed
        adjustment_needed = target_ph - predicted_ph
        
        result = MashPHResult(
            predicted_ph=round(predicted_ph, 2),
            grain_contribution=round(grain_ph_shift, 3),
            water_contribution=round(water_ph_shift, 3),
            target_ph=target_ph,
            adjustment_needed=round(adjustment_needed, 2)
        )
        
        # If pH too high, calculate acid additions
        if adjustment_needed < -0.05:
            # 88% Lactic acid: ~1ml per gallon per 0.1 pH for light beers
            # Scale by mash volume (gallons = L / 3.785)
            mash_gallons = mash_volume_l / 3.785
            ph_drop_needed = abs(adjustment_needed)
            
            # Lactic 88%: ~0.8ml per gallon per 0.1 pH
            result.lactic_acid_ml = round(ph_drop_needed * 10 * 0.8 * mash_gallons, 1)
            
            # Phosphoric 10%: ~2.5ml per gallon per 0.1 pH  
            result.phosphoric_acid_ml = round(ph_drop_needed * 10 * 2.5 * mash_gallons, 1)
            
            result.notes = f"pH too high. Add {result.lactic_acid_ml}ml lactic acid (88%) OR {result.phosphoric_acid_ml}ml phosphoric acid (10%)"
        
        # If pH too low, suggest calcium carbonate
        elif adjustment_needed > 0.05:
            # CaCO3 (chalk): ~0.5g per gallon per 0.1 pH rise
            mash_gallons = mash_volume_l / 3.785
            ph_raise_needed = adjustment_needed
            result.calcium_carbite_g = round(ph_raise_needed * 10 * 0.5 * mash_gallons, 1)
            result.notes = f"pH too low. Add {result.calcium_carbite_g}g calcium carbonate (chalk) - dissolve in acidified water first"
        else:
            result.notes = "pH within target range. No adjustment needed."
        
        return asdict(result)
        
    except Exception as e:
        logger.error(f"Mash pH prediction error: {e}")
        return {"error": str(e)}


def get_style_target_ph(style: str) -> float:
    """Returns target mash pH for beer style"""
    style_lower = style.lower()
    
    # Dark beers can tolerate higher pH
    if any(word in style_lower for word in ["stout", "porter", "schwarzbier", "dark"]):
        return 5.4
    
    # Sours need lower pH
    if any(word in style_lower for word in ["sour", "berliner", "gose", "lambic"]):
        return 4.5
    
    # Lagers slightly lower
    if any(word in style_lower for word in ["lager", "pilsner", "helles", "bock"]):
        return 5.3
    
    # Default for ales
    return 5.4
