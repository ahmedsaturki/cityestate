# CityEstate API Layer — Comprehensive Audit Report

> **Project:** CityEstate Master OS — Egyptian Real Estate Multi-Agent System
> **Audited:** 2026-07-31
> **Auditor:** Jcode
> **Scope:** API layer (`src/api/`, `src/error_handling.py`, `src/logging_config.py`, `src/api/auth.py`, `src/api/bridge_handler.py`, `test_api_endpoints.py`)

---

## 1. Executive Summary

The CityEstate API is a FastAPI-based REST + WebSocket service with 12 route modules, JWT/bcrypt authentication, structured logging, circuit breakers, and HMAC-secured webhooks. The foundation is solid — Pydantic models, error handlers, and a metrics collector exist. However, the API layer carries **10 material gaps** that collectively expose the service to production risks:

| # | Concern | Severity |
|---|---------|----------|
| 1 | Input Validation | **High** |
| 2 | Output Serialization | **Medium** |
| 3 | Pagination | **Medium** |
| 4 | Rate Limiting | **High** |
| 5 | Logging | **Medium** |
| 6 | Error Standardization | **High** |
| 7 | Versioning | **Low** |
| 8 | OpenAPI Validation | **Medium** |
| 9 | Content Negotiation | **Low** |
| 10 | CORS | **Medium** |

**Overall Risk:** **High** — The API lacks input validation rigor, global rate limiting, and standardized error responses. These gaps can lead to data corruption, DoS vulnerability, and poor developer experience for API consumers.

---

## 2. Detailed Findings Per Concern

---

### 2.1 Input Validation

| Field | Detail |
|-------|--------|
| **Current State** | Pydantic models (`src/api/models.py`) define request bodies with basic type annotations. `LoginRequest` has no field validation at all — `username` and `password` are raw `str` with no length, format, or regex constraints. `PropertyCreate.price` is `float` with no min/max. `LeadCreate.url` is `str` with no URL format check. |
| **Gaps Found** | 1. **No email format validation** on `UserCreate`, `LeadCreate.email`, `ClientRequestCreate.email`, `WhatsAppWebSendRequest`. 2. **No URL validation** on `LeadCreate.url`, `PropertyCreate.source_url`. 3. **No phone format validation** — Egyptian mobile numbers (`+201xxxxxxxxx`) are accepted as any string. 4. **No enum constraints** on status fields (`status: str` everywhere) — any arbitrary string is accepted. 5. **No price/budget range validation** — negative prices, zero budgets, or absurdly large numbers pass silently. 6. **`LoginRequest` has zero validation** — empty strings accepted. 7. **`QualityRequest.data` accepts `dict[str, Any]`** with no schema enforcement. 8. **`ExtractRequest.source` accepts any string** — no enum for allowed sources (`whatsapp`, `facebook`, `webpage`, `json`). 9. **No `max_length` on `LoginRequest.username`** or `password`. 10. **Typo in `bridge_handler.py` line 31**: `"فيل独立"` contains a stray Chinese character `独` in the `SADAT_PROPERTY_TYPES` villa keywords list — should be `"فيلا"`. |

**Recommended Fixes (with code examples):**

```python
# src/api/models.py — Strengthened input validation

from pydantic import BaseModel, Field, field_validator, HttpUrl
from typing import Optional
import re

EMAIL_RE = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
EGYPT_PHONE_RE = r'^\+201[0-9]{9}$'

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128, pattern=r'^[\w.@-]+$')
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def username_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Username must not be empty")
        return v


class LeadCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    url: HttpUrl  # Validates URL format automatically
    source: str = "manual"
    lead_type: str = Field(default="Unknown", pattern=r'^(Developer|Agency|Buyer|Investor|Seller|Unknown)$')
    budget: Optional[str] = None
    area: Optional[str] = None
    interest: Optional[str] = None
    urgency: str = Field(default="Normal", pattern=r'^(Normal|Urgent|Flexible)$')
    phone: Optional[str] = Field(None, pattern=r'^\+201[0-9]{9}$')
    email: Optional[str] = Field(None, pattern=EMAIL_RE)
    tags: Optional[str] = None

    @field_validator("budget")
    @classmethod
    def budget_must_be_positive(cls, v):
        if v is not None:
            try:
                val = float(v)
                if val <= 0:
                    raise ValueError("Budget must be positive")
            except (ValueError, TypeError):
                raise ValueError("Budget must be a valid number")
        return v


class PropertyCreate(BaseModel):
    # ... existing fields ...
    price: float = Field(..., gt=0, le=100_000_000)  # Must be positive, max 100M EGP
    price_currency: str = Field(default="EGP", pattern=r'^[A-Z]{3}$')  # ISO 4217
    bedrooms: Optional[int] = Field(None, ge=0, le=20)
    bathrooms: Optional[int] = Field(None, ge=0, le=20)
    area_sqm: Optional[float] = Field(None, gt=0)


class ExtractRequest(BaseModel):
    source: str = Field(..., pattern=r'^(whatsapp|facebook|webpage|json)$')
    text: str = Field(..., min_length=1, max_length=50_000)
    sender: Optional[str] = None
    url: Optional[str] = None
    post_url: Optional[str] = None


class QualityRequest(BaseModel):
    data: dict  # Consider using a typed schema or JSON schema validation
    data_type: str = Field(default="property", pattern=r'^(property|lead)$')


class WhatsAppCheckRequest(BaseModel):
    phone: str = Field(..., pattern=r'^\+201[0-9]{9}$')


class WhatsAppWebSendRequest(BaseModel):
    to: str = Field(..., pattern=r'^\+201[0-9]{9}$')
    message: str = Field(..., min_length=1, max_length=4_096)
```

