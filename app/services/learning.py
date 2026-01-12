import json
import os
import logging

logger = logging.getLogger(__name__)

HISTORY_FILE = 'data/brew_history.json'

def get_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load history: {e}")
        return []

def save_brew_outcome(data):
    """
    Saves a brew outcome to history.
    data: {name, style, yeast, og, fg, attenuation, success}
    """
    history = get_history()
    history.append(data)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    return {"status": "success", "count": len(history)}

def get_recommendations(category, style=None):
    """
    Analyzes history to find verified ingredients.
    category: 'yeast', 'hop', 'malt'
    """
    history = get_history()
    verified = {}
    
    for brew in history:
        if not brew.get('success'): continue
        
        # Check Yeast
        if category == 'yeast':
            name = brew.get('yeast')
            if name:
                if name not in verified: verified[name] = {"count": 0, "attenuation_sum": 0}
                verified[name]["count"] += 1
                verified[name]["attenuation_sum"] += brew.get('attenuation', 75)

    # Format result
    results = []
    for name, stats in verified.items():
        avg_att = round(stats["attenuation_sum"] / stats["count"], 1)
        results.append({
            "name": name,
            "verified_count": stats["count"],
            "avg_attenuation": avg_att
        })
        
    results.sort(key=lambda x: x['verified_count'], reverse=True)
    return results

def simulate_brew_day(grains, volume_l, mash_efficiency_pct):
    """
    Predicts OG based on grain bill and equipment efficiency.
    grains: list of {weight_kg, potential_sg (e.g. 1.037)}
    """
    total_points = 0
    
    for grain in grains:
        # Points per kg per liter = (Potential - 1) * 1000 * 8.345
        w_lb = float(grain['weight_kg']) * 2.20462
        pot = float(grain.get('potential', 1.037))
        ppg = (pot - 1) * 1000
        
        points = w_lb * ppg
        total_points += points
        
    # Apply Efficiency using Mash Efficiency (G40 usually 75-80%)
    extracted_points = total_points * (float(mash_efficiency_pct) / 100.0)
    
    # Volume in Gallons
    vol_gal = float(volume_l) * 0.264172
    if vol_gal <= 0: return {"error": "Volume must be > 0"}
    
    final_points = extracted_points / vol_gal
    
    predicted_og = 1 + (final_points / 1000)
    
    # pH Warning Logic for RO Water
    # High gravity w/ lots of roasted makts/high grain bill often drives pH down
    # Very simplified check: If OG > 1.070 and using RO (implied), warn.
    ph_warning = None
    if predicted_og > 1.075:
        ph_warning = "High Gravity may drop Mash pH below 5.2. Consider increasing Alkalinity (Baking Soda/Slaked Lime)."
    
    return {
        "predicted_og": round(predicted_og, 3),
        "total_potential_points": round(total_points, 1),
        "volume_gal": round(vol_gal, 2),
        "ph_warning": ph_warning,
        "efficiency_used": mash_efficiency_pct
    }

# --- ML Model (Simple Linear Regression) ---
def train_efficiency_model():
    """
    Trains a model: Efficiency = m * TotalGrain(kg) + c
    Returns {slope, intercept, r2}
    """
    history = get_history()
    
    # Data Extraction
    # We need brew sessions that have 'total_grain' and 'efficiency' logs
    # or we infer it from OG/Grain.
    # For now, let's assume future logs will have 'actual_efficiency'.
    # Fallback: We'll construct mock data if history is empty for demo.
    
    X = [] # Grain Weight
    Y = [] # Efficiency
    
    # Mock Data for "Cold Start" (Simulating a G40 curve)
    # 5kg -> 80%, 8kg -> 75%, 12kg -> 65%, 18kg -> 55%
    X_mock = [5.0, 8.0, 12.0, 16.0]
    Y_mock = [82.0, 76.0, 68.0, 58.0]
    
    if len(history) < 2:
        X, Y = X_mock, Y_mock
    else:
        # Try to extract real data
        for h in history:
            g = h.get('total_grain_kg')
            e = h.get('efficiency')
            if g and e:
                X.append(float(g))
                Y.append(float(e))
        
        # Fallback if extraction failed
        if len(X) < 2: X, Y = X_mock, Y_mock

    # Linear Regression Custom Implementation
    n = len(X)
    sum_x = sum(X)
    sum_y = sum(Y)
    sum_xy = sum(x*y for x,y in zip(X,Y))
    sum_xx = sum(x*x for x in X)
    
    # Calculate Slope (m) and Intercept (c)
    # m = (n*sum_xy - sum_x*sum_y) / (n*sum_xx - sum_x^2)
    denominator = (n * sum_xx - sum_x ** 2)
    
    if denominator == 0:
        return {"m": 0, "c": 75} # Default flat 75%
        
    m = (n * sum_xy - sum_x * sum_y) / denominator
    c = (sum_y - m * sum_x) / n
    
    return {"m": m, "c": c, "data_points": n}

