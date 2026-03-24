"""
cache.py — The Tech Brief V3
Article cache with TTL support. Prevents redundant API calls.
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("techbrief.cache")

ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE_FILE = os.path.join(ROOT, 'data', 'article_cache_v3.json')
CACHE_TTL_DAYS = 30  # Regenerate after 30 days


class ArticleCache:
    def __init__(self, cache_file: str = CACHE_FILE, ttl_days: int = CACHE_TTL_DAYS):
        self.cache_file = cache_file
        self.ttl = timedelta(days=ttl_days)
        self._data: dict = {}
        self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                logger.debug("Cache loaded: %d entries", len(self._data))
            except Exception as e:
                logger.warning("Cache load failed: %s — starting fresh", e)
                self._data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _is_fresh(self, entry: dict) -> bool:
        cached_at = entry.get("cached_at", "2000-01-01T00:00:00+00:00")
        try:
            dt = datetime.fromisoformat(cached_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt) < self.ttl
        except Exception:
            return False

    def get(self, key: str) -> dict | None:
        entry = self._data.get(key)
        if entry and self._is_fresh(entry):
            logger.debug("Cache HIT: %s", key[:16])
            return entry.get("data")
        if entry:
            logger.debug("Cache STALE: %s", key[:16])
        return None

    def set(self, key: str, data: dict):
        self._data[key] = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        self._save()
        logger.debug("Cache SET: %s", key[:16])

    def invalidate(self, key: str):
        if key in self._data:
            del self._data[key]
            self._save()

    def clear_stale(self):
        stale_keys = [k for k, v in self._data.items() if not self._is_fresh(v)]
        for k in stale_keys:
            del self._data[k]
        if stale_keys:
            self._save()
            logger.info("Cleared %d stale cache entries", len(stale_keys))

    def stats(self) -> dict:
        fresh  = sum(1 for v in self._data.values() if self._is_fresh(v))
        stale  = len(self._data) - fresh
        return {"total": len(self._data), "fresh": fresh, "stale": stale}