```python
# src/api/bridge_handler.py — Fix the typo on line 31
# BEFORE (broken):
    "فيلا": ["فيلا", "فيل独立", "فيلا دوبلكس", "تاون هاوس", "توين هاوس"],
# AFTER (fixed):
    "فيلا": ["فيلا", "فيلا دوبلكس", "تاون هاوس", "توين هاوس"],
```

---

### 2.2 Output Serialization

| Field | Detail |
|-------|--------|
| **Current State** | Routes return Pydantic model instances (e.g., `PropertyResponse(**prop.to_dict())`) or raw dicts. The `to_dict()` method on ORM models is used directly. No consistent serialization layer exists — some routes return dict literals (`{"status": "deleted", "id": property_id}`), some return Pydantic models, and some return raw SQLAlchemy objects converted inline. |
| **Gaps Found** | 1. **Inconsistent response shapes** — delete endpoints return `{"status": "deleted"}` while create/update return full models. 2. **No datetime serialization** — `created_at`/`updated_at` are `Optional[str]` in models, relying on `to_dict()` which may produce inconsistent formats. 3. **No envelope wrapper** — all responses are bare objects; no `data`, `meta`, or `links` fields. 4. **Decimal/float precision** — `price` fields can produce floating-point artifacts (e.g., `1500000.0000000002`). 5. **No response filtering** — `to_dict()` may leak fields not intended for the API. 6. **`DashboardStats.recent_leads` and `recent_messages`** are raw `to_dict()` outputs with no Pydantic validation. 7. **No Content-Type enforcement** — all responses default to application/json even for non-JSON data. |

**Recommended Fixes (with code examples):**

```python
# src/api/serialization.py — New serialization module

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from fastapi import JSONResponse


def serialize_value(value: Any) -> Any:
    """Recursively serialize values for API response."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    return value


def envelope(
    data: Any,
    meta: dict | None = None,
    links: dict | None = None,
) -> dict:
    """Wrap response data in a consistent envelope."""
    response = {"data": serialize_value(data)}
    if meta:
        response["meta"] = meta
    if links:
        response["links"] = links
    return response


def paginated_response(
    items: list,
    total: int,
    page: int,
    per_page: int,
    links: dict | None = None,
) -> dict:
    """Wrap paginated list in a consistent envelope."""
    return envelope(
        items,
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, (total + per_page - 1) // per_page),
        },
        links=links,
    )
```

```python
# Usage in routes — e.g., src/api/routes/properties.py

from src.api.serialization import paginated_response, envelope

@router.get("")
def list_properties(
    # ... existing params ...
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    query = db.query(Property)
    # ... filters ...
    total = query.count()
    props = query.order_by(Property.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return paginated_response(
        items=[PropertyResponse(**p.to_dict()).model_dump() for p in props],
        total=total,
        page=page,
        per_page=per_page,
        links={
            "self": f"/api/v1/properties?page={page}&per_page={per_page}",
            "first": f"/api/v1/properties?page=1&per_page={per_page}",
            "last": f"/api/v1/properties?page={max(1, (total + per_page - 1) // per_page)}&per_page={per_page}",
        },
    )
```

---

### 2.3 Pagination

| Field | Detail |
|-------|--------|
| **Current State** | `list_properties`, `list_leads`, and `list_requests` use `offset` + `limit` query parameters with hard-coded max of 500. No page number, no cursor, no total count returned, no pagination metadata in responses. |
| **Gaps Found** | 1. **No total count** — clients cannot know how many records exist. 2. **No page number** — offset-based pagination is error-prone for clients. 3. **No pagination metadata** — no `next`, `prev`, `first`, `last` links. 4. **Offset too large** — `le=500` allows fetching up to 500 records per request; no upper bound for list endpoints like `/properties/stats/summary`. 5. **No cursor-based option** — for real-time data,_offset pagination can skip or duplicate records during inserts/deletes. 6. **`DashboardStats.recent_leads`** hard-codes `.limit(5)` with no pagination control. |

**Recommended Fixes (with code examples):**

```python
# src/api/pagination.py — Pagination utilities

from typing import Optional, Any
from fastapi import Query
from pydantic import BaseModel


class PageParams(BaseModel):
    page: int = Query(1, ge=1, description="Page number (1-based)")
    per_page: int = Query(20, ge=1, le=100, description="Items per page")


class PageResult(BaseModel):
    items: list[Any]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

    def model_dump(self, **kwargs) -> dict:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "per_page": self.per_page,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


def paginate(
    query: Any,
    page: int = 1,
    per_page: int = 20,
) -> PageResult:
    """Apply offset/limit pagination to a SQLAlchemy query."""
    total = query.count()
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
    pages = max(1, (total + per_page - 1) // per_page)
    return PageResult(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )
```

