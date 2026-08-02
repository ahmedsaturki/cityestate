"""
Tests for Task Manager Skill
"""
import json
import pytest
from pathlib import Path
from src.skills.task_manager import TaskManagerSkill, Priority, TaskStatus


@pytest.fixture
def skill(tmp_path):
    """Create a TaskManagerSkill with temp file."""
    import src.skills.task_manager as tm
    original = tm.TASKS_FILE
    tm.TASKS_FILE = tmp_path / "tasks.json"
    s = TaskManagerSkill()
    yield s
    tm.TASKS_FILE = original


class TestTaskCreation:
    def test_create_task(self, skill):
        result = skill.create_task("Test Task", "Description", priority="high")
        assert result["status"] == "created"
        assert result["task"]["id"].startswith("TASK-")
        assert result["task"]["title"] == "Test Task"
        assert result["task"]["priority"] == "high"
        assert result["task"]["status"] == "todo"

    def test_create_task_with_deadline(self, skill):
        result = skill.create_task("Deadline Task", deadline="2026-12-31")
        assert result["task"]["deadline"] == "2026-12-31"

    def test_create_task_with_parent(self, skill):
        parent = skill.create_task("Parent Task")
        child = skill.create_task("Child Task", parent_id=parent["task"]["id"])
        assert child["status"] == "created"

    def test_create_multiple_tasks(self, skill):
        skill.create_task("Task 1")
        skill.create_task("Task 2")
        skill.create_task("Task 3")
        result = skill.list_tasks()
        assert result["total"] == 3


class TestTaskUpdate:
    def test_update_status(self, skill):
        created = skill.create_task("Update Test")
        task_id = created["task"]["id"]
        result = skill.update_task(task_id, status="in_progress")
        assert result["status"] == "updated"
        assert result["task"]["status"] == "in_progress"

    def test_complete_task(self, skill):
        created = skill.create_task("Complete Test")
        task_id = created["task"]["id"]
        result = skill.update_task(task_id, status="done")
        assert result["task"]["completed_at"] is not None

    def test_update_nonexistent(self, skill):
        result = skill.update_task("TASK-9999", status="done")
        assert result["status"] == "error"


class TestTaskListing:
    def test_list_all(self, skill):
        skill.create_task("Task 1")
        skill.create_task("Task 2")
        result = skill.list_tasks()
        assert result["total"] == 2

    def test_filter_by_status(self, skill):
        t1 = skill.create_task("Todo Task")
        t2 = skill.create_task("Done Task")
        skill.update_task(t2["task"]["id"], status="done")
        result = skill.list_tasks(status="todo")
        assert result["total"] == 1

    def test_filter_by_priority(self, skill):
        skill.create_task("High Task", priority="high")
        skill.create_task("Low Task", priority="low")
        result = skill.list_tasks(priority="high")
        assert result["total"] == 1


class TestTaskProgress:
    def test_progress_report(self, skill):
        skill.create_task("Task 1")
        skill.create_task("Task 2")
        t3 = skill.create_task("Task 3")
        skill.update_task(t3["task"]["id"], status="done")
        report = skill.get_progress_report()
        assert report["total"] == 3
        assert report["completed"] == 1
        assert report["progress_percent"] > 0


class TestTaskTags:
    def test_add_tag(self, skill):
        created = skill.create_task("Tagged Task")
        result = skill.add_tag(created["task"]["id"], "urgent")
        assert "urgent" in result["tags"]


class TestTaskDelete:
    def test_delete_task(self, skill):
        created = skill.create_task("Delete Me")
        result = skill.delete_task(created["task"]["id"])
        assert result["status"] == "deleted"
        assert skill.get_task(created["task"]["id"]) is None


class TestOverdueTasks:
    def test_overdue_detection(self, skill):
        skill.create_task("Overdue", deadline="2020-01-01")
        result = skill.get_overdue_tasks()
        assert result["overdue"] >= 1