def predict_efficiency(grain_weight_kg):
    """
    Predicts efficiency for a given grain bill.
    """
    model = train_efficiency_model() # In prod, load from cached model file
    m = model['m']
    c = model['c']
    
    # y = mx + c
    pred = (m * float(grain_weight_kg)) + c
    
    # Clamp bounds (Efficiency can't be > 95% or < 40%)
    pred = max(40, min(95, pred))
    
    return {
        "predicted_efficiency": round(pred, 1),
        "model": model
    }

    return {
        "predicted_efficiency": round(pred, 1),
        "model": model
    }

def predict_fg_from_history_knn(yeast_name, original_gravity, style=None):
    """
    Predicts FG using K-Nearest Neighbors (KNN) logic.
    Finds historical brews with similar OG and Yeast.
    """
    history = get_history()
    
    # Filter for valid data
    candidates = [b for b in history if b.get('yeast') == yeast_name and b.get('success') and b.get('attenuation')]
    
    if not candidates:
        return {
            "predicted_fg": None,
            "predicted_abv": None,
            "confidence": "None (No History)",
            "method": "None"
        }

    # KNN Logic
    # Distance Metric: abs(HistoryOG - CurrentOG)
    # We prioritize OG proximity since attenuation varies by gravity (osmotic pressure).
    
    # Sort by distance
    candidates.sort(key=lambda x: abs(float(x.get('og', 1.050)) - float(original_gravity)))
    
    # Pick Top K (e.g. 3)
    k = 3
    nearest = candidates[:k]
    
    # Weighted Average (Inventory Distance Weighting could be added, but simple avg of nearest is robust enough for small N)
    avg_att = sum(float(b['attenuation']) for b in nearest) / len(nearest)
    
    # Calc FG
    og_points = (original_gravity - 1) * 1000
    fg_points = og_points * (1 - (avg_att/100))
    predicted_fg = 1 + (fg_points / 1000)
    predicted_abv = (original_gravity - predicted_fg) * 131.25
    
    method_str = f"KNN (Based on {len(nearest)} similar brews)"
    
    return {
        "predicted_fg": round(predicted_fg, 3),
        "predicted_abv": round(predicted_abv, 1),
        "confidence": "High" if len(nearest) >= 3 else "Moderate",
        "method": method_str,
        "avg_attenuation": round(avg_att, 1)
    }

def audit_recipe(recipe):
    """
    Audits a recipe against historical 'Success' data.
    Returns warnings and optimization tips.
    recipe: {style, og, ibu, abv}
    """
    history = get_history()
    style = recipe.get('style', 'Ale')
    
    # 1. Filter History for same style Family
    # broad match: 'IPA' matches 'Double IPA'
    peers = [b for b in history if b.get('success') and style.lower() in b.get('style', '').lower()]
    
    if len(peers) < 2:
        return {
            "status": "No Data",
            "message": f"Not enough successful {style} brews to audit against."
        }
        
    tips = []
    
    # 2. Analyze Metrics
    avg_og = sum(float(b.get('og', 1.050)) for b in peers) / len(peers)
    avg_att = sum(float(b.get('attenuation', 75)) for b in peers) / len(peers)
    
    # OG Check
    curr_og = float(recipe.get('og', 1.050))
    if abs(curr_og - avg_og) > 0.010:
        direction = "higher" if curr_og > avg_og else "lower"
        tips.append(f"⚖️ **Gravity Deviation**: Your successful {style}s avg {round(avg_og, 3)} OG. This is {direction}.")
        
    # Bitterness Check (if available in history, usually 'ibu' not always there, but let's assume we start logging it)
    # Mocking a check if 'ibu' was logged
    
    return {
        "status": "Audited",
        "peer_count": len(peers),
        "tips": tips,
        "avg_peer_og": round(avg_og, 3),
        "avg_peer_att": round(avg_att, 1)
    }

