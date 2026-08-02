"""
Webhook Routes — استقبال البيانات من النماذج المجانية
=====================================================
Generic webhook to receive form submissions from Google Forms, Tally.so, Typeform, etc.

SECURITY MODEL:
    POST /webhooks/form is now authenticated by HMAC signature.
    Each provider (Google Forms, Tally, Typeform, custom) gets its own secret
    stored in env: WEBHOOK_SECRET_<PROVIDER>. The provider sends the secret in
    the `X-Webhook-Signature` header; we recompute HMAC-SHA256 over the raw body
    and constant-time compare.

    The previous implementation accepted any anonymous POST and immediately
    ran match-making inside the request — an unauthenticated spam / DoS surface.
    Matching is now enqueued and runs in the background.
"""

import hashlib
import hmac
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth
from src.database.ingester import Lead
from src.database.models import ClientRequest, Property

logger = logging.getLogger("api.webhooks")

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class GenericFormSubmission(BaseModel):
    """Generic form submission — accepts any field names."""
    # Standard fields (mapped if present)
    name: str | None = Field(None, alias="name")
    phone: str | None = Field(None, alias="phone")
    email: str | None = Field(None, alias="email")
    message: str | None = Field(None, alias="message")

    # Real estate specific (mapped if present)
    area: str | None = Field(None, alias="area")
    min_budget: float | None = Field(None, alias="min_budget")
    max_budget: float | None = Field(None, alias="max_budget")
    bedrooms: int | None = Field(None, alias="bedrooms")
    property_type: str | None = Field(None, alias="property_type")

    # Catch-all for any additional fields
    extra_fields: dict[str, Any] | None = Field(default_factory=dict, alias="extra_fields")

    model_config = {"extra": "allow"}


class WebhookResponse(BaseModel):
    status: str
    lead_id: int | None = None
    request_id: int | None = None
    matches_found: int = 0
    message: str


# ---------------------------------------------------------------------------
# Field mapping — translate common form field names to our schema
# ---------------------------------------------------------------------------
FIELD_MAP = {
    # Name variations
    "full_name": "name",
    "client_name": "name",
    "customer_name": "name",
    "الاسم": "name",
    "اسم": "name",
    # Phone variations
    "mobile": "phone",
    "whatsapp": "phone",
    "رقم التليفون": "phone",
    "رقم الموبايل": "phone",
    "موبايل": "phone",
    "واتساب": "phone",
    # Email
    "البريد": "email",
    "بريد": "email",
    # Area
    "المنطقة": "area",
    "الحي": "area",
    "المنطقة المفضلة": "area",
    # Budget
    "budget": "max_budget",
    "الميزانية": "max_budget",
    "حد أقصى": "max_budget",
    "حد أدنى": "min_budget",
    # Bedrooms
    "عدد الغرف": "bedrooms",
    "غرف": "bedrooms",
    # Property type
    "نوع العقار": "property_type",
    "النوع": "property_type",
}


def _normalize_fields(data: dict) -> dict:
    """Map field names from various form providers to our schema."""
    normalized = {}
    extra = {}

    for key, value in data.items():
        key_lower = key.lower().strip()
        if key_lower in FIELD_MAP:
            normalized[FIELD_MAP[key_lower]] = value
        elif key_lower in ("name", "phone", "email", "message", "area",
                           "min_budget", "max_budget", "bedrooms", "property_type"):
            normalized[key_lower] = value
        else:
            extra[key] = value

    if extra:
        normalized["extra_fields"] = extra

    return normalized


# ---------------------------------------------------------------------------
# HMAC verification — constant-time
# ---------------------------------------------------------------------------
def _verify_webhook_signature(request: Request, raw_body: bytes) -> None:
    """Verify X-Webhook-Signature header against every configured provider secret.

    Providers send `X-Webhook-Signature: sha256=<hex>` or just the secret directly.
    We accept any of the configured secrets because multiple form providers can
    submit to the same endpoint.
    """
    provided = request.headers.get("X-Webhook-Signature", "").strip()
    if not provided:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Webhook-Signature header.",
        )

    # Strip `sha256=` prefix if provider uses GitHub-style headers.
    provided = provided.removeprefix("sha256=")

    expected_secrets: list[bytes] = []
    for env_key, env_val in os.environ.items():
        if env_key.startswith("WEBHOOK_SECRET_") and env_val:
            expected_secrets.append(env_val.encode("utf-8"))

    if not expected_secrets:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No WEBHOOK_SECRET_* configured on the server. "
                   "Webhook intake is disabled until operators configure a secret.",
        )

    digest_hex = hashlib.sha256(raw_body).hexdigest()
    for secret in expected_secrets:
        expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, provided) or hmac.compare_digest(expected, digest_hex):
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid webhook signature.",
    )


