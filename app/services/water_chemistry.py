"""
Brew Brain - Water Chemistry Calculator

Calculates salt additions needed to transform source water to target brewing profiles.
Uses standard brewing chemistry for CaSO4 (Gypsum), CaCl2, MgSO4 (Epsom), NaHCO3 (Baking Soda).
"""

import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class WaterProfile:
    name: str
    calcium: float
    magnesium: float
    sodium: float
    chloride: float
    sulfate: float
    bicarbonate: float
    ph: float = 7.0
    description: str = ""

PROFILES = {
    "ro": WaterProfile("RO Water", 0, 0, 0, 0, 0, 0, 5.5, "Zero-ion baseline"),
    "west_coast": WaterProfile("West Coast IPA", 110, 18, 25, 50, 250, 20, 5.2, "High sulfate for crisp bitterness"),
    "neipa_juicy": WaterProfile("NEIPA Juicy", 140, 18, 20, 150, 80, 0, 5.3, "High chloride for soft mouthfeel"),
    "london_porter": WaterProfile("London Porter", 100, 15, 35, 100, 80, 150, 5.4, "High bicarbonate for dark malts"),
    "pilsen_soft": WaterProfile("Pilsen Soft", 10, 5, 5, 10, 10, 5, 5.1, "Extremely soft water for lagers"),
    "balanced": WaterProfile("Balanced Profile", 80, 10, 15, 75, 75, 40, 5.3, "Versatile for many styles"),
    "black_full": WaterProfile("Black Full", 90, 12, 30, 120, 60, 180, 5.6, "Rich profile for stouts"),
    "neipa": WaterProfile("NEIPA", 150, 15, 10, 200, 100, 50, 5.2, "High chloride for soft mouthfeel")
}

# --- ION CONTRIBUTION RATES (Bru'n Water Exact Constants, mg/g) ---
# Grams = (needed_mg/L * volume_L) / contribution_rate_mg_per_g
ION_CONTRIBUTIONS = {
    "gypsum": {"ca": 232.8, "so4": 557.9},
    "calcium_chloride": {"ca": 272.6, "cl": 482.3}, # Dihydrate
    "epsom": {"mg": 98.6, "so4": 389.5},
    "baking_soda": {"na": 273.7, "hco3": 726.3},
    "table_salt": {"na": 393.4, "cl": 606.6}
}

@dataclass
class WaterAdditions:
    gypsum_g: float = 0.0
    calcium_chloride_g: float = 0.0
    epsom_g: float = 0.0
    baking_soda_g: float = 0.0
    table_salt_g: float = 0.0
    final_calcium: float = 0.0
    final_magnesium: float = 0.0
    final_sodium: float = 0.0
    final_chloride: float = 0.0
    final_sulfate: float = 0.0
    final_bicarbonate: float = 0.0
    sulfate_chloride_ratio: float = 0.0
    ratio_description: str = ""

def get_profile(name: str) -> Optional[dict]:
    p = PROFILES.get(name.lower())
    if p: return asdict(p)
    return None

def get_all_profiles() -> dict:
    return {k: asdict(v) for k, v in PROFILES.items()}

def calculate_salt_additions(source_water: Dict[str, float], target_profile_name: str, volume_liters: float = 23.0) -> Dict:
    target = get_profile(target_profile_name)
    if not target: return {"error": f"Unknown profile: {target_profile_name}"}
    
    add = WaterAdditions()
    
    # 1. Magnesium via Epsom
    needed_mg = max(0, target["magnesium"] - source_water.get("magnesium", 0))
    if needed_mg > 0:
        add.epsom_g = round((needed_mg * volume_liters) / ION_CONTRIBUTIONS["epsom"]["mg"], 1)

    # 2. Sulfate: Remainder after Epsom
    so4_from_epsom = (add.epsom_g * ION_CONTRIBUTIONS["epsom"]["so4"]) / volume_liters
    needed_so4 = max(0, target["sulfate"] - (source_water.get("sulfate", 0) + so4_from_epsom))
    if needed_so4 > 0:
        add.gypsum_g = round((needed_so4 * volume_liters) / ION_CONTRIBUTIONS["gypsum"]["so4"], 1)
    
    # 3. Chloride via Calcium Chloride
    needed_cl = max(0, target["chloride"] - source_water.get("chloride", 0))
    if needed_cl > 0:
        add.calcium_chloride_g = round((needed_cl * volume_liters) / ION_CONTRIBUTIONS["calcium_chloride"]["cl"], 1)
    
    # 4. Bicarb via Baking Soda
    needed_hco3 = max(0, target["bicarbonate"] - source_water.get("bicarbonate", 0))
    if needed_hco3 > 0:
        add.baking_soda_g = round((needed_hco3 * volume_liters) / ION_CONTRIBUTIONS["baking_soda"]["hco3"], 1)

    # Final Totals
    def gain(salt, ion, grams): return (grams * ION_CONTRIBUTIONS[salt][ion]) / volume_liters

    add.final_calcium = round(source_water.get("calcium", 0) + gain("gypsum", "ca", add.gypsum_g) + gain("calcium_chloride", "ca", add.calcium_chloride_g), 1)
    add.final_magnesium = round(source_water.get("magnesium", 0) + gain("epsom", "mg", add.epsom_g), 1)
    add.final_sodium = round(source_water.get("sodium", 0) + gain("baking_soda", "na", add.baking_soda_g), 1)
    add.final_chloride = round(source_water.get("chloride", 0) + gain("calcium_chloride", "cl", add.calcium_chloride_g), 1)
    add.final_sulfate = round(source_water.get("sulfate", 0) + gain("gypsum", "so4", add.gypsum_g) + gain("epsom", "so4", add.epsom_g), 1)
    add.final_bicarbonate = round(source_water.get("bicarbonate", 0) + gain("baking_soda", "hco3", add.baking_soda_g), 1)

    if add.final_chloride > 0: add.sulfate_chloride_ratio = round(add.final_sulfate / add.final_chloride, 2)
    else: add.sulfate_chloride_ratio = 9.99

    r = add.sulfate_chloride_ratio
    if r > 2.0: add.ratio_description = "Very Bitter / Crisp"
    elif r > 1.5: add.ratio_description = "Bitter-Forward"
    elif r > 0.8: add.ratio_description = "Balanced"
    elif r > 0.5: add.ratio_description = "Malt-Forward / Soft"
    else: add.ratio_description = "Very Malty / Full"

    res = asdict(add)
    res["target_profile"] = target_profile_name
    res["volume_liters"] = volume_liters
    return res

def get_ro_water_source() -> Dict[str, float]:
    return {"calcium": 0, "magnesium": 0, "sodium": 0, "chloride": 0, "sulfate": 0, "bicarbonate": 0}
