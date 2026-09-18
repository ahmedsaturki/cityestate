"""
API Models — نماذج البيانات للـ API
====================================
Pydantic models for request/response validation.

Security: all free-text fields exposed to clients (`title`, `description`,
`notes`, `url`, etc.) go through field validators that strip HTML/script
markers and reject `javascript:` / `data:` URI schemes. This is the input
boundary; downstream code is allowed to assume the strings are safe to
render without escaping (defense-in-depth — rendering still escapes).
"""

import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

# Tags / markers we never want reaching the database or being rendered.
# Stripped rather than rejected to avoid breaking Arabic-named leads like
# `<محمد>` (treated as a stray angle bracket, not an injection attempt).
_DANGEROUS_TAG_RE = re.compile(
    r"<\s*/?\s*(?:script|iframe|object|embed|link|meta|style|svg|img|video|audio|source|form|input|button|frame)\b[^>]*>",
    re.IGNORECASE,
)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_NULL_BYTE_RE = re.compile(r"\x00")
# javascript:/data:text-html/vbscript: payload URIs. http(s) and mailto OK.
_BAD_URI_SCHEMES = re.compile(r"^\s*(?:javascript|data|vbscript|file)\s*:", re.IGNORECASE)
# Anything still resembling an HTML tag after stripping dangerous ones —
# closing tags like `</script>` also match this.
_HTML_TAG_FRAGMENT_RE = re.compile(r"<\s*/?\s*[A-Za-z][A-Za-z0-9]*\b")

# Allowed free-text field length ceilings.
_TITLE_MAX = 500
_TEXT_MAX = 4000
_URL_MAX = 2048


def _sanitize_text(value: str | None, *, max_length: int) -> str | None:
    """Strip script/iframe tags, null bytes, HTML comments.

    Returns None unchanged so optional fields stay optional. Rejects residual
    HTML tag fragments like `<div ` that would still render in browsers even
    after tag stripping. Length is enforced after stripping.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        # Accept numeric types (e.g. budget=2000000) and coerce to string
        if isinstance(value, (int, float)):
            value = str(value)
        else:
            raise TypeError("expected string")
    cleaned = _NULL_BYTE_RE.sub("", value)
    cleaned = _HTML_COMMENT_RE.sub("", cleaned)
    cleaned = _DANGEROUS_TAG_RE.sub("", cleaned)
    # Reject residual HTML tag fragments: opening tags like `<div ` or
    # closing tags like `</script>`. Catches anything we missed.
    if _HTML_TAG_FRAGMENT_RE.search(cleaned):
        raise ValueError("HTML tag fragments are not allowed")
    cleaned = cleaned.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"value exceeds {max_length} characters after sanitization")
    return cleaned


def _validate_url(value: str | None) -> str | None:
    """Reject javascript:/data:/vbscript:/file: URIs and require a host."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("expected string")
    candidate = _NULL_BYTE_RE.sub("", value).strip()
    if not candidate:
        raise ValueError("URL cannot be empty")
    if _BAD_URI_SCHEMES.match(candidate):
        raise ValueError("URL scheme not allowed")
    try:
        parsed = urlparse(candidate)
    except Exception as exc:
        raise ValueError(f"invalid URL: {exc}") from exc
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https", "mailto", "tel"}:
        raise ValueError(f"URL scheme '{parsed.scheme}' not allowed")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError("URL must include a host")
    if len(candidate) > _URL_MAX:
        raise ValueError(f"URL exceeds {_URL_MAX} characters")
    return candidate


# ---------------------------------------------------------------------------
# Auth Models
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    role: str = "user"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "admin",
                    "password": "Str0ng!Pass#2026",
                    "full_name": "Admin User",
                    "role": "admin",
                }
            ]
        }
    }


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: str | None