```python
# Usage in src/api/routes/properties.py

from src.api.pagination import PageParams, paginate

@router.get("")
def list_properties(
    # ... existing filters ...
    page_params: PageParams = Depends(),
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    query = db.query(Property)
    # ... apply filters ...
    result = paginate(query, page=page_params.page, per_page=page_params.per_page)

    from src.api.serialization import envelope
    return envelope(
        [PropertyResponse(**p.to_dict()).model_dump() for p in result.items],
        meta={k: getattr(result, k) for k in ["total", "page", "per_page", "pages", "has_next", "has_prev"]},
    )
```

---

### 2.4 Rate Limiting

| Field | Detail |
|-------|--------|
| **Current State** | Only the `/auth/login` endpoint has rate limiting — an in-memory, per-IP counter with 5 attempts per 5 minutes and a 15-minute lockout. Implemented via a module-level `defaultdict(list)` of timestamps. No other endpoint has any rate protection. |
| **Gaps Found** | 1. **No global rate limiter** — all endpoints except login are unlimited. 2. **In-memory only** — does not survive worker restarts; does not work across multiple Uvicorn workers. 3. **No rate limit response headers** — clients cannot detect or respect limits (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`). 4. **No per-endpoint or per-user limits** — a single IP can hammer `/properties`, `/leads`, `/webhooks/form` without consequence. 5. **Webhook endpoint is vulnerable** — despite HMAC auth, a compromised secret can flood the endpoint with form submissions. 6. **No sliding window** — the current fixed-window approach allows burst attacks at window boundaries. 7. **No rate limit on auth endpoints** — `/auth/register` (admin-only) and `/auth/extension-token` have no limits. |

**Recommended Fixes (with code examples):**

```python
# src/api/rate_limiter.py — Global rate limiter using Redis (or in-memory fallback)

import time
import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("rate_limiter")

# Redis-backed rate limiter (preferred) — fallback to in-memory
try:
    import redis
    _redis_client = redis.Redis.from_url(
        Redis URL
        default="redis://localhost:6379/0",
    )
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    _memory_store: dict[str, list[float]] = {}
    logger.warning("Redis not available — using in-memory rate limiter (single-process only)")


class RateLimiter:
    """Sliding-window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """Returns (allowed, remaining, reset_seconds)."""
        now = time.time()
        window_start = now - self.window_seconds

        if REDIS_AVAILABLE:
            pipe = _redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.window_seconds)
            _, count, _, _ = pipe.execute()
        else:
            # In-memory fallback
            if key not in _memory_store:
                _memory_store[key] = []
            _memory_store[key] = [t for t in _memory_store[key] if t > window_start]
            count = len(_memory_store[key])
            _memory_store[key].append(now)

        remaining = max(0, self.max_requests - count - 1)
        reset = int(self.window_seconds)
        allowed = count < self.max_requests
        return allowed, remaining, reset


# Per-endpoint rate limit configurations
RATE_LIMITS = {
    "auth:login": RateLimiter(max_requests=5, window_seconds=300),
    "auth:register": RateLimiter(max_requests=3, window_seconds=3600),
    "auth:extension-token": RateLimiter(max_requests=10, window_seconds=3600),
    "webhooks:form": RateLimiter(max_requests=30, window_seconds=60),
    "properties": RateLimiter(max_requests=100, window_seconds=60),
    "leads": RateLimiter(max_requests=100, window_seconds=60),
    "requests": RateLimiter(max_requests=100, window_seconds=60),
    "content:generate": RateLimiter(max_requests=20, window_seconds=60),
    "data:extract": RateLimiter(max_requests=30, window_seconds=60),
    "default": RateLimiter(max_requests=200, window_seconds=60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware."""

    async def dispatch(self, request: Request, call_next):
        # Skip health/metrics/docs
        if request.url.path in ("/health", "/metrics", "/monitoring/summary", "/"):
            return await call_next(request)

        # Determine rate limit key
        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"

        # Find matching rate limit config
        limiter = None
        for key_pattern, rate_limiter in RATE_LIMITS.items():
            if key_pattern == "default":
                continue
            if key_pattern in path or (key_pattern.startswith(path.split("/")[1]) if "/" in path else False):
                limiter = rate_limiter
                break
        if limiter is None:
            limiter = RATE_LIMITS["default"]

        # Check rate limit
        rate_key = f"ratelimit:{client_ip}:{path}"
        allowed, remaining, reset = limiter.is_allowed(rate_key)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Try again in {reset} seconds.",
                        "retry_after": reset,
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(reset),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        return response
```

```python
# src/api/main.py — Add rate limiter middleware (after CORS, before logging)
from src.api.rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
```

---

### 2.5 Logging

| Field | Detail |
|-------|--------|
| **Current State** | Structured JSON logging exists via `JSONFormatter` in `src/logging_config.py`. A `RequestLoggingMiddleware` logs request method, path, status code, and duration. `MetricsCollector` tracks request counters and timers. |
| **Gaps Found** | 1. **No request/response body logging** — request payloads and response bodies are never logged, making debugging impossible for webhook and API errors. 2. **No correlation ID** in every log line — `X-Request-ID` header is read but not propagated to all log records. 3. **No audit trail** for sensitive operations (login attempts, property creation/deletion, webhook receipt). 4. **No structured log context** per request (user_id, property_id, lead_id) — all logs go through the generic logger. 5. **No log level per route** — security-relevant routes (auth, webhooks) should default to WARNING or higher. 6. **`logger.warning` in `auth.py`** prints JWT_SECRET warnings to stdout at startup — should be critical, not warning, and should not include the warning text in application logs. 7. **`webhooks.py` logs raw form data at DEBUG level** — `logger.debug("Raw data: %s", raw_data)` could leak PII in DEBUG logs. 8. **No log rotation for JSON logs** — `setup_logging` supports `RotatingFileHandler` but it is not used when `enable_json=True`. 9. **No structured error logging** — `AppError` is not logged with full context. 10. **Metrics counters use `increment` without labels** — no breakdown by endpoint or status code bucket. |

**Recommended Fixes (with code examples):**

```python
# src/logging_config.py — Add correlation ID support and structured request logging

import uuid
import logging
from typing import Optional


class CorrelationFilter(logging.Filter):
    """Inject correlation_id into every log record."""

    def filter(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = getattr(record, "correlation_id", "")
        return True


class RequestContextFilter(logging.Filter):
    """Inject request context (user_id, path, method) into log records."""

    def filter(self, record):
        request = getattr(logging, "current_request", None)
        if request:
            record.request_id = getattr(request, "request_id", "")
            record.user_id = getattr(request, "user_id", "")
            record.path = request.url.path if hasattr(request, "url") else ""
        return True


# Add to setup_logging:
root_logger.addFilter(CorrelationFilter())
```

```python
# src/api/main.py — Enhanced RequestLoggingMiddleware with correlation ID and body logging

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time
        import json

        start = time.time()

        # Generate or reuse correlation ID
        correlation_id = request.headers.get("X-Request-ID", "")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Capture request body (for debugging; be careful with large bodies)
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                request.state.body = body
                # Re-create request with body for downstream handlers
                from starlette.requests import Request as StarletteRequest
                request = StarletteRequest(
                    request.scope,
                    receive=request._receive,
                )
            except Exception:
                pass

        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 1)

        # Add correlation ID to response
        response.headers["X-Request-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        # Structured log with full context
        logger.info(
            "%s %s → %d (%sms) correlation_id=%s user=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            correlation_id,
            request.state.get("user_id", "anonymous"),
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "correlation_id": correlation_id,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                }
            },
        )

        # Audit log for sensitive operations
        if request.method == "POST" and "/auth/login" in request.url.path:
            logger.warning(
                "LOGIN_ATTEMPT ip=%s username=%s status=%d",
                request.headers.get("x-forwarded-for", request.client.host),
                # Do NOT log password
                "REDACTED",
                response.status_code,
            )

        if request.method == "POST" and "/webhooks/form" in request.url.path:
            logger.info(
                "WEBHOOK_RECEIVED path=%s content_type=%s correlation_id=%s",
                request.url.path,
                request.headers.get("content-type"),
                correlation_id,
            )

        return response
