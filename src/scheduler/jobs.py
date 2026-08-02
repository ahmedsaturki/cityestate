"""
Scheduler Jobs — Automated Background Tasks
============================================
Each job is a standalone function called by APScheduler.
All jobs create their own DB session and handle errors internally.
Uses structured logging and metrics for observability.
"""

import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from src.database.models import ClientRequest, Property

logger = logging.getLogger("scheduler.jobs")


def _metrics():
    """Lazy import of global metrics to avoid circular imports."""
    from src.logging_config import metrics
    return metrics


def _timed(label: str):
    """Context manager that records job duration as a metric."""
    class _Timer:
        def __enter__(self):
            self.start = time.monotonic()
            return self
        def __exit__(self, *args):
            elapsed_ms = (time.monotonic() - self.start) * 1000
            _metrics().record_timer(f"job.{label}.duration_ms", elapsed_ms)
    return _Timer()

# Project root for subprocess calls
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)


def _run_cli(command: str, label: str) -> dict:
    """DEPRECATED in-process shim. See _run_in_process.

    Kept so external shell callers that still do
    `python main.py --match` from cron or supervisor configs continue to work.
    Do NOT call this from inside the API process — it creates a second Python
    process that re-loads .env, opens a second DB connection, and forks a
    duplicate scheduler. Use the in-process helpers below.
    """
    logger.warning("[%s] DEPRECATED subprocess path invoked (command=%s). "
                   "Use _run_in_process from in-process schedulers.",
                   label, command)
    _metrics().increment(f"job.{label}.deprecated_subprocess")
    return _run_in_process_via_subprocess(command, label)


def _run_in_process_via_subprocess(command: str, label: str) -> dict:
    """Subprocess runner kept for the deprecated _run_cli path and for
    one-off CLI jobs that genuinely need isolation (none right now)."""
    logger.info("[%s] Starting: %s", label, command)
    _metrics().increment(f"job.{label}.runs")
    with _timed(label):
        try:
            result = subprocess.run(
                [sys.executable, str(Path(PROJECT_ROOT) / "main.py"), command],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                check=False,
            )
            if result.returncode == 0:
                logger.info("[%s] Completed successfully", label)
                _metrics().increment(f"job.{label}.success")
                return {"status": "success", "output": result.stdout[-500:] if result.stdout else ""}
            else:
                logger.error("[%s] Failed (rc=%d): %s", label, result.returncode, result.stderr[-300:])
                _metrics().increment(f"job.{label}.errors")
                return {"status": "error", "returncode": result.returncode, "stderr": result.stderr[-300:]}
        except subprocess.TimeoutExpired:
            logger.error("[%s] Timed out after 300s", label)
            _metrics().increment(f"job.{label}.timeouts")
            return {"status": "timeout"}
        except Exception as e:
            logger.error("[%s] Exception: %s", label, e)
            _metrics().increment(f"job.{label}.errors")
            return {"status": "error", "error": str(e)}


def _run_in_process(fn_name: str, label: str) -> dict:
    """Invoke a top-level function from main.py in the current process.

    This is the preferred way to run scheduled jobs from inside the API
    process. Avoids the subprocess overhead, duplicate .env loads, and DB
    contention of spawning `python main.py`.
    """
    logger.info("[%s] Starting (in-process)", label)
    _metrics().increment(f"job.{label}.runs")
    with _timed(label):
        try:
            import main as _main
            fn = getattr(_main, fn_name, None)
            if fn is None:
                logger.error("[%s] main.%s not found", label, fn_name)
                _metrics().increment(f"job.{label}.errors")
                return {"status": "error", "error": f"main.{fn_name} not found"}
            result = fn()
            status = (result or {}).get("status", "success")
            if status == "success":
                _metrics().increment(f"job.{label}.success")
            else:
                _metrics().increment(f"job.{label}.errors")
            logger.info("[%s] Completed: %s", label, status)
            return result or {"status": status}
        except Exception as e:
            logger.error("[%s] Exception: %s", label, e)
            _metrics().increment(f"job.{label}.errors")
            return {"status": "error", "error": str(e)}


def _get_db_session():
    """Create a new database session using the engine from deps."""
    from src.api.deps import SessionLocal
    return SessionLocal()


# ---------------------------------------------------------------------------
# Job: Match-Making Engine
# ---------------------------------------------------------------------------
def run_matchmaking():
    """Run the match-making engine IN-PROCESS.

    Schedulers inside the API process must not spawn `python main.py --match`
    as a subprocess — that creates a second Python process that re-loads .env,
    opens a second DB connection (against the same SQLite file = locking
    contention), and forks duplicate scheduler loops. We delegate to the
    main.py implementation which uses the same SessionLocal pool.
    """
    return _run_in_process("run_matchmaking", "matchmaking")


