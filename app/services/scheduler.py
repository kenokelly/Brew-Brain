"""
APScheduler integration for Brew Brain.
Provides scheduled task management with persistence.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Scheduler configuration
jobstores = {
    'default': MemoryJobStore()
}

executors = {
    'default': ThreadPoolExecutor(max_workers=8)
}

job_defaults = {
    'coalesce': True,  # Combine missed runs into single run
    'max_instances': 1,  # Prevent overlapping job runs
    'misfire_grace_time': 60  # 60s grace for missed jobs
}

# Global scheduler instance
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='Europe/London'
)


def init_scheduler(app):
    """Initialize and start the scheduler with default jobs."""
    scheduler.app = app # Attach app for context usage elsewhere
    # Import the run-once versions of the tasks
    from services.worker import process_data_once, check_alerts_once
    from services.telegram import telegram_poll_once
    from services.status import get_status_dict
    from app.extensions import socketio

    def emit_status_update():
        """Fetch and broadcast system status via WebSocket."""
        try:
            status = get_status_dict()
            with scheduler.app.app_context():
                socketio.emit('status_update', status)
        except Exception as e:
            logger.error(f"WebSocket Emit Error: {e}")

    # Add recurring jobs
    # Real-time Status Emit (Every 5s)
    scheduler.add_job(
        emit_status_update,
        'interval',
        seconds=5,
        id='emit_status',
        name='Real-time Status',
        replace_existing=True
    )
    
    # Data processing every 60 seconds (matches the sleep in the original loop)
    scheduler.add_job(
        process_data_once,
        'interval',
        seconds=60,
        id='process_data',
        name='Process Sensor Data',
        replace_existing=True
    )
    
    # Alert checking every 300 seconds (5 min, matches original)
    scheduler.add_job(
        check_alerts_once,
        'interval',
        seconds=300,
        id='check_alerts',
        name='Check Fermentation Alerts',
        replace_existing=True
    )
    
    # Telegram polling every 35 seconds (long poll timeout + buffer)
    scheduler.add_job(
        telegram_poll_once,
        'interval',
        seconds=35,
        id='telegram_poller',
        name='Telegram Poller',
        replace_existing=True
    )
    
    # Anomaly detection every 5 minutes
    from app.services.anomaly import run_all_anomaly_checks
    from app.core.config import get_config
    
    def anomaly_check_job():
        """Run anomaly detection with current batch name."""
        try:
            batch_name = get_config("batch_name") or "Current Batch"
            result = run_all_anomaly_checks(batch_name)
            if result.get("alerts_sent", 0) > 0:
                logger.warning(f"Anomaly detection sent {result['alerts_sent']} alerts")
        except Exception as e:
            logger.error(f"Anomaly check error: {e}")
    
    # Real-time TiltPi Polling (Every 15s)
    from app.services.tilt_monitor import poll_tilt_api
    scheduler.add_job(
        poll_tilt_api,
        'interval',
        seconds=15,
        id='poll_tilt',
        name='Real-time Tilt Monitoring',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("APScheduler started with %d jobs", len(scheduler.get_jobs()))
    
    # Log registered jobs
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} ({job.id}): {job.trigger}")


def get_scheduler():
    """Get the scheduler instance."""
    return scheduler


def get_job_status():
    """Get status of all scheduled jobs for API/UI."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })
    return jobs


def add_scheduled_job(func, trigger, job_id, name, **trigger_args):
    """Add a new scheduled job dynamically."""
    scheduler.add_job(
        func,
        trigger,
        id=job_id,
        name=name,
        replace_existing=True,
        **trigger_args
    )
    logger.info(f"Added job: {name} ({job_id})")


def remove_job(job_id):
    """Remove a scheduled job."""
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Removed job: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to remove job {job_id}: {e}")
        return False


def pause_job(job_id):
    """Pause a scheduled job."""
    scheduler.pause_job(job_id)
    logger.info(f"Paused job: {job_id}")


def resume_job(job_id):
    """Resume a paused job."""
    scheduler.resume_job(job_id)
    logger.info(f"Resumed job: {job_id}")