# ---------------------------------------------------------------------------
# POST /api/v1/webhooks/form
# ---------------------------------------------------------------------------
@router.post("/form", response_model=WebhookResponse)
async def receive_form_submission(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receive a generic form submission from any provider.

    Auth: HMAC-SHA256 signature in `X-Webhook-Signature` header.

    Side effects: writes Lead + ClientRequest synchronously (small, transactional).
    Match-making is enqueued and runs in the background so the webhook returns
    fast and a flood of submissions cannot monopolise the request worker.
    """
    raw_body = await request.body()
    _verify_webhook_signature(request, raw_body)

    content_type = request.headers.get("content-type", "")
    if "json" in content_type:
        try:
            raw_data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
    elif "form" in content_type:
        form = await request.form()
        raw_data = dict(form)
    else:
        try:
            raw_data = await request.json()
        except Exception:
            form = await request.form()
            raw_data = dict(form)

    logger.info("Webhook received: %d fields", len(raw_data))
    logger.debug("Raw data: %s", raw_data)

    data = _normalize_fields(raw_data)

    name = data.get("name", "عميل جديد")
    phone = data.get("phone")
    email = data.get("email")
    message = data.get("message", "")

    if not phone and not email:
        raise HTTPException(
            status_code=400,
            detail="At least phone or email is required",
        )

    try:
        lead = Lead(
            title=name or "عميل جديد",
            url=f"webhook:{uuid.uuid4().hex[:12]}",
            phone=phone or "",
            email=email or "",
            source="webhook",
            tags="webhook,organic",
            status="new",
            created_at=datetime.now(timezone.utc),
        )
        db.add(lead)
        db.flush()
        logger.info("Created lead #%d: %s", lead.id, name)

        min_budget = data.get("min_budget")
        max_budget = data.get("max_budget")
        bedrooms = data.get("bedrooms")
        area = data.get("area")
        prop_type = data.get("property_type")

        request_obj = None
        if max_budget or area or bedrooms:
            request_obj = ClientRequest(
                client_name=name or "عميل جديد",
                phone=phone or "",
                email=email or "",
                min_budget=float(min_budget) if min_budget else None,
                max_budget=float(max_budget) if max_budget else None,
                bedrooms=int(bedrooms) if bedrooms else None,
                property_type=prop_type,
                area=area,
                notes=f"Webhook submission: {message}" if message else None,
                status="pending",
                priority="normal",
                created_at=datetime.now(timezone.utc),
            )
            db.add(request_obj)
            db.flush()
            logger.info("Created client request #%d for %s", request_obj.id, name)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Webhook processing failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")

    # Enqueue matching in the background — does not block the webhook response.
    if request_obj is not None:
        _enqueue_matching(request_obj.id)

    return WebhookResponse(
        status="received",
        lead_id=lead.id,
        request_id=request_obj.id if request_obj else None,
        matches_found=0,
        message=f"تم استلام بيانات {name} بنجاح" if name else "تم الاستلام بنجاح",
    )


def _enqueue_matching(request_id: int) -> None:
    """Submit a match-making job. Uses the app's running SchedulerEngine when
    available (so we get retries + persistence); falls back to a fire-and-forget
    background thread for environments where the scheduler isn't started."""
    scheduler_inst = None
    try:
        # The FastAPI app holds the singleton at module level.
        from src.api.main import scheduler as _main_scheduler
        if _main_scheduler is not None and getattr(_main_scheduler, "_started", False):
            scheduler_inst = _main_scheduler
    except Exception as e:
        logger.debug("Could not import main scheduler: %s", e)

    if scheduler_inst is None:
        try:
            from src.api.routes.scheduler import _get_scheduler
            scheduler_inst = _get_scheduler()
        except Exception as e:
            logger.debug("Could not get routes scheduler: %s", e)

    if scheduler_inst is not None:
        try:
            from src.scheduler.jobs import run_matching_for_request
            scheduler_inst.scheduler.add_job(
                run_matching_for_request,
                args=[request_id],
                id=f"match_webhook_{request_id}",
                replace_existing=True,
            )
            return
        except Exception as e:
            logger.warning("Failed to add scheduler job (%s); falling back to thread.", e)

    try:
        import asyncio

        from src.scheduler.jobs import run_matching_for_request

        async def _run_in_thread():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, run_matching_for_request, request_id)

        asyncio.create_task(_run_in_thread()).add_done_callback(
            lambda t: logger.error("Matching task failed: %s", t.exception()) if t.exception() else None
        )
    except Exception as e:
        logger.error("Failed to enqueue matching for request #%d: %s", request_id, e)


