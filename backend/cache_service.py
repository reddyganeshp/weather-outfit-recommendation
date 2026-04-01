
from __future__ import annotations
import hashlib
import json
import time
import threading
import logging

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300   # 5 minutes


class CacheService:
    def __init__(self, max_size: int = 512, ttl: int = DEFAULT_TTL):
        self._store: dict[str, tuple[dict, float]] = {}   # key → (value, expires_at)
        self._lock = threading.Lock()
        self._max_size = max_size
        self._ttl = ttl

    def make_key(self, temp: float, condition: str,
                 humidity: float, wind: float,
                 occasion: str, gender: str) -> str:
        raw = f"{round(temp)}|{condition}|{round(humidity)}|{round(wind)}|{occasion}|{gender}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str) -> dict | None:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: dict):
        with self._lock:
            if len(self._store) >= self._max_size:
                # Evict oldest entry
                oldest = min(self._store, key=lambda k: self._store[k][1])
                del self._store[oldest]
            self._store[key] = (value, time.time() + self._ttl)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)
