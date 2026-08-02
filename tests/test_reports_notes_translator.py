"""
Tests for Report Generator, Notes, and Translator Skills
"""
import pytest


# --- Report Generator ---
class TestReportGenerator:
    def test_property_report(self):
        from src.skills.report_generator import ReportGeneratorSkill
        skill = ReportGeneratorSkill()
        report = skill.generate_property_report({
            "title": "Test Property",
            "location": "Cairo",
            "price": "5000000",
            "type": "apartment",
        })
        assert "Test Property" in report
        assert "Cairo" in report

    def test_market_report(self):
        from src.skills.report_generator import ReportGeneratorSkill
        skill = ReportGeneratorSkill()
        report = skill.generate_market_report({"area": "Sheikh Zayed", "condition": "Growing"})
        assert "Sheikh Zayed" in report

    def test_client_report(self):
        from src.skills.report_generator import ReportGeneratorSkill
        skill = ReportGeneratorSkill()
        report = skill.generate_client_report({"name": "Ahmed", "budget": "3M EGP"})
        assert "Ahmed" in report

    def test_performance_report(self):
        from src.skills.report_generator import ReportGeneratorSkill
        skill = ReportGeneratorSkill()
        report = skill.generate_performance_report({"leads": 50, "deals": 5})
        assert "50" in report

    def test_save_report(self, tmp_path):
        from src.skills.report_generator import ReportGeneratorSkill
        skill = ReportGeneratorSkill()
        result = skill.save_report("# Test Report", "test.md", "general")
        assert result["status"] == "saved"


# --- Notes & Brainstorming ---
class TestNotes:
    @pytest.fixture
    def skill(self, tmp_path):
        from src.skills import notes_brainstorming as nb
        original = nb.NOTES_FILE
        nb.NOTES_FILE = tmp_path / "notes.json"
        s = nb.NotesSkill()
        yield s
        nb.NOTES_FILE = original

    def test_create_note(self, skill):
        result = skill.create_note("My Note", "Content here")
        assert result["status"] == "created"
        assert result["note"]["id"].startswith("NOTE-")

    def test_search_notes(self, skill):
        skill.create_note("Python Tips", "Use list comprehensions")
        skill.create_note("Java Tips", "Use streams")
        result = skill.search_notes("Python")
        assert result["results"] == 1

    def test_pin_note(self, skill):
        created = skill.create_note("Pin Me", "Content")
        result = skill.pin_note(created["note"]["id"])
        assert result["status"] == "pinned"

    def test_update_note(self, skill):
        created = skill.create_note("Original", "Content")
        result = skill.update_note(created["note"]["id"], "Updated content")
        assert result["note"]["content"] == "Updated content"

    def test_delete_note(self, skill):
        created = skill.create_note("Delete", "Me")
        result = skill.delete_note(created["note"]["id"])
        assert result["status"] == "deleted"

    def test_brainstorm(self, skill):
        result = skill.brainstorm("Marketing Ideas", ["Social media", "SEO", "Cold calls"])
        assert result["status"] == "brainstormed"
        assert len(result["session"]["ideas"]) == 3

    def test_quick_idea(self, skill):
        result = skill.add_idea("coding", "Add dark mode")
        assert result["status"] == "created"


# --- Translator ---
class TestTranslator:
    def test_detect_language(self):
        from src.skills.translator import TranslatorSkill
        import asyncio
        skill = TranslatorSkill()
        result = asyncio.run(skill.detect_language("مرحبا بالعالم"))
        assert result["status"] == "success"
        assert result["language"] == "ar"

    def test_translate_arabic_to_english(self):
        from src.skills.translator import TranslatorSkill
        import asyncio
        skill = TranslatorSkill()
        result = asyncio.run(skill.translate("مرحبا", target_lang="en"))
        assert result["status"] == "success"
        assert len(result["translated"]) > 0

    def test_common_phrases(self):
        from src.skills.translator import TranslatorSkill
        skill = TranslatorSkill()
        phrases = skill.get_common_phrases("ar")
        assert "greeting" in phrases["phrases"]
