"""
Time Tracker Skill — متتبع الوقت
===================================
Track time spent on tasks, projects, and client activities.
Supports timers, manual entries, and time reports.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("skills.time_tracker")

TIME_FILE = Path("data/time_entries.json")


class TimeTrackerSkill:
    """Time tracking skill."""

    def __init__(self):
        self._entries = self._load_entries()
        self._active_timer = None

    def _load_entries(self) -> list[dict]:
        if TIME_FILE.exists():
            try:
                return json.loads(TIME_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_entries(self):
        TIME_FILE.parent.mkdir(parents=True, exist_ok=True)
        TIME_FILE.write_text(json.dumps(self._entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def start_timer(self, task: str, project: str = "general", tags: list[str] | None = None) -> dict:
        """Start a timer for a task."""
        if self._active_timer:
            return {"status": "error", "error": "Timer already running. Stop it first.", "active": self._active_timer}

        timer = {
            "id": f"TIMER-{len(self._entries) + 1:04d}",
            "task": task,
            "project": project,
            "tags": tags or [],
            "started_at": datetime.now().isoformat(),
        }
        self._active_timer = timer
        return {"status": "started", "timer": timer}

    def stop_timer(self, notes: str = "") -> dict:
        """Stop the active timer and record the entry."""
        if not self._active_timer:
            return {"status": "error", "error": "No active timer"}

        started = datetime.fromisoformat(self._active_timer["started_at"])
        duration = datetime.now() - started
        duration_minutes = round(duration.total_seconds() / 60, 1)

        entry = {
            **self._active_timer,
            "ended_at": datetime.now().isoformat(),
            "duration_minutes": duration_minutes,
            "notes": notes,
        }

        self._entries.append(entry)
        self._active_timer = None
        self._save_entries()

        return {"status": "stopped", "entry": entry, "duration_formatted": self._format_duration(duration_minutes)}

    def log_time(self, task: str, minutes: float, project: str = "general", date: str | None = None, notes: str = "") -> dict:
        """Manually log time entry."""
        entry = {
            "id": f"LOG-{len(self._entries) + 1:04d}",
            "task": task,
            "project": project,
            "duration_minutes": minutes,
            "date": date or datetime.now().date().isoformat(),
            "logged_at": datetime.now().isoformat(),
            "notes": notes,
            "manual": True,
        }

        self._entries.append(entry)
        self._save_entries()
        return {"status": "logged", "entry": entry, "duration_formatted": self._format_duration(minutes)}

    def get_active_timer(self) -> dict:
        """Get the currently active timer."""
        if not self._active_timer:
            return {"status": "no_active_timer"}

        started = datetime.fromisoformat(self._active_timer["started_at"])
        elapsed = datetime.now() - started
        return {
            "status": "running",
            "timer": self._active_timer,
            "elapsed_minutes": round(elapsed.total_seconds() / 60, 1),
            "elapsed_formatted": self._format_duration(elapsed.total_seconds() / 60),
        }

    def get_summary(self, days: int = 7, project: str | None = None) -> dict:
        """Get time summary for a period."""
        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
        entries = [e for e in self._entries if e.get("date", e.get("logged_at", "")[:10]) >= cutoff]

        if project:
            entries = [e for e in entries if e.get("project") == project]

        total_minutes = sum(e.get("duration_minutes", 0) for e in entries)

        by_project = {}
        for e in entries:
            proj = e.get("project", "general")
            by_project[proj] = by_project.get(proj, 0) + e.get("duration_minutes", 0)

        by_task = {}
        for e in entries:
            task = e.get("task", "Unknown")
            by_task[task] = by_task.get(task, 0) + e.get("duration_minutes", 0)

        return {
            "period_days": days,
            "total_entries": len(entries),
            "total_minutes": round(total_minutes, 1),
            "total_hours": round(total_minutes / 60, 2),
            "total_formatted": self._format_duration(total_minutes),
            "by_project": {k: {"minutes": round(v, 1), "hours": round(v / 60, 2)} for k, v in sorted(by_project.items(), key=lambda x: -x[1])},
            "by_task": {k: {"minutes": round(v, 1)} for k, v in sorted(by_task.items(), key=lambda x: -x[1])},
            "average_per_day": round(total_minutes / days, 1) if days > 0 else 0,
        }

    def get_daily_report(self, date: str | None = None) -> dict:
        """Get detailed report for a specific day."""
        target_date = date or datetime.now().date().isoformat()
        day_entries = [e for e in self._entries if e.get("date", e.get("logged_at", "")[:10]) == target_date]

        total_minutes = sum(e.get("duration_minutes", 0) for e in day_entries)

        return {
            "date": target_date,
            "total_entries": len(day_entries),
            "total_minutes": round(total_minutes, 1),
            "total_formatted": self._format_duration(total_minutes),
            "entries": day_entries,
        }

    def delete_entry(self, entry_id: str) -> dict:
        """Delete a time entry."""
        for i, e in enumerate(self._entries):
            if e.get("id") == entry_id:
                self._entries.pop(i)
                self._save_entries()
                return {"status": "deleted", "entry_id": entry_id}
        return {"status": "error", "error": f"Entry {entry_id} not found"}

    def _format_duration(self, minutes: float) -> str:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"


def get_time_tools():
    """Return CrewAI-compatible tools for time tracking."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class StartTimerInput(BaseModel):
        task: str = Field(description="Task name")
        project: str = Field(default="general", description="Project name")

    class StartTimerTool(BaseTool):
        name: str = "start_timer"
        description: str = "Start a timer for a task."
        args_schema: type = StartTimerInput

        def _run(self, task: str, project: str = "general") -> str:
            skill = TimeTrackerSkill()
            result = skill.start_timer(task, project)
            return json.dumps(result, ensure_ascii=False)

    class StopTimerInput(BaseModel):
        notes: str = Field(default="", description="Notes about what was done")

    class StopTimerTool(BaseTool):
        name: str = "stop_timer"
        description: str = "Stop the active timer and log the time entry."
        args_schema: type = StopTimerInput

        def _run(self, notes: str = "") -> str:
            skill = TimeTrackerSkill()
            result = skill.stop_timer(notes)
            return json.dumps(result, ensure_ascii=False)

    class LogTimeInput(BaseModel):
        task: str = Field(description="Task name")
        minutes: float = Field(description="Time spent in minutes")
        project: str = Field(default="general", description="Project name")
        notes: str = Field(default="", description="Notes")

    class LogTimeTool(BaseTool):
        name: str = "log_time"
        description: str = "Manually log time spent on a task."
        args_schema: type = LogTimeInput

        def _run(self, task: str, minutes: float, project: str = "general", notes: str = "") -> str:
            skill = TimeTrackerSkill()
            result = skill.log_time(task, minutes, project, notes=notes)
            return json.dumps(result, ensure_ascii=False)

    class TimeSummaryInput(BaseModel):
        days: int = Field(default=7, description="Number of days to summarize")
        project: str | None = Field(default=None, description="Filter by project")

    class TimeSummaryTool(BaseTool):
        name: str = "time_summary"
        description: str = "Get time tracking summary for a period."
        args_schema: type = TimeSummaryInput

        def _run(self, days: int = 7, project: str | None = None) -> str:
            skill = TimeTrackerSkill()
            result = skill.get_summary(days=days, project=project)
            return json.dumps(result, ensure_ascii=False)

    class ActiveTimerTool(BaseTool):
        name: str = "active_timer"
        description: str = "Check if there's an active timer running."

        def _run(self) -> str:
            skill = TimeTrackerSkill()
            result = skill.get_active_timer()
            return json.dumps(result, ensure_ascii=False)

    return [StartTimerTool(), StopTimerTool(), LogTimeTool(), TimeSummaryTool(), ActiveTimerTool()]
