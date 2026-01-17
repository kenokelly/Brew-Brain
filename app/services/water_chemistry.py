"""
Brew Brain - Water Chemistry Calculator

Calculates salt additions needed to transform source water to target brewing profiles.
Uses standard brewing chemistry for CaSO4 (Gypsum), CaCl2, MgSO4 (Epsom), NaHCO3 (Baking Soda).
"""

import logging
from dataclasses import dataclass, asdict
from typing import Dict, Optional
from services.water import get_profile, PROFILES

logger = logging.getLogger(__name__)

# Salt contribution rates (ppm per gram per liter)
# Source: Bru'n Water / Palmer's How to Brew
SALT_CONTRIBUTIONS = {
    "gypsum": {      # CaSO4·2H2O
        "calcium": 61.5,
        "sulfate": 147.4
    },
    "calcium_chloride": {  # CaCl2·2H2O
        "calcium": 72.0,
        "chloride": 127.4
    },
    "epsom": {       # MgSO4·7H2O
        "magnesium": 26.1,
        "sulfate": 103.0
    },
    "baking_soda": {  # NaHCO3
        "sodium": 72.3,
        "bicarbonate": 191.0
    },
    "chalk": {        # Cite CaCO3 (rarely dissolves fully)
        "calcium": 105.8,
        "bicarbonate": 158.4
    },
    "table_salt": {   # NaCl (non-iodized)
        "sodium": 103.9,
        "chloride": 160.3
    }
}


@dataclass
class WaterAdditions:
    """Result of salt addition calculations"""
    gypsum_g: float = 0.0
    calcium_chloride_g: float = 0.0
    epsom_g: float = 0.0
    baking_soda_g: float = 0.0
    table_salt_g: float = 0.0
    
    # Resulting chemistry (estimated)
    final_calcium: float = 0.0
    final_magnesium: float = 0.0
    final_sodium: float = 0.0
    final_chloride: float = 0.0
    final_sulfate: float = 0.0
    final_bicarbonate: float = 0.0
    
    # Ratios
    sulfate_chloride_ratio: float = 0.0
    ratio_description: str = ""


