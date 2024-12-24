from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading

class CacheService:
    def __init__(self):
        self._cache = {}
        self._locks = {}
        self._global_lock = threading.Lock()
        self.default_ttl = timedelta(hours=3)  # 3 hours TTL
    
    def _get_lock(self, key: str) -> threading.Lock:
        """Get or create a lock for a specific key"""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and hasn't expired"""
        with self._get_lock(key):
            if key in self._cache:
                item = self._cache[key]
                if datetime.now() < item['expiry']:
                    return item['value']
                else:
                    # Clean up expired item
                    del self._cache[key]
                    if key in self._locks:
                        del self._locks[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Set value in cache with expiration"""
        expiry = datetime.now() + (ttl if ttl is not None else self.default_ttl)
        with self._get_lock(key):
            self._cache[key] = {
                'value': value,
                'expiry': expiry
            }
    
    def delete(self, key: str) -> None:
        """Remove item from cache"""
        with self._get_lock(key):
            if key in self._cache:
                del self._cache[key]
            if key in self._locks:
                del self._locks[key]
    
    def clear(self) -> None:
        """Clear all items from cache"""
        with self._global_lock:
            self._cache.clear()
            self._locks.clear()
    
    def cleanup_expired(self) -> None:
        """Remove all expired items from cache"""
        now = datetime.now()
        with self._global_lock:
            expired_keys = [
                key for key, item in self._cache.items()
                if now >= item['expiry']
            ]
            for key in expired_keys:
                self.delete(key)

# Create a global cache instance
cache = CacheService() 