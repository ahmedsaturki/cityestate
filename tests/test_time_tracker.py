"""
Tests for Time Tracker Skill
"""
import pytest
from src.skills.time_tracker import TimeTrackerSkill


@pytest.fixture
def skill(tmp_path):
    import src.skills.time_tracker as tt
    original = tt.TIME_FILE
    tt.TIME_FILE = tmp_path / "time.json"
    s = TimeTrackerSkill()
    yield s
    tt.TIME_FILE = original


class TestTimerOperations:
    def test_start_timer(self, skill):
        result = skill.start_timer("Coding", "project1")
        assert result["status"] == "started"
        assert result["timer"]["task"] == "Coding"

    def test_active_timer(self, skill):
        skill.start_timer("Task")
        result = skill.get_active_timer()
        assert result["status"] == "running"

    def test_no_active_timer(self, skill):
        result = skill.get_active_timer()
        assert result["status"] == "no_active_timer"

    def test_double_start(self, skill):
        skill.start_timer("Task 1")
        result = skill.start_timer("Task 2")
        assert result["status"] == "error"

    def test_stop_timer(self, skill):
        skill.start_timer("Task")
        result = skill.stop_timer(notes="Done")
        assert result["status"] == "stopped"
        assert "duration_minutes" in result["entry"]

    def test_stop_without_start(self, skill):
        result = skill.stop_timer()
        assert result["status"] == "error"


class TestManualLogging:
    def test_log_time(self, skill):
        result = skill.log_time("Meeting", 30, "work")
        assert result["status"] == "logged"
        assert result["entry"]["duration_minutes"] == 30

    def test_log_with_notes(self, skill):
        result = skill.log_time("Call", 15, notes="Client follow-up")
        assert result["entry"]["notes"] == "Client follow-up"


class TestTimeSummary:
    def test_summary(self, skill):
        skill.log_time("Task 1", 60)
        skill.log_time("Task 2", 30)
        result = skill.get_summary(days=30)
        assert result["total_entries"] == 2
        assert result["total_minutes"] == 90

    def test_summary_by_project(self, skill):
        skill.log_time("Task 1", 60, project="proj_a")
        skill.log_time("Task 2", 30, project="proj_b")
        result = skill.get_summary(days=30, project="proj_a")
        assert result["total_entries"] == 1

    def test_daily_report(self, skill):
        skill.log_time("Today Task", 45)
        result = skill.get_daily_report()
        assert result["total_entries"] >= 1


class TestTimeFormatting:
    def test_format_hours_minutes(self, skill):
        result = skill._format_duration(125)
        assert "2h" in result and "5m" in result

    def test_format_minutes_only(self, skill):
        result = skill._format_duration(30)
        assert result == "30m"


class TestEntryDeletion:
    def test_delete_entry(self, skill):
        logged = skill.log_time("Delete Me", 10)
        result = skill.delete_entry(logged["entry"]["id"])
        assert result["status"] == "deleted"