def run_notifications():
    """Send pending notifications IN-PROCESS (see run_matchmaking for rationale).

    The in-process implementation in main.py correctly marks MessageLog rows
    status='pending' instead of lying with status='sent' when no real
    dispatcher is configured. See main.run_notifications.
    """
    return _run_in_process("run_notifications", "notifications")


def run_backup():
    """Create an encrypted backup IN-PROCESS (see run_matchmaking for rationale).

    In-process execution also avoids a race where two containers both try to
    prune `output/backups/` at the same time and one deletes the other's
    artifact mid-write.
    """
    return _run_in_process("run_backup", "backup")


def run_matching_for_request(request_id: int) -> dict:
    """Match a single client request to available properties in-process.

    Designed to be called from API handlers (e.g. webhook intake) without
    spawning a subprocess. Returns a dict so callers can log the outcome.
    Skips work if the request was already matched.
    """
    logger.info("[match_one] starting for request_id=%s", request_id)
    _metrics().increment("job.match_one.runs")
    with _timed("match_one"):
        db = _get_db_session()
        try:
            req = db.query(ClientRequest).filter(ClientRequest.id == request_id).first()
            if req is None:
                logger.warning("[match_one] request %s not found", request_id)
                return {"status": "missing"}
            if req.matched_property_id is not None:
                logger.info("[match_one] request %s already matched to property %s",
                            request_id, req.matched_property_id)
                return {"status": "already_matched"}

            from src.matching.engine import MatchScorer
            scorer = MatchScorer()
            properties = db.query(Property).filter(Property.status == "available").all()
            best_score, best_prop = 0.0, None
            for prop in properties:
                score = scorer.score(req, prop)
                if score > best_score:
                    best_score, best_prop = score, prop

            if best_prop and best_score > 0.3:
                req.matched_property_id = best_prop.id
                req.match_score = best_score
                req.status = "matched"
                db.commit()
                logger.info("[match_one] matched request %s → property %s (score=%.2f)",
                            request_id, best_prop.id, best_score)
                _metrics().increment("job.match_one.success")
                return {"status": "matched", "property_id": best_prop.id, "score": best_score}

            db.commit()
            logger.info("[match_one] no match above threshold for request %s", request_id)
            _metrics().increment("job.match_one.no_match")
            return {"status": "no_match", "best_score": best_score}
        except Exception as e:
            db.rollback()
            logger.error("[match_one] failed for request %s: %s", request_id, e)
            _metrics().increment("job.match_one.errors")
            return {"status": "error", "error": str(e)}
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Job: WhatsApp Inbound Message Processing
# ---------------------------------------------------------------------------
def run_inbound_whatsapp():
    """DEPRECATED: inbound_handler was removed in Phase 5 Meta API cleanup."""
    logger.warning("[inbound_whatsapp] DEPRECATED — inbound_handler removed in Phase 5")
    return {"status": "deprecated", "message": "inbound_handler removed"}


# ---------------------------------------------------------------------------
# Job: Facebook Groups Social Radar
# ---------------------------------------------------------------------------
def run_facebook_radar():
    """DEPRECATED: FacebookExpert was removed in Phase 5 Meta API cleanup."""
    logger.warning("[facebook_radar] DEPRECATED — FacebookExpert removed in Phase 5")
    return {"status": "deprecated", "message": "FacebookExpert removed"}


# ---------------------------------------------------------------------------
# Job: Session Vault Health Check
# ---------------------------------------------------------------------------
def run_vault_check():
    """Check vault sessions for expiration and report status."""
    logger.info("[vault_check] Starting session health check")
    _metrics().increment("job.vault_check.runs")
    with _timed("vault_check"):
        try:
            from src.session_vault import SessionVault

            vault = SessionVault()
            status = vault.get_session_status("whatsapp")
            fb_status = vault.get_session_status("facebook")

            result = {
                "status": "success",
                "whatsapp": status,
                "facebook": fb_status,
                "checked_at": datetime.now().isoformat(),
            }

            for platform, st in [("whatsapp", status), ("facebook", fb_status)]:
                if st.get("status") == "no_session":
                    logger.warning("[vault_check] %s has no session — run --%s-init", platform, platform)
                elif st.get("status") == "expired":
                    logger.warning("[vault_check] %s session expired — re-authenticate", platform)
                    _metrics().increment(f"job.vault_check.{platform}.expired")
                else:
                    logger.info("[vault_check] %s session OK", platform)
                    _metrics().increment(f"job.vault_check.{platform}.ok")

            _metrics().increment("job.vault_check.success")
            return result
        except Exception as e:
            logger.error("[vault_check] Failed: %s", e)
            _metrics().increment("job.vault_check.errors")
            return {"status": "error", "error": str(e)}
