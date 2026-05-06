import os
from flask_socketio import SocketIO
from celery import Celery

socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

def make_celery(app_name=__name__):
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return Celery(
        app_name,
        backend=redis_url,
        broker=redis_url,
        include=['ml.tasks'] # We will create this
    )

celery = make_celery()
