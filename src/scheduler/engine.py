"""
Scheduler Engine — APScheduler Wrapper
======================================
Manages background jobs: match-making, notifications, backups, vault checks.
Reads intervals from .env with sensible defaults.
"""

import logging
import os
from datetime import datetime, timezone

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("scheduler")

# ---------------------------------------------------------------------------
# Default intervals (seconds) — overridden by .env
# ---------------------------------------------------------------------------
DEFAULTS = {
    "MATCH_INTERVAL": 3600,       # 1 hour
    "NOTIFY_INTERVAL": 1800,      # 30 min
    "BACKUP_INTERVAL": 86400,     # 24 hours
    "VAULT_CHECK_INTERVAL": 21600,  # 6 hours
    "INBOUND_WA_INTERVAL": 300,   # 5 min
    "RADAR_INTERVAL": 14400,      # 4 hours
}


def _env_int(key: str) -> int:
    """Read an integer from env, falling back to default."""
    val = os.getenv(key)
    if val:
        try:
            return int(val)
        except ValueError:
            logger.warning("Invalid %s=%s, using default %d", key, val, DEFAULTS[key])
    return DEFAULTS[key]


class SchedulerEngine:
    """Async-background scheduler wrapping APScheduler 3.x."""

    def __init__(self):
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(max_workers=4)}
        job_defaults = {
            "coalesce": True,          # Missed runs → 1 execution
            "max_instances": 1,        # No duplicate jobs
            "misfire_grace_time": 300, # 5 min grace
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="Africa/Cairo",
        )
        self.scheduler.add_listener(self._on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self._started = False
        self._jobs: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self):
        """Start the scheduler and register all jobs."""
        if self._started:
            logger.warning("Scheduler already running")
            return

        self._register_jobs()
        self.scheduler.start()
        self._started = True
        logger.info("Scheduler started with %d jobs", len(self._jobs))

    def shutdown(self, wait: bool = True):
        """Gracefully shut down the scheduler."""
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("Scheduler shut down")

    def pause(self):
        """Pause all jobs."""
        self.scheduler.pause()
        logger.info("Scheduler paused")

    def resume(self):
        """Resume all jobs."""
        self.scheduler.resume()
        logger.info("Scheduler resumed")

    # ------------------------------------------------------------------
    # Job registration
    # ------------------------------------------------------------------
    def _register_jobs(self):
        """Register all scheduled jobs."""
        jobs = [
            {
                "id": "match_run",
                "func": "src.scheduler.jobs:run_matchmaking",
                "seconds": _env_int("MATCH_INTERVAL"),
                "name": "Match-Making Engine",
            },
            {
                "id": "notify_run",
                "func": "src.scheduler.jobs:run_notifications",
                "seconds": _env_int("NOTIFY_INTERVAL"),
                "name": "WhatsApp Notifications",
            },
            {
                "id": "backup_run",
                "func": "src.scheduler.jobs:run_backup",
                "seconds": _env_int("BACKUP_INTERVAL"),
                "name": "Database Backup",
            },
            {
                "id": "vault_check",
                "func": "src.scheduler.jobs:run_vault_check",
                "seconds": _env_int("VAULT_CHECK_INTERVAL"),
                "name": "Vault Session Check",
            },
        ]

        for job in jobs:
            self.scheduler.add_job(
                job["func"],
                "interval",
                seconds=job["seconds"],
                id=job["id"],
                name=job["name"],
                replace_existing=True,
            )
            self._jobs[job["id"]] = {
                "name": job["name"],
                "interval": job["seconds"],
                "next_run": None,
                "last_run": None,
                "last_status": "pending",
                "run_count": 0,
                "error_count": 0,
            }

    # ------------------------------------------------------------------
    # Event listener
    # ------------------------------------------------------------------
    def _on_job_event(self, event):
        """Update job state on execution events."""
        job_id = event.job_id
        if job_id not in self._jobs:
            return

        info = self._jobs[job_id]
        info["last_run"] = datetime.now(timezone.utc).isoformat()
        info["run_count"] += 1

        if event.exception:
            info["last_status"] = "error"
            info["error_count"] += 1
            logger.error("Job %s failed: %s", job_id, event.exception)
        else:
            info["last_status"] = "success"

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def get_status(self) -> dict:
        """Return scheduler status + per-job info."""
        jobs = {}
        for job_id, info in self._jobs.items():
            aps_job = self.scheduler.get_job(job_id)
            jobs[job_id] = {
                **info,
                "next_run": str(aps_job.next_run_time) if aps_job else None,
                "running": aps_job is not None,
            }

        return {
            "running": self._started,
            "job_count": len(self._jobs),
            "jobs": jobs,
        }

    def run_job_now(self, job_id: str) -> dict:
        """Trigger a job immediately (outside its schedule)."""
        if job_id not in self._jobs:
            return {"error": f"Unknown job: {job_id}"}

        try:
            self.scheduler.modify_job(job_id, next_run_time=datetime.now(timezone.utc))
            return {"status": "triggered", "job_id": job_id}
        except Exception as e:
            return {"error": str(e)}
