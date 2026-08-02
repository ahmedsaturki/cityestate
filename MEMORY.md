# CityEstate — Memory

Persistent notes across sessions. Captures the state of the repo, hard
lessons learned, and what to NOT redo. Update whenever a fix lands.

---

## Tier 1 security — completed 2026-07-29 / 2026-07-30

Six items locked down with explicit pass-tests in `tests/`:

1. **`.env` rotation** — `scripts/bootstrap_env.py --rotate [KEY...]` rotates
   specific keys; `--rotate` rotates everything. Test: bootstrap fresh env,
   assert all required keys present and non-placeholder.
2. **Encrypted backups** — `src/backup/encrypted_backup.py` writes Fernet
   blobs with manifest + sha256. Retention is timestamp-based. Test:
   `restore_backup.py` round-trips data.
3. **`PASSWORD_SALT` documented as no-op** — bcrypt uses its own salt; old
   hashes still accepted via `USE_LEGACY_SALT=1`. Test confirms both
   paths through `verify_password`.
4. **`/auth/extension-token`** uses HMAC `compare_digest` + dedicated
   `extension` role + popup UI for the shared secret. Test verifies timing-
   safe compare and that wrong secret returns 401.
5. **`/webhooks/form`** requires HMAC matching; queues matching via
   `run_matching_for_request`. Test feeds in a Tally-style payload with
   correct and incorrect signatures.
6. **SessionVault at-rest encryption** — `EncryptionManager` Fernet-encrypts
   every secret before write. Test confirms Fernet `gAAAAA` prefix and
   no plaintext in stored JSON.

---

## Tier 3 hardening — completed 2026-07-31

Eleven follow-on items beyond the Tier 1 list. Driven by a fresh review that
surfaced XSS surface and missing-config gaps.

### Fixed in this round

1. **N+1 queries in stats endpoints** — `src/api/routes/leads.py`,
   `properties.py`, `requests.py` now use `group_by` / `count()` aggregate
   queries instead of looping.
2. **`list_users` pagination** — `src/api/auth.py` `.all()` replaced with
   `limit/offset` and total-count query.
3. **Rate limiting on automation/data/content endpoints** — slowapi
   limiter added with per-IP + per-route limits.
4. **Security headers middleware** — `X-Frame-Options: DENY`,
   `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`,
   `Referrer-Policy: same-origin`.
5. **Password strength** — `UserCreate.password` requires min_length=8 plus
   complexity (upper, lower, digit, special).
6. **Missing FK indexes** — `Lead.status`, `lead_type`, `created_at`,
   `user_id`, etc. now have explicit `index=True`.
7. **Input sanitization on free-text fields** — see below.
8. **`.env.example` completeness** — see below.

### Input sanitization design (Tier 3 item 7)

All free-text fields in `src/api/models.py` now go through:

- `_sanitize_text(value, max_length=N)` — strips `<script>`, `<iframe>`,
  `<object>`, `<embed>`, `<link>`, `<meta>`, `<style>`, `<svg>`, `<img>`,
  `<video>`, `<audio>`, `<source>`, `<form>`, `<input>`, `<button>`,
  `<frame>` (open and close), HTML comments, null bytes. Rejects any
  residual `<tag>` fragment. Length enforced after stripping.
- `_validate_url(value)` — rejects `javascript:`, `data:`, `vbscript:`,
  `file:` URIs (case-insensitive, whitespace bypass-safe). Requires host
  for `http(s)`. Max 2048 chars.

**Strip vs reject policy**: known-dangerous tags are STRIPPED (the safe
text content survives); other HTML tag fragments (e.g. `<div>`,
`<a href=...>`) are REJECTED — they almost never appear in real lead data
and stripping silently would mask a client bug.

Field length ceilings:
- title: 500
- description / notes / tags / payment_plan_details: 4000
- URL: 2048
- email: 254 (RFC 5321)
- phone: 64
- name / area / district / developer / project_name / contact_name / source: 256
- short enums (status / lead_type / property_type / city): 64–128

Tests: `tests/test_input_sanitization.py` — 52 tests covering
script/iframe/object/etc stripping, javascript:/data:/vbscript:/file:
rejection (including whitespace bypass), null-byte stripping, length caps,
Arabic-with-angle-bracket preservation, plain text untouched.

### .env.example completeness (Tier 3 item 8)

Audited every `os.getenv` / `os.environ[...]` reference in `src/` and
`scripts/`. Found 16 keys referenced but undocumented.

Added (with comments explaining defaults, when to rotate, security notes):
- `WEBHOOK_SECRET_TEST` (referenced by `tests/test_webhook_hmac.py`)
- `JWT_EXPIRY_HOURS` (8h default; tunable per environment)
- `USE_LEGACY_SALT` (off by default; only for hash migration)
- `LOG_DIR` (optional override; defaults to `./logs`)
- `ENABLE_DOCS` (off in production)
- `API_BASE_URL` (dashboard → API)
- `OLLAMA_BASE_URL` / `OLLAMA_MODEL` (local LLM fallback)
- `OPENAI_API_KEY` (voice/STT only)
- `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_HOST` / `SMTP_PORT` (email)
- `PROJECT_ROOT` (backup script fallback)

Auto-managed (set by `loader.py`) listed as comments for transparency:
`OPENROUTER_API_KEY`, `OTEL_*`.

Regression test: `tests/test_env_documentation.py` — runs on every CI,
fails if a code reference appears without a `.env.example` entry.

---

## Hard lessons

- **`pydantic` v2 wants `Annotated[str, Field(max_length=N)]` OR explicit
  `field_validator`** — using `Annotated[str, max_length=...]` without
  `Field()` is silently ignored. Sticking with explicit validators is
  safer for security-relevant models.

- **Closing-tag-only XSS bypasses naive `<script>` strippers** — the
  sanitizer initially let `</script>` survive because the regex only
  matched opening tags. Always run the residual-tag-fragment check AFTER
  stripping dangerous open tags.

- **cp1252 stdout crashes on Arabic** — pytest/python on Windows defaults
  to cp1252 for `print()`. Use `sys.stdout.reconfigure(encoding="utf-8")`
  in any script that prints Arabic.

- **Regexes for env-var discovery must handle quoted string literals**
  consistently — `os.getenv("FOO")` vs `os.environ['FOO']` vs
  `os.environ.get("FOO", default)`. The audit script handles all three.

- **Tests, not promises** — every Tier 1 / Tier 3 item has a test that
  fails when the protection is removed. "Has a test" is the contract.

---

## Test counts (as of 2026-07-31)

469 passed, 1 skipped, 0 failures across 30 test files. Includes 52 new
input-sanitization tests and 5 new env-documentation tests.

Run: `python -m pytest tests/ -v`

---

## What NOT to redo

- Don't reintroduce auto-trust of `Link`, `meta`, `style`, `form` tags in
  sanitization — they're XSS vectors (CSS injection, CSRF token theft).
- Don't read `os.environ["PASSWORD_SALT"]` as if it changes hashing —
  it's documented no-op; the salt is in the bcrypt hash itself.
- Don't add new env vars without adding them to `.env.example` AND to
  the regression test (which fails closed).
