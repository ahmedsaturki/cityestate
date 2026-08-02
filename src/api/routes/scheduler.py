"""
Scheduler API — REST Endpoints
================================
Control and monitor the background scheduler.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import require_auth
from src.scheduler.engine import SchedulerEngine

logger = logging.getLogger("api.scheduler")

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

# Shared reference — set by api/main.py during startup
_scheduler: SchedulerEngine | None = None


def set_scheduler(scheduler: SchedulerEngine) -> None:
    """Called once at startup to inject the scheduler instance."""
    global _scheduler
    _scheduler = scheduler


def _get_scheduler() -> SchedulerEngine:
    if _scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    return _scheduler


# ------------------------------------------------------------------
# GET /scheduler/status
# ------------------------------------------------------------------
@router.get("/status")
def scheduler_status(
    user: dict = Depends(require_auth),
    sched: SchedulerEngine = Depends(_get_scheduler),
) -> dict:
    """Get scheduler status and job details."""
    return sched.get_status()


# ------------------------------------------------------------------
# POST /scheduler/pause
# ------------------------------------------------------------------
@router.post("/pause")
def scheduler_pause(
    user: dict = Depends(require_auth),
    sched: SchedulerEngine = Depends(_get_scheduler),
) -> dict:
    """Pause all scheduled jobs."""
    sched.pause()
    return {"status": "paused"}


# ------------------------------------------------------------------
# POST /scheduler/resume
# ------------------------------------------------------------------
@router.post("/resume")
def scheduler_resume(
    user: dict = Depends(require_auth),
    sched: SchedulerEngine = Depends(_get_scheduler),
) -> dict:
    """Resume all scheduled jobs."""
    sched.resume()
    return {"status": "resumed"}


# ------------------------------------------------------------------
# POST /scheduler/run/{job_id}
# ------------------------------------------------------------------
@router.post("/run/{job_id}")
def run_job_now(
    job_id: str,
    user: dict = Depends(require_auth),
    sched: SchedulerEngine = Depends(_get_scheduler),
) -> dict:
    """Trigger a job immediately (outside its schedule)."""
    result = sched.run_job_now(job_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
