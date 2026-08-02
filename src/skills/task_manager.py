"""
Task Manager Skill — مدير المهام
==================================
Full task management: create, update, prioritize, track, and report on tasks.
Supports deadlines, priorities, categories, and progress tracking.
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

logger = logging.getLogger("skills.task_manager")

TASKS_FILE = Path("data/tasks.json")


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"


class TaskManagerSkill:
    """Task management and tracking skill."""

    def __init__(self):
        self._tasks = self._load_tasks()

    def _load_tasks(self) -> list[dict]:
        """Load tasks from file."""
        if TASKS_FILE.exists():
            try:
                return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_tasks(self):
        """Save tasks to file."""
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(json.dumps(self._tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        category: str = "general",
        deadline: str | None = None,
        assignee: str | None = None,
        parent_id: str | None = None,
    ) -> dict:
        """Create a new task."""
        task_id = f"TASK-{len(self._tasks) + 1:04d}"
        now = datetime.now().isoformat()

        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": TaskStatus.TODO.value,
            "category": category,
            "deadline": deadline,
            "assignee": assignee,
            "parent_id": parent_id,
            "subtasks": [],
            "tags": [],
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "time_estimate_hours": None,
            "time_spent_hours": 0,
        }

        if parent_id:
            for t in self._tasks:
                if t["id"] == parent_id:
                    t["subtasks"].append(task_id)
                    break

        self._tasks.append(task)
        self._save_tasks()
        return {"status": "created", "task": task}

    def update_task(self, task_id: str, **kwargs) -> dict:
        """Update a task's fields."""
        for task in self._tasks:
            if task["id"] == task_id:
                for key, value in kwargs.items():
                    if key in task and key not in ("id", "created_at"):
                        task[key] = value
                task["updated_at"] = datetime.now().isoformat()

                if kwargs.get("status") == TaskStatus.DONE.value:
                    task["completed_at"] = datetime.now().isoformat()

                self._save_tasks()
                return {"status": "updated", "task": task}
        return {"status": "error", "error": f"Task {task_id} not found"}

    def get_task(self, task_id: str) -> dict | None:
        """Get a task by ID."""
        for task in self._tasks:
            if task["id"] == task_id:
                return task
        return None

    def delete_task(self, task_id: str) -> dict:
        """Delete a task."""
        for i, task in enumerate(self._tasks):
            if task["id"] == task_id:
                self._tasks.pop(i)
                self._save_tasks()
                return {"status": "deleted", "task_id": task_id}
        return {"status": "error", "error": f"Task {task_id} not found"}

    def list_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        assignee: str | None = None,
    ) -> dict:
        """List tasks with optional filters."""
        filtered = self._tasks
        if status:
            filtered = [t for t in filtered if t["status"] == status]
        if priority:
            filtered = [t for t in filtered if t["priority"] == priority]
        if category:
            filtered = [t for t in filtered if t["category"] == category]
        if assignee:
            filtered = [t for t in filtered if t["assignee"] == assignee]

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        filtered.sort(key=lambda t: (priority_order.get(t["priority"], 4), t.get("deadline") or "9999"))

        return {
            "total": len(filtered),
            "tasks": filtered,
            "by_status": self._count_by_status(filtered),
            "by_priority": self._count_by_priority(filtered),
        }

    def get_overdue_tasks(self) -> dict:
        """Get tasks that are past their deadline."""
        now = datetime.now().isoformat()
        overdue = [t for t in self._tasks if t.get("deadline") and t["deadline"] < now and t["status"] != TaskStatus.DONE.value]
        return {"overdue": len(overdue), "tasks": overdue}

    def get_upcoming_tasks(self, days: int = 7) -> dict:
        """Get tasks due in the next N days."""
        now = datetime.now()
        cutoff = (now + timedelta(days=days)).isoformat()
        upcoming = [
            t for t in self._tasks
            if t.get("deadline") and t["deadline"] <= cutoff and t["status"] != TaskStatus.DONE.value
        ]
        return {"upcoming": len(upcoming), "days": days, "tasks": upcoming}

    def get_progress_report(self) -> dict:
        """Generate a progress report."""
        total = len(self._tasks)
        if total == 0:
            return {"total": 0, "completed": 0, "progress_percent": 0}

        completed = sum(1 for t in self._tasks if t["status"] == TaskStatus.DONE.value)
        in_progress = sum(1 for t in self._tasks if t["status"] == TaskStatus.IN_PROGRESS.value)
        blocked = sum(1 for t in self._tasks if t["status"] == TaskStatus.BLOCKED.value)

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked,
            "progress_percent": round((completed / total) * 100, 1),
            "by_category": self._count_by_category(self._tasks),
        }

    def add_tag(self, task_id: str, tag: str) -> dict:
        """Add a tag to a task."""
        for task in self._tasks:
            if task["id"] == task_id:
                if tag not in task["tags"]:
                    task["tags"].append(tag)
                    self._save_tasks()
                return {"status": "tagged", "task_id": task_id, "tags": task["tags"]}
        return {"status": "error", "error": f"Task {task_id} not found"}

    def _count_by_status(self, tasks: list) -> dict:
        counts = {}
        for t in tasks:
            s = t["status"]
            counts[s] = counts.get(s, 0) + 1
        return counts

    def _count_by_priority(self, tasks: list) -> dict:
        counts = {}
        for t in tasks:
            p = t["priority"]
            counts[p] = counts.get(p, 0) + 1
        return counts

    def _count_by_category(self, tasks: list) -> dict:
        counts = {}
        for t in tasks:
            c = t.get("category", "general")
            counts[c] = counts.get(c, 0) + 1
        return counts


