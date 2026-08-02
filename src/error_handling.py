"""
Error Handling & Resilience
===========================
Standardized error responses, retry logic, circuit breaker pattern,
and error recovery for CityEstate.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("error_handling")


# ---------------------------------------------------------------------------
# Error Codes
# ---------------------------------------------------------------------------
class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""
    # Authentication
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"

    # Database
    DB_CONNECTION_ERROR = "DB_CONNECTION_ERROR"
    DB_QUERY_ERROR = "DB_QUERY_ERROR"
    DB_CONSTRAINT_VIOLATION = "DB_CONSTRAINT_VIOLATION"

    # External Services
    EXT_SERVICE_UNAVAILABLE = "EXT_SERVICE_UNAVAILABLE"
    EXT_SERVICE_TIMEOUT = "EXT_SERVICE_TIMEOUT"
    EXT_SERVICE_RATE_LIMITED = "EXT_SERVICE_RATE_LIMITED"

    # WhatsApp
    WA_NOT_CONNECTED = "WA_NOT_CONNECTED"
    WA_RATE_LIMITED = "WA_RATE_LIMITED"
    WA_NUMBER_NOT_FOUND = "WA_NUMBER_NOT_FOUND"
    WA_SEND_FAILED = "WA_SEND_FAILED"

    # Facebook
    FB_SESSION_EXPIRED = "FB_SESSION_EXPIRED"
    FB_RATE_LIMITED = "FB_RATE_LIMITED"
    FB_SCRAPE_FAILED = "FB_SCRAPE_FAILED"

    # General
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"


class AppError(Exception):
    """Application error with code and details."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict | None = None,
        status_code: int = 500,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert to API response dict."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }


# ---------------------------------------------------------------------------
# Error Response Builder
# ---------------------------------------------------------------------------
def error_response(
    code: ErrorCode,
    message: str,
    details: dict | None = None,
    status_code: int = 500,
) -> dict:
    """Build a standardized error response."""
    return {
        "error": {
            "code": code.value,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# Retry Logic
# ---------------------------------------------------------------------------
def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """Decorator for retrying failed operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "Retry %d/%d for %s after %.1fs: %s",
                            attempt + 1, max_retries, func.__name__,
                            current_delay, str(e)
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            "All %d retries failed for %s: %s",
                            max_retries, func.__name__, str(e)
                        )

            raise last_exception

        return wrapper
    return decorator


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """Decorator for retrying async operations with exponential backoff."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "Retry %d/%d for %s after %.1fs: %s",
                            attempt + 1, max_retries, func.__name__,
                            current_delay, str(e)
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            "All %d retries failed for %s: %s",
                            max_retries, func.__name__, str(e)
                        )

            raise last_exception

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------
class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern for external service calls.

    Prevents cascading failures by stopping calls to failing services.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for auto-recovery."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        current = self.state  # triggers auto-transition OPEN→HALF_OPEN
        if current == CircuitState.HALF_OPEN:
            # Service recovered
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info("Circuit breaker '%s' closed (service recovered)", self.name)
        elif current == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        current = self.state  # triggers auto-transition OPEN→HALF_OPEN
        if current == CircuitState.HALF_OPEN:
            # Failed during half-open, back to open
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker '%s' re-opened (half-open test failed)", self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker '%s' opened after %d failures",
                self.name, self._failure_count
            )

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        else:  # OPEN
            return False

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with circuit breaker protection."""
        if not self.can_execute():
            raise AppError(
                code=ErrorCode.EXT_SERVICE_UNAVAILABLE,
                message=f"Circuit breaker '{self.name}' is open",
                details={"state": self.state.value},
                status_code=503,
            )

        if self.state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


# Global circuit breakers for external services
circuit_breakers = {
    "whatsapp": CircuitBreaker("whatsapp", failure_threshold=3, recovery_timeout=300),
    "facebook": CircuitBreaker("facebook", failure_threshold=3, recovery_timeout=300),
    "llm": CircuitBreaker("llm", failure_threshold=3, recovery_timeout=300),
    "database": CircuitBreaker("database", failure_threshold=3, recovery_timeout=30),
}


# ---------------------------------------------------------------------------
# Exception Handler for FastAPI
# ---------------------------------------------------------------------------
def setup_error_handlers(app) -> None:
    """Register error handlers with FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request, exc: Exception):
        from fastapi.responses import JSONResponse
        logger.error("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=error_response(
                code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred",
                details={"type": type(exc).__name__},
            ),
        )
