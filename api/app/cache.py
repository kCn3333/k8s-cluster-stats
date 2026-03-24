from cachetools import TTLCache

metrics_cache: TTLCache = TTLCache(maxsize=1, ttl=15)
