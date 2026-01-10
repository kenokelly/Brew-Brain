import threading
import logging
from flask import Flask
from flask_cors import CORS
from waitress import serve
from core.config import refresh_config_from_influx, logger
from services.worker import process_data, check_alerts
from services.telegram import telegram_poller
from api.routes import api_bp
from api.automation import automation_bp

app = Flask(__name__, static_folder='static')
CORS(app)

# Register Blueprints
app.register_blueprint(api_bp)
app.register_blueprint(automation_bp)

if __name__ == '__main__':
    # Initialize Config from InfluxDB
    refresh_config_from_influx()
    
    # Start Background Threads
    threading.Thread(target=process_data, daemon=True).start()
    threading.Thread(target=check_alerts, daemon=True).start()
    threading.Thread(target=telegram_poller, daemon=True).start()
    
    logger.info("Starting Production Server (Waitress) on port 5000...")
    serve(app, host='0.0.0.0', port=5000)
