import logging
import qrcode
import base64
from io import BytesIO
from core.config import get_config, set_config
from services.learning import get_history

logger = logging.getLogger(__name__)

def generate_qr_code_base64(url: str) -> str:
    """Generates a base64 encoded QR code PNG for a given URL."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        return ""

def init_tap(tap_id: str, batch_id: str, keg_volume_l: float) -> dict:
    """Initializes a tap with a specific batch from history."""
    # 1. Fetch batch from history
    history = get_history()
    batch = next((b for b in history if b.get('_id') == batch_id or b.get('name') == batch_id), None)
    
    if not batch:
        return {"error": "Batch not found in history"}
        
    # 2. Dynamic ABV & Calorie Calculation based on actual FG/OG
    og = float(batch.get('og', 1.050))
    fg = float(batch.get('fg', 1.010))
    abv = (og - fg) * 131.25
    
    # 3. Create Tap Profile
    tap_data = {
        "name": batch.get('name', 'Unknown Batch'),
        "style": batch.get('style', 'Unknown Style'),
        "abv": round(abv, 1),
        "color": "#FFC107", # Could derive from SRM if we had it
        "keg_date": batch.get('start_date', ''), # Or today
        "keg_volume_l": float(keg_volume_l),
        "volume_remaining_ml": float(keg_volume_l) * 1000.0,
        "remaining_pct": 100.0,
        "batch_id": batch_id
    }
    
    # 4. Save to config
    taps = get_config("taps") or {}
    taps[tap_id] = tap_data
    set_config("taps", taps)
    
    return {"status": "success", "message": f"Tap {tap_id} initialized with {keg_volume_l}L of {tap_data['name']}."}

def pour_tap(tap_id: str, amount_ml: float) -> dict:
    """Decrements volume from a tap and updates percentage."""
    taps = get_config("taps") or {}
    tap = taps.get(tap_id)
    
    if not tap:
        return {"error": f"Tap {tap_id} not found or not initialized"}
        
    current_ml = tap.get('volume_remaining_ml', 0.0)
    keg_vol_l = tap.get('keg_volume_l', 19.0)
    
    new_ml = max(0.0, current_ml - amount_ml)
    new_pct = (new_ml / (keg_vol_l * 1000.0)) * 100.0
    
    tap['volume_remaining_ml'] = new_ml
    tap['remaining_pct'] = round(new_pct, 1)
    
    taps[tap_id] = tap
    set_config("taps", taps)
    
    return {"status": "success", "new_remaining_pct": tap['remaining_pct']}

def get_tap_list(base_url: str) -> list:
    """Gets the formatted tap list with QR codes."""
    taps_config = get_config("taps") or {}
    result = []
    
    for tap_id, tap in taps_config.items():
        if isinstance(tap, dict):
            # Generate public URL for QR
            # Format: http://<ip>/public/tap/<tap_id>
            public_url = f"{base_url}/public/tap/{tap_id}"
            
            formatted_tap = {
                "tap_id": tap_id,
                "beer_name": tap.get('name', 'Empty'),
                "style": tap.get('style', 'N/A'),
                "abv": tap.get('abv', 0.0),
                "keg_volume_l": tap.get('keg_volume_l', 19.0),
                "remaining_pct": tap.get('remaining_pct', 0.0),
                "qr_code_base64": generate_qr_code_base64(public_url)
            }
            result.append(formatted_tap)
            
    return result

def update_tap(tap_id: str, data: dict) -> dict:
    """Handles manual assignments, snapshots, and clearing taps from UI."""
    action = data.get('action')
    taps = get_config("taps") or {}
    
    if action == "clear":
        if tap_id in taps:
            del taps[tap_id]
            set_config("taps", taps)
        return {"status": "success", "message": "Tap cleared"}
        
    elif action == "manual":
        taps[tap_id] = {
            "active": True,
            "name": data.get("name", "Unknown"),
            "style": data.get("style", "N/A"),
            "abv": float(data.get("abv") or 0.0),
            "srm": float(data.get("srm") or 0.0),
            "ibu": float(data.get("ibu") or 0.0),
            "keg_total": float(data.get("keg_total") or 19.0),
            "keg_remaining": float(data.get("keg_remaining") or 19.0),
            "volume_unit": data.get("volume_unit", "L")
        }
        set_config("taps", taps)
        return {"status": "success", "message": "Tap updated manually"}
        
    elif action == "assign_current":
        # Get current batch config, default to some values if not found
        name = get_config("batch_name") or "Unknown Batch"
        
        # Calculate ABV if possible
        og = float(get_config("og") or 1.050)
        fg = float(get_config("target_fg") or 1.010)
        
        # In a real system we'd use the actual current gravity from the sensor
        abv = (og - fg) * 131.25
        
        taps[tap_id] = {
            "active": True,
            "name": name,
            "style": "Current Batch",
            "abv": round(abv, 1),
            "keg_total": float(data.get("keg_total") or 19.0),
            "keg_remaining": float(data.get("keg_remaining") or 19.0),
            "volume_unit": data.get("volume_unit", "L")
        }
        set_config("taps", taps)
        return {"status": "success", "message": "Snapshot assigned"}
        
    return {"error": f"Invalid action: {action}"}
