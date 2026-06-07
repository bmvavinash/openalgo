"""
Quote Cache Service
Provides caching for quotes to reduce API calls and improve performance
"""
import time
from typing import Dict, Tuple, Optional
from threading import Lock
from utils.logging import get_logger

logger = get_logger(__name__)

class QuoteCache:
    """Thread-safe quote cache with TTL"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._cache: Dict[Tuple[str, str], Dict] = {}  # (symbol, exchange) -> {quote, timestamp}
        self._cache_lock = Lock()
        self._default_ttl = 5  # 5 seconds default TTL
        self._max_cache_size = 1000  # Maximum number of cached quotes
        
        self._initialized = True
        logger.info("Quote cache initialized")
    
    def get(self, symbol: str, exchange: str, ttl: Optional[int] = None) -> Optional[Dict]:
        """
        Get cached quote if available and not expired
        
        Args:
            symbol: Symbol name
            exchange: Exchange name
            ttl: Time-to-live in seconds (uses default if None)
        
        Returns:
            Cached quote dict or None if not found/expired
        """
        cache_key = (symbol.upper(), exchange.upper())
        ttl = ttl or self._default_ttl
        
        with self._cache_lock:
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                age = time.time() - cached_data.get('timestamp', 0)
                
                if age < ttl:
                    logger.debug(f"Cache HIT for {symbol} on {exchange} (age: {age:.1f}s)")
                    return cached_data.get('quote')
                else:
                    # Expired, remove from cache
                    del self._cache[cache_key]
                    logger.debug(f"Cache EXPIRED for {symbol} on {exchange} (age: {age:.1f}s)")
        
        logger.debug(f"Cache MISS for {symbol} on {exchange}")
        return None
    
    def set(self, symbol: str, exchange: str, quote: Dict, ttl: Optional[int] = None):
        """
        Cache a quote
        
        Args:
            symbol: Symbol name
            exchange: Exchange name
            quote: Quote data to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        cache_key = (symbol.upper(), exchange.upper())
        
        with self._cache_lock:
            # Remove oldest entries if cache is too large
            if len(self._cache) >= self._max_cache_size:
                # Remove oldest 10% of entries
                sorted_items = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].get('timestamp', 0)
                )
                to_remove = int(self._max_cache_size * 0.1)
                for key, _ in sorted_items[:to_remove]:
                    del self._cache[key]
                logger.debug(f"Cache cleanup: removed {to_remove} oldest entries")
            
            self._cache[cache_key] = {
                'quote': quote,
                'timestamp': time.time()
            }
            logger.debug(f"Cached quote for {symbol} on {exchange}")
    
    def clear(self):
        """Clear all cached quotes"""
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Quote cache cleared ({count} entries)")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self._cache_lock:
            return {
                'size': len(self._cache),
                'max_size': self._max_cache_size,
                'default_ttl': self._default_ttl
            }

# Global cache instance
quote_cache = QuoteCache()








