"""
CityEstate API — واجهة برمجة التطبيقات
=======================================
FastAPI application for the CityEstate Master OS.
Security: bcrypt + Fernet encryption + JWT auth + CORS lockdown.
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env BEFORE reading any env vars
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes import (
    auth_router,
    automation_router,
    content_router,
    dashboard_router,
    data_router,
    leads_router,
    properties_router,
    requests_router,
    scheduler_router,
    webhooks_router,
)
from src.api.routes.skills import router as skills_router
from src.api.routes.websocket import router as websocket_router

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
from src.logging_config import metrics, setup_logging

# Setup structured logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", None)
setup_logging(log_dir=LOG_DIR, log_level=LOG_LEVEL, enable_json=False)

logger = logging.getLogger("cityestate")

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
API_VERSION = os.getenv("API_VERSION", "v1")
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown."""
    import time
    
    # --- STARTUP ---
    app.state.start_time = time.time()
    logger.info("CityEstate API starting up...")

    # Import engine and session factory
    from src.api.deps import SessionLocal, engine

    # Import ALL models to register them with Base.metadata.
    # `ingester.Base` is the declarative base; importing `models` triggers
    # the registration of User, Property, ClientRequest, MessageLog, etc.
    from src.database.ingester import Base  # noqa: F811
    import src.database.models  # registers all ORM models on Base

    # Step 1: Create ALL tables
    Base.metadata.create_all(engine)
    logger.info("Database tables created/verified")

    # Step 2: Create default admin (with generated password if needed)
    from src.api.auth import ensure_default_admin
    db = SessionLocal()
    try:
        admin_password = ensure_default_admin(db)
        if admin_password:
            logger.info("Default admin user created")
        else:
            logger.info("Default admin user already exists")
    finally:
        db.close()

    # Step 3: Start scheduler
    from src.api.routes.scheduler import set_scheduler
    from src.scheduler.engine import SchedulerEngine

    scheduler = SchedulerEngine()
    scheduler.start()
    set_scheduler(scheduler)
    logger.info("Background scheduler started")

    logger.info("CityEstate API ready (env=%s, docs=%s)", ENVIRONMENT, ENABLE_DOCS)
    yield
    # --- SHUTDOWN ---
    scheduler.shutdown(wait=False)
    logger.info("CityEstate API shut down")


app = FastAPI(
    title="CityEstate API",
    description="Egyptian Real Estate Multi-Agent System — REST API",
    version=f"1.0.0-{API_VERSION}",
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
from src.error_handling import setup_error_handlers

setup_error_handlers(app)


# ---------------------------------------------------------------------------
# CORS — Lock down in production
# ---------------------------------------------------------------------------
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8050,http://localhost:3000")
allowed_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]

# Only add dev origins if ENVIRONMENT is not production
environment = os.getenv("ENVIRONMENT", "development").lower()
if environment != "production":
    dev_origins = [
        "http://localhost:8050",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8050",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
    ]
    final_origins = list(set(allowed_origins + dev_origins))
else:
    final_origins = allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=final_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# ---------------------------------------------------------------------------
# Request Logging Middleware with Metrics
# ---------------------------------------------------------------------------
SLOW_QUERY_THRESHOLD_MS = 100


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time

        start = time.time()

        # Add request ID
        request_id = request.headers.get("X-Request-ID", "")

        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 1)

        # Record metrics
        metrics.increment(f"requests.{request.method}")
        metrics.increment(f"requests.status.{response.status_code}")
        metrics.record_timer("requests.duration", duration_ms)

        # Log slow requests
        if duration_ms > SLOW_QUERY_THRESHOLD_MS:
            logger.warning(
                "SLOW REQUEST %s %s -> %d (%sms) %s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                f"[{request_id}]" if request_id else "",
            )
        else:
            logger.info(
                "%s %s -> %d (%sms) %s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                f"[{request_id}]" if request_id else "",
            )
        return response


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


# ---------------------------------------------------------------------------
# Request Size Limiting Middleware
# ---------------------------------------------------------------------------
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", str(1 * 1024 * 1024)))  # 1 MB default


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header."},
                )
            if size > MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request body too large. Maximum size is {MAX_REQUEST_SIZE} bytes."
                    },
                )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Rate Limiting Middleware
# ---------------------------------------------------------------------------
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for auth and health endpoints
        if request.url.path in (
            f"/api/{API_VERSION}/auth/token",
            f"/api/{API_VERSION}/auth/register",
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        ) or request.url.path.startswith("/api/extension-token"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}:{request.url.path}"
        now = time.time()
        window_start = now - 60  # 60-second window

        # Clean old entries
        if key in _rate_limit_store:
            _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > window_start]
        else:
            _rate_limit_store[key] = []

        if len(_rate_limit_store[key]) >= 120:  # 120 requests per minute
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        _rate_limit_store[key].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(120 - len(_rate_limit_store[key]))
        return response


