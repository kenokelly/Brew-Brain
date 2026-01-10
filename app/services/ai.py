import numpy as np
from datetime import datetime, timezone, timedelta
from app.core.influx import query_api, INFLUX_BUCKET

def analyze_yeast_history(yeast_name):
    """
    Analyzes measurements for a specific yeast strain over the last 90 days
    to determine 'Normal Behavior'.
    
    Returns:
       dict: { "avg_rate": float (points/day), "attenuation": float (%), "samples": int }
       OR None if insufficient data.
    """
    if not yeast_name or yeast_name == "Unknown":
        return None

    # 1. Query Data (Last 90 days)
    # We want ALL calibrated readings for this yeast
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -90d)
      |> filter(fn: (r) => r["_measurement"] == "calibrated_readings")
      |> filter(fn: (r) => r["yeast"] == "{yeast_name}")
      |> filter(fn: (r) => r["_field"] == "sg")
      |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
      |> yield(name: "mean")
    '''
    
    try:
        tables = query_api.query(query)
        readings = []
        
        for table in tables:
            for record in table.records:
                readings.append((record.get_time(), record.get_value()))
        
        if not readings:
            return None

        # 2. Separate into Batches
        # Logic: If gap > 72 hours (3 days), it's a new batch
        batches = []
        current_batch = []
        last_time = None
        
        # Sort by time just in case
        readings.sort(key=lambda x: x[0])
        
        for r_time, r_val in readings:
            if last_time is None:
                current_batch.append((r_time, r_val))
            else:
                diff = (r_time - last_time).total_seconds()
                if diff > (72 * 3600): # 72 hours
                    if len(current_batch) > 20: # Only count significant batches
                        batches.append(current_batch)
                    current_batch = [(r_time, r_val)]
                else:
                    current_batch.append((r_time, r_val))
            last_time = r_time
            
        if len(current_batch) > 20:
            batches.append(current_batch)
            
        # 3. Analyze Each Batch
        # We exclude the "Current" batch if it looks active (last reading < 24h ago)
        # Actually, user said: "Exclude the current batch".
        # We can just filter out any batch where the last point is very recent (e.g. < 24h)
        
        historic_batches = []
        now = datetime.now(timezone.utc)
        
        for b in batches:
            last_point_time = b[-1][0]
            if (now - last_point_time).total_seconds() > (24 * 3600):
                historic_batches.append(b)
                
        if len(historic_batches) < 1:
            return None # Not enough history

        rates = []
        attenuations = []
        
        for b in historic_batches:
            # Calculate Rate: (Start SG - End SG) / Days
            start_sg = b[0][1]
            end_sg = b[-1][1]
            duration_days = (b[-1][0] - b[0][0]).total_seconds() / 86400
            
            if duration_days > 1.0:
                drop = start_sg - end_sg
                rate = drop / duration_days # points per day
                
                # Attenuation (Apparent): (OG - FG) / (OG - 1)
                # We assume Start SG is close to OG for this math
                if start_sg > 1.0:
                    att = (start_sg - end_sg) / (start_sg - 1)
                    attenuations.append(att)
                
                rates.append(rate)

        if not rates:
            return None
            
        return {
            "avg_rate": float(np.mean(rates)),
            "avg_attenuation": float(np.mean(attenuations)) if attenuations else 0.75,
            "samples": len(historic_batches)
        }

    except Exception as e:
        print(f"AI Error: {e}")
        return None