def _run_inline_match(db: Session, request_obj: ClientRequest) -> int:
    """Run lightweight match-making for a new client request."""
    from src.matching.engine import MatchScorer

    scorer = MatchScorer()
    properties = db.query(Property).filter(Property.status == "available").all()

    if not properties:
        return 0

    best_score = 0.0
    best_prop = None

    for prop in properties:
        score = scorer.score(request_obj, prop)
        if score > best_score:
            best_score = score
            best_prop = prop

    if best_prop and best_score > 0.3:
        request_obj.matched_property_id = best_prop.id
        request_obj.match_score = best_score
        request_obj.status = "matched"
        logger.info(
            "Matched request #%d → property #%d (score=%.2f)",
            request_obj.id, best_prop.id, best_score,
        )
        return 1

    return 0


def _run_inline_match(db: Session, request_obj: ClientRequest) -> int:
    """DEPRECATED shim — preserved for any external caller that may still
    import it. The webhook handler no longer calls this; matching is
    enqueued via `_enqueue_matching` so the request returns fast."""
    from src.scheduler.jobs import run_matching_for_request
    result = run_matching_for_request(request_obj.id)
    return 1 if result.get("status") == "matched" else 0


# ---------------------------------------------------------------------------
# GET /api/v1/webhooks/form — show webhook info (admin-only)
# ---------------------------------------------------------------------------
@router.get("/form")
def webhook_info(user: dict = Depends(require_auth)):
    """Show webhook endpoint info and supported field mappings.

    Restricted to authenticated users because the response includes the
    example curl command and field schema, which are useful intel for an
    attacker even if the endpoint itself requires HMAC.
    """
    return {
        "endpoint": "/api/v1/webhooks/form",
        "method": "POST",
        "content_types": ["application/json", "application/x-www-form-urlencoded"],
        "required_fields": ["phone OR email"],
        "optional_fields": {
            "name": "Client name",
            "phone": "Phone number (WhatsApp)",
            "email": "Email address",
            "message": "Additional message",
            "area": "Preferred area (e.g., Sheikh Zayed)",
            "max_budget": "Maximum budget in EGP",
            "min_budget": "Minimum budget in EGP",
            "bedrooms": "Number of bedrooms",
            "property_type": "apartment, villa, etc.",
        },
        "supported_languages": ["Arabic", "English"],
        "field_mapping_examples": {
            "الاسم → name": "Arabic name mapped to English",
            "رقم الموبايل → phone": "Arabic phone mapped",
            "الميزانية → max_budget": "Arabic budget mapped",
            "عدد الغرف → bedrooms": "Arabic bedrooms mapped",
        },
        "providers": [
            "Google Forms (via webhook relay)",
            "Tally.so (native webhook)",
            "Typeform (native webhook)",
            "Custom HTML forms",
            "Any system that sends JSON POST",
        ],
        "example_curl": (
            'curl -X POST http://localhost:8000/api/v1/webhooks/form '
            '-H "Content-Type: application/json" '
            '-d \'{"name": "Ahmed", "phone": "+201234567890", '
            '"area": "Sheikh Zayed", "max_budget": 5000000}\''
        ),
    }


# ---------------------------------------------------------------------------
# WhatsApp Web Routes — Browser-based automation
# ---------------------------------------------------------------------------
class WhatsAppWebSendRequest(BaseModel):
    to: str
    message: str


