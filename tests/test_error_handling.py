"""
Unit Tests for Error Handling & Resilience
==========================================
Tests for circuit breaker, retry logic, and error responses.
"""

import asyncio
import pytest
import time
from unittest.mock import MagicMock, AsyncMock

from src.error_handling import (
    AppError,
    ErrorCode,
    CircuitBreaker,
    CircuitState,
    error_response,
    retry,
    async_retry,
)


class TestAppError:
    """Test AppError exception class."""

    def test_error_creation(self):
        error = AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Invalid token",
            details={"token": "expired"},
            status_code=401,
        )
        assert error.code == ErrorCode.AUTH_INVALID_TOKEN
        assert error.message == "Invalid token"
        assert error.details == {"token": "expired"}
        assert error.status_code == 401

    def test_error_to_dict(self):
        error = AppError(
            code=ErrorCode.DB_CONNECTION_ERROR,
            message="Connection failed",
        )
        result = error.to_dict()
        assert "error" in result
        assert result["error"]["code"] == "DB_CONNECTION_ERROR"
        assert result["error"]["message"] == "Connection failed"
        assert "timestamp" in result["error"]


class TestErrorResponse:
    """Test error_response builder."""

    def test_basic_response(self):
        response = error_response(
            code=ErrorCode.NOT_FOUND,
            message="Resource not found",
        )
        assert "error" in response
        assert response["error"]["code"] == "NOT_FOUND"

    def test_response_with_details(self):
        response = error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid input",
            details={"field": "email"},
        )
        assert response["error"]["details"] == {"field": "email"}


class TestCircuitBreaker:
    """Test CircuitBreaker pattern."""

    def test_initial_state(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_failure_opens_circuit(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 1

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=0.1)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True

    def test_half_open_success_closes(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=0.1)
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=0.1)
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_get_status(self):
        cb = CircuitBreaker("test", failure_threshold=5, recovery_timeout=60)
        status = cb.get_status()
        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["threshold"] == 5


class TestRetryDecorator:
    """Test retry decorator."""

    def test_retry_success_first_attempt(self):
        @retry(max_retries=3, delay=0.01)
        def success():
            return "ok"
        
        result = success()
        assert result == "ok"

    def test_retry_success_after_failures(self):
        call_count = 0
        
        @retry(max_retries=3, delay=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"
        
        result = fail_then_succeed()
        assert result == "ok"
        assert call_count == 3

    def test_retry_exhausted(self):
        @retry(max_retries=2, delay=0.01)
        def always_fail():
            raise ValueError("always fails")
        
        with pytest.raises(ValueError):
            always_fail()


class TestAsyncRetryDecorator:
    """Test async retry decorator."""

    def test_async_retry_success(self):
        import asyncio

        @async_retry(max_retries=3, delay=0.01)
        async def success():
            return "ok"
        
        result = asyncio.run(success())
        assert result == "ok"

    def test_async_retry_after_failures(self):
        import asyncio
        call_count = 0
        
        @async_retry(max_retries=3, delay=0.01)
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"
        
        result = asyncio.run(fail_then_succeed())
        assert result == "ok"
        assert call_count == 3
