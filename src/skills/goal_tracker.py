"""
Goal Tracker Skill — متتبع الأهداف
====================================
Goal setting, milestone tracking, progress measurement, and OKR support.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("skills.goal_tracker")

GOALS_FILE = Path("data/goals.json")


class GoalTrackerSkill:
    """Goal setting and tracking skill."""

    def __init__(self):
        self._goals = self._load_goals()

    def _load_goals(self) -> list[dict]:
        if GOALS_FILE.exists():
            try:
                return json.loads(GOALS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_goals(self):
        GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        GOALS_FILE.write_text(json.dumps(self._goals, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_goal(
        self,
        title: str,
        description: str = "",
        category: str = "general",
        target_value: float | None = None,
        unit: str | None = None,
        deadline: str | None = None,
        parent_id: str | None = None,
    ) -> dict:
        """Create a new goal."""
        goal_id = f"GOAL-{len(self._goals) + 1:04d}"
        now = datetime.now().isoformat()

        goal = {
            "id": goal_id,
            "title": title,
            "description": description,
            "category": category,
            "status": "active",
            "target_value": target_value,
            "current_value": 0,
            "unit": unit,
            "deadline": deadline,
            "parent_id": parent_id,
            "milestones": [],
            "key_results": [],
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }

        if parent_id:
            for g in self._goals:
                if g["id"] == parent_id:
                    g.setdefault("sub_goals", []).append(goal_id)
                    break

        self._goals.append(goal)
        self._save_goals()
        return {"status": "created", "goal": goal}

    def update_goal(self, goal_id: str, **kwargs) -> dict:
        """Update a goal."""
        for goal in self._goals:
            if goal["id"] == goal_id:
                for key, value in kwargs.items():
                    if key in goal and key not in ("id", "created_at"):
                        goal[key] = value
                goal["updated_at"] = datetime.now().isoformat()

                if kwargs.get("status") == "completed":
                    goal["completed_at"] = datetime.now().isoformat()

                self._save_goals()
                return {"status": "updated", "goal": goal}
        return {"status": "error", "error": f"Goal {goal_id} not found"}

    def add_milestone(self, goal_id: str, title: str, target_date: str | None = None) -> dict:
        """Add a milestone to a goal."""
        for goal in self._goals:
            if goal["id"] == goal_id:
                milestone = {
                    "id": f"MS-{len(goal['milestones']) + 1:03d}",
                    "title": title,
                    "target_date": target_date,
                    "completed": False,
                    "completed_at": None,
                }
                goal["milestones"].append(milestone)
                self._save_goals()
                return {"status": "milestone_added", "goal_id": goal_id, "milestone": milestone}
        return {"status": "error", "error": f"Goal {goal_id} not found"}

    def complete_milestone(self, goal_id: str, milestone_id: str) -> dict:
        """Mark a milestone as completed."""
        for goal in self._goals:
            if goal["id"] == goal_id:
                for ms in goal["milestones"]:
                    if ms["id"] == milestone_id:
                        ms["completed"] = True
                        ms["completed_at"] = datetime.now().isoformat()
                        self._save_goals()
                        return {"status": "milestone_completed", "goal_id": goal_id, "milestone": ms}
                return {"status": "error", "error": f"Milestone {milestone_id} not found"}
        return {"status": "error", "error": f"Goal {goal_id} not found"}

    def add_key_result(self, goal_id: str, title: str, target_value: float, unit: str = "") -> dict:
        """Add a key result (OKR style) to a goal."""
        for goal in self._goals:
            if goal["id"] == goal_id:
                kr = {
                    "id": f"KR-{len(goal['key_results']) + 1:03d}",
                    "title": title,
                    "target_value": target_value,
                    "current_value": 0,
                    "unit": unit,
                }
                goal["key_results"].append(kr)
                self._save_goals()
                return {"status": "kr_added", "goal_id": goal_id, "key_result": kr}
        return {"status": "error", "error": f"Goal {goal_id} not found"}

    def update_key_result(self, goal_id: str, kr_id: str, current_value: float) -> dict:
        """Update key result progress."""
        for goal in self._goals:
            if goal["id"] == goal_id:
                for kr in goal["key_results"]:
                    if kr["id"] == kr_id:
                        kr["current_value"] = current_value
                        self._save_goals()
                        progress = (current_value / kr["target_value"] * 100) if kr["target_value"] > 0 else 0
                        return {"status": "kr_updated", "kr": kr, "progress_percent": round(progress, 1)}
                return {"status": "error", "error": f"Key result {kr_id} not found"}
        return {"status": "error", "error": f"Goal {goal_id} not found"}

    def record_progress(self, goal_id: str, value: float, note: str = "") -> dict:
        """Record progress toward a goal's target."""
        for goal in self._goals:
            if goal["id"] == goal_id:
                goal["current_value"] = value
                goal["updated_at"] = datetime.now().isoformat()
                if note:
                    goal.setdefault("progress_notes", []).append({
                        "date": datetime.now().isoformat(),
                        "value": value,
                        "note": note,
                    })
                self._save_goals()
                progress = (value / goal["target_value"] * 100) if goal.get("target_value") else 0
                return {"status": "progress_recorded", "goal_id": goal_id, "current": value, "progress_percent": min(round(progress, 1), 100)}
        return {"status": "error", "error": f"Goal {goal_id} not found"}

    def get_goal(self, goal_id: str) -> dict | None:
        """Get a goal by ID."""
        for goal in self._goals:
            if goal["id"] == goal_id:
                return goal
        return None

    def list_goals(self, status: str | None = None, category: str | None = None) -> dict:
        """List all goals with optional filters."""
        filtered = self._goals
        if status:
            filtered = [g for g in filtered if g["status"] == status]
        if category:
            filtered = [g for g in filtered if g["category"] == category]

        for goal in filtered:
            goal["progress_percent"] = self._calc_progress(goal)

        return {
            "total": len(filtered),
            "goals": filtered,
            "summary": {
                "active": sum(1 for g in filtered if g["status"] == "active"),
                "completed": sum(1 for g in filtered if g["status"] == "completed"),
                "paused": sum(1 for g in filtered if g["status"] == "paused"),
            },
        }

    def get_dashboard(self) -> dict:
        """Get a goal dashboard with overall progress."""
        goals = self._goals
        active = [g for g in goals if g["status"] == "active"]
        completed = [g for g in goals if g["status"] == "completed"]

        avg_progress = 0
        if active:
            avg_progress = sum(self._calc_progress(g) for g in active) / len(active)

        return {
            "total_goals": len(goals),
            "active": len(active),
            "completed": len(completed),
            "average_progress": round(avg_progress, 1),
            "goals_at_risk": self._get_at_risk_goals(active),
            "top_performers": sorted(active, key=lambda g: self._calc_progress(g), reverse=True)[:3],
        }

    def _calc_progress(self, goal: dict) -> float:
        """Calculate goal progress percentage."""
        if goal.get("target_value") and goal.get("current_value") is not None:
            return min(round((goal["current_value"] / goal["target_value"]) * 100, 1), 100)
        if goal.get("milestones"):
            completed = sum(1 for ms in goal["milestones"] if ms.get("completed"))
            return round((completed / len(goal["milestones"])) * 100, 1)
        return 0

    def _get_at_risk_goals(self, goals: list) -> list:
        """Find goals that are at risk (deadline approaching, low progress)."""
        at_risk = []
        now = datetime.now()
        for goal in goals:
            if goal.get("deadline"):
                deadline = datetime.fromisoformat(goal["deadline"])
                days_left = (deadline - now).days
                progress = self._calc_progress(goal)
                if days_left <= 7 and progress < 50:
                    at_risk.append({**goal, "days_left": days_left, "progress": progress})
        return at_risk


