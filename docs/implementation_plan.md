# Debugging Signal Strength (Part 2)

## Goal Description
The user confirmed the "Tilt Pi" shows the signal strength, but our Brew-Brain dashboard shows it as empty. My previous query `filter(fn: (r) => r["_field"] == "RSSI")` failed to find data. I need to discover the *actual* field name stored in InfluxDB (e.g., "Signal", "rssi", "Rssi").

## Proposed Changes

### Investigation
- Create `app/debug_influx.py` to:
    - Connect to InfluxDB using environment variables.
    - Query and list all measurements in `INFLUX_BUCKET`.
    - For `sensor_data` (or similar), list all unique fields.
- Run this script inside the remote container.

### Backend
#### [MODIFY] [brew_brain.py](file:///Users/kokelly/Brew-Brain/app/brew_brain.py)
- Update `get_status_dict` with the correct field name found during investigation.

## Verification Plan
### Manual Verification
- Run debug script to find field name.
- Apply fix.
- Deploy and verify `/api/status` returns a number for `rssi`.