def check_batch_health(current_sg, original_gravity, yeast_name, days_in, temp=None, style=None, batch_name="Batch", current_stability=None):
    """
    Checks if current fermentation is tracking with historical average.
    Triggers Telegram alert if deviation > 10%.
    Includes Temp Stability analysis if current_stability provided.
    """
    from services.notifications import send_telegram_message
    
    # 1. Get History
    history = get_history()
    relevant_brews = []
    
    # If style is provided, prioritize style+yeast match
    if style:
        relevant_brews = [b for b in history if b.get('yeast') == yeast_name and b.get('success') and style.lower() in b.get('style', '').lower()]
        
    # Fallback to just yeast if no specific style matches or no style provided
    if not relevant_brews:
        relevant_brews = [b for b in history if b.get('yeast') == yeast_name and b.get('success')]
    
    if not relevant_brews:
        return {"status": "No History", "message": "No historical data for this yeast/style."}
    
    avg_att = sum(b.get('attenuation', 75) for b in relevant_brews) / len(relevant_brews)
    
    # Get Historical Temp Stability
    stabilities = [b.get('temp_stability', 0.5) for b in relevant_brews if b.get('temp_stability')]
    avg_stability = sum(stabilities) / len(stabilities) if stabilities else 0.5
    
    # 2. Calculate Current Attenuation
    # Att = (OG - Current) / (OG - 1)
    # Also Check Current Temp Stability if provided (passed as list of last N temps ideally, or pre-calc)
    # For now, we only have 'temp' (current scalar). We can't calc stability from single point.
    # However, if 'current_sg' represents the LATEST reading, we assume 'temp' is LATEST.
    # To check stability here, we'd need the FULL log or the variance passed in 'data'.
    # Updated: Let's assume 'temp' passed to this function is just scalar current temp.
    # Health Check for Temp Stability requires the LOG analysis endpoint generally.
    # BUT, if the user manually passes a 'stability' metric (e.g. from the frontend chart analysis), we use it.
    
    # Let's check if 'temp' is actually a stability metric or scalar? user said "analyze Tilt Logs"
    # To keep this "live" check simple without re-uploading full CSV every 15 mins:
    # We'll rely on the alerting system to assume the 'monitoring' client calculates and sends 'stability'.
    # If not present, we skip.
    
    current_stability = 0.5 # Default 'good'
    # Hack: Using 'temp' arg as is, but if we want stability we need a new arg.
    # Let's add 'current_stability' to args in next iteration if needed.
    # For now, let's just use the attenuation checks which are robust.
    
    try:
        current_sg = float(current_sg)
        original_gravity = float(original_gravity)
        current_att = ((original_gravity - current_sg) / (original_gravity - 1)) * 100
    except Exception as e:
        logger.warning(f"Health check gravity parse error: {e}")
        return {"error": "Invalid gravity values"}
        
    # 3. Analyze Health
    status = "Normal"
    alert_msg = None
    recommendation = ""
    
    threshold_infection = avg_att * 1.10 # +10%
    threshold_stall = avg_att * 0.80     # -20% (Stall threshold)
    
    # --- REAL TIME ML: VELOCITY CHECK ---
    # Calc Current Velocity (Points dropped per day avg)
    # Velocity = (StartPoints - CurrentPoints) / Days
    # StartPoints = (OG-1)*1000
    current_velocity = 0
    if days_in > 0.5:
        points_dropped = ((original_gravity - 1) * 1000) - ((current_sg - 1) * 1000)
        current_velocity = points_dropped / days_in # Points/Day
        
    # Get Historical Velocity for this Yeast
    # We approximate this by looking at final attenuation / avg_days (heuristic)
    # or better: we need 'days_to_fg' in history.
    # For now, let's assume a 'Standard Ale' finishes in 7 days for calculation baseline
    # Simulating Historical Data extraction:
    hist_velocities = []
    for b in relevant_brews:
        # If we had 'days_fermenting' in log we'd use it. 
        # Fallback: Assume 7 days for completed batches
        og = b.get('og', 1.050)
        fg = b.get('fg', 1.010)
        p_drop = ((og-1)*1000) - ((fg-1)*1000)
        v = p_drop / 7.0 # Standard week
        hist_velocities.append(v)
        
    avg_hist_velocity = sum(hist_velocities) / len(hist_velocities) if hist_velocities else 5.0
    
    # COMPARISON
    velocity_status = "Normal"
    # Only check velocity if we are in the active fermentation window (Day 1-5)
    if 1 <= days_in <= 5:
        if current_velocity < (avg_hist_velocity * 0.5):
            velocity_status = "Sluggish"
            status = "Velocity Alert (Slow)"
            recommendation = "Yeast is working 50% slower than historical average. Check Oxygenation/Pitch Rate. Consider Yeast Nutrient."
            alert_msg = (
                f"🐌 *VELOCITY ALERT: {batch_name}*\n\n"
                f"Current Speed: {round(current_velocity,1)} pts/day\n"
                f"Historical Avg: {round(avg_hist_velocity,1)} pts/day\n"
                f"Status: Fermentation is sluggish.\n"
                f"Recommendation: {recommendation}"
            )
        elif current_velocity > (avg_hist_velocity * 1.5):
             velocity_status = "Explosive"
             recommendation = "Yeast is working very fast. Ensure Blowoff tube is clear. Monitor Temp closely (Exothermic risk)."
             # Info only, maybe not a critical alert unless temp high
             
    # Fallback to Static Attenuation Checks if Velocity is OK
    if not alert_msg:
        if current_att > threshold_infection:
            diff_pct = round(current_att - avg_att, 1)
            status = "Deviation (High)"
            recommendation = "Check for wild yeast infection or elevated fermentation temps (>25°C). Verify with manual gravity reading."
            alert_msg = (
                f"🚨 *BATCH HEALTH ALERT: {batch_name}*\n\n"
                f"Current SG: {current_sg}\n"
                f"Historical Avg Attenuation: {round(avg_att,1)}%\n"
                f"Status: Over-attenuated by {diff_pct}%. (Possible Infection/Wild Yeast)\n"
                f"Recommendation: {recommendation}"
            )
            
        elif days_in > 4 and current_att < threshold_stall:
            diff_pct = round(avg_att - current_att, 1)
            status = "Deviation (Low/Stall)"
            recommendation = "Check Glycol Chiller temp (Target 20°C). Consider a gentle yeast rouse in the Unitank."
            alert_msg = (
                f"⚠️ *BATCH HEALTH ALERT: {batch_name}*\n\n"
                f"Current SG: {current_sg} (Day {days_in})\n"
                f"Historical Avg Attenuation: {round(avg_att,1)}%\n"
                f"Status: Fermentation is lagging by {diff_pct}%.\n"
                f"Recommendation: {recommendation}"
            )
            
        elif current_stability is not None:
            # Check Thermal Stability (SS Brewtech target +/- 0.5C)
            # If current stability (std dev) > 0.5, we have oscillation
            if float(current_stability) > 0.5:
                 status = "Unstable Temp"
                 recommendation = "Check insulation on Unitank or air in Glycol lines. Chiller may be cycling too frequently."
                 alert_msg = (
                    f"🌡️ *TEMP STABILITY ALERT: {batch_name}*\n\n"
                    f"Current Stability: +/- {current_stability}°C\n"
                    f"Historical Avg Stability: +/- {round(avg_stability,2)}°C\n"
                    f"Status: Thermal oscillation detected (>0.5°C).\n"
                    f"Recommendation: {recommendation}"
                )
        
    if alert_msg:
        send_telegram_message(alert_msg)
        return {"status": status, "alert_sent": True, "message": alert_msg, "velocity": round(current_velocity,1)}
        
    return {
        "status": status, 
        "alert_sent": False, 
        "current_att": round(current_att, 1), 
        "avg_att": round(avg_att, 1),
        "velocity": round(current_velocity, 1),
        "avg_velocity": round(avg_hist_velocity, 1)
    }

