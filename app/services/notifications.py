import requests
import logging
from datetime import datetime
from typing import Optional
from app.core.config import get_config

logger = logging.getLogger(__name__)


def is_quiet_hours() -> bool:
    """
    Check if current time is within quiet hours.
    Quiet hours are between alert_end_time and alert_start_time.
    
    Example: If start=08:00 and end=22:00, quiet hours are 22:00-08:00.
    """
    try:
        start_str = get_config("alert_start_time") or "08:00"
        end_str = get_config("alert_end_time") or "22:00"
        
        # Parse times
        start_hour, start_min = map(int, start_str.split(":"))
        end_hour, end_min = map(int, end_str.split(":"))
        
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        # Quiet hours are between end_time and start_time
        if end_minutes > start_minutes:
            # Normal case: e.g., 08:00-22:00 active, 22:00-08:00 quiet
            return current_minutes >= end_minutes or current_minutes < start_minutes
        else:
            # Overnight case: e.g., 22:00-08:00 active, 08:00-22:00 quiet
            return end_minutes <= current_minutes < start_minutes
            
    except Exception as e:
        logger.error(f"Quiet hours check failed: {e}")
        return False  # Default to allowing notifications


def broadcast_alert(alert_type: str, message: str, severity: str = "warning", data: Optional[dict] = None):
    """
    Broadcast an alert to the dashboard via WebSocket.
    
    Args:
        alert_type: Type of alert (stalled, temp, runaway, signal_loss, etc.)
        message: Human-readable message
        severity: 'info', 'warning', 'error', 'critical'
        data: Optional additional data
    """
    try:
        from app.extensions import socketio
        
        alert_payload = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        socketio.emit('anomaly_alert', alert_payload)
        logger.info(f"Broadcast alert: {alert_type} - {message[:50]}...")
        return {"status": "broadcast"}
        
    except Exception as e:
        logger.error(f"WebSocket broadcast failed: {e}")
        return {"error": str(e)}


def troubleshoot_tiltpi() -> dict:
    """
    Auto-troubleshoot TiltPi connectivity issues.
    Checks TiltPi service status and attempts reconnection.
    
    Returns diagnostic info and suggested actions.
    """
    tiltpi_url = get_config("tiltpi_url")
    results = {
        "status": "checking",
        "checks": [],
        "suggested_actions": []
    }
    
    # Check 1: TiltPi URL configured?
    if not tiltpi_url:
        results["checks"].append({"name": "tiltpi_url", "status": "missing"})
        results["suggested_actions"].append("Configure TiltPi URL in settings")
        results["status"] = "config_error"
        return results
    
    results["checks"].append({"name": "tiltpi_url", "status": "ok", "value": tiltpi_url})
    
    # Check 2: TiltPi reachable?
    try:
        # TiltPi typically runs Node-RED on port 1880
        health_url = tiltpi_url.rstrip('/') + '/flows'
        resp = requests.get(health_url, timeout=5)
        if resp.status_code == 200:
            results["checks"].append({"name": "tiltpi_reachable", "status": "ok"})
        else:
            results["checks"].append({"name": "tiltpi_reachable", "status": "error", "code": resp.status_code})
            results["suggested_actions"].append("TiltPi service may be down - check Node-RED")
    except requests.exceptions.ConnectionError:
        results["checks"].append({"name": "tiltpi_reachable", "status": "error", "error": "connection_refused"})
        results["suggested_actions"].append("TiltPi not responding - check if Raspberry Pi is online")
    except requests.exceptions.Timeout:
        results["checks"].append({"name": "tiltpi_reachable", "status": "error", "error": "timeout"})
        results["suggested_actions"].append("TiltPi responding slowly - check network")
    except Exception as e:
        results["checks"].append({"name": "tiltpi_reachable", "status": "error", "error": str(e)})
    
    # Check 3: Telegraf receiving data?
    try:
        from app.core.influx import query_api, INFLUX_BUCKET
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
            |> range(start: -5m)
            |> filter(fn: (r) => r["_measurement"] == "sensor_data")
            |> count()
        '''
        tables = query_api.query(query)
        count = 0
        for table in tables:
            for record in table.records:
                count = record.get_value() or 0
        
        if count > 0:
            results["checks"].append({"name": "data_flow", "status": "ok", "readings_5m": count})
        else:
            results["checks"].append({"name": "data_flow", "status": "no_data"})
            results["suggested_actions"].append("No data in last 5 min - check Tilt battery and orientation")
    except Exception as e:
        results["checks"].append({"name": "data_flow", "status": "error", "error": str(e)})
    
    # Determine overall status
    failed_checks = [c for c in results["checks"] if c.get("status") not in ["ok"]]
    if not failed_checks:
        results["status"] = "healthy"
    elif any(c.get("status") == "no_data" for c in results["checks"]):
        results["status"] = "data_issue"
    else:
        results["status"] = "connectivity_issue"
    
    return results


def send_telegram_message(message: str, force: bool = False) -> dict:
    """
    Send a message via Telegram.
    
    Args:
        message: The message text (supports Markdown)
        force: If True, ignore quiet hours and send anyway
        
    Returns:
        Dict with status or error
    """
    # Check quiet hours
    if not force and is_quiet_hours():
        logger.info("Telegram message skipped: quiet hours active")
        return {"status": "skipped", "reason": "quiet_hours"}
    
    token = get_config("alert_telegram_token")
    chat_id = get_config("alert_telegram_chat")
    
    if not token or not chat_id:
        logger.warning("Telegram credentials not set. Message skipped.")
        return {"error": "Telegram credentials not set"}
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            return {"status": "success"}
        else:
            logger.error(f"Telegram Error: {res.text}")
            return {"error": res.text}
    except Exception as e:
        logger.error(f"Telegram Exception: {e}")
        return {"error": str(e)}

