"""
Token Bucket Rate Limiter
=========================
Thread-safe token-bucket implementation for API call and dispatch throttling.

Architecture Decision:
- Token bucket chosen over fixed-window for smoother rate distribution
- Separate instances for LLM API calls and dispatch to prevent one from starving the other
- Blocking (acquire) and non-blocking (try_acquire) modes for flexibility
"""

import threading
import time


class TokenBucket:
    """Token-bucket rate limiter.

    Args:
        max_tokens: Maximum burst capacity (tokens available immediately).
        refill_rate: Tokens added per second (sustained rate).
    """

    def __init__(self, max_tokens: int, refill_rate: float) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")

        self.max_tokens: int = max_tokens
        self.refill_rate: float = refill_rate
        self._tokens: float = float(max_tokens)
        self._last_refill: float = time.monotonic()
        self._lock: threading.Lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_tokens, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def acquire(self, timeout: float | None = None) -> bool:
        """Block until a token is available.

        Args:
            timeout: Maximum seconds to wait. None = wait forever.

        Returns:
            True if token acquired, False if timeout expired.
        """
        deadline = time.monotonic() + timeout if timeout else None

        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True

            if deadline and time.monotonic() >= deadline:
                return False

            # Sleep for the minimum time until next token arrives
            wait_time = (1.0 - self._tokens) / self.refill_rate
            time.sleep(min(wait_time, 0.1))

    def try_acquire(self) -> bool:
        """Non-blocking attempt to acquire a token.

        Returns:
            True if token acquired, False if bucket empty.
        """
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    @property
    def available_tokens(self) -> float:
        """Current token count (for monitoring)."""
        with self._lock:
            self._refill()
            return self._tokens

    def reset(self) -> None:
        """Reset bucket to full capacity."""
        with self._lock:
            self._tokens = float(self.max_tokens)
            self._last_refill = time.monotonic()