def get_task_tools():
    """Return CrewAI-compatible tools for task management."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class CreateTaskInput(BaseModel):
        title: str = Field(description="Task title")
        description: str = Field(default="", description="Task description")
        priority: str = Field(default="medium", description="Priority: critical, high, medium, low")
        category: str = Field(default="general", description="Category")
        deadline: str = Field(default=None, description="Deadline (ISO format)")
        assignee: str | None = Field(default=None, description="Assignee name")

    class CreateTaskTool(BaseTool):
        name: str = "create_task"
        description: str = "Create a new task with title, priority, deadline, and category."
        args_schema: type = CreateTaskInput

        def _run(self, title: str, description: str = "", priority: str = "medium", category: str = "general", deadline: str | None = None, assignee: str | None = None) -> str:
            skill = TaskManagerSkill()
            result = skill.create_task(title, description, priority, category, deadline, assignee)
            return json.dumps(result, ensure_ascii=False)

    class UpdateTaskInput(BaseModel):
        task_id: str = Field(description="Task ID (e.g., TASK-0001)")
        status: str | None = Field(default=None, description="New status: todo, in_progress, blocked, review, done")
        priority: str | None = Field(default=None, description="New priority")
        description: str | None = Field(default=None, description="New description")

    class UpdateTaskTool(BaseTool):
        name: str = "update_task"
        description: str = "Update a task's status, priority, or description."
        args_schema: type = UpdateTaskInput

        def _run(self, task_id: str, status: str | None = None, priority: str | None = None, description: str | None = None) -> str:
            skill = TaskManagerSkill()
            kwargs = {k: v for k, v in {"status": status, "priority": priority, "description": description}.items() if v is not None}
            result = skill.update_task(task_id, **kwargs)
            return json.dumps(result, ensure_ascii=False)

    class ListTasksInput(BaseModel):
        status: str | None = Field(default=None, description="Filter by status")
        priority: str | None = Field(default=None, description="Filter by priority")

    class ListTasksTool(BaseTool):
        name: str = "list_tasks"
        description: str = "List all tasks with optional filters. Shows progress report."
        args_schema: type = ListTasksInput

        def _run(self, status: str | None = None, priority: str | None = None) -> str:
            skill = TaskManagerSkill()
            result = skill.list_tasks(status=status, priority=priority)
            return json.dumps(result, ensure_ascii=False)

    class TaskProgressTool(BaseTool):
        name: str = "task_progress"
        description: str = "Get overall task progress report with completion percentage."

        def _run(self) -> str:
            skill = TaskManagerSkill()
            result = skill.get_progress_report()
            return json.dumps(result, ensure_ascii=False)

    return [CreateTaskTool(), UpdateTaskTool(), ListTasksTool(), TaskProgressTool()]
