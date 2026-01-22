import logging
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from app.core.config import refresh_config_from_influx, logger
from app.extensions import socketio
from api.routes import api_bp
from api.automation import automation_bp

app = Flask(__name__, static_folder='static')
CORS(app)
socketio.init_app(app)

# Register Blueprints
app.register_blueprint(api_bp)
app.register_blueprint(automation_bp)

if __name__ == '__main__':
    # Initialize Config from InfluxDB
    refresh_config_from_influx()
    
    # Initialize APScheduler (replaces manual threading)
    from services.scheduler import init_scheduler
    init_scheduler(app)
    
    logger.info("Starting Production Server (SocketIO/Eventlet) on port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000)
