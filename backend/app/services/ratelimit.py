"""A simple sliding-window limit kept in memory. It works for one server process (the current Render plan runs one
worker). It resets when the server restarts, so it slows down abuse but is not a full defence on its own."""
import time
from collections import defaultdict, deque

_hits = defaultdict(deque)


def allow(key, limit, window_seconds):
    now = time.time()
    hits = _hits[key]
    while hits and now - hits[0] > window_seconds:
        hits.popleft()
    if len(hits) >= limit:
        return False
    hits.append(now)
    return True


def reset():
    _hits.clear()