# ---------------------------------------------------------------------------
# Lead Models
# ---------------------------------------------------------------------------
class LeadCreate(BaseModel):
    title: str = Field(..., max_length=_TITLE_MAX)
    url: str = Field(..., max_length=_URL_MAX)
    source: str = Field(default="manual", max_length=128)
    lead_type: str = Field(default="Unknown", max_length=64)
    budget: str | None = Field(default=None, max_length=128)
    area: str | None = Field(default=None, max_length=256)
    interest: str | None = Field(default=None, max_length=_TEXT_MAX)
    urgency: str = Field(default="Normal", max_length=32)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=254)
    tags: str | None = Field(default=None, max_length=_TEXT_MAX)

    @field_validator("title", "source", "lead_type", "budget", "area",
                     "interest", "urgency", "phone", "email", "tags",
                     mode="before")
    @classmethod
    def _sanitize(cls, v, info):
        max_len = _TEXT_MAX if info.field_name in {"interest", "tags"} else _TITLE_MAX
        if info.field_name == "title":
            max_len = _TITLE_MAX
        elif info.field_name in {"source", "lead_type", "urgency"} or info.field_name in {"budget", "phone"}:
            max_len = 128
        elif info.field_name == "area":
            max_len = 256
        elif info.field_name == "email":
            max_len = 254
        return _sanitize_text(v, max_length=max_len)

    @field_validator("url", mode="before")
    @classmethod
    def _url(cls, v):
        return _validate_url(v)


class LeadUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=_TITLE_MAX)
    lead_type: str | None = Field(default=None, max_length=64)
    budget: str | None = Field(default=None, max_length=128)
    area: str | None = Field(default=None, max_length=256)
    interest: str | None = Field(default=None, max_length=_TEXT_MAX)
    urgency: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=254)
    status: str | None = Field(default=None, max_length=64)
    score: float | None = None
    tags: str | None = Field(default=None, max_length=_TEXT_MAX)

    @field_validator("title", "lead_type", "budget", "area", "interest",
                     "urgency", "phone", "email", "status", "tags",
                     mode="before")
    @classmethod
    def _sanitize(cls, v, info):
        name = info.field_name
        if name == "title":
            return _sanitize_text(v, max_length=_TITLE_MAX)
        if name in {"interest", "tags"}:
            return _sanitize_text(v, max_length=_TEXT_MAX)
        if name == "area":
            return _sanitize_text(v, max_length=256)
        if name == "email":
            return _sanitize_text(v, max_length=254)
        if name in {"budget", "phone"}:
            return _sanitize_text(v, max_length=128)
        return _sanitize_text(v, max_length=128)


class LeadResponse(BaseModel):
    id: int
    title: str
    url: str
    source: str
    lead_type: str
    budget: str | None
    area: str | None
    interest: str | None
    urgency: str
    phone: str | None
    email: str | None
    status: str
    score: float
    tags: str | None
    created_at: str | None
    updated_at: str | None


