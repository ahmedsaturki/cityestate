"""
Skills Routes — واجهات المهارات الجديدة
========================================
API endpoints for Task Manager, Goal Tracker, Kanban, Notes, and Time Tracker.
Security: All endpoints require JWT authentication.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import require_auth

logger = logging.getLogger("api.routes.skills")

router = APIRouter(prefix="/skills", tags=["Skills"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
class TaskCreate(BaseModel):
    title: str
    description: str | None = ""
    assignee: str | None = ""
    priority: str = "medium"
    status: str = "todo"
    due_date: str | None = None
    tags: list[str] = Field(default_factory=list)


class GoalCreate(BaseModel):
    title: str
    description: str | None = ""
    category: str = "other"
    target_value: float = 100
    unit: str = "lead"


class NoteCreate(BaseModel):
    title: str
    content: str | None = ""
    category: str = "general"
    tags: list[str] = Field(default_factory=list)


class BrainstormRequest(BaseModel):
    topic: str


class QuickIdea(BaseModel):
    idea: str


class KanbanBoardCreate(BaseModel):
    name: str
    columns: list[str] = Field(default_factory=lambda: ["todo", "in_progress", "review", "done"])


class KanbanCardCreate(BaseModel):
    title: str
    description: str | None = ""
    column: str = "todo"
    labels: list[str] = Field(default_factory=list)


class CardMove(BaseModel):
    column: str


# ---------------------------------------------------------------------------
# Task Manager Endpoints
# ---------------------------------------------------------------------------
@router.get("/tasks")
def list_tasks(user: dict = Depends(require_auth)):
    """List all tasks."""
    try:
        from src.skills.task_manager import TaskManagerSkill
        tm = TaskManagerSkill()
        tasks = tm.list_tasks()
        return tasks
    except Exception as e:
        logger.error("Failed to list tasks: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {e!s}")


@router.post("/tasks")
def create_task(task: TaskCreate, user: dict = Depends(require_auth)) -> dict:
    """Create a new task."""
    try:
        from src.skills.task_manager import TaskManagerSkill
        tm = TaskManagerSkill()
        result = tm.create_task(
            title=task.title,
            description=task.description,
            assignee=task.assignee,
            priority=task.priority,
            deadline=task.due_date,
        )
        return result
    except Exception as e:
        logger.error("Failed to create task: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create task: {e!s}")


@router.post("/tasks/{task_id}/status")
def update_task_status(task_id: str, data: dict, user: dict = Depends(require_auth)):
    """Update task status."""
    try:
        from src.skills.task_manager import TaskManagerSkill
        tm = TaskManagerSkill()
        result = tm.update_task(task_id, status=data.get("status", "todo"))
        return result
    except Exception as e:
        logger.error("Failed to update task %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to update task: {e!s}")


@router.post("/tasks/{task_id}/delete")
def delete_task(task_id: str, user: dict = Depends(require_auth)) -> dict:
    """Delete a task."""
    try:
        from src.skills.task_manager import TaskManagerSkill
        tm = TaskManagerSkill()
        tm.delete_task(task_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error("Failed to delete task %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {e!s}")


# ---------------------------------------------------------------------------
# Goal Tracker Endpoints
# ---------------------------------------------------------------------------
@router.get("/goals")
def list_goals(user: dict = Depends(require_auth)):
    """List all goals."""
    try:
        from src.skills.goal_tracker import GoalTrackerSkill
        gt = GoalTrackerSkill()
        goals = gt.list_goals()
        return goals
    except Exception as e:
        logger.error("Failed to list goals: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list goals: {e!s}")


@router.post("/goals")
def create_goal(goal: GoalCreate, user: dict = Depends(require_auth)) -> dict:
    """Create a new goal."""
    try:
        from src.skills.goal_tracker import GoalTrackerSkill
        gt = GoalTrackerSkill()
        result = gt.create_goal(
            title=goal.title,
            description=goal.description,
            category=goal.category,
            target_value=goal.target_value,
            unit=goal.unit,
        )
        return result
    except Exception as e:
        logger.error("Failed to create goal: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create goal: {e!s}")


@router.post("/goals/{goal_id}/progress")
def update_goal_progress(goal_id: str, data: dict, user: dict = Depends(require_auth)):
    """Update goal progress."""
    try:
        from src.skills.goal_tracker import GoalTrackerSkill
        gt = GoalTrackerSkill()
        result = gt.record_progress(goal_id, data.get("value", 0))
        return result
    except Exception as e:
        logger.error("Failed to update goal %s: %s", goal_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to update goal: {e!s}")


# ---------------------------------------------------------------------------
# Kanban Endpoints
# ---------------------------------------------------------------------------
@router.get("/kanban/boards")
def list_kanban_boards(user: dict = Depends(require_auth)) -> dict:
    """List all kanban boards."""
    try:
        from src.skills.kanban_board import KanbanSkill
        kb = KanbanSkill()
        boards = kb.list_boards()
        return boards
    except Exception as e:
        logger.error("Failed to list kanban boards: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list boards: {e!s}")


@router.post("/kanban/boards")
def create_kanban_board(board: KanbanBoardCreate, user: dict = Depends(require_auth)):
    """Create a new kanban board."""
    try:
        from src.skills.kanban_board import KanbanSkill
        kb = KanbanSkill()
        result = kb.create_board(board_name=board.name, columns=board.columns)
        return result
    except Exception as e:
        logger.error("Failed to create kanban board: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create board: {e!s}")


@router.get("/kanban/boards/{board_name}")
def get_kanban_board(board_name: str, user: dict = Depends(require_auth)) -> dict:
    """Get a kanban board with all columns and cards."""
    try:
        from src.skills.kanban_board import KanbanSkill
        kb = KanbanSkill()
        board = kb.get_board(board_name)
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")
        return board
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get kanban board %s: %s", board_name, e)
        raise HTTPException(status_code=500, detail=f"Failed to get board: {e!s}")


@router.post("/kanban/boards/{board_name}/cards")
def add_kanban_card(board_name: str, card: KanbanCardCreate, user: dict = Depends(require_auth)):
    """Add a card to a kanban board."""
    try:
        from src.skills.kanban_board import KanbanSkill
        kb = KanbanSkill()
        result = kb.add_card(
            board_name=board_name,
            title=card.title,
            description=card.description,
            column_name=card.column,
            labels=card.labels,
        )
        return result
    except Exception as e:
        logger.error("Failed to add card to board %s: %s", board_name, e)
        raise HTTPException(status_code=500, detail=f"Failed to add card: {e!s}")


@router.post("/kanban/boards/{board_name}/cards/{card_id}/move")
def move_kanban_card(board_name: str, card_id: str, move: CardMove, user: dict = Depends(require_auth)) -> dict:
    """Move a card to a different column."""
    try:
        from src.skills.kanban_board import KanbanSkill
        kb = KanbanSkill()
        result = kb.move_card(board_name, card_id, move.column)
        return result
    except Exception as e:
        logger.error("Failed to move card %s: %s", card_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to move card: {e!s}")


# ---------------------------------------------------------------------------
# Notes Endpoints
# ---------------------------------------------------------------------------
@router.get("/notes")
def list_notes(user: dict = Depends(require_auth)):
    """List all notes."""
    try:
        from src.skills.notes_brainstorming import NotesSkill
        ns = NotesSkill()
        notes = ns.list_notes()
        return notes
    except Exception as e:
        logger.error("Failed to list notes: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list notes: {e!s}")


@router.post("/notes")
def create_note(note: NoteCreate, user: dict = Depends(require_auth)) -> dict:
    """Create a new note."""
    try:
        from src.skills.notes_brainstorming import NotesSkill
        ns = NotesSkill()
        result = ns.create_note(
            title=note.title,
            content=note.content,
            category=note.category,
            tags=note.tags,
        )
        return result
    except Exception as e:
        logger.error("Failed to create note: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create note: {e!s}")


@router.post("/notes/{note_id}/delete")
def delete_note(note_id: str, user: dict = Depends(require_auth)):
    """Delete a note."""
    try:
        from src.skills.notes_brainstorming import NotesSkill
        ns = NotesSkill()
        ns.delete_note(note_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error("Failed to delete note %s: %s", note_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete note: {e!s}")


@router.post("/notes/brainstorm")
def brainstorm_ideas(req: BrainstormRequest, user: dict = Depends(require_auth)) -> dict:
    """Generate brainstorming ideas for a topic."""
    try:
        from src.skills.notes_brainstorming import NotesSkill
        ns = NotesSkill()
        result = ns.brainstorm(topic=req.topic)
        return result
    except Exception as e:
        logger.error("Failed to brainstorm ideas: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to brainstorm: {e!s}")


@router.get("/notes/quick")
def list_quick_notes(user: dict = Depends(require_auth)):
    """List quick notes/ideas."""
    try:
        from src.skills.notes_brainstorming import NotesSkill
        ns = NotesSkill()
        return ns.list_quick_notes()
    except Exception as e:
        logger.error("Failed to list quick notes: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list quick notes: {e!s}")


@router.post("/notes/quick")
def create_quick_note(data: QuickIdea, user: dict = Depends(require_auth)) -> dict:
    """Save a quick idea."""
    try:
        from src.skills.notes_brainstorming import NotesSkill
        ns = NotesSkill()
        result = ns.quick_idea(idea=data.idea)
        return result
    except Exception as e:
        logger.error("Failed to save quick note: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save idea: {e!s}")


# ---------------------------------------------------------------------------
# Time Tracker Endpoints
# ---------------------------------------------------------------------------
@router.get("/time/summary")
def get_time_summary(project: str | None = None, user: dict = Depends(require_auth)):
    """Get time tracking summary."""
    try:
        from src.skills.time_tracker import TimeTrackerSkill
        tt = TimeTrackerSkill()
        summary = tt.get_summary(project=project)
        return summary
    except Exception as e:
        logger.error("Failed to get time summary: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {e!s}")


@router.post("/time/start")
def start_timer(data: dict, user: dict = Depends(require_auth)) -> dict:
    """Start a timer."""
    try:
        from src.skills.time_tracker import TimeTrackerSkill
        tt = TimeTrackerSkill()
        result = tt.start_timer(
            task=data.get("task", ""),
            project=data.get("project", ""),
        )
        return result
    except Exception as e:
        logger.error("Failed to start timer: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to start timer: {e!s}")


@router.post("/time/stop")
def stop_timer(user: dict = Depends(require_auth)):
    """Stop the current timer."""
    try:
        from src.skills.time_tracker import TimeTrackerSkill
        tt = TimeTrackerSkill()
        result = tt.stop_timer()
        return result
    except Exception as e:
        logger.error("Failed to stop timer: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to stop timer: {e!s}")


# ---------------------------------------------------------------------------
# Decision Matrix Endpoints
# ---------------------------------------------------------------------------
@router.post("/decisions/compare")
def compare_properties(data: dict, user: dict = Depends(require_auth)) -> dict:
    """Compare properties using weighted decision matrix."""
    try:
        from src.skills.decision_matrix import DecisionMatrixSkill
        dm = DecisionMatrixSkill()
        result = dm.compare_properties(properties=data.get("properties", []))
        return result
    except Exception as e:
        logger.error("Failed to compare properties: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to compare: {e!s}")


@router.post("/decisions/investment")
def analyze_investment(data: dict, user: dict = Depends(require_auth)):
    """Analyze investment opportunity."""
    try:
        from src.skills.decision_matrix import DecisionMatrixSkill
        dm = DecisionMatrixSkill()
        result = dm.analyze_investment(property_data=data.get("property", {}))
        return result
    except Exception as e:
        logger.error("Failed to analyze investment: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to analyze: {e!s}")


# ---------------------------------------------------------------------------
# Checklist Endpoints
# ---------------------------------------------------------------------------
@router.get("/checklists")
def list_checklists(user: dict = Depends(require_auth)) -> dict:
    """List all checklists."""
    try:
        from src.skills.checklist_builder import ChecklistSkill
        cs = ChecklistSkill()
        return cs.list_checklists()
    except Exception as e:
        logger.error("Failed to list checklists: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list checklists: {e!s}")


@router.post("/checklists")
def create_checklist(data: dict, user: dict = Depends(require_auth)):
    """Create a new checklist from template or custom."""
    try:
        from src.skills.checklist_builder import ChecklistSkill
        cs = ChecklistSkill()
        result = cs.create_checklist(
            name=data.get("name", ""),
            template=data.get("template"),
        )
        return result
    except Exception as e:
        logger.error("Failed to create checklist: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create checklist: {e!s}")


@router.post("/checklists/{checklist_id}/toggle")
def toggle_checklist_item(checklist_id: str, data: dict, user: dict = Depends(require_auth)) -> dict:
    """Toggle a checklist item."""
    try:
        from src.skills.checklist_builder import ChecklistSkill
        cs = ChecklistSkill()
        result = cs.toggle_item(checklist_id, data.get("item_index", 0))
        return result
    except Exception as e:
        logger.error("Failed to toggle checklist item: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to toggle item: {e!s}")


@router.post("/checklists/{checklist_id}/add")
def add_checklist_item(checklist_id: str, data: dict, user: dict = Depends(require_auth)):
    """Add item to checklist."""
    try:
        from src.skills.checklist_builder import ChecklistSkill
        cs = ChecklistSkill()
        result = cs.add_item(checklist_id, data.get("text", ""))
        return result
    except Exception as e:
        logger.error("Failed to add checklist item: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to add item: {e!s}")


# ---------------------------------------------------------------------------
# Lead Scoring Endpoints
# ---------------------------------------------------------------------------
@router.post("/leads/score")
def score_lead(data: dict, user: dict = Depends(require_auth)) -> dict:
    """Score a lead based on multiple factors."""
    try:
        from src.skills.lead_scoring import LeadScoringSkill
        ls = LeadScoringSkill()
        result = ls.score_lead(data)
        return result
    except Exception as e:
        logger.error("Failed to score lead: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to score lead: {e!s}")


@router.post("/leads/match")
def match_lead(data: dict, user: dict = Depends(require_auth)):
    """Auto-match a lead to properties."""
    try:
        from src.skills.lead_scoring import LeadScoringSkill
        ls = LeadScoringSkill()
        lead = data.get("lead", {})
        properties = data.get("properties", [])
        matches = ls.match_lead_to_properties(lead, properties)
        return {"matches": matches}
    except Exception as e:
        logger.error("Failed to match lead: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to match lead: {e!s}")


@router.post("/leads/batch-score")
def batch_score_leads(data: dict, user: dict = Depends(require_auth)) -> dict:
    """Score multiple leads at once."""
    try:
        from src.skills.lead_scoring import LeadScoringSkill
        ls = LeadScoringSkill()
        leads = data.get("leads", [])
        results = ls.score_leads_batch(leads)
        return {"scored_leads": results}
    except Exception as e:
        logger.error("Failed to batch score leads: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to batch score: {e!s}")


@router.get("/leads/scoring-dashboard")
def scoring_dashboard(user: dict = Depends(require_auth)):
    """Get lead scoring dashboard."""
    try:
        from src.skills.lead_scoring import LeadScoringSkill
        ls = LeadScoringSkill()
        return ls.get_scoring_dashboard()
    except Exception as e:
        logger.error("Failed to get scoring dashboard: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {e!s}")