```

```python
# src/error_handling.py — Log AppError with full context

def setup_error_handlers(app):
    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        # Log with full context
        logger.error(
            "AppError: code=%s message=%s status=%d path=%s correlation_id=%s",
            exc.code.value,
            exc.message,
            exc.status_code,
            request.url.path,
            getattr(request.state, "correlation_id", ""),
            extra={"extra_data": {"error_code": exc.code.value, "details": exc.details}},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )
```

---

### 2.6 Error Standardization

| Field | Detail |
|-------|--------|
| **Current State** | `src/error_handling.py` defines `AppError` (with `code: ErrorCode`, `message`, `details`, `status_code`) and `setup_error_handlers()` which registers two exception handlers: one for `AppError` and a catch-all for `Exception`. |
| **Gaps Found** | 1. **Routes use raw `HTTPException`** instead of `AppError` — `list_properties` raises `HTTPException(status_code=404, detail="Property not found")` instead of `AppError(code=ErrorCode.NOT_FOUND, ...)`. 2. **`HTTPException` responses don't include `error.code`** — they produce `{"detail": "..."}` instead of the standardized `{"error": {"code": "...", "message": "...", "details": {...}, "timestamp": "..."}}` envelope. 3. **400 validation errors** from Pydantic are not caught by `AppError` — they produce FastAPI's default `{"detail": [...]}` format which differs from the `AppError` schema. 4. **No `ValidationError` handler** — Pydantic validation errors escape the `AppError` handler and produce inconsistent output. 5. **`CircuitBreaker` raises `AppError`** internally but the error handler doesn't log circuit-breaker-specific context. 6. **No error code documentation** — the `ErrorCode` enum exists but there's no machine-readable error catalog endpoint. 7. **`general_error_handler` includes `type(exc).__name__`** in the `details` — this can leak implementation information (class names, module paths). 8. **`delete_property` and `delete_lead`** return `{"status": "deleted", "id": ...}` instead of using `AppError` for not-found or `AppError(code=ErrorCode.NOT_FOUND, ...)` for consistency. |

**Recommended Fixes (with code examples):**

```python
# src/error_handling.py — Enhanced