# ---------------------------------------------------------------------------
# Property Models
# ---------------------------------------------------------------------------
class PropertyCreate(BaseModel):
    title: str = Field(..., max_length=_TITLE_MAX)
    description: str | None = Field(default=None, max_length=_TEXT_MAX)
    property_type: str = Field(default="primary", max_length=64)
    status: str = Field(default="available", max_length=64)
    area: str = Field(..., max_length=256)
    city: str = Field(default="Cairo", max_length=128)
    district: str | None = Field(default=None, max_length=256)
    price: float
    price_currency: str = Field(default="EGP", max_length=8)
    bedrooms: int | None = None
    bathrooms: int | None = None
    area_sqm: float | None = None
    developer: str | None = Field(default=None, max_length=256)
    project_name: str | None = Field(default=None, max_length=256)
    delivery_date: str | None = Field(default=None, max_length=64)
    down_payment: float | None = None
    monthly_installment: float | None = None
    installment_years: int | None = None
    payment_plan_details: str | None = Field(default=None, max_length=_TEXT_MAX)
    contact_name: str | None = Field(default=None, max_length=256)
    contact_phone: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=254)
    source: str | None = Field(default=None, max_length=256)
    source_url: str | None = Field(default=None, max_length=_URL_MAX)
    tags: str | None = Field(default=None, max_length=_TEXT_MAX)

    _TEXT_FIELDS_TITLE = ("title",)
    _TEXT_FIELDS_LONG = ("description", "payment_plan_details", "tags")
    _TEXT_FIELDS_256 = ("district", "developer", "project_name",
                        "contact_name", "source")
    _TEXT_FIELDS_128 = ("property_type", "status", "city", "delivery_date")
    _TEXT_FIELDS_64 = ("contact_phone", "price_currency")

    @field_validator("title", "description", "property_type", "status",
                     "area", "city", "district", "developer",
                     "project_name", "delivery_date", "payment_plan_details",
                     "contact_name", "contact_phone", "contact_email",
                     "source", "tags", mode="before")
    @classmethod
    def _sanitize(cls, v, info):
        name = info.field_name
        if name == "title":
            return _sanitize_text(v, max_length=_TITLE_MAX)
        if name in {"description", "payment_plan_details", "tags"}:
            return _sanitize_text(v, max_length=_TEXT_MAX)
        if name in {"district", "developer", "project_name", "contact_name", "source"}:
            return _sanitize_text(v, max_length=256)
        if name in {"area"}:
            return _sanitize_text(v, max_length=256)
        if name in {"property_type", "status", "city", "delivery_date"}:
            return _sanitize_text(v, max_length=128)
        if name == "contact_phone":
            return _sanitize_text(v, max_length=64)
        if name == "contact_email":
            return _sanitize_text(v, max_length=254)
        return _sanitize_text(v, max_length=128)

    @field_validator("source_url", mode="before")
    @classmethod
    def _url(cls, v):
        return _validate_url(v)


class PropertyUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=_TITLE_MAX)
    description: str | None = Field(default=None, max_length=_TEXT_MAX)
    property_type: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=64)
    area: str | None = Field(default=None, max_length=256)
    city: str | None = Field(default=None, max_length=128)
    district: str | None = Field(default=None, max_length=256)
    price: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    area_sqm: float | None = None
    developer: str | None = Field(default=None, max_length=256)
    project_name: str | None = Field(default=None, max_length=256)
    delivery_date: str | None = Field(default=None, max_length=64)
    down_payment: float | None = None
    monthly_installment: float | None = None
    installment_years: int | None = None
    payment_plan_details: str | None = Field(default=None, max_length=_TEXT_MAX)
    contact_name: str | None = Field(default=None, max_length=256)
    contact_phone: str | None = Field(default=None, max_length=64)
    contact_email: str | None = Field(default=None, max_length=254)
    tags: str | None = Field(default=None, max_length=_TEXT_MAX)

    @field_validator("title", "description", "property_type", "status",
                     "area", "city", "district", "developer",
                     "project_name", "delivery_date", "payment_plan_details",
                     "contact_name", "contact_phone", "contact_email",
                     "tags", mode="before")
    @classmethod
    def _sanitize(cls, v, info):
        name = info.field_name
        if name == "title":
            return _sanitize_text(v, max_length=_TITLE_MAX)
        if name in {"description", "payment_plan_details", "tags"}:
            return _sanitize_text(v, max_length=_TEXT_MAX)
        if name in {"district", "developer", "project_name", "contact_name"}:
            return _sanitize_text(v, max_length=256)
        if name == "area":
            return _sanitize_text(v, max_length=256)
        if name in {"property_type", "status", "city", "delivery_date"}:
            return _sanitize_text(v, max_length=128)
        if name == "contact_phone":
            return _sanitize_text(v, max_length=64)
        if name == "contact_email":
            return _sanitize_text(v, max_length=254)
        return _sanitize_text(v, max_length=128)