_rate_limit_store: dict = {}
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)

app.add_middleware(RequestLoggingMiddleware)

# ---------------------------------------------------------------------------
# Register Routes — versioned prefix only (/api/v1/)
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix=f"/api/{API_VERSION}")
app.include_router(leads_router, prefix=f"/api/{API_VERSION}")
app.include_router(properties_router, prefix=f"/api/{API_VERSION}")
app.include_router(requests_router, prefix=f"/api/{API_VERSION}")
app.include_router(automation_router, prefix=f"/api/{API_VERSION}")
app.include_router(dashboard_router, prefix=f"/api/{API_VERSION}")
app.include_router(scheduler_router, prefix=f"/api/{API_VERSION}")
app.include_router(webhooks_router, prefix=f"/api/{API_VERSION}")
app.include_router(content_router, prefix=f"/api/{API_VERSION}")
app.include_router(data_router, prefix=f"/api/{API_VERSION}")
app.include_router(skills_router, prefix=f"/api/{API_VERSION}")
app.include_router(websocket_router)  # WebSocket doesn't need /api prefix


# ---------------------------------------------------------------------------
# Enhanced Health Check
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    """Health check endpoint — verifies all system components."""
    from sqlalchemy import text

    from src.error_handling import circuit_breakers
    
    checks = {}
    overall_status = "healthy"

    # Database check
    try:
        from src.api.deps import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = {"status": "healthy"}
        finally:
            db.close()
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}
        overall_status = "degraded"

    # Circuit breaker status
    checks["circuit_breakers"] = {
        name: cb.get_status()
        for name, cb in circuit_breakers.items()
    }

    # Metrics
    checks["metrics"] = metrics.get_all_metrics()

    status_code = 200 if overall_status == "healthy" else 503
    return JSONResponse(
        content={
            "status": overall_status,
            "service": "CityEstate API",
            "version": f"1.0.0-{API_VERSION}",
            "environment": ENVIRONMENT,
            "api_prefix": f"/api/{API_VERSION}",
            "checks": checks,
        },
        status_code=status_code,
    )


@app.get("/metrics")
def get_metrics():
    """Comprehensive metrics endpoint for monitoring.
    
    Returns system metrics, circuit breaker status, and job performance data.
    """
    import time

    from src.error_handling import circuit_breakers
    
    # System uptime
    uptime_seconds = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    
    # Circuit breaker status
    cb_status = {
        name: cb.get_status()
        for name, cb in circuit_breakers.items()
    }
    
    # Scheduler status (if available)
    scheduler_status = {}
    try:
        from src.api.routes.scheduler import get_scheduler
        sched = get_scheduler()
        if sched:
            scheduler_status = sched.get_status()
    except Exception:
        scheduler_status = {"error": "scheduler not available"}
    
    return {
        "uptime_seconds": round(uptime_seconds, 1),
        "metrics": metrics.get_all_metrics(),
        "circuit_breakers": cb_status,
        "scheduler": scheduler_status,
        "environment": ENVIRONMENT,
        "version": f"1.0.0-{API_VERSION}",
    }


@app.get("/monitoring/summary")
def monitoring_summary():
    """Lightweight monitoring summary for dashboards."""
    return {
        "status": "ok",
        "environment": ENVIRONMENT,
        "version": f"1.0.0-{API_VERSION}",
        "metrics_count": len(metrics.get_all_metrics()),
    }


@app.get("/cache/keys")
def cache_keys():
    """List all active cache keys."""
    from src.cache_utils import cache

    return {"keys": cache.keys(), "count": len(cache.keys())}


@app.post("/cache/clear")
def cache_clear():
    """Clear all cached entries."""
    from src.cache_utils import cache

    cache.clear()
    return {"status": "cleared"}


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "name": "CityEstate API",
        "version": f"1.0.0-{API_VERSION}",
        "environment": ENVIRONMENT,
        "docs": "/docs" if ENABLE_DOCS else "disabled",
        "health": "/health",
        "metrics": "/metrics",
        "endpoints": {
            "auth": f"/api/{API_VERSION}/auth",
            "leads": f"/api/{API_VERSION}/leads",
            "properties": f"/api/{API_VERSION}/properties",
            "requests": f"/api/{API_VERSION}/requests",
            "automation": f"/api/{API_VERSION}/automation",
            "dashboard": f"/api/{API_VERSION}/dashboard",
            "scheduler": f"/api/{API_VERSION}/scheduler",
            "webhooks": f"/api/{API_VERSION}/webhooks",
            "content": f"/api/{API_VERSION}/content",
        },
    }


# ---------------------------------------------------------------------------
# Run with uvicorn
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
