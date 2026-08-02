"""
API Routes — مسارات الـ API
============================
All API route modules.
"""

from src.api.routes.auth import router as auth_router
from src.api.routes.automation import router as automation_router
from src.api.routes.content import router as content_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.data import router as data_router
from src.api.routes.leads import router as leads_router
from src.api.routes.properties import router as properties_router
from src.api.routes.requests import router as requests_router
from src.api.routes.scheduler import router as scheduler_router
from src.api.routes.webhooks import router as webhooks_router
from src.api.routes.websocket import router as websocket_router

__all__ = [
    "auth_router",
    "automation_router",
    "content_router",
    "dashboard_router",
    "data_router",
    "leads_router",
    "properties_router",
    "requests_router",
    "scheduler_router",
    "webhooks_router",
    "websocket_router",
]
