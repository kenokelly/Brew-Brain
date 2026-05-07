from extensions import celery
from services.worker import process_data_once, check_alerts_once
from services.status import get_status_dict
from services.anomaly import run_all_anomaly_checks
from core.config import get_config
from core.cache import cache
import logging

logger = logging.getLogger("BrewBrain.Tasks")

@celery.task(name="services.tasks.process_sensor_data")
def process_sensor_data():
    """Background task to process sensor data and update status cache."""
    try:
        process_data_once()
        # Update the status cache after processing data
        status = get_status_dict()
        cache.set("system_status", status, ttl=300)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Process sensor data task failed: {e}")
        return {"status": "error", "message": str(e)}

@celery.task(name="services.tasks.check_fermentation_alerts")
def check_fermentation_alerts():
    """Background task to check fermentation alerts."""
    try:
        check_alerts_once()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Check fermentation alerts task failed: {e}")
        return {"status": "error", "message": str(e)}

@celery.task(name="services.tasks.run_anomaly_detection")
def run_anomaly_detection():
    """Background task to run anomaly detection and update cache."""
    try:
        batch_name = get_config("batch_name") or "Current Batch"
        result = run_all_anomaly_checks(batch_name)
        cache.set("anomaly_status", result, ttl=600)
        return {"status": "success", "alerts_sent": result.get("alerts_sent", 0)}
    except Exception as e:
        logger.error(f"Anomaly detection task failed: {e}")
        return {"status": "error", "message": str(e)}

@celery.task(name="ml.tasks.predict_batch_stats")
def predict_batch_stats():
    """Background task to run ML predictions and update cache."""
    try:
        from ml.prediction import predict_fg, predict_time_to_fg
        from ml.features import query_batch_data, calculate_sg_velocity, calculate_temp_variance, calculate_time_in_phase
        from core.config import get_all_config
        from datetime import datetime, timezone, timedelta
        import numpy as np

        config = get_all_config()
        og = float(config.get("og", 1.050))
        pitch_date_str = config.get("start_date")
        if not pitch_date_str:
            return {"status": "error", "message": "Missing start date"}

        # Date parsing logic
        try:
            if len(pitch_date_str) == 10:
                pitch_time = datetime.strptime(pitch_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                pitch_time = datetime.fromisoformat(pitch_date_str).replace(tzinfo=timezone.utc)
        except Exception:
            pitch_time = datetime.now(timezone.utc) - timedelta(days=7)

        now = datetime.now(timezone.utc)
        data = query_batch_data(pitch_time, now)
        velocity = calculate_sg_velocity(data["sg_readings"], data["sg_times"])
        variance = calculate_temp_variance(data["temp_readings"])
        avg_temp = np.mean(data["temp_readings"]) if data["temp_readings"] else 20.0
        days_elapsed = calculate_time_in_phase(pitch_time, now)
        
        style = config.get("style", "Unknown")
        yeast = config.get("yeast_strain", "Unknown")

        prediction_fg = predict_fg(og, velocity, variance, avg_temp, style, yeast)
        prediction_time = predict_time_to_fg(og, velocity, variance, avg_temp, days_elapsed, style, yeast)

        result = {
            "batch_metadata": {"og": og, "days_elapsed": days_elapsed, "data_points": data["data_points"], "style": style, "yeast": yeast},
            "features": {"velocity": velocity, "temp_variance": variance, "avg_temp": round(float(avg_temp), 1)},
            "prediction_fg": prediction_fg,
            "prediction_time": prediction_time,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        cache.set("ml_predictions", result, ttl=900)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"ML Prediction task failed: {e}")
        return {"status": "error", "message": str(e)}

@celery.task(name="services.tasks.recipe_ingest")
def recipe_ingest():
    """Weekly recipe ingestion from external sources."""
    try:
        from ml.scraper import ingest_all_sources
        result = ingest_all_sources()
        logger.info(f"Recipe ingestion complete: {result['total_inserted']} new")
        return result
    except Exception as e:
        logger.error(f"Recipe ingestion failed: {e}")
        return {"status": "error", "message": str(e)}

@celery.task(name="services.tasks.daily_board_report")
def daily_board_report():
    """Daily board telemetry report."""
    try:
        from services.telemetry import send_daily_board_report
        send_daily_board_report()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Daily board report failed: {e}")
        return {"status": "error", "message": str(e)}

@celery.task(name="services.tasks.maintenance_summary")
def maintenance_summary():
    """Weekly maintenance summary report."""
    try:
        from services.status import get_maintenance_summary
        from services.notifications import send_telegram_message
        summary = get_maintenance_summary()
        disk = summary.get("disk", {})
        msg = (
            "📊 *Brew Brain Weekly Maintenance*\n\n"
            f"💾 *Root Disk:* {disk.get('used_percent', '?')}% used\n"
            f"🌡️ *Pi Temp:* {summary.get('pi_temp', 0.0)}°C\n"
        )
        send_telegram_message(msg, force=True)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Maintenance summary failed: {e}")
        return {"status": "error", "message": str(e)}
