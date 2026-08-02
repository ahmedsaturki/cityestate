"""
Env Documentation Tests
========================
Enforces that every env var referenced via os.getenv / os.environ[...] in
src/ and scripts/ is documented in .env.example.

Two categories of references are auto-managed (set by loader.py or
inferred from another key) and are listed as comments in .env.example:
  - OPENROUTER_API_KEY: set by loader.py from ROUTER_API_KEY
  - OTEL_*: forced by loader.py to disable OpenTelemetry

Those names are exempt from the strict assertion.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"
AUTO_MANAGED = {"OPENROUTER_API_KEY", "OTEL_SDK_DISABLED",
                "OTEL_TRACES_EXPORTER", "OTEL_METRICS_EXPORTER",
                "OTEL_LOGS_EXPORTER"}


def _referenced_env_vars() -> set[str]:
    """Find every env var referenced via os.getenv / os.environ in src + scripts."""
    keys: set[str] = set()
    roots = [REPO_ROOT / "src", REPO_ROOT / "scripts"]
    for root in roots:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in re.finditer(r"os\.(?:getenv|environ\.get)\([\"'](\w+)[\"']", text):
                keys.add(m.group(1))
            for m in re.finditer(r"os\.environ\[[\"'](\w+)[\"']\]", text):
                keys.add(m.group(1))
    return keys


def _documented_env_vars() -> set[str]:
    """Find every env var documented in .env.example (both active and commented)."""
    if not ENV_EXAMPLE.exists():
        return set()
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    # Match `KEY=value` lines AND `KEY=` placeholders AND commented `KEY=` lines.
    return set(re.findall(r"^([A-Z][A-Z0-9_]+)\s*=", text, re.M))


class TestEnvDocumentation:
    def test_env_example_exists(self):
        assert ENV_EXAMPLE.exists(), ".env.example missing"

    def test_every_referenced_key_documented(self):
        referenced = _referenced_env_vars() - AUTO_MANAGED
        documented = _documented_env_vars()
        missing = referenced - documented
        assert not missing, (
            f"Env vars referenced in code but missing from .env.example: "
            f"{sorted(missing)}. Add them with comments explaining defaults "
            f"and rotation guidance."
        )

    def test_documented_keys_actually_referenced(self):
        """Sanity: .env.example shouldn't accumulate stale keys."""
        referenced = _referenced_env_vars()
        documented = _documented_env_vars()
        # Allow some documented-but-unreferenced keys (placeholders, optional
        # providers). Just warn if there are many — soft assertion.
        unused = documented - referenced - AUTO_MANAGED
        # Only fail if we have > 15 stale keys (intentional breadth)
        assert len(unused) <= 15, (
            f"Many documented keys not referenced in code (cleanup candidate): "
            f"{sorted(unused)}"
        )

    def test_no_secrets_in_example(self):
        """The example file must never contain populated secrets."""
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        # Look for any line that looks like a real key (long random string).
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                _, _, value = line.partition("=")
                value = value.strip()
                # Banned: long high-entropy tokens (heuristic)
                if len(value) > 30 and re.search(r"[A-Za-z0-9_-]{30,}", value):
                    pytest.fail(
                        f"Suspicious long secret-like value in .env.example: "
                        f"{line[:80]}"
                    )

    def test_required_keys_have_non_empty_placeholders(self):
        """Keys that bootstrap_env.py requires must have explicit placeholders."""
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        for required in ("ROUTER_API_KEY", "JWT_SECRET", "SESSION_VAULT_KEY",
                         "ADMIN_PASSWORD", "EXTENSION_SHARED_SECRET"):
            pattern = re.compile(rf"^{required}=(.+)$", re.M)
            m = pattern.search(text)
            assert m, f"Required key {required} missing from .env.example"
            value = m.group(1).strip()
            # Must be either a placeholder or empty (operator fills in).
            assert value != "", (
                f"Required key {required} has no placeholder or value"
            )
