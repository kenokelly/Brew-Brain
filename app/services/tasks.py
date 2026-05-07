from extensions import celery
from services.worker import process_data_once, check_alerts_once
from services.telegram import telegram_poll_once
from services.status import get_status_dict
from services.anomaly import run_all_anomaly_checks
from core.config import get_config
import logging

logger = logging.getLogger("BrewBrain.Tasks")

@celery.task(name="services.tasks.process_sensor_data")
def process_sensor_data():
    """Background task to process sensor data."""
    try:
        process_data_once()
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
    """Background task to run anomaly detection."""
    try:
        batch_name = get_config("batch_name") or "Current Batch"
        result = run_all_anomaly_checks(batch_name)
        return {"status": "success", "alerts_sent": result.get("alerts_sent", 0)}
    except Exception as e:
        logger.error(f"Anomaly detection task failed: {e}")
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
