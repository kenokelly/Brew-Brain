import requests
import logging
from app.core.config import get_config

logger = logging.getLogger(__name__)

def send_telegram_message(message):
    token = get_config("alert_telegram_token")
    chat_id = get_config("alert_telegram_chat")
    
    if not token or not chat_id:
        logger.warning("Telegram credentials not set. Message skipped.")
        return {"error": "Telegram credentials not set"}
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            return {"status": "success"}
        else:
            logger.error(f"Telegram Error: {res.text}")
            return {"error": res.text}
    except Exception as e:
        logger.error(f"Telegram Exception: {e}")
        return {"error": str(e)}
