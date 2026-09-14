"""Failed-login throttling for ``/auth/token``.

bcrypt at cost 12 makes each guess expensive, but expensive is not the same as
bounded. This tracker counts *failures* per (client address, username) inside a sliding
window and refuses further attempts with ``429`` and a ``Retry-After`` once the limit is
reached. A successful login clears the key.

Why failures rather than attempts: a user who types their password correctly ten times
in a minute is not an attack, and counting them would turn a busy demo into a lockout.

Why (address, username) rather than either alone: keyed on the address only, one
attacker behind a NAT locks out everyone behind it; keyed on the username only, an
attacker can lock a victim out on purpose. The pair bounds one client's guesses at one
account, which is the case that matters, and leaves the others to the account-level
lockout SECURITY.md still lists as absent.

In-process, so it resets on restart and is per-worker under a multi-process server.
That is a known limit, stated in SECURITY.md; a shared store is the production step.
"""

import threading
from collections import defaultdict, deque


class FailureTracker:
    def __init__(self) -> None:
        self._failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: tuple[str, str], now: float, window: float) -> deque[float]:
        stamps = self._failures[key]
        while stamps and stamps[0] <= now - window:
            stamps.popleft()
        return stamps

    def retry_after(
        self, key: tuple[str, str], *, now: float, limit: int, window: float
    ) -> int | None:
        """Seconds until the next attempt is allowed, or None if it is allowed now."""
        with self._lock:
            stamps = self._prune(key, now, window)
            if len(stamps) < limit:
                return None
            return max(1, int(stamps[0] + window - now) + 1)

    def record_failure(self, key: tuple[str, str], *, now: float) -> None:
        with self._lock:
            self._failures[key].append(now)

    def clear(self, key: tuple[str, str]) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_failures = FailureTracker()
