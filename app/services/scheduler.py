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


def _emit_status_update():
    """Fetch and broadcast system status via WebSocket."""
    from services.status import get_status_dict
    from extensions import socketio
    try:
        status = get_status_dict()
        # Use global socketio instance directly
        socketio.emit('status_update', status)
    except Exception as e:
        # Silence this error during early startup as it's expected until server is fully ready
        if "NoneType" not in str(e):
            logger.error(f"WebSocket Emit Error: {e}")


def register_status_jobs(scheduler_instance):
    """Register jobs related to system status."""
    # Real-time Status Emit (Every 5s) - Kept in APScheduler for low latency
    scheduler_instance.add_job(
        _emit_status_update,
        'interval',
        seconds=5,
        id='emit_status',
        name='Real-time Status',
        replace_existing=True
    )


def init_scheduler(app):
    """Initialize and start the scheduler with default jobs."""
    scheduler.app = app # Attach app for context usage elsewhere

    # Register different job types
    register_status_jobs(scheduler)
    
    # Other periodic tasks (Processing, Alerts, ML, Reports) 
    # have been migrated to Celery Beat in extensions.py
    
    # Start the scheduler
    scheduler.start()
    logger.info("APScheduler started with status emission job")


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
