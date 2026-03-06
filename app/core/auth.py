import os
import secrets
from functools import wraps
from flask import request, jsonify
from app.core.config import logger

# Initialize the critical API token from environment, or generate a secure random one if missing
API_TOKEN = os.environ.get("BREW_BRAIN_API_TOKEN")

if not API_TOKEN:
    # Fail-close approach: If the user forgets to set a token, do NOT leave the API open.
    # We generate a random one and log it prominently so the user can easily find it on first boot.
    API_TOKEN = secrets.token_hex(16)
    logger.critical("="*60)
    logger.critical("SECURITY WARNING: BREW_BRAIN_API_TOKEN environment variable not set!")
    logger.critical(f"A temporary secure token has been generated for this session: {API_TOKEN}")
    logger.critical("Please set BREW_BRAIN_API_TOKEN in your docker-compose.yml or environment.")
    logger.critical("="*60)
else:
    logger.info("API Authentication Token successfully loaded from environment.")

def require_api_token(f):
    """
    Flask decorator that enforces API token authentication.
    The token can be passed via:
    1. HTTP Header: 'Authorization: Bearer <token>'
    2. Query Parameter: '?token=<token>'
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        supplied_token = None
        
        # 1. Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            supplied_token = auth_header.split(' ')[1]
            
        # 2. Check Query String Token (useful for simple web UI initial integrations)
        if not supplied_token:
            supplied_token = request.args.get('token')
            
        # 3. Validate
        if not supplied_token or supplied_token != API_TOKEN:
            logger.warning(f"Unauthorized API access attempt from {request.remote_addr} to {request.path}")
            return jsonify({"status": "error", "message": "Unauthorized: Invalid or missing API token."}), 401
            
        return f(*args, **kwargs)
        
    return decorated