def calculate_salt_additions(
    source_water: Dict[str, float],
    target_profile_name: str,
    volume_liters: float = 23.0
) -> Dict:
    """
    Calculates required salt additions to hit target water profile.
    
    Args:
        source_water: Dict with keys: calcium, magnesium, sodium, chloride, sulfate, bicarbonate
                     Use all zeros for RO/distilled water
        target_profile_name: Name of target profile (e.g., 'neipa', 'west_coast')
        volume_liters: Batch volume in liters (default: G40 standard 23L)
    
    Returns:
        Dict with salt additions (grams) and final estimated water chemistry
    """
    target = get_profile(target_profile_name)
    if not target:
        return {"error": f"Unknown profile: {target_profile_name}"}
    
    # Ensure source water has all keys
    source = {
        "calcium": source_water.get("calcium", 0),
        "magnesium": source_water.get("magnesium", 0),
        "sodium": source_water.get("sodium", 0),
        "chloride": source_water.get("chloride", 0),
        "sulfate": source_water.get("sulfate", 0),
        "bicarbonate": source_water.get("bicarbonate", 0)
    }
    
    # Calculate deltas needed
    delta = {
        "calcium": max(0, target["calcium"] - source["calcium"]),
        "magnesium": max(0, target["magnesium"] - source["magnesium"]),
        "sodium": max(0, target["sodium"] - source["sodium"]),
        "chloride": max(0, target["chloride"] - source["chloride"]),
        "sulfate": max(0, target["sulfate"] - source["sulfate"]),
        "bicarbonate": max(0, target["bicarbonate"] - source["bicarbonate"])
    }
    
    # ---- Simple Linear Approach ----
    # Priority: Calcium first (via gypsum for sulfate, CaCl2 for chloride)
    # Then Magnesium (epsom), Sodium (baking soda for bicarb, table salt for chloride boost)
    
    additions = WaterAdditions()
    
    # 1. Sulfate: Use Gypsum (also adds Calcium)
    if delta["sulfate"] > 0:
        # grams = (ppm_needed * volume_L) / contribution_per_g_per_L
        gypsum_for_sulfate = (delta["sulfate"] * volume_liters) / (SALT_CONTRIBUTIONS["gypsum"]["sulfate"] * volume_liters)
        gypsum_for_sulfate = delta["sulfate"] / SALT_CONTRIBUTIONS["gypsum"]["sulfate"]
        additions.gypsum_g = round(gypsum_for_sulfate, 1)
        
        # Calcium contributed by gypsum
        ca_from_gypsum = additions.gypsum_g * SALT_CONTRIBUTIONS["gypsum"]["calcium"]
        delta["calcium"] = max(0, delta["calcium"] - ca_from_gypsum)
    
    # 2. Chloride: Use Calcium Chloride (also adds Calcium)
    if delta["chloride"] > 0:
        cacl2_for_chloride = delta["chloride"] / SALT_CONTRIBUTIONS["calcium_chloride"]["chloride"]
        additions.calcium_chloride_g = round(cacl2_for_chloride, 1)
        
        # Calcium contributed
        ca_from_cacl2 = additions.calcium_chloride_g * SALT_CONTRIBUTIONS["calcium_chloride"]["calcium"]
        delta["calcium"] = max(0, delta["calcium"] - ca_from_cacl2)
    
    # 3. Magnesium: Use Epsom Salt
    if delta["magnesium"] > 5:  # Only add if significant
        epsom_for_mg = delta["magnesium"] / SALT_CONTRIBUTIONS["epsom"]["magnesium"]
        additions.epsom_g = round(epsom_for_mg, 1)
    
    # 4. Bicarbonate (for dark beers): Use Baking Soda
    if delta["bicarbonate"] > 20:  # Only add if significant
        soda_for_bicarb = delta["bicarbonate"] / SALT_CONTRIBUTIONS["baking_soda"]["bicarbonate"]
        additions.baking_soda_g = round(soda_for_bicarb, 1)
    
    # Calculate final estimated chemistry
    additions.final_calcium = round(
        source["calcium"] + 
        additions.gypsum_g * SALT_CONTRIBUTIONS["gypsum"]["calcium"] +
        additions.calcium_chloride_g * SALT_CONTRIBUTIONS["calcium_chloride"]["calcium"],
        1
    )
    additions.final_magnesium = round(
        source["magnesium"] + 
        additions.epsom_g * SALT_CONTRIBUTIONS["epsom"]["magnesium"],
        1
    )
    additions.final_sodium = round(
        source["sodium"] + 
        additions.baking_soda_g * SALT_CONTRIBUTIONS["baking_soda"]["sodium"] +
        additions.table_salt_g * SALT_CONTRIBUTIONS["table_salt"]["sodium"],
        1
    )
    additions.final_chloride = round(
        source["chloride"] + 
        additions.calcium_chloride_g * SALT_CONTRIBUTIONS["calcium_chloride"]["chloride"] +
        additions.table_salt_g * SALT_CONTRIBUTIONS["table_salt"]["chloride"],
        1
    )
    additions.final_sulfate = round(
        source["sulfate"] + 
        additions.gypsum_g * SALT_CONTRIBUTIONS["gypsum"]["sulfate"] +
        additions.epsom_g * SALT_CONTRIBUTIONS["epsom"]["sulfate"],
        1
    )
    additions.final_bicarbonate = round(
        source["bicarbonate"] + 
        additions.baking_soda_g * SALT_CONTRIBUTIONS["baking_soda"]["bicarbonate"],
        1
    )
    
    # Calculate SO4:Cl ratio
    if additions.final_chloride > 0:
        additions.sulfate_chloride_ratio = round(
            additions.final_sulfate / additions.final_chloride, 2
        )
    else:
        additions.sulfate_chloride_ratio = float('inf')
    
    # Describe the ratio effect
    ratio = additions.sulfate_chloride_ratio
    if ratio > 2.0:
        additions.ratio_description = "Very Bitter / Crisp (West Coast)"
    elif ratio > 1.5:
        additions.ratio_description = "Bitter-Forward"
    elif ratio > 0.8:
        additions.ratio_description = "Balanced"
    elif ratio > 0.5:
        additions.ratio_description = "Malt-Forward / Soft"
    else:
        additions.ratio_description = "Very Malty / Full"
    
    result = asdict(additions)
    result["target_profile"] = target_profile_name
    result["volume_liters"] = volume_liters
    result["source_water"] = source
    result["target_water"] = target
    
    return result


def get_ro_water_source() -> Dict[str, float]:
    """Returns a zero-ion source water profile (RO/distilled)"""
    return {
        "calcium": 0,
        "magnesium": 0,
        "sodium": 0,
        "chloride": 0,
        "sulfate": 0,
        "bicarbonate": 0
    }


def get_typical_tap_water() -> Dict[str, float]:
    """Returns a typical UK tap water profile (London-ish)"""
    return {
        "calcium": 100,
        "magnesium": 5,
        "sodium": 30,
        "chloride": 35,
        "sulfate": 60,
        "bicarbonate": 180
    }
