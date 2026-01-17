from functools import wraps
from flask import jsonify
import logging
import traceback
import time

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


def retry_with_backoff(retries=3, backoff_base=1.0, exceptions=(Exception,)):
    """
    Decorator for resilient external calls with exponential backoff.
    
    Usage:
        @retry_with_backoff(retries=3, backoff_base=1.0)
        def call_external_api():
            ...
    
    Args:
        retries: Maximum number of retry attempts
        backoff_base: Base delay in seconds (doubles each retry)
        exceptions: Tuple of exception types to catch and retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries - 1:
                        delay = backoff_base * (2 ** attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{retries} for {func.__name__} "
                            f"after {delay:.1f}s delay. Error: {str(e)}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {retries} retries exhausted for {func.__name__}. "
                            f"Final error: {str(e)}"
                        )
            raise last_exception
        return wrapper
    return decorator
