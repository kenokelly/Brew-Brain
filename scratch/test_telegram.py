from app.core.config import load_initial_config
load_initial_config()

from app.services.notifications import send_telegram_message
print("Result:", send_telegram_message("Test message from dev script", force=True))
