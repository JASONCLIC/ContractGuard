from collections import defaultdict
from time import time

_bucket = defaultdict(list)


def check_limit(key: str, limit=10, window_sec=60) -> bool:
    now = time()
    records = _bucket[key]
    records[:] = [t for t in records if now - t < window_sec]
    if len(records) >= limit:
        return False
    records.append(now)
    return True