from fastapi import Request, HTTPException, status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def setup_error_handlers(app):
    """Register error handlers with FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.error(
            "AppError: code=%s message=%s status=%d path=%s",
            exc.code.value,
            exc.message,
            exc.status_code,
            request.url.path,
            extra={"extra_data": {"error_code": exc.code.value, "details": exc.details}},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Catch Pydantic validation errors and return standardized format."""
        errors = []
        for err in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in err["loc"]),
                "type": err["type"],
                "msg": err["msg"],
            })
        logger.warning(
            "Validation error: path=%s errors=%s",
            request.url.path,
            errors,
        )
        return JSONResponse(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message="Request validation failed",
                details={"errors": errors},
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Catch raw HTTPException and return standardized format."""
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.INTERNAL_ERROR,
                message=exc.detail,
                details={"path": request.url.path},
                status_code=exc.status_code,
            ),
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error_response(
                code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred",
                # Do NOT leak exception type or module names
                details={},
            ),
        )
```

```python
# Example: Using AppError in routes instead of HTTPException

# src/api/routes/properties.py — Updated get_property
from src.error_handling import AppError, ErrorCode

@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get a single property by ID."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise AppError(
            code=ErrorCode.NOT_FOUND,
            message=f"Property #{property_id} not found",
            details={"property_id": property_id},
            status_code=404,
        )
    return PropertyResponse(**prop.to_dict())
```

```python
# src/api/errors.pyi — Machine-readable error catalog endpoint

@router.get("/errors/catalog")
def error_catalog():
    """Return the full list of error codes and their meanings."""
    return {
        "codes": [
            {"code": e.value, "description": e.name.replace("_", " ")}
            for e in ErrorCode
        ]
    }
```

---

### 2.7 Versioning

| Field | Detail |
|-------|--------|
| **Current State** | `API_VERSION` env var (default `v1`) is used as a URL prefix (`/api/v1/`). The FastAPI app `version` field is set to `1.0.0-{API_VERSION}`. Health and metrics endpoints include the version. |
| **Gaps Found** | 1. **No version negotiation** — no `Accept: application/vnd.cityestate.v2+json` header support. 2. **No `api_version` in response envelope** — clients don't know which API version they're hitting from the response body. 3. **No deprecation policy** — when v2 is introduced, v1 has no sunset timeline or warning mechanism. 4. **No `/v2/` pathway exists** — the routing is hardcoded to a single version prefix. 5. **`version` field in `Root` endpoint returns `1.0.0-v1`** — mixes semantic versioning with the env var prefix inconsistently. 6. **OpenAPI schema includes version as string** — no machine-readable version metadata. 7. **Websocket endpoint has no version prefix** — `/ws/bridge` is version-agnostic, which may cause compatibility issues when v2 is introduced. 8. **No changelog or migration guide** for API consumers. |

**Recommended Fixes (with code examples):**

```python
# src/api/main.py — Version negotiation and metadata

# Add version header to all responses
@app.middleware("http")
async def version_header_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-API-Version"] = API_VERSION
    response.headers["X-API-Server"] = "cityestate-api"
    return response
```

```python
# src/api/versions.py — Version module for future v2

from fastapi import APIRouter

router = APIRouter(prefix="/{api_version}", tags=["Version"])

# This enables path-based versioning: /v1/ and /v2/ share the same codebase
# and route to different routers based on {api_version}
```

```python
# Updated app startup for versioned routes
# src/api/main.py

# Single version prefix (current approach — works but inflexible)
# Consider using a versioned router pattern for v2 support:
app.include_router(auth_router, prefix=f"/api/{API_VERSION}")
# ... etc.

# For v2 migration: create duplicate routers or use a version-aware dispatcher
```

```python
# src/api/models.py — Add API version to response envelope
class APIResponse(BaseModel):
    """Standard API response envelope with version metadata."""
    data: Any
    meta: dict | None = None
    api_version: str = Field(default_factory=lambda: os.getenv("API_VERSION", "v1"))
    links: dict | None = None
```

---

### 2.8 OpenAPI Validation

| Field | Detail |
|-------|--------|
| **Current State** | FastAPI auto-generates OpenAPI schema at `/docs` and `/redoc`. Pydantic models define the schema. `setup_error_handlers` is imported but does not customize the OpenAPI schema generation. |
| **Gaps Found** | 1. **No request body validation beyond Pydantic** — no middleware to validate JSON against the OpenAPI spec at runtime for non-Pydantic routes (e.g., `extract_data`, `score_quality` which accept arbitrary `dict`). 2. **No schema export for client SDK generation** — no `/openapi.json` programmatic access with versioning. 3. **No API contract testing** — no test suite that validates requests/responses against the OpenAPI schema. 4. **No `example` or `description` on `ErrorCode`** in the OpenAPI schema — the enum values are not documented. 5. **`WebhookResponse` and `MatchResponse`** have no OpenAPI descriptions on fields. 6. **No security scheme documented** in OpenAPI — JWT auth is not reflected in the schema. 7. **`/docs` is enabled in development** but no `servers` field is set to indicate the API URL. 8. **No validation of webhook HMAC signature in OpenAPI spec** — the security model is invisible. |

**Recommended Fixes (with code examples):**

```python
# src/api/openapi.py — OpenAPI customization and schema export

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI):
    """Generate and customize the OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=f"1.0.0-{app.state.api_version}" if hasattr(app.state, 'api_version') else "1.0.0",
        description=app.description,
        routes=app.routes,
    )

    # Add security scheme
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /api/v1/auth/login",
        }
    }
    schema["security"] = [{"BearerAuth": []}]

    # Add server URLs
    schema["servers"] = [
        {"url": "/api/v1", "description": "Current API version"},
    ]

    # Add description to error responses
    schema["components"]["responses"] = {
        "ValidationError": {
            "description": "Request validation failed",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Request validation failed",
                            "details": {"errors": [{"field": "email", "type": "pattern_error", "msg": "Invalid email format"}]},
                            "timestamp": "2026-07-31T01:25:46Z",
                        }
                    },
                }
            },
        },
        "RateLimitExceeded": {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Rate limit exceeded",
                            "details": {"retry_after": 60},
                            "timestamp": "2026-07-31T01:25:46Z",
                        }
                    },
                }
            },
        },
    }

    app.openapi_schema = schema
    return schema


