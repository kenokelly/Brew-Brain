import os
from flask_socketio import SocketIO
from celery import Celery
from core.config import load_initial_config

# Ensure config is loaded (crucial for workers)
load_initial_config()

socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

def make_celery(app_name=__name__):
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    celery = Celery(
        app_name,
        backend=redis_url,
        broker=redis_url,
        include=['ml.tasks', 'services.tasks']
    )
    
    # Configure periodic tasks (Beat schedule)
    from celery.schedules import crontab
    celery.conf.beat_schedule = {
        'process-sensor-data': {
            'task': 'services.tasks.process_sensor_data',
            'schedule': 60.0,
        },
        'check-fermentation-alerts': {
            'task': 'services.tasks.check_fermentation_alerts',
            'schedule': 300.0,
        },
        'run-anomaly-detection': {
            'task': 'services.tasks.run_anomaly_detection',
            'schedule': 300.0,
        },
        'predict-batch-stats': {
            'task': 'ml.tasks.predict_batch_stats',
            'schedule': 300.0,
        },
        'daily-report-weekday': {
            'task': 'services.tasks.daily_board_report',
            'schedule': crontab(day_of_week='1-5', hour=8, minute=30),
        },
        'daily-report-weekend': {
            'task': 'services.tasks.daily_board_report',
            'schedule': crontab(day_of_week='0,6', hour=11, minute=0),
        },
        'recipe-ingest-weekly': {
            'task': 'services.tasks.recipe_ingest',
            'schedule': crontab(day_of_week=0, hour=3, minute=0),
        },
        'maintenance-summary-weekly': {
            'task': 'services.tasks.maintenance_summary',
            'schedule': crontab(day_of_week=1, hour=8, minute=0),
        },
        'train-prediction-models': {
            'task': 'ml.tasks.train_prediction_models',
            'schedule': 86400.0,
        }
    }
    
    return celery

celery = make_celery()