def get_goal_tools():
    """Return CrewAI-compatible tools for goal tracking."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class CreateGoalInput(BaseModel):
        title: str = Field(description="Goal title")
        description: str = Field(default="", description="Goal description")
        category: str = Field(default="general", description="Category")
        target_value: float | None = Field(default=None, description="Target value")
        unit: str | None = Field(default=None, description="Unit of measurement")
        deadline: str | None = Field(default=None, description="Deadline (ISO format)")

    class CreateGoalTool(BaseTool):
        name: str = "create_goal"
        description: str = "Create a new goal with target value, category, and deadline."
        args_schema: type = CreateGoalInput

        def _run(self, title: str, description: str = "", category: str = "general", target_value: float | None = None, unit: str | None = None, deadline: str | None = None) -> str:
            skill = GoalTrackerSkill()
            result = skill.create_goal(title, description, category, target_value, unit, deadline)
            return json.dumps(result, ensure_ascii=False)

    class UpdateGoalInput(BaseModel):
        goal_id: str = Field(description="Goal ID (e.g., GOAL-0001)")
        status: str | None = Field(default=None, description="New status: active, completed, paused")
        current_value: float | None = Field(default=None, description="Current progress value")

    class UpdateGoalTool(BaseTool):
        name: str = "update_goal"
        description: str = "Update a goal's status or record progress."
        args_schema: type = UpdateGoalInput

        def _run(self, goal_id: str, status: str | None = None, current_value: float | None = None) -> str:
            skill = GoalTrackerSkill()
            if current_value is not None:
                return json.dumps(skill.record_progress(goal_id, current_value), ensure_ascii=False)
            kwargs = {k: v for k, v in {"status": status}.items() if v is not None}
            result = skill.update_goal(goal_id, **kwargs)
            return json.dumps(result, ensure_ascii=False)

    class GoalDashboardTool(BaseTool):
        name: str = "goal_dashboard"
        description: str = "Get overall goal dashboard with progress, at-risk goals, and summary."

        def _run(self) -> str:
            skill = GoalTrackerSkill()
            result = skill.get_dashboard()
            return json.dumps(result, ensure_ascii=False)

    return [CreateGoalTool(), UpdateGoalTool(), GoalDashboardTool()]