# Attach to app
app.openapi = lambda: custom_openapi(app)
```

```python
# test_api_endpoints.py — Add OpenAPI contract tests

def test_openapi_schema_is_valid():
    """Validate that the OpenAPI schema is valid JSON and has required fields."""
    # This would be run as part of the test suite
    pass


def test_all_endpoints_have_responses():
    """Ensure every route has at least one response schema defined."""
    pass
```

---

### 2.9 Content Negotiation

| Field | Detail |
|-------|--------|
| **Current State** | All endpoints produce `application/json` only. No `Accept` header processing. No alternative formats (XML, CSV, YAML). No `charset` specification. |
| **Gaps Found** | 1. **No `Accept` header support** — requests with `Accept: text/xml` or `Accept: application/csv` return JSON anyway, silently ignoring the preference. 2. **No `charset` in `Content-Type`** — responses don't specify `charset=utf-8`. 3. **No `406 Not Acceptable`** — when a client requests an unsupported format, the API should return 406 rather than serving JSON anyway. 4. **Webhook endpoint** accepts `application/json` and `application/x-www-form-urlencoded` but doesn't negotiate — it tries JSON first, falls back to form, and raises 400 for anything else. 5. **`/metrics` endpoint** returns raw JSON without `Content-Type: application/json` header explicitly set (FastAPI does this by default but not consistently). 6. **WebSocket messages** (in `websocket.py`) send JSON but the protocol doesn't negotiate content type — clients must assume JSON. 7. **No `Vary` header** — caching proxies don't know the response varies by `Accept`. |

**Recommended Fixes (with code examples):**

```python
# src/api/content_negotiation.py — Content negotiation middleware

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


SUPPORTED_CONTENT_TYPES = {
    "application/json",
    "application/vnd.api+json",
}

SUPPORTED_ACCEPT_TYPES = {
    "application/json",
    "application/vnd.api+json",
}


