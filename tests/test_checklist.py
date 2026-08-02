"""
Tests for Checklist Builder Skill
"""
import pytest
from src.skills.checklist_builder import ChecklistSkill, TEMPLATES


@pytest.fixture
def skill(tmp_path):
    import src.skills.checklist_builder as cb
    original = cb.CHECKLISTS_FILE
    cb.CHECKLISTS_FILE = tmp_path / "checklists.json"
    s = ChecklistSkill()
    yield s
    cb.CHECKLISTS_FILE = original


class TestChecklistCreation:
    def test_create_checklist(self, skill):
        result = skill.create_checklist("My List", ["Item 1", "Item 2", "Item 3"])
        assert result["status"] == "created"
        assert len(result["checklist"]["items"]) == 3

    def test_create_empty_checklist(self, skill):
        result = skill.create_checklist("Empty List", [])
        assert result["status"] == "created"
        assert len(result["checklist"]["items"]) == 0


class TestTemplates:
    def test_get_templates(self, skill):
        result = skill.get_templates()
        assert len(result["templates"]) == len(TEMPLATES)

    def test_create_from_template(self, skill):
        result = skill.create_from_template("property_listing")
        assert result["status"] == "created"
        assert result["checklist"]["category"] == "property_listing"
        assert len(result["checklist"]["items"]) > 0

    def test_create_from_template_with_custom(self, skill):
        result = skill.create_from_template("client_onboarding", custom_items=["Custom step"])
        assert len(result["checklist"]["items"]) > 0

    def test_invalid_template(self, skill):
        result = skill.create_from_template("nonexistent")
        assert result["status"] == "error"


class TestChecklistItems:
    def test_toggle_item(self, skill):
        created = skill.create_checklist("Toggle", ["A", "B"])
        result = skill.toggle_item(created["checklist"]["id"], 0)
        assert result["status"] == "toggled"
        assert result["completed_count"] == 1

    def test_toggle_back(self, skill):
        created = skill.create_checklist("Toggle Back", ["A"])
        skill.toggle_item(created["checklist"]["id"], 0)
        result = skill.toggle_item(created["checklist"]["id"], 0)
        assert result["completed_count"] == 0

    def test_add_item(self, skill):
        created = skill.create_checklist("Add", ["A"])
        result = skill.add_item(created["checklist"]["id"], "B")
        assert result["total_items"] == 2

    def test_remove_item(self, skill):
        created = skill.create_checklist("Remove", ["A", "B"])
        result = skill.remove_item(created["checklist"]["id"], 0)
        assert result["remaining"] == 1

    def test_invalid_index(self, skill):
        created = skill.create_checklist("Invalid", ["A"])
        result = skill.toggle_item(created["checklist"]["id"], 5)
        assert result["status"] == "error"


class TestChecklistProgress:
    def test_completion_detection(self, skill):
        created = skill.create_checklist("Complete", ["A", "B"])
        skill.toggle_item(created["checklist"]["id"], 0)
        skill.toggle_item(created["checklist"]["id"], 1)
        cl = skill.get_checklist(created["checklist"]["id"])
        assert cl["completed_at"] is not None

    def test_list_with_progress(self, skill):
        created = skill.create_checklist("Progress", ["A", "B", "C"])
        skill.toggle_item(created["checklist"]["id"], 0)
        result = skill.list_checklists()
        assert result["total"] == 1
        assert result["checklists"][0]["progress"]["percent"] > 0


class TestChecklistDelete:
    def test_delete_checklist(self, skill):
        created = skill.create_checklist("Delete", ["A"])
        result = skill.delete_checklist(created["checklist"]["id"])
        assert result["status"] == "deleted"
