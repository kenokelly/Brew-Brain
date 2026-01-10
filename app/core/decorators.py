from functools import wraps
from flask import jsonify
import logging
import traceback

logger = logging.getLogger(__name__)

class AppError(Exception):
    """Custom Base Exception for Application Errors"""
    def __init__(self, message, code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.payload = payload

def api_safe(f):
    """
    Decorator to wrap API endpoints.
    Catches ALL exceptions, logs trace, and returns standardized JSON error.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AppError as e:
            # Trusted Application Error
            logger.warning(f"AppError in {f.__name__}: {str(e)}")
            return jsonify({
                "status": "error",
                "code": e.code,
                "message": e.message,
                "data": e.payload
            }), e.code
        except Exception as e:
            # Unexpected Crash
            trace = traceback.format_exc()
            logger.error(f"CRITICAL ERROR in {f.__name__}: {str(e)}\n{trace}")
            return jsonify({
                "status": "fatal",
                "code": 500,
                "message": "Internal System Error",
                "debug_error": str(e)
            }), 500
    return decorated_function