@router.post("/whatsapp-web/start")
async def start_whatsapp_web(
    headless: bool = False,
    user: dict = Depends(require_auth),
):
    """Start WhatsApp Web browser automation"""
    from src.services.whatsapp_web import get_whatsapp_web
    
    whatsapp = await get_whatsapp_web()
    success = await whatsapp.start(headless=headless)
    
    return {
        "status": "started" if success else "failed",
        "authenticated": whatsapp.is_authenticated,
        "message": "WhatsApp Web started" if success else "Failed to start WhatsApp Web"
    }


@router.post("/whatsapp-web/stop")
async def stop_whatsapp_web(user: dict = Depends(require_auth)):
    """Stop WhatsApp Web browser automation"""
    from src.services.whatsapp_web import get_whatsapp_web
    
    whatsapp = await get_whatsapp_web()
    await whatsapp.stop()
    
    return {"status": "stopped", "message": "WhatsApp Web stopped"}


@router.get("/whatsapp-web/status")
async def whatsapp_web_status(user: dict = Depends(require_auth)):
    """Check WhatsApp Web connection status"""
    from src.services.whatsapp_web import get_whatsapp_web
    
    whatsapp = await get_whatsapp_web()
    if whatsapp.is_running:
        await whatsapp.check_and_update_auth()
    
    return {
        "is_running": whatsapp.is_running,
        "is_authenticated": whatsapp.is_authenticated,
        "is_online": whatsapp.is_authenticated
    }


@router.post("/whatsapp-web/send")
async def send_whatsapp_web_message(
    req: WhatsAppWebSendRequest,
    user: dict = Depends(require_auth),
):
    """Send a WhatsApp message via browser automation"""
    from src.services.whatsapp_web import get_whatsapp_web
    
    whatsapp = await get_whatsapp_web()
    if not whatsapp.is_authenticated:
        raise HTTPException(status_code=503, detail="WhatsApp Web not authenticated")
    
    success = await whatsapp.send_message(req.to, req.message)
    return {"status": "sent" if success else "failed", "message": "Message sent" if success else "Failed to send message"}


@router.get("/whatsapp-web/unread")
async def get_whatsapp_web_unread(user: dict = Depends(require_auth)):
    """Get unread WhatsApp messages"""
    from src.services.whatsapp_web import get_whatsapp_web
    
    whatsapp = await get_whatsapp_web()
    if not whatsapp.is_authenticated:
        raise HTTPException(status_code=503, detail="WhatsApp Web not authenticated")
    
    messages = await whatsapp.get_unread_messages()
    return {"messages": messages, "count": len(messages)}


@router.get("/whatsapp-web/chats")
async def get_whatsapp_web_chats(
    limit: int = 20,
    user: dict = Depends(require_auth),
):
    """Get list of recent WhatsApp chats"""
    from src.services.whatsapp_web import get_whatsapp_web
    
    whatsapp = await get_whatsapp_web()
    if not whatsapp.is_authenticated:
        raise HTTPException(status_code=503, detail="WhatsApp Web not authenticated")
    
    chats = await whatsapp.get_chat_list()
    return {"chats": chats[:limit], "count": len(chats[:limit])}


@router.get("/whatsapp-web/search")
async def search_whatsapp_web_contact(
    query: str,
    user: dict = Depends(require_auth),
):
    """Search for a WhatsApp contact"""
    from src.services.whatsapp_web import get_whatsapp_web
    
    whatsapp = await get_whatsapp_web()
    if not whatsapp.is_authenticated:
        raise HTTPException(status_code=503, detail="WhatsApp Web not authenticated")
    
    results = await whatsapp.search_contact(query)
    return {"results": results, "count": len(results)}


@router.get("/whatsapp-web/screenshot")
async def take_whatsapp_web_screenshot(
    filename: str = "whatsapp_screenshot.png",
    user: dict = Depends(require_auth),
):
    """Take a screenshot of WhatsApp Web"""
    from src.services.whatsapp_web import get_whatsapp_web
    
    whatsapp = await get_whatsapp_web()
    if not whatsapp.is_running:
        raise HTTPException(status_code=503, detail="WhatsApp Web not running")
    
    filepath = await whatsapp.take_screenshot(filename)
    return {"filepath": filepath, "message": f"Screenshot saved to {filepath}" if filepath else "Failed to take screenshot"}
