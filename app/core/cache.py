import os
import json
import time
import logging
import redis
from typing import Any, Dict, Optional

logger = logging.getLogger("BrewBrain.Cache")

class ResultCache:
    """Cache for heavy computation results, preferring Redis."""
    def __init__(self, ttl: int = 120):
        self.ttl = ttl
        self.redis_client = None
        
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory cache.")
                self.redis_client = None
        
        self._local_cache: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expiry = ttl or self.ttl
        if self.redis_client:
            try:
                # Use a simple string serialization for speed
                self.redis_client.setex(key, expiry, json.dumps(value))
                # Trigger a backup to local cache for resilience
                self._local_cache[key] = {
                    "value": value,
                    "expiry": time.time() + expiry
                }
                return
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        self._local_cache[key] = {
            "value": value,
            "expiry": time.time() + expiry
        }

    def get(self, key: str) -> Optional[Any]:
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        item = self._local_cache.get(key)
        if item and item["expiry"] > time.time():
            return item["value"]
        if item:
            del self._local_cache[key]
        return None

    def clear(self):
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        self._local_cache.clear()

# Global cache instance
cache = ResultCache(ttl=300) # 5 minute default TTL (matches Celery Beat)
