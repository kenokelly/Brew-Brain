"""
Anomaly Detection Module for Brew Brain

Real-time detection of fermentation issues:
- Stalled fermentation (SG not dropping)
- Temperature deviation (outside yeast tolerance)
- Runaway fermentation (dropping too fast)
- Tilt signal loss (offline too long)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from app.core.config import get_config
from app.core.influx import query_api, INFLUX_BUCKET
from app.services.notifications import send_telegram_message

logger = logging.getLogger(__name__)

# Thresholds
STALL_THRESHOLD_POINTS_PER_DAY = 1.0  # SG change < 0.001/day
RUNAWAY_THRESHOLD_POINTS_12H = 20.0   # SG change > 0.020 in 12h
TEMP_DEVIATION_F = 2.0                 # ±2°F from target for 30m
SIGNAL_LOSS_MINUTES = 60               # No reading for > 60 min


def check_stalled_fermentation(batch_name: str = "Current Batch") -> Dict[str, Any]:
    """
    Detects stalled fermentation by calculating SG slope over 24 hours.
    Triggers alert if SG change < 0.001/day during active fermentation.
    """
    try:
        # Query last 24h of SG readings
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: -24h)
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["_field"] == "SG")
            |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
        '''
        tables = query_api.query(query)
        
        readings = []
        for table in tables:
            for record in table.records:
                readings.append({
                    "time": record.get_time(),
                    "sg": record.get_value()
                })
        
        if len(readings) < 4:  # Need at least 4 hours of data
            return {"status": "insufficient_data", "readings": len(readings)}
        
        # Calculate slope (points dropped per day)
        first_sg = readings[0]["sg"]
        last_sg = readings[-1]["sg"]
        hours_elapsed = (readings[-1]["time"] - readings[0]["time"]).total_seconds() / 3600
        
        if hours_elapsed < 1:
            return {"status": "insufficient_time"}
        
        # Convert to points/day (1 SG point = 0.001)
        sg_change = first_sg - last_sg  # Positive = dropping (fermenting)
        points_per_day = (sg_change * 1000) / (hours_elapsed / 24)
        
        # Only alert if we're in active fermentation (SG > 1.020)
        if last_sg > 1.020 and points_per_day < STALL_THRESHOLD_POINTS_PER_DAY:
            alert_msg = (
                f"🛑 *STALLED FERMENTATION: {batch_name}*\n\n"
                f"SG Change: {sg_change:.4f} ({points_per_day:.1f} pts/day)\n"
                f"Current SG: {last_sg:.3f}\n"
                f"Status: Fermentation appears stalled\n\n"
                f"*Suggestions:*\n"
                f"• Check temperature (raise to 20°C)\n"
                f"• Gently rouse yeast\n"
                f"• Consider yeast nutrient"
            )
            send_telegram_message(alert_msg)
            return {
                "status": "stalled",
                "alert_sent": True,
                "sg_change": round(sg_change, 4),
                "points_per_day": round(points_per_day, 2),
                "current_sg": round(last_sg, 3)
            }
        
        return {
            "status": "normal",
            "sg_change": round(sg_change, 4),
            "points_per_day": round(points_per_day, 2),
            "current_sg": round(last_sg, 3)
        }
        
    except Exception as e:
        logger.error(f"Stall detection error: {e}")
        return {"status": "error", "error": str(e)}


def check_temperature_deviation(
    target_temp_f: Optional[float] = None,
    yeast_min_f: Optional[float] = None,
    yeast_max_f: Optional[float] = None,
    batch_name: str = "Current Batch"
) -> Dict[str, Any]:
    """
    Detects temperature outside yeast tolerance range.
    Uses config values if not provided.
    """
    try:
        # Get target from config if not provided
        if target_temp_f is None:
            # Try to get from yeast metadata in config
            yeast_min_f = yeast_min_f or float(get_config("yeast_min_temp") or 60)
            yeast_max_f = yeast_max_f or float(get_config("yeast_max_temp") or 75)
            target_temp_f = (yeast_min_f + yeast_max_f) / 2
        
        # Query last 30 minutes of temperature
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: -30m)
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["_field"] == "Temp")
            |> mean()
        '''
        tables = query_api.query(query)
        
        avg_temp = None
        for table in tables:
            for record in table.records:
                avg_temp = record.get_value()
        
        if avg_temp is None:
            return {"status": "no_data"}
        
        # Check deviation
        deviation = avg_temp - target_temp_f
        
        if abs(deviation) > TEMP_DEVIATION_F:
            direction = "HIGH" if deviation > 0 else "LOW"
            emoji = "🔥" if deviation > 0 else "❄️"
            
            alert_msg = (
                f"{emoji} *TEMP DEVIATION: {batch_name}*\n\n"
                f"Current Temp: {avg_temp:.1f}°F\n"
                f"Target: {target_temp_f:.1f}°F (±{TEMP_DEVIATION_F}°F)\n"
                f"Deviation: {abs(deviation):.1f}°F {direction}\n\n"
                f"*Action:* Check glycol chiller / heating wrap"
            )
            send_telegram_message(alert_msg)
            return {
                "status": "deviation",
                "alert_sent": True,
                "current_temp": round(avg_temp, 1),
                "target_temp": round(target_temp_f, 1),
                "deviation": round(deviation, 1)
            }
        
        return {
            "status": "normal",
            "current_temp": round(avg_temp, 1),
            "target_temp": round(target_temp_f, 1),
            "deviation": round(deviation, 1)
        }
        
    except Exception as e:
        logger.error(f"Temp deviation check error: {e}")
        return {"status": "error", "error": str(e)}


def check_runaway_fermentation(batch_name: str = "Current Batch") -> Dict[str, Any]:
    """
    Detects rapid fermentation (SG dropping > 0.020 in 12 hours).
    This can indicate temperature issues or contamination.
    """
    try:
        # Query last 12h of SG readings
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: -12h)
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["_field"] == "SG")
            |> first()
        '''
        tables = query_api.query(query)
        first_sg = None
        for table in tables:
            for record in table.records:
                first_sg = record.get_value()
        
        # Get latest SG
        query_last = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["_field"] == "SG")
            |> last()
        '''
        tables = query_api.query(query_last)
        last_sg = None
        for table in tables:
            for record in table.records:
                last_sg = record.get_value()
        
        if first_sg is None or last_sg is None:
            return {"status": "insufficient_data"}
        
        sg_drop = first_sg - last_sg
        points_dropped = sg_drop * 1000
        
        if points_dropped > RUNAWAY_THRESHOLD_POINTS_12H:
            alert_msg = (
                f"⚡ *RUNAWAY FERMENTATION: {batch_name}*\n\n"
                f"SG Drop (12h): {sg_drop:.4f} ({points_dropped:.0f} pts)\n"
                f"Current SG: {last_sg:.3f}\n"
                f"Status: Fermentation is very rapid\n\n"
                f"*Check:*\n"
                f"• Current temperature (exothermic heat?)\n"
                f"• Blowoff tube clearance\n"
                f"• Lower temp if needed"
            )
            send_telegram_message(alert_msg)
            return {
                "status": "runaway",
                "alert_sent": True,
                "sg_drop_12h": round(sg_drop, 4),
                "points_dropped": round(points_dropped, 1)
            }
        
        return {
            "status": "normal",
            "sg_drop_12h": round(sg_drop, 4),
            "points_dropped": round(points_dropped, 1)
        }
        
    except Exception as e:
        logger.error(f"Runaway detection error: {e}")
        return {"status": "error", "error": str(e)}


def check_signal_loss(batch_name: str = "Current Batch") -> Dict[str, Any]:
    """
    Detects Tilt hydrometer signal loss (no reading for > 60 minutes).
    """
    try:
        # Query for most recent reading
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: -24h)
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> filter(fn: (r) => r["_field"] == "SG")
            |> last()
        '''
        tables = query_api.query(query)
        
        last_reading_time = None
        for table in tables:
            for record in table.records:
                last_reading_time = record.get_time()
        
        if last_reading_time is None:
            # No readings at all in 24h
            alert_msg = (
                f"📡 *TILT OFFLINE: {batch_name}*\n\n"
                f"No readings in last 24 hours!\n\n"
                f"*Check:*\n"
                f"• Tilt battery\n"
                f"• TiltPi/Bluetooth connection\n"
                f"• Tilt orientation in wort"
            )
            send_telegram_message(alert_msg)
            return {"status": "offline", "alert_sent": True, "minutes_since": "24h+"}
        
        # Calculate time since last reading
        now = datetime.now(timezone.utc)
        minutes_since = (now - last_reading_time).total_seconds() / 60
        
        if minutes_since > SIGNAL_LOSS_MINUTES:
            alert_msg = (
                f"📡 *TILT SIGNAL LOSS: {batch_name}*\n\n"
                f"Last reading: {int(minutes_since)} minutes ago\n"
                f"Threshold: {SIGNAL_LOSS_MINUTES} minutes\n\n"
                f"*Check:*\n"
                f"• Tilt battery\n"
                f"• TiltPi service status\n"
                f"• Bluetooth connectivity"
            )
            send_telegram_message(alert_msg)
            return {
                "status": "signal_loss",
                "alert_sent": True,
                "minutes_since": round(minutes_since, 1),
                "last_reading": last_reading_time.isoformat()
            }
        
        return {
            "status": "normal",
            "minutes_since": round(minutes_since, 1),
            "last_reading": last_reading_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Signal loss check error: {e}")
        return {"status": "error", "error": str(e)}


def run_all_anomaly_checks(batch_name: str = "Current Batch") -> Dict[str, Any]:
    """
    Runs all anomaly detection checks and returns combined results.
    Called periodically by the scheduler.
    """
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "batch": batch_name,
        "checks": {}
    }
    
    # Run each check
    results["checks"]["stalled"] = check_stalled_fermentation(batch_name)
    results["checks"]["temp_deviation"] = check_temperature_deviation(batch_name=batch_name)
    results["checks"]["runaway"] = check_runaway_fermentation(batch_name)
    results["checks"]["signal_loss"] = check_signal_loss(batch_name)
    
    # Summary
    alerts_sent = sum(
        1 for check in results["checks"].values() 
        if check.get("alert_sent", False)
    )
    results["alerts_sent"] = alerts_sent
    results["status"] = "alerts" if alerts_sent > 0 else "ok"
    
    return results
