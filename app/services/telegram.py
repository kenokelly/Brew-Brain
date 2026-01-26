import time
import requests
import logging
from app.core.config import get_config
from services.status import get_status_dict

logger = logging.getLogger("BrewBrain")

def send_telegram(msg, target_chat=None):
    token = get_config("alert_telegram_token")
    chat = target_chat or get_config("alert_telegram_chat")
    if not token or not chat: return
    try: 
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage", 
            json={"chat_id": chat, "text": msg, "parse_mode": "Markdown"}, 
            timeout=5
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram: {e}")

def handle_telegram_command(chat_id, command, text):
    cmd = command.lower().strip()
    if cmd == "/status":
        s = get_status_dict()
        sg = s.get('sg', 0) or 0
        temp = s.get('temp', 0) or 0
        og = s.get('og', 0)
        fg = s.get('target_fg', 0)
        abv = max(0, (og - sg) * 131.25) if sg > 0 else 0
        
        msg = (
            f"🍺 *Brew Brain Status*\n"
            f"🏷 *Batch:* {s.get('batch_name') or 'No Active Batch'}\n"
            f"🌡 *Temp:* {temp:.1f}°C\n"
            f"⚖️ *Gravity:* {sg:.3f} (Target: {fg:.3f})\n"
            f"📊 *ABV:* {abv:.1f}%\n"
            f"📡 *Tilt:* {s.get('rssi') or '--'} dBm (Seen: {s.get('last_sync') or 'Never'})\n"
            f"💾 *CPU:* {s.get('pi_temp')}°C"
        )
        send_telegram(msg, chat_id)
    elif cmd == "/help":
        send_telegram("Commands: /status, /ping", chat_id)
    elif cmd == "/ping":
        send_telegram("Pong", chat_id)

def telegram_poller():
    logger.info("Telegram Poller Started")
    last_update_id = 0
    while True:
        token = get_config("alert_telegram_token")
        if not token:
            time.sleep(30)
            continue
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            resp = requests.get(url, params=params, timeout=35)
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get("result", []):
                    last_update_id = result["update_id"]
                    message = result.get("message", {})
                    text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")
                    
                    configured_chat = get_config("alert_telegram_chat")
                    if str(chat_id) != str(configured_chat):
                        continue
                    if text.startswith("/"):
                        parts = text.split(" ", 1)
                        cmd = parts[0]
                        payload = parts[1] if len(parts) > 1 else ""
                        handle_telegram_command(chat_id, cmd, payload)
        except Exception as e:
            logger.error(f"Telegram Poll Error: {e}")
            time.sleep(15)


# Global state for poll_once
_last_update_id = 0


def telegram_poll_once():
    """Single execution of Telegram polling for APScheduler."""
    global _last_update_id
    
    token = get_config("alert_telegram_token")
    if not token:
        return
        
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {"offset": _last_update_id + 1, "timeout": 2}
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for result in data.get("result", []):
                _last_update_id = result["update_id"]
                message = result.get("message", {})
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")
                
                configured_chat = get_config("alert_telegram_chat")
                if str(chat_id) != str(configured_chat):
                    continue
                if text.startswith("/"):
                    parts = text.split(" ", 1)
                    cmd = parts[0]
                    payload = parts[1] if len(parts) > 1 else ""
                    handle_telegram_command(chat_id, cmd, payload)
    except Exception as e:
        logger.error(f"Telegram Poll Error: {e}")
