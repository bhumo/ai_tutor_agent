"""Thread-safe local rate and concurrency limits with deterministic test hooks."""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int = 0


class SlidingWindowRateLimiter:
    """Sliding-window limiter suitable for one application process."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        if limit < 1 or window_seconds < 1:
            raise ValueError("rate-limit policy values must be positive")
        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, math.ceil(events[0] + window_seconds - now))
                return RateLimitDecision(False, retry_after)
            events.append(now)
            return RateLimitDecision(True)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


class ConcurrencyLimitExceeded(RuntimeError):
    pass


class ConcurrencyLimiter:
    def __init__(self):
        self._active: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    @contextmanager
    def acquire(self, key: str, limit: int) -> Iterator[None]:
        if limit < 1:
            raise ValueError("concurrency limit must be positive")
        with self._lock:
            if self._active[key] >= limit:
                raise ConcurrencyLimitExceeded(key)
            self._active[key] += 1
        try:
            yield
        finally:
            with self._lock:
                self._active[key] -= 1
                if self._active[key] == 0:
                    self._active.pop(key, None)

    def active(self, key: str) -> int:
        with self._lock:
            return self._active.get(key, 0)
