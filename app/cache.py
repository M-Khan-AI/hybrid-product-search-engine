"""Thread-safe in-memory LRU cache with hit/miss counters."""
import threading

from cachetools import LRUCache


class QueryCache:
    def __init__(self, maxsize: int):
        self._cache = LRUCache(maxsize=maxsize)
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        with self._lock:
            try:
                value = self._cache[key]   # reading also marks it "recently used"
            except KeyError:
                self.misses += 1
                return None
            self.hits += 1
            return value

    def set(self, key, value):
        with self._lock:
            self._cache[key] = value

    def clear(self):
        with self._lock:
            self._cache.clear()
            self.hits = self.misses = 0

    def stats(self) -> dict:
        with self._lock:
            return {"size": len(self._cache), "maxsize": self._cache.maxsize,
                    "hits": self.hits, "misses": self.misses}