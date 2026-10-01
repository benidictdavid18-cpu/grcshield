"""Bounded per-user/feature calls and in-flight inference in this server process."""

import threading
import time
from collections import deque
from contextlib import contextmanager

from fastapi import HTTPException

from app.core.config import get_settings


class InferenceLimits:
    def __init__(self):
        self.lock = threading.Lock()
        self.calls = {}
        self.active = 0

    def reset(self):
        with self.lock:
            self.calls.clear()
            self.active = 0

    @contextmanager
    def acquire(self, username, feature):
        settings = get_settings()
        now = time.monotonic()
        with self.lock:
            for key in list(self.calls):
                stamps = self.calls[key]
                while stamps and stamps[0] <= now - settings.ai_rate_window_seconds:
                    stamps.popleft()
                if not stamps:
                    del self.calls[key]
            key = (username, feature)
            stamps = self.calls.setdefault(key, deque())
            if (
                len(stamps) >= settings.ai_request_limit
                or self.active >= settings.ai_concurrency_limit
            ):
                raise HTTPException(
                    429,
                    "AI capacity limit reached; retry later.",
                    headers={"Retry-After": str(settings.ai_rate_window_seconds)},
                )
            stamps.append(now)
            self.active += 1
        try:
            yield
        finally:
            with self.lock:
                self.active -= 1


inference_limits = InferenceLimits()
