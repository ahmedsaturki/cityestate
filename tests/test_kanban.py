"""
Tests for Kanban Board Skill
"""
import pytest
from src.skills.kanban_board import KanbanSkill


@pytest.fixture
def skill(tmp_path):
    import src.skills.kanban_board as kb
    original = kb.KANBAN_FILE
    kb.KANBAN_FILE = tmp_path / "kanban.json"
    s = KanbanSkill()
    yield s
    kb.KANBAN_FILE = original


class TestBoardCreation:
    def test_create_board(self, skill):
        result = skill.create_board("Test Board")
        assert result["status"] == "created"
        assert "Backlog" in result["columns"]

    def test_create_custom_board(self, skill):
        result = skill.create_board("Custom", ["Todo", "Doing", "Done"])
        assert result["columns"] == ["Todo", "Doing", "Done"]


class TestCardManagement:
    def test_add_card(self, skill):
        skill.create_board("Board1")
        result = skill.add_card("Board1", "To Do", "Test Card")
        assert result["status"] == "card_added"
        assert result["card"]["title"] == "Test Card"

    def test_add_card_to_nonexistent_board(self, skill):
        result = skill.add_card("NoBoard", "To Do", "Card")
        assert result["status"] == "error"

    def test_add_card_to_nonexistent_column(self, skill):
        skill.create_board("Board2")
        result = skill.add_card("Board2", "NoColumn", "Card")
        assert result["status"] == "error"


class TestCardMovement:
    def test_move_card(self, skill):
        skill.create_board("MoveBoard")
        card = skill.add_card("MoveBoard", "To Do", "Move Me")
        result = skill.move_card("MoveBoard", card["card"]["id"], "To Do", "In Progress")
        assert result["status"] == "moved"

    def test_move_nonexistent_card(self, skill):
        skill.create_board("MoveBoard2")
        result = skill.move_card("MoveBoard2", "CARD-9999", "To Do", "Done")
        assert result["status"] == "error"


class TestBoardRetrieval:
    def test_get_board(self, skill):
        skill.create_board("GetBoard")
        skill.add_card("GetBoard", "To Do", "Card 1")
        result = skill.get_board("GetBoard")
        assert result["total_cards"] == 1

    def test_list_boards(self, skill):
        skill.create_board("Board A")
        skill.create_board("Board B")
        result = skill.list_boards()
        assert result["count"] == 2


class TestLabels:
    def test_add_label(self, skill):
        skill.create_board("LabelBoard")
        card = skill.add_card("LabelBoard", "To Do", "Labeled")
        result = skill.add_label("LabelBoard", card["card"]["id"], "urgent")
        assert "urgent" in result["labels"]
