import logging
from datetime import datetime, date, timedelta
from services import alerts
from services.hop_math import calculate_hop_freshness
from extensions import celery
from core.cache import cache

logger = logging.getLogger(__name__)

@celery.task(bind=True, max_retries=3, name="services.inventory.fetch_inventory_with_backoff")
def fetch_inventory_with_backoff(self, base_delay=1):
    """
    Fetches inventory from Brewfather, handling 429 Rate Limit errors 
    with exponential backoff using Celery.
    """
    try:
        inv = alerts.fetch_brewfather_inventory()
        
        if isinstance(inv, dict) and 'error' in inv:
            if '429' in str(inv['error']):
                delay = base_delay * (2 ** self.request.retries)
                logger.warning(f"Rate limited (429). Celery retrying in {delay} seconds...")
                raise self.retry(countdown=delay)
            else:
                return inv # Other errors (401, 500)
        
        cache.set("raw_inventory", inv, ttl=86400)
        return {"status": "success", "message": "Inventory successfully synced"}
        
    except Exception as e:
        from celery.exceptions import Retry
        if isinstance(e, Retry):
            raise
        logger.error(f"Inventory sync error: {e}")
        return {"error": str(e)}

def get_processed_inventory():
    """
    Fetches the raw inventory from cache and applies data transformations:
    1. HSI Alpha Acid Degradation for Hops
    2. Threshold alerts (low stock)
    """
    raw_inv = cache.get("raw_inventory")
    if not raw_inv:
        return {"error": "No inventory synced. Please trigger a sync."}
    if 'error' in raw_inv:
        return raw_inv
        
    processed = {
        "hops": [],
        "fermentables": [],
        "yeast": [],
        "salts": [],
        "misc": []
    }
    
    # Process Hops with HSI Degradation
    # We assume a default age of 6 months if purchase date isn't recorded locally,
    # and default freezer storage.
    default_purchase_date = (date.today() - timedelta(days=180)).strftime("%Y-%m-%d")
    
    for hop_name, amount_g in raw_inv.get('hops', {}).items():
        # Default alpha acid assumption for degradation calc if unknown
        # In a real scenario, this would come from the local DB or Brewfather
        original_alpha = 10.0 
        
        freshness_data = calculate_hop_freshness(
            hop_name=hop_name,
            original_alpha=original_alpha,
            purchase_date=default_purchase_date,
            storage_condition="freezer"
        )
        
        processed["hops"].append({
            "name": hop_name.title(),
            "amount_g": amount_g,
            "original_alpha": original_alpha,
            "current_alpha": freshness_data["current_alpha"],
            "alpha_loss_pct": freshness_data["alpha_loss_pct"],
            "freshness": freshness_data.get("freshness", "Unknown"),
            "low_stock_alert": amount_g < 100 # Alert if less than 100g
        })
        
    # Process Fermentables
    for name, amount_kg in raw_inv.get('fermentables', {}).items():
        processed["fermentables"].append({
            "name": name.title(),
            "amount_kg": round(amount_kg, 2),
            "low_stock_alert": amount_kg < 5.0 # Alert if less than 5kg
        })
        
    # Process Yeasts
    for name, amount_pkgs in raw_inv.get('yeast', {}).items():
        processed["yeast"].append({
            "name": name.title(),
            "amount": amount_pkgs,
            "low_stock_alert": amount_pkgs < 2
        })
        
    # Process Salts & Misc
    for name, amt in raw_inv.get('salts', {}).items():
        processed["salts"].append({"name": name.title(), "amount_g": amt})
        
    for name, amt in raw_inv.get('misc', {}).items():
        processed["misc"].append({"name": name.title(), "amount": amt})
        
    return processed