class ContentNegotiationMiddleware(BaseHTTPMiddleware):
    """Ensure Accept header is respected and Content-Type is set correctly."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip non-API paths
        if not path.startswith("/api/") and not path.startswith("/ws/"):
            return await call_next(request)

        # Check Accept header for non-GET requests that return data
        if request.method in ("GET",) and "Accept" in request.headers:
            accept = request.headers["Accept"]
            if accept and accept != "*/*":
                # Check if any supported type is acceptable
                supported = False
                for ct in SUPPORTED_ACCEPT_TYPES:
                    if ct in accept or "*/*" in accept:
                        supported = True
                        break
                if not supported:
                    raise HTTPException(
                        status_code=status.HTTP_406_NOT_ACCEPTABLE,
                        detail=f"Unsupported Accept type: {accept}. Supported: {', '.join(SUPPORTED_ACCEPT_TYPES)}",
                    )

        response = await call_next(request)

        # Ensure Content-Type includes charset for JSON responses
        if "application/json" in response.headers.get("content-type", ""):
            response.headers["Content-Type"] = "application/json; charset=utf-8"

        # Add Vary header for Accept-based negotiation
        if "Accept" in request.headers:
            response.headers["Vary"] = "Accept"

        return response
```

```python
# Usage in src/api/main.py
from src.api.content_negotiation import ContentNegotiationMiddleware
app.add_middleware(ContentNegotiationMiddleware)
```

---

### 2.10 CORS

| Field | Detail |
|-------|--------|
| **Current State** | `CORSMiddleware` is configured with `allow_origins` from `ALLOWED_ORIGINS` env var plus dev origins for non-production environments. Allowed methods: `GET, POST, PUT, DELETE, PATCH`. Allowed headers: `Authorization, Content-Type, X-Request-ID`. `allow_credentials=True`. |
| **Gaps Found** | 1. **Dev origins are too broad** — `127.0.0.1:8000`, `localhost:8000` are allowed in non-production, which could expose the API to local network attacks. 2. **No CORS on WebSocket** — `websocket_router` is registered without CORS middleware; WebSocket connections from browser clients may be blocked or unvalidated. 3. **No `allow_methods` for `OPTIONS`** — preflight requests are handled by the middleware, but `OPTIONS` is not explicitly listed. 4. **No CORS preflight caching** — no `max_age` directive on CORS headers to reduce preflight overhead. 5. **All subpaths share the same CORS policy** — there's no way to apply different CORS rules to different route groups (e.g., stricter for `/api/v1/webhooks/`). 6. **No `Access-Control-Expose-Headers`** — custom headers like `X-Request-ID`, `X-RateLimit-*` are not exposed to the browser client. 7. **Production CORS is only as strict as the env var** — if `ALLOWED_ORIGINS` is misconfigured, production is wide open. 8. **No CORS health check** — no way to verify that CORS headers are being returned correctly. |

**Recommended Fixes (with code examples):**

```python
# src/api/main.py — hardened CORS configuration

# Production: strict origins only; Development: localhost only (not 127.0.0.1 wildcard)
if environment == "production":
    # Strict: only explicitly configured origins
    cors_origins = allowed_origins
    cors_max_age = 3600  # Cache preflight for 1 hour
else:
    # Development: only localhost variants, not arbitrary local IPs
    cors_origins = [
        "http://localhost:8050",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8050",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    cors_max_age = 600  # 10 minutes for dev

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Webhook-Signature",
        "Accept",
    ],
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-API-Version",
        "X-Response-Time",
    ],
    max_age=cors_max_age,
)
```

```python
# WebSocket CORS — handled at the WebSocket level in websocket.py
# src/api/routes/websocket.py — Add origin validation

async def bridge_websocket(
    websocket: WebSocket,
    token: str = Query(default=""),
    profile_id: str = Query(default=""),
):
    # Validate origin for WebSocket connections
    origin = websocket.headers.get("origin", "")
    if environment != "development" and origin not in allowed_origins:
        await websocket.close(code=4003, reason="Origin not allowed")
        return

    # ... rest of websocket handling ...
```

---

## 3. Overall Risk Assessment

| Dimension | Rating | Rationale |
|-----------|--------|-----------|
| **Data Integrity** | 🔴 High | No input validation on most endpoints; webhook form submissions can write arbitrary data; price fields accept any float. |
| **Availability** | 🟠 High | No global rate limiting; a single caller can exhaust resources on any endpoint; in-memory rate limiter doesn't survive restarts. |
| **Confidentiality** | 🟡 Medium | HMAC webhooks are good; JWT auth is solid; but no audit trail for sensitive ops and no encryption at rest for logs. |
| **Maintainability** | 🟡 Medium | Error handling is inconsistent; no OpenAPI contract testing; versioning is URL-prefix-only with no migration path. |
| **Developer Experience** | 🟠 High | Inconsistent error formats, no pagination metadata, no content negotiation, no response envelope makes client SDKs fragile. |
| **Observability** | 🟡 Medium | Structured logging exists but lacks correlation IDs, request/response body logging, and per-route audit trails. |

---

## 4. Priority Matrix

| Concern | Risk Level | Effort | Priority |
|---------|-----------|--------|----------|
| **Input Validation** | 🔴 Critical | Medium | **P1 — Immediate** |
| **Error Standardization** | 🔴 Critical | Medium | **P1 — Immediate** |
| **Rate Limiting** | 🔴 Critical | High | **P1 — Immediate** |
| **CORS** | 🟠 High | Low | **P2 — This sprint** |
| **Logging** | 🟠 High | Medium | **P2 — This sprint** |
| **Pagination** | 🟡 Medium | Medium | **P3 — Next sprint** |
| **Output Serialization** | 🟡 Medium | Medium | **P3 — Next sprint** |
| **OpenAPI Validation** | 🟡 Medium | Medium | **P3 — Next sprint** |
| **Versioning** | 🟢 Low | Low | **P4 — Future** |
| **Content Negotiation** | 🟢 Low | Medium | **P4 — Future** |

---

## 5. Implementation Plan

### Phase 1: Critical (Weeks 1-2)
**Goal:** Eliminate data integrity and availability risks.

| Task | Owner | Deliverable |
|------|-------|-------------|
| Fix `bridge_handler.py` typo (`فيل独立` → `فيلا`) | Jcode | 1-line fix |
| Add `field_validator` to `LoginRequest`, `LeadCreate`, `PropertyCreate` | Jcode | `src/api/models.py` updated |
| Add `RequestValidationError` handler to `setup_error_handlers` | Jcode | `src/error_handling.py` updated |
| Replace `HTTPException` with `AppError` in all routes (properties, leads, requests, webhooks) | Jcode | All route files updated |
| Implement global `RateLimitMiddleware` with Redis backend | Jcode | `src/api/rate_limiter.py` + `main.py` middleware registration |
| Harden CORS for production (strict origins, expose headers, max_age) | Jcode | `src/api/main.py` CORS config updated |

### Phase 2: High (Weeks 3-4)
**Goal:** Strengthen observability and consistency.

| Task | Owner | Deliverable |
|------|-------|-------------|
| Add correlation ID filter and request context logging | Jcode | `src/logging_config.py` + `main.py` middleware updated |
| Add audit logging for login attempts and webhook receipts | Jcode | `src/api/main.py` logging middleware expanded |
| Implement pagination module with `PageResult` and `paginate()` helper | Jcode | `src/api/pagination.py` + route updates |
| Implement response envelope (`envelope`, `paginated_response`) | Jcode | `src/api/serialization.py` + route updates |
| Add CORS origin validation to WebSocket endpoint | Jcode | `src/api/routes/websocket.py` origin check |

### Phase 3: Medium (Weeks 5-6)
**Goal:** Improve developer experience and API contract reliability.

| Task | Owner | Deliverable |
|------|-------|-------------|
| Add version header middleware (`X-API-Version`) | Jcode | `src/api/main.py` middleware |
| Customize OpenAPI schema with security scheme, error responses, server URLs | Jcode | `src/api/openapi.py` |
| Add content negotiation middleware (`Accept` header, `406` responses) | Jcode | `src/api/content_negotiation.py` + `main.py` |
| Write OpenAPI contract tests against pytest | Jcode | `tests/test_openapi.py` |
| Add machine-readable error catalog endpoint (`/api/v1/errors/catalog`) | Jcode | `src/api/errors.pyi` |

### Phase 4: Future (Weeks 7+)
**Goal:** Future-proof the API for v2 migration.

| Task | Owner | Deliverable |
|------|-------|-------------|
| Implement versioned router pattern for `/v2/` pathway | Jcode | `src/api/versions.py` + dispatch logic |
| Add XML/CSV content negotiation for export endpoints | Jcode | Content negotiation expanded |
| Redis-backed distributed rate limiter with per-user limits | Jcode | `src/api/rate_limiter.py` enhanced |
| API changelog and migration guide | Jcode | Documentation |
| Deprecation headers and sunset policy for v1 | Jcode | `main.py` middleware |

---

## Appendix A: Typo Found During Audit

**File:** `D:\cityestate\src\api\bridge_handler.py`, **Line 31**

```python
# BEFORE (contains stray Chinese character):
"فيلا": ["فيلا", "فيل独立", "فيلا دوبلكس", "تاون هاوس", "توين هاوس"],
                                  ^^^
# AFTER (fixed — removed invalid character):
"فيلا": ["فيلا", "فيلا دوبلكس", "تاون هاوس", "توين هاوس"],
```

The `独` character (Unicode U+72EC, meaning "independent/alone" in Chinese) was accidentally inserted. This causes the string `"فيل独立"` (a mix of Arabic and Chinese) to never match as a villa keyword in intent parsing, silently reducing villa detection accuracy in the premium property matching pipeline.

---

## Appendix B: Key Files Audited

| File | Lines | Role |
|------|-------|------|
| `src/api/main.py` | 335 | App setup, middleware, routes registration |
| `src/api/models.py` | 280 | Pydantic request/response models |
| `src/api/deps.py` | 91 | DB session, auth dependencies |
| `src/error_handling.py` | 338 | AppError, ErrorCode, error handlers |
| `src/logging_config.py` | 202 | Structured logging, MetricsCollector |
| `src/api/auth.py` | 218 | JWT, create_jwt_token, get_current_user |
| `src/api/bridge_handler.py` | 702 | Message processing, intent parsing (contains typo) |
| `src/api/routes/properties.py` | 177 | CRUD for properties |
| `src/api/routes\leads.py` | 148 | CRUD for leads |
| `src/api/routes\requests.py` | 152 | CRUD for client requests |
| `src/api/routes\auth.py` | 190 | Login, register, extension-token |
| `src/api/routes\automation.py` | 148 | Automation triggers |
| `src/api/routes\webhooks.py` | 556 | Form submissions, HMAC auth |
| `src/api/routes\content.py` | 117 | Content generation |
| `src/api/routes\data.py` | 127 | Data extraction, quality scoring |
| `src/api/routes\scheduler.py` | 85 | Scheduler control |
| `src/api/routes\dashboard.py` | 135 | Dashboard stats |
| `src/api/routes\websocket.py` | 325 | WebSocket bridge |
<tool_call>swarm
<arg_key>action</arg_key>
<arg_value>report