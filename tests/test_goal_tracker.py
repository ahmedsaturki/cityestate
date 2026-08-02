"""
Tests for Goal Tracker Skill
"""
import pytest
from src.skills.goal_tracker import GoalTrackerSkill


@pytest.fixture
def skill(tmp_path):
    import src.skills.goal_tracker as gt
    original = gt.GOALS_FILE
    gt.GOALS_FILE = tmp_path / "goals.json"
    s = GoalTrackerSkill()
    yield s
    gt.GOALS_FILE = original


class TestGoalCreation:
    def test_create_goal(self, skill):
        result = skill.create_goal("Revenue Target", target_value=1000000, unit="EGP")
        assert result["status"] == "created"
        assert result["goal"]["id"].startswith("GOAL-")
        assert result["goal"]["target_value"] == 1000000

    def test_create_goal_with_category(self, skill):
        result = skill.create_goal("Marketing Goal", category="marketing")
        assert result["goal"]["category"] == "marketing"

    def test_create_goal_with_deadline(self, skill):
        result = skill.create_goal("Q4 Goal", deadline="2026-12-31")
        assert result["goal"]["deadline"] == "2026-12-31"

    def test_create_subgoal(self, skill):
        parent = skill.create_goal("Parent Goal")
        child = skill.create_goal("Child Goal", parent_id=parent["goal"]["id"])
        assert child["status"] == "created"


class TestGoalProgress:
    def test_record_progress(self, skill):
        created = skill.create_goal("Progress Goal", target_value=100)
        result = skill.record_progress(created["goal"]["id"], 50, note="Halfway there")
        assert result["current"] == 50
        assert result["progress_percent"] == 50.0

    def test_progress_notes(self, skill):
        created = skill.create_goal("Notes Goal", target_value=100)
        skill.record_progress(created["goal"]["id"], 25, note="First quarter")
        skill.record_progress(created["goal"]["id"], 50, note="Second quarter")
        goal = skill.get_goal(created["goal"]["id"])
        assert len(goal["progress_notes"]) == 2

    def test_progress_capped_at_100(self, skill):
        created = skill.create_goal("Cap Goal", target_value=50)
        result = skill.record_progress(created["goal"]["id"], 100)
        assert result["progress_percent"] == 100.0


class TestMilestones:
    def test_add_milestone(self, skill):
        created = skill.create_goal("Milestone Goal")
        result = skill.add_milestone(created["goal"]["id"], "Phase 1", "2026-06-30")
        assert result["status"] == "milestone_added"
        assert result["milestone"]["completed"] is False

    def test_complete_milestone(self, skill):
        created = skill.create_goal("MS Goal")
        ms = skill.add_milestone(created["goal"]["id"], "Phase 1")
        result = skill.complete_milestone(created["goal"]["id"], ms["milestone"]["id"])
        assert result["milestone"]["completed"] is True


class TestKeyResults:
    def test_add_key_result(self, skill):
        created = skill.create_goal("OKR Goal")
        result = skill.add_key_result(created["goal"]["id"], "Increase leads", 100, "leads")
        assert result["key_result"]["target_value"] == 100

    def test_update_key_result(self, skill):
        created = skill.create_goal("KR Goal")
        kr = skill.add_key_result(created["goal"]["id"], "Leads", 100)
        result = skill.update_key_result(created["goal"]["id"], kr["key_result"]["id"], 75)
        assert result["progress_percent"] == 75.0


class TestGoalDashboard:
    def test_dashboard(self, skill):
        skill.create_goal("Active Goal")
        g2 = skill.create_goal("Completed Goal")
        skill.update_goal(g2["goal"]["id"], status="completed")
        dashboard = skill.get_dashboard()
        assert dashboard["total_goals"] == 2
        assert dashboard["active"] == 1
        assert dashboard["completed"] == 1


class TestGoalListing:
    def test_list_goals(self, skill):
        skill.create_goal("Goal 1", category="sales")
        skill.create_goal("Goal 2", category="marketing")
        result = skill.list_goals(category="sales")
        assert result["total"] == 1

    def test_list_by_status(self, skill):
        skill.create_goal("Active")
        g2 = skill.create_goal("Done")
        skill.update_goal(g2["goal"]["id"], status="completed")
        result = skill.list_goals(status="completed")
        assert result["total"] == 1
