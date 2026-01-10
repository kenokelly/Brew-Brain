from dataclasses import dataclass, asdict

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

PROFILES = {
    "ro": WaterProfile("RO Water", 0, 0, 0, 0, 0, 0, 5.5),
    # Simple / Legacy Profiles
    "west_coast": WaterProfile("West Coast IPA (Simple)", 110, 18, 25, 50, 250, 20),
    "neipa": WaterProfile("NEIPA (Simple)", 130, 15, 25, 150, 80, 30),
    "balanced": WaterProfile("Balanced Profile (Simple)", 100, 15, 20, 90, 90, 45),
    
    # Bru'n Water Standards
    "yellow_dry": WaterProfile("Yellow Dry (Bru'n Water)", 110, 18, 15, 50, 300, 0, 5.3),
    "yellow_balanced": WaterProfile("Yellow Balanced (Bru'n Water)", 75, 10, 10, 65, 75, 0, 5.4),
    "yellow_full": WaterProfile("Yellow Full (Bru'n Water)", 90, 15, 15, 100, 65, 0, 5.4),
    "neipa_juicy": WaterProfile("NEIPA Juicy (Bru'n Water)", 140, 18, 20, 150, 80, 0, 5.3),
    "black_balanced": WaterProfile("Black Balanced (Bru'n Water)", 80, 10, 25, 65, 55, 130, 5.5)
}

def get_profile(name):
    p = PROFILES.get(name.lower())
    if p:
        return asdict(p)
    return None

def get_all_profiles():
    return {k: asdict(v) for k, v in PROFILES.items()}