class PropertyResponse(BaseModel):
    id: int
    title: str
    description: str | None
    property_type: str
    status: str
    area: str
    city: str | None
    district: str | None
    price: float
    price_currency: str
    bedrooms: int | None
    bathrooms: int | None
    area_sqm: float | None
    developer: str | None
    project_name: str | None
    delivery_date: str | None
    down_payment: float | None
    monthly_installment: float | None
    installment_years: int | None
    payment_plan_details: str | None
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    source: str | None
    score: float
    tags: str | None
    created_at: str | None
    updated_at: str | None


# ---------------------------------------------------------------------------
# Client Request Models
# ---------------------------------------------------------------------------
class ClientRequestCreate(BaseModel):
    client_name: str = Field(..., max_length=256)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=254)
    notes: str | None = Field(default=None, max_length=_TEXT_MAX)
    area: str | None = Field(default=None, max_length=256)
    property_type: str | None = Field(default=None, max_length=64)
    min_budget: float | None = None
    max_budget: float | None = None
    bedrooms: int | None = None
    min_area_sqm: float | None = None
    max_area_sqm: float | None = None
    prefer_payment_plan: bool = False
    priority: str = Field(default="normal", max_length=32)

    @field_validator("client_name", "phone", "email", "notes", "area",
                     "property_type", "priority", mode="before")
    @classmethod
    def _sanitize(cls, v, info):
        name = info.field_name
        if name == "client_name":
            return _sanitize_text(v, max_length=256)
        if name == "notes":
            return _sanitize_text(v, max_length=_TEXT_MAX)
        if name == "area":
            return _sanitize_text(v, max_length=256)
        if name == "email":
            return _sanitize_text(v, max_length=254)
        if name == "phone":
            return _sanitize_text(v, max_length=64)
        return _sanitize_text(v, max_length=128)


class ClientRequestUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=64)
    priority: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=_TEXT_MAX)
    notification_channel: str | None = Field(default=None, max_length=64)

    @field_validator("status", "priority", "notes", "notification_channel",
                     mode="before")
    @classmethod
    def _sanitize(cls, v, info):
        name = info.field_name
        if name == "notes":
            return _sanitize_text(v, max_length=_TEXT_MAX)
        return _sanitize_text(v, max_length=128)


class ClientRequestResponse(BaseModel):
    id: int
    client_name: str
    phone: str | None
    email: str | None
    notes: str | None
    area: str | None
    property_type: str | None
    min_budget: float | None
    max_budget: float | None
    bedrooms: int | None
    min_area_sqm: float | None
    max_area_sqm: float | None
    prefer_payment_plan: bool
    status: str
    matched_property_id: int | None
    matched_at: str | None
    match_score: float | None
    notified_at: str | None
    notification_channel: str | None
    priority: str
    created_at: str | None
    updated_at: str | None


# ---------------------------------------------------------------------------
# Automation Models
# ---------------------------------------------------------------------------
class AutomationRequest(BaseModel):
    action: str = Field(..., description="scrape, send, or enrich", max_length=64)
    platform: str = Field(default="facebook", description="facebook, whatsapp", max_length=64)
    target: str | None = Field(default=None, max_length=_URL_MAX)
    dry_run: bool = False

    @field_validator("action", "platform", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return _sanitize_text(v, max_length=64)

    @field_validator("target", mode="before")
    @classmethod
    def _url(cls, v):
        return _validate_url(v)


class AutomationResponse(BaseModel):
    status: str
    message: str
    task_id: str | None
    details: dict | None


# ---------------------------------------------------------------------------
# Dashboard Models
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_leads: int
    total_properties: int
    total_requests: int
    total_messages: int
    leads_by_type: dict
    leads_by_status: dict
    properties_by_status: dict
    requests_by_status: dict
    recent_leads: list
    recent_messages: list


# ---------------------------------------------------------------------------
# Match Models
# ---------------------------------------------------------------------------
class MatchResult(BaseModel):
    request_id: int
    property_id: int
    match_score: float
    matched_at: str
    property_title: str
    property_area: str
    property_price: float


class MatchResponse(BaseModel):
    status: str
    matches: list[MatchResult]
    total_matches: int
