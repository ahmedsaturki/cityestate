"""
Kanban Board Skill — لوحة كانبان
==================================
Visual task management with columns, cards, and workflow tracking.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("skills.kanban")

KANBAN_FILE = Path("data/kanban.json")


class KanbanSkill:
    """Kanban board management skill."""

    def __init__(self):
        self._boards = self._load_boards()

    def _load_boards(self) -> dict:
        if KANBAN_FILE.exists():
            try:
                return json.loads(KANBAN_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_boards(self):
        KANBAN_FILE.parent.mkdir(parents=True, exist_ok=True)
        KANBAN_FILE.write_text(json.dumps(self._boards, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_board(self, board_name: str, columns: list[str] | None = None) -> dict:
        """Create a new Kanban board."""
        if not columns:
            columns = ["Backlog", "To Do", "In Progress", "Review", "Done"]

        board = {
            "name": board_name,
            "columns": {col: [] for col in columns},
            "created_at": datetime.now().isoformat(),
        }

        self._boards[board_name] = board
        self._save_boards()
        return {"status": "created", "board": board_name, "columns": columns}

    def add_card(self, board_name: str, column: str, title: str, description: str = "", assignee: str = "", priority: str = "medium") -> dict:
        """Add a card to a column."""
        if board_name not in self._boards:
            return {"status": "error", "error": f"Board '{board_name}' not found"}

        board = self._boards[board_name]
        if column not in board["columns"]:
            return {"status": "error", "error": f"Column '{column}' not found"}

        card = {
            "id": f"CARD-{sum(len(cards) for cards in board['columns'].values()) + 1:04d}",
            "title": title,
            "description": description,
            "assignee": assignee,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "moved_at": datetime.now().isoformat(),
            "labels": [],
            "due_date": None,
        }

        board["columns"][column].append(card)
        self._save_boards()
        return {"status": "card_added", "card": card, "column": column}

    def move_card(self, board_name: str, card_id: str, from_column: str, to_column: str) -> dict:
        """Move a card from one column to another."""
        if board_name not in self._boards:
            return {"status": "error", "error": f"Board '{board_name}' not found"}

        board = self._boards[board_name]
        if from_column not in board["columns"] or to_column not in board["columns"]:
            return {"status": "error", "error": "Column not found"}

        card = None
        for i, c in enumerate(board["columns"][from_column]):
            if c["id"] == card_id:
                card = board["columns"][from_column].pop(i)
                break

        if not card:
            return {"status": "error", "error": f"Card {card_id} not found in {from_column}"}

        card["moved_at"] = datetime.now().isoformat()
        board["columns"][to_column].append(card)
        self._save_boards()
        return {"status": "moved", "card": card, "from": from_column, "to": to_column}

    def get_board(self, board_name: str) -> dict:
        """Get full board state."""
        if board_name not in self._boards:
            return {"status": "error", "error": f"Board '{board_name}' not found"}

        board = self._boards[board_name]
        summary = {}
        for col, cards in board["columns"].items():
            summary[col] = {
                "count": len(cards),
                "cards": cards,
            }

        return {"board": board_name, "columns": summary, "total_cards": sum(len(cards) for cards in board["columns"].values())}

    def list_boards(self) -> dict:
        """List all boards."""
        boards = []
        for name, board in self._boards.items():
            total = sum(len(cards) for cards in board["columns"].values())
            boards.append({"name": name, "columns": list(board["columns"].keys()), "total_cards": total})
        return {"boards": boards, "count": len(boards)}

    def add_label(self, board_name: str, card_id: str, label: str) -> dict:
        """Add a label to a card."""
        if board_name not in self._boards:
            return {"status": "error", "error": f"Board '{board_name}' not found"}

        for cards in self._boards[board_name]["columns"].values():
            for card in cards:
                if card["id"] == card_id:
                    if label not in card["labels"]:
                        card["labels"].append(label)
                        self._save_boards()
                    return {"status": "labeled", "card_id": card_id, "labels": card["labels"]}
        return {"status": "error", "error": f"Card {card_id} not found"}

    def get_card(self, board_name: str, card_id: str) -> dict | None:
        """Get a specific card."""
        if board_name not in self._boards:
            return None

        for col, cards in self._boards[board_name]["columns"].items():
            for card in cards:
                if card["id"] == card_id:
                    return {**card, "column": col}
        return None


def get_kanban_tools():
    """Return CrewAI-compatible tools for Kanban."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class CreateBoardInput(BaseModel):
        board_name: str = Field(description="Board name")
        columns: str = Field(default="", description="Comma-separated column names (optional)")

    class CreateBoardTool(BaseTool):
        name: str = "create_kanban_board"
        description: str = "Create a Kanban board with columns."
        args_schema: type = CreateBoardInput

        def _run(self, board_name: str, columns: str = "") -> str:
            skill = KanbanSkill()
            cols = [c.strip() for c in columns.split(",") if c.strip()] if columns else None
            result = skill.create_board(board_name, cols)
            return json.dumps(result, ensure_ascii=False)

    class AddCardInput(BaseModel):
        board_name: str = Field(description="Board name")
        column: str = Field(description="Column name")
        title: str = Field(description="Card title")
        description: str = Field(default="", description="Card description")
        priority: str = Field(default="medium", description="Priority: low, medium, high, critical")

    class AddCardTool(BaseTool):
        name: str = "add_kanban_card"
        description: str = "Add a card to a Kanban board column."
        args_schema: type = AddCardInput

        def _run(self, board_name: str, column: str, title: str, description: str = "", priority: str = "medium") -> str:
            skill = KanbanSkill()
            result = skill.add_card(board_name, column, title, description, priority=priority)
            return json.dumps(result, ensure_ascii=False)

    class MoveCardInput(BaseModel):
        board_name: str = Field(description="Board name")
        card_id: str = Field(description="Card ID")
        from_column: str = Field(description="Source column")
        to_column: str = Field(description="Destination column")

    class MoveCardTool(BaseTool):
        name: str = "move_kanban_card"
        description: str = "Move a card from one column to another."
        args_schema: type = MoveCardInput

        def _run(self, board_name: str, card_id: str, from_column: str, to_column: str) -> str:
            skill = KanbanSkill()
            result = skill.move_card(board_name, card_id, from_column, to_column)
            return json.dumps(result, ensure_ascii=False)

    class GetBoardInput(BaseModel):
        board_name: str = Field(description="Board name")

    class GetBoardTool(BaseTool):
        name: str = "get_kanban_board"
        description: str = "Get full Kanban board state with all cards."
        args_schema: type = GetBoardInput

        def _run(self, board_name: str) -> str:
            skill = KanbanSkill()
            result = skill.get_board(board_name)
            return json.dumps(result, ensure_ascii=False)

    return [CreateBoardTool(), AddCardTool(), MoveCardTool(), GetBoardTool()]
