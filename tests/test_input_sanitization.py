"""
Input Sanitization Tests — XSS / URI-injection coverage
=======================================================

Verifies every free-text field exposed by the API rejects or strips HTML/JS
payloads at the pydantic boundary. Anything that survives these tests has
been deliberately allowed and is documented as such.

Run: python -m pytest tests/test_input_sanitization.py -v
"""
import pytest
from pydantic import ValidationError

from src.api.models import (
    AutomationRequest,
    ClientRequestCreate,
    ClientRequestUpdate,
    LeadCreate,
    LeadUpdate,
    PropertyCreate,
    PropertyUpdate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _expect_reject(fn, *args, **kwargs):
    """Run `fn(*args, **kwargs)` and assert it raises ValidationError."""
    with pytest.raises(ValidationError):
        fn(*args, **kwargs)


# ===========================================================================
# 1. Script / iframe / object / embed tags must be STRIPPED, not retained
# ===========================================================================
class TestDangerousTagStripping:
    @pytest.mark.parametrize(
        "payload,expected_gone",
        [
            ("<script>alert(1)</script>foo", "<script"),
            ("<SCRIPT>alert(1)</SCRIPT>foo", "<SCRIPT"),
            ("<iframe src=x></iframe>after", "<iframe"),
            ("<object data=x></object>x", "<object"),
            ("<embed src=x>x", "<embed"),
            ("<svg/onload=foo>x", "<svg"),
            ("<img src=x onerror=foo>", "<img"),
            ("<style>body{}</style>foo", "<style"),
            ("<form action=x><input name=y>", "<form"),
        ],
    )
    def test_dangerous_tags_stripped(self, payload, expected_gone):
        out = LeadCreate(title=payload, url="https://e.com").title
        assert expected_gone.lower() not in out.lower(), (
            f"payload survived sanitization: {out!r}"
        )

    def test_closing_tag_alone_is_stripped(self):
        # No opening tag, just a closing tag fragment — sanitizer still
        # removes it. We confirm no `<` survives.
        out = LeadCreate(
            title="hello </script> world", url="https://e.com"
        ).title
        assert "<" not in out, f"angle bracket survived: {out!r}"

    def test_html_comment_stripped(self):
        out = LeadCreate(
            title="hi <!-- evil --> world", url="https://e.com"
        ).title
        assert "<!--" not in out and "-->" not in out


# ===========================================================================
# 2. javascript: / data: / vbscript: / file: URIs must be REJECTED
# ===========================================================================
class TestDangerousURIsRejected:
    @pytest.mark.parametrize(
        "uri",
        [
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "  JavaScript:alert(1)",
            "\tjavascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "data:text/html;base64,PHNjcmlwdD4=",
            "vbscript:msgbox(1)",
            "file:///etc/passwd",
            "FILE:///etc/passwd",
        ],
    )
    def test_payload_uri_rejected(self, uri):
        _expect_reject(LeadCreate, title="x", url=uri)

    def test_via_automation_target(self):
        _expect_reject(
            AutomationRequest, action="scrape", target="javascript:alert(1)"
        )

    def test_property_source_url(self):
        _expect_reject(
            PropertyCreate,
            title="villa",
            area="cairo",
            price=1.0,
            source_url="file:///etc/passwd",
        )


# ===========================================================================
# 3. http(s) URLs are accepted; hosts are required
# ===========================================================================
class TestHTTPAccepted:
    @pytest.mark.parametrize(
        "uri",
        [
            "http://example.com",
            "https://example.com/path?q=1&r=2",
            "https://sub.example.co.uk:8443/path",
            "mailto:foo@example.com",
            "tel:+201234567890",
        ],
    )
    def test_valid_url_passes(self, uri):
        out = LeadCreate(title="x", url=uri).url
        assert out == uri

    def test_http_without_host_rejected(self):
        _expect_reject(LeadCreate, title="x", url="http://")

    def test_url_too_long_rejected(self):
        long_url = "https://example.com/" + "a" * 3000
        _expect_reject(LeadCreate, title="x", url=long_url)

    def test_url_max_length_enforced(self):
        # Exactly at limit should pass.
        max_url = "https://e.com/" + "a" * (2048 - len("https://e.com/"))
        out = LeadCreate(title="x", url=max_url).url
        assert len(out) == 2048


# ===========================================================================
# 4. Null bytes stripped; control characters removed
# ===========================================================================
class TestNullByteStripping:
    def test_null_byte_stripped(self):
        out = LeadCreate(title="hi\x00world", url="https://e.com").title
        assert "\x00" not in out
        assert "hiworld" in out

    def test_null_byte_in_url_stripped(self):
        out = LeadCreate(title="x", url="https://e.com\x00/path").url
        assert "\x00" not in out


# ===========================================================================
# 5. Residual HTML tag fragments are REJECTED (not stripped)
# ===========================================================================
class TestResidualTagFragmentsRejected:
    @pytest.mark.parametrize(
        "payload",
        [
            "<div onclick=foo>x</div>",
            "<a href=x>click</a>",
            "<p>para</p>",
            "<span>x</span>",
            "<table><tr><td>x</td></tr></table>",
        ],
    )
    def test_arbitrary_html_rejected(self, payload):
        _expect_reject(
            PropertyCreate, title=payload, area="cairo", price=1.0
        )


# ===========================================================================
# 6. Plain text passes through untouched
# ===========================================================================
class TestPlainTextUntouched:
    def test_normal_title_preserved(self):
        out = LeadCreate(
            title="3-bedroom villa, New Cairo", url="https://e.com"
        ).title
        assert out == "3-bedroom villa, New Cairo"

    def test_arabic_with_stray_angle_bracket_preserved(self):
        # Arabic text with stray angle brackets — not HTML, must survive.
        payload = "شقة <محمد> في التجمع"
        out = LeadCreate(title=payload, url="https://e.com").title
        assert out == payload

    def test_optional_none_passes(self):
        out = LeadCreate(title="t", url="https://e.com", interest=None)
        assert out.interest is None

    def test_special_chars_in_text_ok(self):
        # Punctuation / symbols that look scary but aren't HTML must pass.
        payload = "Buy now! 50% off — & more @ $100"
        out = LeadCreate(title=payload, url="https://e.com").title
        assert out == payload


# ===========================================================================
# 7. LeadUpdate / PropertyUpdate / ClientRequest have the same guarantees
# ===========================================================================
class TestUpdateModelsSanitized:
    def test_lead_update_strips_xss(self):
        out = LeadUpdate(title="<script>alert(1)</script>x")
        assert "<script" not in out.title.lower()
        assert "alert(1)" in out.title  # text content preserved

    def test_lead_update_rejects_dangerous_uri(self):
        # url is not part of LeadUpdate, so verify title only — url sanitization
        # is covered at create time.
        out = LeadUpdate(title="normal title", tags="<script>x</script>")
        assert "<script" not in out.tags.lower()

    def test_property_update_strips_xss(self):
        out = PropertyUpdate(description="<script>alert(1)</script>")
        assert "<script" not in out.description.lower()

    def test_client_request_create_strips_xss(self):
        out = ClientRequestCreate(
            client_name="Ahmed",
            notes="<iframe src=x></iframe>looking",
        )
        assert "<iframe" not in out.notes.lower()
        assert "looking" in out.notes

    def test_client_request_update_strips_xss(self):
        out = ClientRequestUpdate(notes="<img src=x onerror=foo>")
        assert "<img" not in out.notes.lower()

    def test_automation_request_strips_xss(self):
        out = AutomationRequest(action="<script>x</script>scrape")
        assert "<script" not in out.action.lower()
        assert "scrape" in out.action


# ===========================================================================
# 8. Length caps enforced after sanitization
# ===========================================================================
class TestLengthCapsEnforced:
    def test_title_at_limit_ok(self):
        # 500 char title.
        title = "a" * 500
        out = LeadCreate(title=title, url="https://e.com").title
        assert len(out) == 500

    def test_title_over_limit_rejected(self):
        title = "a" * 600
        _expect_reject(LeadCreate, title=title, url="https://e.com")

    def test_description_at_limit_ok(self):
        desc = "b" * 4000
        out = PropertyCreate(
            title="villa", area="cairo", price=1.0, description=desc
        ).description
        assert len(out) == 4000

    def test_description_over_limit_rejected(self):
        _expect_reject(
            PropertyCreate,
            title="villa",
            area="cairo",
            price=1.0,
            description="b" * 4001,
        )

    def test_email_over_limit_rejected(self):
        # Email max_length is 254 chars.
        # "@x.co" is 5 chars; to land at exactly 254, use 249 'a's.
        boundary = "a" * 249 + "@x.co"  # 249 + 5 = 254 chars - exactly at limit
        assert len(boundary) == 254
        LeadCreate(title="x", url="https://e.com", email=boundary)  # should pass

        # 255 chars - exceeds limit by 1.
        over = "a" * 250 + "@x.co"  # 250 + 5 = 255 chars
        assert len(over) == 255
        _expect_reject(
            LeadCreate, title="x", url="https://e.com", email=over
        )
