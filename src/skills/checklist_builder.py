"""
Checklist Builder Skill — منشئ القوائم
=======================================
Generate, manage, and validate checklists for real estate processes.
Supports templates, recurring checklists, and completion tracking.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("skills.checklist")

CHECKLISTS_FILE = Path("data/checklists.json")


TEMPLATES = {
    "property_listing": {
        "name": "Property Listing Checklist",
        "items": [
            "Take high-quality photos (exterior, interior, kitchen, bathroom)",
            "Write compelling property description",
            "Set competitive price based on market analysis",
            "Verify property documents (title deed, permits)",
            "List on major platforms (Aqarmap, OLX, Wasl)",
            "Share on social media groups",
            "Set up WhatsApp broadcast for leads",
            "Schedule open house / viewings",
        ],
    },
    "client_onboarding": {
        "name": "Client Onboarding Checklist",
        "items": [
            "Collect client requirements (budget, area, bedrooms)",
            "Verify identity documents",
            "Sign agency agreement",
            "Set up client in CRM",
            "Create property shortlist",
            "Schedule first viewing",
            "Set follow-up reminders",
        ],
    },
    "closing_deal": {
        "name": "Deal Closing Checklist",
        "items": [
            "Verify buyer/seller identity",
            "Review and finalize contract terms",
            "Arrange property inspection",
            "Verify no outstanding payments/dues",
            "Prepare all required documents",
            "Schedule signing appointment",
            "Process payment/transfer",
            "Update property status to sold",
            "Send confirmation to all parties",
            "File completed documents",
        ],
    },
    "property_inspection": {
        "name": "Property Inspection Checklist",
        "items": [
            "Check structural integrity (walls, ceiling, foundation)",
            "Inspect plumbing (faucets, pipes, water pressure)",
            "Test electrical systems (switches, outlets, breaker)",
            "Check HVAC system functionality",
            "Inspect windows and doors",
            "Check for pest issues",
            "Note cosmetic repairs needed",
            "Photograph any issues found",
        ],
    },
    "morning_routine": {
        "name": "Morning Agent Routine",
        "items": [
            "Check overnight leads and inquiries",
            "Review today's scheduled viewings",
            "Update CRM with yesterday's activities",
            "Check market news and price changes",
            "Post on social media",
            "Review task list for the day",
        ],
    },
}


class ChecklistSkill:
    """Checklist management skill."""

    def __init__(self):
        self._checklists = self._load_checklists()

    def _load_checklists(self) -> list[dict]:
        if CHECKLISTS_FILE.exists():
            try:
                return json.loads(CHECKLISTS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_checklists(self):
        CHECKLISTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CHECKLISTS_FILE.write_text(json.dumps(self._checklists, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_checklist(self, name: str, items: list[str], category: str = "general") -> dict:
        """Create a new checklist."""
        checklist_id = f"CHK-{len(self._checklists) + 1:04d}"
        checklist = {
            "id": checklist_id,
            "name": name,
            "category": category,
            "items": [
                {"text": item, "completed": False, "completed_at": None}
                for item in items
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
        }
        self._checklists.append(checklist)
        self._save_checklists()
        return {"status": "created", "checklist": checklist}

    def create_from_template(self, template_name: str, custom_items: list[str] | None = None) -> dict:
        """Create a checklist from a predefined template."""
        template = TEMPLATES.get(template_name)
        if not template:
            return {"status": "error", "error": f"Template '{template_name}' not found. Available: {list(TEMPLATES.keys())}"}

        items = template["items"]
        if custom_items:
            items.extend(custom_items)

        return self.create_checklist(template["name"], items, category=template_name)

    def get_checklist(self, checklist_id: str) -> dict | None:
        """Get a checklist by ID."""
        for cl in self._checklists:
            if cl["id"] == checklist_id:
                return cl
        return None

    def toggle_item(self, checklist_id: str, item_index: int) -> dict:
        """Toggle completion of a checklist item."""
        for cl in self._checklists:
            if cl["id"] == checklist_id:
                if 0 <= item_index < len(cl["items"]):
                    item = cl["items"][item_index]
                    item["completed"] = not item["completed"]
                    item["completed_at"] = datetime.now().isoformat() if item["completed"] else None
                    cl["updated_at"] = datetime.now().isoformat()

                    # Check if all items completed
                    if all(i["completed"] for i in cl["items"]):
                        cl["completed_at"] = datetime.now().isoformat()

                    self._save_checklists()
                    completed = sum(1 for i in cl["items"] if i["completed"])
                    return {
                        "status": "toggled",
                        "item": item,
                        "completed_count": completed,
                        "total_count": len(cl["items"]),
                        "progress_percent": round((completed / len(cl["items"])) * 100, 1),
                    }
                return {"status": "error", "error": f"Invalid item index: {item_index}"}
        return {"status": "error", "error": f"Checklist {checklist_id} not found"}

    def add_item(self, checklist_id: str, text: str) -> dict:
        """Add an item to a checklist."""
        for cl in self._checklists:
            if cl["id"] == checklist_id:
                item = {"text": text, "completed": False, "completed_at": None}
                cl["items"].append(item)
                cl["updated_at"] = datetime.now().isoformat()
                self._save_checklists()
                return {"status": "item_added", "checklist_id": checklist_id, "item": item, "total_items": len(cl["items"])}
        return {"status": "error", "error": f"Checklist {checklist_id} not found"}

    def remove_item(self, checklist_id: str, item_index: int) -> dict:
        """Remove an item from a checklist."""
        for cl in self._checklists:
            if cl["id"] == checklist_id:
                if 0 <= item_index < len(cl["items"]):
                    removed = cl["items"].pop(item_index)
                    cl["updated_at"] = datetime.now().isoformat()
                    self._save_checklists()
                    return {"status": "item_removed", "removed": removed, "remaining": len(cl["items"])}
                return {"status": "error", "error": f"Invalid item index: {item_index}"}
        return {"status": "error", "error": f"Checklist {checklist_id} not found"}

    def list_checklists(self, category: str | None = None) -> dict:
        """List all checklists with progress."""
        filtered = self._checklists
        if category:
            filtered = [cl for cl in filtered if cl.get("category") == category]

        for cl in filtered:
            completed = sum(1 for i in cl["items"] if i["completed"])
            cl["progress"] = {
                "completed": completed,
                "total": len(cl["items"]),
                "percent": round((completed / len(cl["items"])) * 100, 1) if cl["items"] else 0,
            }

        return {"total": len(filtered), "checklists": filtered}

    def get_templates(self) -> dict:
        """List available checklist templates."""
        return {
            "templates": [
                {"key": k, "name": v["name"], "items_count": len(v["items"])}
                for k, v in TEMPLATES.items()
            ]
        }

    def delete_checklist(self, checklist_id: str) -> dict:
        """Delete a checklist."""
        for i, cl in enumerate(self._checklists):
            if cl["id"] == checklist_id:
                self._checklists.pop(i)
                self._save_checklists()
                return {"status": "deleted", "checklist_id": checklist_id}
        return {"status": "error", "error": f"Checklist {checklist_id} not found"}


def get_checklist_tools():
    """Return CrewAI-compatible tools for checklists."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class CreateChecklistInput(BaseModel):
        name: str = Field(description="Checklist name")
        items: str = Field(description="Comma-separated list items")
        category: str = Field(default="general", description="Category")

    class CreateChecklistTool(BaseTool):
        name: str = "create_checklist"
        description: str = "Create a checklist with name and comma-separated items."
        args_schema: type = CreateChecklistInput

        def _run(self, name: str, items: str, category: str = "general") -> str:
            skill = ChecklistSkill()
            item_list = [i.strip() for i in items.split(",") if i.strip()]
            result = skill.create_checklist(name, item_list, category)
            return json.dumps(result, ensure_ascii=False)

    class TemplateChecklistInput(BaseModel):
        template_name: str = Field(description="Template key (e.g., property_listing, client_onboarding)")

    class TemplateChecklistTool(BaseTool):
        name: str = "create_checklist_from_template"
        description: str = "Create a checklist from a predefined template. Templates: property_listing, client_onboarding, closing_deal, property_inspection, morning_routine"
        args_schema: type = TemplateChecklistInput

        def _run(self, template_name: str) -> str:
            skill = ChecklistSkill()
            result = skill.create_from_template(template_name)
            return json.dumps(result, ensure_ascii=False)

    class ToggleChecklistItemInput(BaseModel):
        checklist_id: str = Field(description="Checklist ID")
        item_index: int = Field(description="Item index (0-based)")

    class ToggleChecklistItemTool(BaseTool):
        name: str = "toggle_checklist_item"
        description: str = "Toggle completion of a checklist item by index."
        args_schema: type = ToggleChecklistItemInput

        def _run(self, checklist_id: str, item_index: int) -> str:
            skill = ChecklistSkill()
            result = skill.toggle_item(checklist_id, item_index)
            return json.dumps(result, ensure_ascii=False)

    class ListChecklistsTool(BaseTool):
        name: str = "list_checklists"
        description: str = "List all checklists with their progress."

        def _run(self) -> str:
            skill = ChecklistSkill()
            result = skill.list_checklists()
            return json.dumps(result, ensure_ascii=False)

    class ChecklistTemplatesTool(BaseTool):
        name: str = "checklist_templates"
        description: str = "List available checklist templates."

        def _run(self) -> str:
            skill = ChecklistSkill()
            result = skill.get_templates()
            return json.dumps(result, ensure_ascii=False)

    return [CreateChecklistTool(), TemplateChecklistTool(), ToggleChecklistItemTool(), ListChecklistsTool(), ChecklistTemplatesTool()]
