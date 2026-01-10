import pandas as pd
import logging
import io
import requests
import base64
import re
from core.config import get_config
from services import yeast

logger = logging.getLogger(__name__)

def get_auth_headers():
    u = get_config("bf_user")
    k = get_config("bf_key")
    if not u or not k: return None
    auth = base64.b64encode(f"{u}:{k}".encode()).decode()
    return {"Authorization": f"Basic {auth}"}

def fetch_brewfather_batches(limit=10):
    """
    Fetches recent batches from Brewfather.
    """
    headers = get_auth_headers()
    if not headers: return {"error": "Missing Credentials"}
    
    # Get Planning, Brewing, Fermenting, Completed
    url = f"https://api.brewfather.app/v2/batches?limit={limit}&order_by=brewDate&order_by_direction=desc"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {"error": f"API Error {r.status_code}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def fetch_batch_readings(batch_id):
    """
    Fetches readings (webhooks/stream items) for a batch.
    """
    headers = get_auth_headers()
    if not headers: return None
    
    url = f"https://api.brewfather.app/v2/batches/{batch_id}/readings"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200: return None
        return r.json()
    except Exception as e:
        logger.error(f"Failed to fetch readings: {e}")
        return None

def fetch_brewfather_recipes(limit=20):
    """
    Fetches recipes from Brewfather.
    """
    headers = get_auth_headers()
    if not headers: return {"error": "Missing Credentials"}
    
    url = f"https://api.brewfather.app/v2/recipes?limit={limit}&order_by=name"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {"error": f"API Error {r.status_code}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def fetch_recipe_details(recipe_id):
    """
    Fetches full details for a single recipe.
    """
    headers = get_auth_headers()
    if not headers: return {"error": "Missing Credentials"}
    
    url = f"https://api.brewfather.app/v2/recipes/{recipe_id}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200: return {"error": f"API Error {r.status_code}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def parse_tilt_csv(file_stream):
    """
    Parses a TiltPi CSV log file from a stream/file object.
    """
    try:
        df = pd.read_csv(file_stream)
        
        # Ensure we have a datetime index if possible, commonly 'Timepoint' or 'Time'
        time_col = next((c for c in df.columns if 'time' in c.lower()), None)
        if time_col:
            df['datetime'] = pd.to_datetime(df[time_col])
        
        return df
    except Exception as e:
        logger.error(f"Failed to parse CSV: {e}")
        return None

def check_temp_stability(data_source, target_temp, threshold=1.0, is_dataframe=False):
    """
    Checks stability. data_source can be a DataFrame or a CSV stream.
    """
    df = data_source
    if not is_dataframe:
        df = parse_tilt_csv(data_source)
    
    if df is None or df.empty:
        return {"status": "error", "message": "Invalid or Empty Data"}
    
    # Look for a Temperature column
    # If from Brewfather API readings, it might be 'temp'
    temp_col = next((c for c in df.columns if 'temp' in c.lower() and 'f' not in c.lower()), None)
    
    if not temp_col:
         return {"status": "error", "message": "Temperature column not found"}

    # Use last 20 readings
    last_temps = df[temp_col].tail(20)
    if last_temps.empty:
         return {"status": "error", "message": "Not enough data"}

    max_dev = abs(last_temps - target_temp).max()
    is_stable = max_dev <= threshold
    
    return {
        "status": "stable" if is_stable else "unstable",
        "max_deviation": round(max_dev, 2),
        "current_temp": round(last_temps.iloc[-1], 2),
        "target_temp": target_temp
    }

def calculate_expected_fg(batch_id, current_gravity):
    """
    Calculates expected FG based on Brewfather batch yeast data.
    """
    headers = get_auth_headers()
    if not headers: return {"error": "Missing Credentials"}
    
    # 1. Get Batch Details for Yeast and OG
    try:
        url = f"https://api.brewfather.app/v2/batches/{batch_id}"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200: return {"error": "Failed to fetch batch details"}
        
        batch = r.json()
        og = batch.get("measuredOg") or batch.get("estimatedOg")
        if not og: return {"error": "No OG found for batch"}
        
        # Get Yeast
        yeasts = batch.get("yeast", [])
        if not yeasts: return {"error": "No yeast found in batch"}
        
        yeast_name = yeasts[0].get("name")
        
        # 2. Get Yeast Specs
        specs = yeast.search_yeast_meta(yeast_name)
        if hasattr(specs, "get") and specs.get("error"):
            return {"error": f"Yeast lookup failed: {specs['error']}"}
            
        attenuation_str = specs.get("attenuation", "75%")
        
        # Parse attenuation (e.g. "75%" or "70-80%")
        # Take average if range
        import re
        nums = [float(n) for n in re.findall(r"[\d\.]+", attenuation_str)]
        if not nums:
            att_avg = 75.0 # Default
        else:
            att_avg = sum(nums) / len(nums)
            
        # 3. Calculate
        # FG = OG - (OG - 1) * (apparent_attenuation / 100)
        # Note: Manufacturers usually list Apparent Attenuation
        expected_fg = og - (og - 1) * (att_avg / 100)
        
        return {
            "yeast_name": yeast_name,
            "attenuation_avg": att_avg,
            "og": og,
            "expected_fg": round(expected_fg, 3),
            "current_gravity": current_gravity,
            "difference": round(current_gravity - expected_fg, 3),
            "status": "Finished" if current_gravity <= expected_fg + 0.002 else "Fermenting"
        }
        
    except Exception as e:
        return {"error": str(e)}

def monitor_active_batches():
    """
    Scans all 'Fermenting' batches in Brewfather.
    Fetches latest Tilt/Stream data.
    Runs check_batch_health for each.
    Triggers alerts if necessary.
    """
    from services import learning
    from datetime import datetime
    
    # 1. Fetch Active Batches
    all_batches = fetch_brewfather_batches(limit=20)
    if isinstance(all_batches, dict) and 'error' in all_batches:
        return all_batches
        
    active_details = []
    
    for batch in all_batches:
        # Check status
        if batch.get('status') != 'Fermenting':
            continue
            
        batch_id = batch.get('_id')
        name = batch.get('name')
        recipe = batch.get('recipe', {})
        style = recipe.get('style', {}).get('name', 'Unknown Style')
        
        # --- PROFILE AWARENESS START ---
        # Get Fermentation Profile
        target_temp = 20.0 # Fallback
        
        # Calculate Days In
        brew_date_ms = batch.get('brewDate')
        days_in = 0
        if brew_date_ms:
            brew_date = datetime.fromtimestamp(brew_date_ms / 1000.0)
            days_in = (datetime.now() - brew_date).days
            
        fermentation = recipe.get('fermentation', {})
        steps = fermentation.get('steps', [])
        
        if steps:
            # Logic: Iterate steps to find current active step
            # Step has { type: 'Primary', stepTemp: 18, stepTime: 14 } (days)
            current_day_count = 0
            found_step = False
            for step in steps:
                duration = step.get('stepTime', 0)
                temp = step.get('stepTemp', 20)
                
                # Check if we are in this step
                if days_in <= (current_day_count + duration):
                    target_temp = float(temp)
                    found_step = True
                    break
                
                current_day_count += duration
            
            # If we are past all steps, default to last step temp (conditioning/aging)
            if not found_step and steps:
                target_temp = float(steps[-1].get('stepTemp', 20))
        # --- PROFILE AWARENESS END ---

        yeast_name = "Unknown Yeast"
        if batch.get('yeast') and len(batch['yeast']) > 0:
            yeast_name = batch['yeast'][0].get('name')
            
        # Get Measured OG or Estimated
        og = batch.get('measuredOg') or batch.get('estimatedOg')
        if not og: continue
        
        # 2. Fetch Readings (Tilt Data)
        readings = fetch_batch_readings(batch_id)
        if not readings:
            continue
            
        # Get Latest Reading
        last_reading = readings[-1]
        current_sg = last_reading.get('sg')
        current_temp = last_reading.get('temp')
        
        if not current_sg: continue
        
        # Calculate Stability
        stability = 0.5
        if len(readings) > 5:
            temps = [float(r.get('temp')) for r in readings[-20:] if r.get('temp')]
            if len(temps) > 1:
                mean = sum(temps) / len(temps)
                var = sum((t - mean)**2 for t in temps) / len(temps)
                stability = round(var ** 0.5, 2)
        
        # 3. Run Health Check
        health_res = learning.check_batch_health(
            current_sg,
            og,
            yeast_name,
            days_in,
            current_temp,
            style,
            name,
            stability
        )
        
        # Check deviation against PROFILE target
        # health_res might have generic checks, but let's add a specific profile check here
        if abs(current_temp - target_temp) > 1.0:
            health_res['temp_status'] = f"WARNING: Temp {current_temp}°C deviates from Profile Target {target_temp}°C"
        else:
            health_res['temp_status'] = f"OK (Target {target_temp}°C)"
            
        active_details.append({
            "batch": name,
            "style": style,
            "days": days_in,
            "target_temp": target_temp,
            "status": "Scanned",
            "health": health_res
        })
        
    return {"status": "success", "scanned_batches": active_details}

def fetch_brewfather_inventory():
    """
    Fetches Hops, Fermentables, Yeast, Miscs from Brewfather and normalizes them.
    """
    headers = get_auth_headers()
    if not headers: return {"error": "Missing Credentials"}
    
    inventory = {
        "hops": {},
        "fermentables": {},
        "yeast": {},
        "salts": {},
        "misc": {}
    }
    
    # helper
    def fetch_cat(endpoint):
        items = []
        url = f"https://api.brewfather.app/v2/inventory/{endpoint}?limit=1000"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
        return []

    # 1. Hops
    for i in fetch_cat("hops"):
        name = i.get("name", "Unknown").lower()
        amt = i.get("amount", 0) # usually grams
        inventory["hops"][name] = inventory["hops"].get(name, 0) + amt

    # 2. Fermentables
    for i in fetch_cat("fermentables"):
        name = i.get("name", "Unknown").lower()
        amt = i.get("amount", 0) # usually kg
        inventory["fermentables"][name] = inventory["fermentables"].get(name, 0) + amt
        
    # 3. Yeast
    for i in fetch_cat("yeasts"):
        name = i.get("name", "Unknown").lower()
        amt = i.get("amount", 0) # units or grams
        inventory["yeast"][name] = inventory["yeast"].get(name, 0) + amt
        
    # 4. Misc (Map to Salts or Misc)
    # Common salts: Gypsum, Calcium Chloride, Epsom, Lactic Acid
    salt_keywords = ["gypsum", "chloride", "epsom", "sulfate", "salt", "acid", "baking", "carbonate"]
    
    for i in fetch_cat("miscs"):
        name = i.get("name", "Unknown").lower()
        amt = i.get("amount", 0)
        
        is_salt = any(k in name for k in salt_keywords)
        target = inventory["salts"] if is_salt else inventory["misc"]
        
        target[name] = target.get(name, 0) + amt
        
    return inventory
