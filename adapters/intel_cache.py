"""
EAON 2.0 — Intel Cache
=======================
Redis-backed caching for threat intelligence lookups.
Falls back to in-memory LRU cache if Redis unavailable.
"""

import json
import time
import hashlib
from typing import Optional, Any
from functools import lru_cache
from dataclasses import dataclass, field
from datetime import datetime

from config import get_settings
from utils import get_logger

logger = get_logger("intel_cache")


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    evictions: int = 0
    size: int = 0
    backend: str = "none"
    last_reset: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def to_dict(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "evictions": self.evictions,
            "size": self.size,
            "hit_rate_percent": round(self.hit_rate, 2),
            "backend": self.backend,
            "last_reset": self.last_reset.isoformat(),
        }


class IntelCache:
    """
    Hybrid cache for intel lookups.
    Uses Redis if available, falls back to in-memory LRU.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
        self.stats = CacheStats()
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        self._max_memory_items = 1000
        
        self._init_redis()
    
    def _init_redis(self) -> None:
        """Initialize Redis connection if enabled."""
        if not self.settings.redis.enabled:
            self.stats.backend = "memory"
            logger.info("cache_init", backend="memory", reason="redis_disabled")
            return
        
        try:
            import redis
            self.redis_client = redis.Redis(
                host=self.settings.redis.host,
                port=self.settings.redis.port,
                db=self.settings.redis.db,
                password=self.settings.redis.password,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            # Test connection
            self.redis_client.ping()
            self.stats.backend = "redis"
            logger.info("cache_init", backend="redis", host=self.settings.redis.host)
        except ImportError:
            logger.warning("cache_init", backend="memory", reason="redis_not_installed")
            self.stats.backend = "memory"
        except Exception as e:
            logger.warning("cache_init", backend="memory", reason=str(e))
            self.redis_client = None
            self.stats.backend = "memory"
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments."""
        raw = ":".join(str(a) for a in args)
        hash_suffix = hashlib.md5(raw.encode()).hexdigest()[:12]
        return f"{self.settings.intel.cache_prefix}{prefix}:{hash_suffix}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        # Try Redis first
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    self.stats.hits += 1
                    return json.loads(data)
                self.stats.misses += 1
                return None
            except Exception as e:
                self.stats.errors += 1
                logger.debug("cache_get_error", key=key, error=str(e))
                # Fall through to memory cache
        
        # Memory cache fallback
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if expiry > time.time():
                self.stats.hits += 1
                return value
            else:
                # Expired
                del self._memory_cache[key]
                self.stats.evictions += 1
        
        self.stats.misses += 1
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default from settings)
        
        Returns:
            True if successful
        """
        ttl = ttl or self.settings.intel.cache_ttl_seconds
        
        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                self.stats.size = self._get_redis_size()
                return True
            except Exception as e:
                self.stats.errors += 1
                logger.debug("cache_set_error", key=key, error=str(e))
                # Fall through to memory cache
        
        # Memory cache fallback
        self._memory_cache_set(key, value, ttl)
        return True
    
    def _memory_cache_set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in memory cache with LRU eviction."""
        # Evict if at capacity
        if len(self._memory_cache) >= self._max_memory_items:
            self._evict_oldest()
        
        expiry = time.time() + ttl
        self._memory_cache[key] = (value, expiry)
        self.stats.size = len(self._memory_cache)
    
    def _evict_oldest(self) -> None:
        """Evict oldest entries from memory cache."""
        if not self._memory_cache:
            return
        
        # Sort by expiry time and remove oldest 10%
        sorted_keys = sorted(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k][1]
        )
        
        evict_count = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:evict_count]:
            del self._memory_cache[key]
            self.stats.evictions += 1
    
    def _get_redis_size(self) -> int:
        """Get approximate Redis cache size."""
        if not self.redis_client:
            return 0
        try:
            prefix = f"{self.settings.intel.cache_prefix}*"
            return len(list(self.redis_client.scan_iter(match=prefix, count=100)))
        except Exception:
            return 0
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
        
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        return True
    
    def clear(self, prefix: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            prefix: Optional prefix to match (clears all if None)
        
        Returns:
            Number of entries cleared
        """
        count = 0
        pattern = f"{self.settings.intel.cache_prefix}{prefix or ''}*"
        
        if self.redis_client:
            try:
                keys = list(self.redis_client.scan_iter(match=pattern, count=1000))
                if keys:
                    count = self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning("cache_clear_error", error=str(e))
        
        # Clear memory cache
        if prefix:
            to_delete = [k for k in self._memory_cache if k.startswith(pattern.rstrip("*"))]
        else:
            to_delete = list(self._memory_cache.keys())
        
        for key in to_delete:
            del self._memory_cache[key]
            count += 1
        
        self.stats.size = len(self._memory_cache)
        return count
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        if self.redis_client:
            self.stats.size = self._get_redis_size()
        else:
            self.stats.size = len(self._memory_cache)
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self.stats = CacheStats(
            backend=self.stats.backend,
            size=self.stats.size,
        )


# Singleton instance
_cache: Optional[IntelCache] = None


def get_cache() -> IntelCache:
    """Get or create cache singleton."""
    global _cache
    if _cache is None:
        _cache = IntelCache()
    return _cache


def cache_stats() -> dict:
    """Get cache stats as dict (for API endpoints)."""
    return get_cache().get_stats().to_dict()


# Convenience decorators
def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorator to cache function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Optional TTL override
    
    Usage:
        @cached("geoip")
        def lookup_geoip(ip: str) -> dict:
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Build key from args
            key_parts = [str(a) for a in args]
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = cache._make_key(prefix, *key_parts)
            
            # Check cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
