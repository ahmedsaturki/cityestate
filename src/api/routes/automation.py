"""
Automation Routes — مسارات التحكم بالروبوتات
=============================================
Control scraping, sending, and enrichment automation.
"""

import os
import subprocess
import sys
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.api.deps import require_auth
from src.api.models import AutomationRequest, AutomationResponse

router = APIRouter(prefix="/automation", tags=["Automation"])


def run_campaign_task(action: str, platform: str, dry_run: bool = False) -> dict:
    """Background task for running campaigns."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(project_root, "output", "automation_logs")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(output_dir, f"{action}_{platform}_{timestamp}.log")

    try:
        cmd = [sys.executable, os.path.join(project_root, "scripts", "campaign_orchestrator.py")]

        if action == "scrape":
            cmd.append("--scrape-only")
        elif action == "enrich":
            cmd.append("--enrich-only")
        elif action == "send":
            cmd.append("--send-only")

        if platform:
            cmd.extend(["--platform", platform])

        if dry_run:
            cmd.append("--dry-run")

        with open(log_file, "w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                timeout=600,
                cwd=project_root,
            )

        return {
            "status": "completed",
            "return_code": result.returncode,
            "log_file": log_file,
        }

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Task timed out after 10 minutes"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/run", response_model=AutomationResponse)
def run_automation(
    request: AutomationRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_auth),
) -> dict:
    """Run an automation task in the background."""
    valid_actions = {"scrape", "send", "enrich"}
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {valid_actions}"
        )

    valid_platforms = {"facebook", "whatsapp", "all"}
    if request.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {valid_platforms}"
        )

    # Run in background
    background_tasks.add_task(
        run_campaign_task,
        action=request.action,
        platform=request.platform,
        dry_run=request.dry_run,
    )

    return AutomationResponse(
        status="started",
        message=f"Automation '{request.action}' for '{request.platform}' started in background",
        task_id=f"{request.action}_{request.platform}_{datetime.now().strftime('%H%M%S')}",
        details={"dry_run": request.dry_run},
    )


@router.post("/scrape")
def trigger_scrape(
    background_tasks: BackgroundTasks,
    platform: str = "facebook",
    user: dict = Depends(require_auth),
) -> dict:
    """Quick trigger for scraping."""
    background_tasks.add_task(
        run_campaign_task,
        action="scrape",
        platform=platform,
        dry_run=False,
    )
    return {"status": "started", "action": "scrape", "platform": platform}


@router.post("/send")
def trigger_send(
    background_tasks: BackgroundTasks,
    platform: str = "whatsapp",
    user: dict = Depends(require_auth),
) -> dict:
    """Quick trigger for sending messages."""
    background_tasks.add_task(
        run_campaign_task,
        action="send",
        platform=platform,
        dry_run=False,
    )
    return {"status": "started", "action": "send", "platform": platform}


@router.post("/enrich")
def trigger_enrich(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_auth),
) -> dict:
    """Quick trigger for lead enrichment."""
    background_tasks.add_task(
        run_campaign_task,
        action="enrich",
        platform="all",
        dry_run=False,
    )
    return {"status": "started", "action": "enrich"}


@router.get("/status")
def get_automation_status(
    user: dict = Depends(require_auth),
) -> dict:
    """Get automation system status."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(project_root, "output", "automation_logs")

    recent_logs = []
    if os.path.exists(log_dir):
        for f in sorted(os.listdir(log_dir), reverse=True)[:10]:
            filepath = os.path.join(log_dir, f)
            recent_logs.append({
                "filename": f,
                "size": os.path.getsize(filepath),
                "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
            })

    return {
        "status": "operational",
        "log_dir": log_dir,
        "recent_logs": recent_logs,
        "campaign_script": os.path.exists(os.path.join(project_root, "scripts", "campaign_orchestrator.py")),
        "whatsapp_pilot": os.path.exists(os.path.join(project_root, "scripts", "whatsapp_pilot.py")),
        "facebook_scraper": os.path.exists(os.path.join(project_root, "scripts", "facebook_scraper.py")),
    }
