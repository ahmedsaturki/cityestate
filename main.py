#!/usr/bin/env python3
"""
CityEstate — Main Entry Point
==============================
Unified CLI for all system operations: matchmaking, notifications, backups,
and more. This is the entry point called by the scheduler.

Usage:
    python main.py --match          Run matchmaking engine
    python main.py --notify         Send pending notifications
    python main.py --backup         Create encrypted backup
    python main.py --vault-check    Check vault session health
    python main.py --all            Run all jobs once
    python main.py --serve          Start API server
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env BEFORE reading any env vars
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("cityestate.main")


def _get_db_session():
    """Create a new database session."""
    from src.api.deps import SessionLocal
    return SessionLocal()


def run_matchmaking():
    """Run the match-making engine to find property matches for requests."""
    logger.info("=== Starting Matchmaking Engine ===")
    try:
        from src.matching.engine import MatchMakingEngine
        db = _get_db_session()
        try:
            engine = MatchMakingEngine(db)
            result = engine.match_all_pending()
            logger.info("Matchmaking complete: %s", result)
            return result
        finally:
            db.close()
    except Exception as e:
        logger.error("Matchmaking failed: %s", e)
        return {"status": "error", "error": str(e)}


def run_notifications():
    """Send pending match notifications via the real dispatcher.

    Uses `src.messaging.dispatcher.MessageDispatcher` to push
    match notifications through the configured channel (WhatsApp by
    default). Each notification is recorded in `MessageLog` with
    status `sent` on success or `failed` on error.

    Status values:
      - "sent"     : dispatcher successfully pushed the message
      - "failed"   : dispatcher raised an exception
    """
    logger.info("=== Starting Notifications Job ===")
    try:
        from src.database.models import ClientRequest, MessageLog
        from src.messaging.dispatcher import MessageDispatcher

        db = _get_db_session()
        try:
            pending = db.query(ClientRequest).filter(
                ClientRequest.status == "matched",
                ClientRequest.notified_at.is_(None),
            ).all()

            if not pending:
                logger.info("No pending notifications")
                return {"status": "success", "notifications_sent": 0, "notifications_pending": 0}

            dispatcher = MessageDispatcher(db)
            sent_count = 0
            failed_count = 0

            for req in pending:
                try:
                    result = dispatcher.send_match_notification(req, channel="whatsapp")
                    if result.get("status") == "sent":
                        sent_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error("Failed to notify request %d: %s", req.id, e)
                    failed_count += 1

            logger.info(
                "Notifications complete: %d sent, %d failed",
                sent_count,
                failed_count,
            )
            return {
                "status": "success",
                "notifications_sent": sent_count,
                "notifications_failed": failed_count,
                "dispatcher_available": True,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error("Notifications failed: %s", e)
        return {"status": "error", "error": str(e)}


def run_backup():
    """Create an encrypted backup of DB + vault (Fernet + ZIP)."""
    logger.info("=== Starting Backup Job ===")
    try:
        from src.backup.encrypted_backup import create_backup
        from src.session_vault.encryption import EncryptionManager

        # Fail fast if SESSION_VAULT_KEY is missing or unusable.
        EncryptionManager()

        backup_dir = PROJECT_ROOT / "output" / "backups"
        db_path = PROJECT_ROOT / "output" / "cityestate.db"
        vault_dir = PROJECT_ROOT / "output" / "vault"

        result = create_backup(
            project_root=PROJECT_ROOT,
            backup_dir=backup_dir,
            db_path=db_path,
            vault_dir=vault_dir,
            retain_count=7,
        )
        logger.info("Backup complete: %s", result)
        return result
    except Exception as e:
        logger.error("Backup failed: %s", e)
        return {"status": "error", "error": str(e)}


def run_vault_check():
    """Check vault sessions for expiration."""
    logger.info("=== Starting Vault Health Check ===")
    try:
        from src.session_vault import SessionVault

        vault = SessionVault()
        wa_status = vault.get_session_status("whatsapp")

        result = {
            "status": "success",
            "whatsapp": wa_status,
            "checked_at": datetime.now().isoformat(),
        }

        if wa_status.get("status") == "no_session":
            logger.warning("WhatsApp has no session")
        elif wa_status.get("status") == "expired":
            logger.warning("WhatsApp session expired")
        else:
            logger.info("WhatsApp session OK")

        return result
    except Exception as e:
        logger.error("Vault check failed: %s", e)
        return {"status": "error", "error": str(e)}


def run_all():
    """Run all jobs once, then loop to stay alive as a service."""
    import time as _time
    interval = int(os.getenv("SCHEDULER_LOOP_INTERVAL", "3600"))
    logger.info("Scheduler loop started — running every %ds", interval)
    while True:
        results = {}
        results["matchmaking"] = run_matchmaking()
        results["notifications"] = run_notifications()
        results["backup"] = run_backup()
        results["vault_check"] = run_vault_check()
        logger.info("Batch complete: %s", {k: v.get("status", "unknown") for k, v in results.items()})
        _time.sleep(interval)


def run_serve():
    """Start the API server."""
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="CityEstate — Egyptian Real Estate Multi-Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --match          Run matchmaking
  python main.py --notify         Send notifications
  python main.py --all            Run all jobs
  python main.py --serve          Start API server
        """,
    )

    parser.add_argument("--match", action="store_true", help="Run matchmaking engine")
    parser.add_argument("--notify", action="store_true", help="Send pending notifications")
    parser.add_argument("--backup", action="store_true", help="Create encrypted backup")
    parser.add_argument("--vault-check", action="store_true", help="Check vault session health")
    parser.add_argument("--all", action="store_true", help="Run all jobs once")
    parser.add_argument("--serve", action="store_true", help="Start API server")

    args = parser.parse_args()

    # If no arguments, show help
    if not any([args.match, args.notify, args.backup,
                args.vault_check, args.all, args.serve]):
        parser.print_help()
        return

    if args.serve:
        run_serve()
    elif args.all:
        results = run_all()
        print("\n" + "=" * 60)
        print("All jobs completed:")
        for job, result in results.items():
            status = result.get("status", "unknown")
            print(f"  {job}: {status}")
        print("=" * 60)
    else:
        if args.match:
            run_matchmaking()
        if args.notify:
            run_notifications()
        if args.backup:
            run_backup()
        if args.vault_check:
            run_vault_check()


if __name__ == "__main__":
    main()
