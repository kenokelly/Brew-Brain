import eventlet
eventlet.monkey_patch()

import os
import logging
from flask import Flask
from flask_cors import CORS
from core.config import load_initial_config, logger
from extensions import socketio
from api.routes import api_bp
from api.automation import automation_bp
from api.settings import settings_bp
from api.batches import batches_bp
from api.taps import taps_bp
from api.untappd import untappd_bp
from api.kiosk import kiosk_bp
from api.ml import ml_bp
from api.ai import ai_bp
from api.calculators import calc_bp
from api.water import water_bp
from api.labels import labels_bp

app = Flask(__name__, static_folder='static')
CORS(app)
socketio.init_app(app, 
    cors_allowed_origins="*", 
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    engineio_logger=True # Enable for debugging connection issues
)

# Register Blueprints
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(automation_bp)
app.register_blueprint(settings_bp, url_prefix='/api')
app.register_blueprint(batches_bp, url_prefix='/api')
app.register_blueprint(taps_bp, url_prefix='/api')
app.register_blueprint(untappd_bp, url_prefix='/api/untappd')
app.register_blueprint(kiosk_bp, url_prefix='/api/kiosk')
app.register_blueprint(ml_bp, url_prefix='/api/ml')
app.register_blueprint(ai_bp, url_prefix='/api/ai')
app.register_blueprint(calc_bp, url_prefix='/api/calculator')
app.register_blueprint(water_bp, url_prefix='/api/water')
app.register_blueprint(labels_bp, url_prefix='/api/label')

@app.after_request
def add_header(response):
    """Disable caching for all routes to ensure frontend updates."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    # Initialize Config (Local File with InfluxDB fallback)
    load_initial_config()
    
    # DEBUG: Add Rotating File Handler to Logger
    try:
        from logging.handlers import RotatingFileHandler
        os.makedirs('/data', exist_ok=True)
        file_handler = RotatingFileHandler('/data/app_debug.log', maxBytes=5*1024*1024, backupCount=3)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        logger.info("Rotating Debug File Handler Initialized at /data/app_debug.log")
    except Exception as e:
        print(f"Failed to init debug log: {e}")

    # Initialize APScheduler (replaces manual threading)
    from services.scheduler import init_scheduler
    init_scheduler(app)
    
    logger.info("Starting Production Server (SocketIO/Eventlet) on port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000)