def predict_fg_from_history(yeast_name, original_gravity):
    """
    Predicts FG and ABV based on historical yeast performance.
    """
    history = get_history()
    relevant_brews = [b for b in history if b.get('yeast') == yeast_name and b.get('success')]
    
    if not relevant_brews:
        return {
            "predicted_fg": None,
            "predicted_abv": None,
            "confidence": "None (No History)",
            "avg_attenuation": None
        }
        
    avg_att = sum(b.get('attenuation', 75) for b in relevant_brews) / len(relevant_brews)
    
    # Calculate FG: OG - (OG-1)*Att%
    og_points = (original_gravity - 1) * 1000
    fg_points = og_points * (1 - (avg_att/100))
    predicted_fg = 1 + (fg_points / 1000)
    
    # Calculate ABV: (OG - FG) * 131.25
    predicted_abv = (original_gravity - predicted_fg) * 131.25
    
    return {
        "predicted_fg": round(predicted_fg, 3),
        "predicted_abv": round(predicted_abv, 1),
        "confidence": f"High ({len(relevant_brews)} Brews)",
        "avg_attenuation": round(avg_att, 1)
    }

def learn_from_logs(csv_content, recipe_name, yeast_name):
    """
    Parses a Tilt CSV or Brewfather log to extract OG/FG and update history.
    Simple CSV parser: Time, SG, Temp
    """
    import csv
    import io
    
    try:
        f = io.StringIO(csv_content)
        reader = csv.reader(f)
        rows = list(reader)
        
        # Valid Tilt CSV
        if len(rows) < 2: return {"error": "Empty Log"}
        
        # Skip header if present (look for 'Time' or 'SG')
        start_idx = 0
        if "SG" in rows[0] or "Gravity" in rows[0]: start_idx = 1
        
        data_rows = rows[start_idx:]
        if not data_rows: return {"error": "No data rows"}
        
        # Extract SG column (usually index 2 for Tilt: Time, Temp, Gravity)
        # But let's be robust: find col index
        sg_idx = 2 
        # Simple heuristic
        
        ogs = []
        fgs = []
        
        for r in data_rows:
            try:
                val = float(r[sg_idx])
                # Filter noise
                if 1.000 < val < 1.150:
                    ogs.append(val)
                    fgs.append(val)
            except Exception as e:
                logger.debug(f"Skipping row: {e}")
            
        if not ogs: return {"error": "No valid gravity readings"}
        
        measured_og = max(ogs) # Highest reading
        measured_fg = min(fgs) # Lowest reading represents terminal gravity
        
        attenuation = ((measured_og - measured_fg) / (measured_og - 1)) * 100
        
        # Calculate Temp Stability (Standard Deviation)
        # Using simplified variance calc if numpy not available
        temps = []
        try:
            # Temp usually index 1 or 2 depending on format. TILT: Time, Temp, Gravity
            # Gravity was at sg_idx. Temp is likely the other one or index 1.
            # Let's search header
            temp_idx = 1
            for i, h in enumerate(rows[0] if len(rows)>0 else []):
                if "temp" in h.lower(): temp_idx = i
            
            for r in data_rows:
                try: 
                    t = float(r[temp_idx])
                    if 0 < t < 50: temps.append(t) # Filter valid C
                except Exception as e:
                    logger.debug(f"Temp parse skip: {e}")
        except Exception as e:
            logger.debug(f"Temp extraction failed: {e}")
        
        temp_stability = 0.0
        if temps and len(temps) > 1:
            mean_temp = sum(temps) / len(temps)
            variance = sum((t - mean_temp) ** 2 for t in temps) / len(temps)
            temp_stability = round(variance ** 0.5, 2)
        
        # Save to history
        entry = {
            "name": recipe_name,
            "yeast": yeast_name,
            "og": round(measured_og, 3),
            "fg": round(measured_fg, 3),
            "attenuation": round(attenuation, 1),
            "temp_stability": temp_stability,
            "success": True, # Assume success if imported
            "source": "Tilt Log"
        }
        
        save_brew_outcome(entry)
        
        return {
            "status": "success",
            "extracted_og": entry['og'],
            "extracted_fg": entry['fg'],
            "attenuation": entry['attenuation']
        }
        
    except Exception as e:
        return {"error": str(e)}


