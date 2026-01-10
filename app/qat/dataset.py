import random

def generate_golden_dataset():
    """
    Generates a robust fake dataset for QAT testing.
    Includes:
    1. History: 50+ brews with correlated Efficiency/Grain and Attenuation/OG curves.
    2. Inventory: Mix of Full and Critical Low items.
    """
    
    # 1. HISTORY (Correlated)
    # We want to prove ML Regression works, so we create a linear relationship + noise
    history = []
    
    # Grain vs Efficiency Curve (simulating G40: efficiency drops as grain rises)
    # Eff = 85 - (1.5 * GrainKG) + Noise
    for i in range(50):
        grain_kg = random.uniform(4.0, 16.0)
        target_eff = 85 - (1.5 * grain_kg)
        real_eff = target_eff + random.uniform(-2, 2) # Noise
        real_eff = max(45, min(95, real_eff))
        
        # Yeast Attenuation Logic
        yeast = "US-05" if i % 2 == 0 else "Verdant IPA"
        og = random.uniform(1.040, 1.090)
        # US-05 drops 80%, Verdant 75%
        att_base = 80 if yeast == "US-05" else 75
        real_att = att_base + random.uniform(-3, 3)
        
        # Calculate FG from Att
        og_pts = (og - 1) * 1000
        fg_pts = og_pts * (1 - (real_att/100))
        fg = 1 + (fg_pts / 1000)
        
        history.append({
            "name": f"Test Brew {i}",
            "yeast": yeast,
            "style": "IPA" if yeast == "Verdant IPA" else "Pale Ale",
            "total_grain_kg": round(grain_kg, 2),
            "efficiency": round(real_eff, 1),
            "og": round(og, 3),
            "fg": round(fg, 3),
            "attenuation": round(real_att, 1),
            "success": True
        })
        
    # 2. INVENTORY (Low Stock Trigger)
    inventory = {
        "hops": {
            "Citra": "50g", # LOW (<100)
            "Mosaic": "400g" # HIGH
        },
        "fermentables": {
            "Maris Otter": "500g", # LOW (<1kg)
            "Oats": "2000g"
        }
    }
    
    # 3. BAD RECIPE (For Auditor)
    bad_recipe = {
        "name": "Broken IPA",
        "style": "IPA",
        "og": 1.030, # Way too low for IPA (Avg ~1.060)
        "ibu": 10   # Way too low
    }
    
    return {
        "history": history,
        "inventory": inventory,
        "bad_recipe": bad_recipe
    }
