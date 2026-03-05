import requests
import json

API_URL = "http://localhost:5000/api"

def migrate():
    print("Fetching taps...")
    try:
        r = requests.get(f"{API_URL}/taps", timeout=5)
        taps = r.json()
    except Exception as e:
        print(f"Error fetching taps: {e}")
        return

    for tap_id, data in taps.items():
        if not data or not data.get('active'):
            print(f"Skipping {tap_id} (inactive)")
            continue
            
        current_unit = data.get('volume_unit', 'oz')
        print(f"Processing {tap_id}: Unit={current_unit}")
        
        # If already L, maybe verify value? 
        # Assuming if "L" is set, it's already migrated. 
        # But user claims "still in oz" despite maybe having "L"? 
        # Let's force check: if value > 100, it's definitely oz.
        
        keg_total = float(data.get('keg_total', 640))
        keg_rem = float(data.get('keg_remaining', 640))
        
        if current_unit == 'oz' or keg_total > 50:
            print(f"  Converting {tap_id} from Oz to Litres...")
            
            # Conversion: 1 fl oz = 0.0295735 L
            # But earlier plan said 640oz ~ 19L. 
            # 640 * 0.0295735 = 18.92.
            # Using 29.5735 ml per oz.
            
            check_factor = 29.5735 / 1000.0
            
            new_total = keg_total * check_factor
            new_rem = keg_rem * check_factor
            
            # Construct update payload
            # "routes.py" now supports preserving fields manually
            payload = data.copy()
            payload['action'] = 'manual'
            payload['keg_total'] = f"{new_total:.2f}"
            payload['keg_remaining'] = f"{new_rem:.2f}"
            payload['volume_unit'] = 'L'
            
            # Send update
            res = requests.post(f"{API_URL}/taps/{tap_id}", json=payload)
            if res.status_code == 200:
                print(f"  ✅ Updated {tap_id}: {keg_total}oz -> {new_total:.2f}L")
            else:
                print(f"  ❌ Failed to update {tap_id}: {res.text}")

        else:
            print(f"  {tap_id} already likely Litres ({keg_total}L). Skipping.")

if __name__ == "__main__":
    migrate()
