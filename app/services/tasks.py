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

@celery.task(name="services.tasks.predict_batch_stats")
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
        send_telegram_message(msg, category="report", force=False)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Maintenance summary failed: {e}")
        return {"status": "error", "message": str(e)}

@celery.task(name="services.tasks.sync_brewfather")
def sync_brewfather():
    """Daily sync of completed batches from Brewfather."""
    try:
        from services.batch_exporter import get_completed_batches, export_batch_to_parquet, aggregate_training_data
        from datetime import datetime, timezone, timedelta
        
        batches = get_completed_batches()
        if not isinstance(batches, list):
            return {"status": "error", "message": str(batches)}
            
        count = 0
        for b in batches:
            try:
                # Basic extraction logic
                bid = b.get('_id')
                name = b.get('name', 'Unknown')
                start_ms = b.get('brewDate', 0)
                start_dt = datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc)
                # Estimate 14 days for fermentation if not defined
                end_dt = start_dt + timedelta(days=14)
                
                recipe = b.get('recipe', {})
                og = recipe.get('og', 1.050)
                fg = recipe.get('fg', 1.010)
                style = recipe.get('style', {}).get('name', 'Unknown')
                yeasts = recipe.get('yeasts', [])
                yeast_name = yeasts[0].get('name', 'Unknown') if yeasts else 'Unknown'
                
                res = export_batch_to_parquet(bid, name, start_dt, end_dt, og, fg, yeast_name, style)
                if res.get("status") == "success":
                    count += 1
            except Exception as inner_e:
                logger.warning(f"Failed to export batch {b.get('_id')}: {inner_e}")
        
        if count > 0:
            aggregate_training_data()
            
        return {"status": "success", "synced_batches": count}
    except Exception as e:
        logger.error(f"Brewfather sync failed: {e}")
        return {"status": "error", "message": str(e)}

@celery.task(name="services.tasks.run_monte_carlo_simulation")
def run_monte_carlo_task(target_og, yeast_name, mash_temp_c):
    """Background task to run the Monte Carlo simulation."""
    try:
        from services.learning import run_monte_carlo_simulation
        result = run_monte_carlo_simulation(target_og, yeast_name, mash_temp_c)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Monte Carlo simulation failed: {e}")
        return {"status": "error", "message": str(e)}
