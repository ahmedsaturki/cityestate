"""
Notes & Brainstorming Skill — ملاحظات وأفكار
==============================================
Capture ideas, take notes, brainstorm, and organize thoughts.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("skills.notes")

NOTES_FILE = Path("data/notes.json")


class NotesSkill:
    """Notes and brainstorming skill."""

    def __init__(self):
        self._notes = self._load_notes()

    def _load_notes(self) -> list[dict]:
        if NOTES_FILE.exists():
            try:
                return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_notes(self):
        NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        NOTES_FILE.write_text(json.dumps(self._notes, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_note(self, title: str, content: str, category: str = "general", tags: list[str] | None = None) -> dict:
        """Create a new note."""
        note = {
            "id": f"NOTE-{len(self._notes) + 1:04d}",
            "title": title,
            "content": content,
            "category": category,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "pinned": False,
        }
        self._notes.append(note)
        self._save_notes()
        return {"status": "created", "note": note}

    def update_note(self, note_id: str, content: str) -> dict:
        """Update note content."""
        for note in self._notes:
            if note["id"] == note_id:
                note["content"] = content
                note["updated_at"] = datetime.now().isoformat()
                self._save_notes()
                return {"status": "updated", "note": note}
        return {"status": "error", "error": f"Note {note_id} not found"}

    def search_notes(self, query: str) -> dict:
        """Search notes by content."""
        query_lower = query.lower()
        results = [
            n for n in self._notes
            if query_lower in n["title"].lower() or query_lower in n["content"].lower() or query_lower in " ".join(n.get("tags", [])).lower()
        ]
        return {"query": query, "results": len(results), "notes": results}

    def list_notes(self, category: str | None = None, tag: str | None = None) -> dict:
        """List notes with optional filters."""
        filtered = self._notes
        if category:
            filtered = [n for n in filtered if n.get("category") == category]
        if tag:
            filtered = [n for n in filtered if tag in n.get("tags", [])]

        # Pinned first
        filtered.sort(key=lambda n: (not n.get("pinned", False), n.get("updated_at", "")))
        return {"total": len(filtered), "notes": filtered}

    def pin_note(self, note_id: str) -> dict:
        """Pin/unpin a note."""
        for note in self._notes:
            if note["id"] == note_id:
                note["pinned"] = not note.get("pinned", False)
                self._save_notes()
                return {"status": "pinned" if note["pinned"] else "unpinned", "note": note}
        return {"status": "error", "error": f"Note {note_id} not found"}

    def delete_note(self, note_id: str) -> dict:
        """Delete a note."""
        for i, note in enumerate(self._notes):
            if note["id"] == note_id:
                self._notes.pop(i)
                self._save_notes()
                return {"status": "deleted", "note_id": note_id}
        return {"status": "error", "error": f"Note {note_id} not found"}

    def list_quick_notes(self) -> list[dict]:
        """List quick ideas/notes (category=idea or pinned=true)."""
        quick = [n for n in self._notes if n.get("category") == "idea" or n.get("pinned")]
        quick.sort(key=lambda n: n.get("updated_at", ""), reverse=True)
        return quick

    def quick_idea(self, idea: str) -> dict:
        """Save a quick idea as a note."""
        return self.create_note(f"Quick: {idea[:80]}", idea, category="idea", tags=["quick-idea"])

    def brainstorm(self, topic: str, ideas: list[str] | None = None) -> dict:
        """Structured brainstorming session."""
        session = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "ideas": ideas or [],
            "categories": {
                "opportunities": [],
                "challenges": [],
                "actions": [],
                "resources": [],
            },
        }

        # Auto-categorize existing ideas
        for idea in session["ideas"]:
            idea_lower = idea.lower()
            if any(w in idea_lower for w in ["can", "opportunity", "chance", "potential"]):
                session["categories"]["opportunities"].append(idea)
            elif any(w in idea_lower for w in ["problem", "challenge", "risk", "issue"]):
                session["categories"]["challenges"].append(idea)
            elif any(w in idea_lower for w in ["do", "action", "implement", "create"]):
                session["categories"]["actions"].append(idea)
            elif any(w in idea_lower for w in ["need", "require", "resource", "tool"]):
                session["categories"]["resources"].append(idea)
            else:
                session["categories"]["actions"].append(idea)

        # Save as note
        content = f"# Brainstorming: {topic}\n\n"
        for cat, items in session["categories"].items():
            if items:
                content += f"## {cat.title()}\n"
                for item in items:
                    content += f"- {item}\n"
                content += "\n"

        self.create_note(f"Brainstorm: {topic}", content, category="brainstorm", tags=["brainstorm", topic.lower()])
        return {"status": "brainstormed", "session": session}

    def add_idea(self, topic: str, idea: str) -> dict:
        """Quick idea capture."""
        return self.create_note(f"Idea: {idea[:50]}", idea, category="idea", tags=["idea", topic.lower()] if topic else ["idea"])


def get_notes_tools():
    """Return CrewAI-compatible tools for notes."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class CreateNoteInput(BaseModel):
        title: str = Field(description="Note title")
        content: str = Field(description="Note content")
        category: str = Field(default="general", description="Category")
        tags: str = Field(default="", description="Comma-separated tags")

    class CreateNoteTool(BaseTool):
        name: str = "create_note"
        description: str = "Create a note with title, content, category, and tags."
        args_schema: type = CreateNoteInput

        def _run(self, title: str, content: str, category: str = "general", tags: str = "") -> str:
            skill = NotesSkill()
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
            result = skill.create_note(title, content, category, tag_list)
            return json.dumps(result, ensure_ascii=False)

    class SearchNotesInput(BaseModel):
        query: str = Field(description="Search query")

    class SearchNotesTool(BaseTool):
        name: str = "search_notes"
        description: str = "Search notes by content or title."
        args_schema: type = SearchNotesInput

        def _run(self, query: str) -> str:
            skill = NotesSkill()
            result = skill.search_notes(query)
            return json.dumps(result, ensure_ascii=False)

    class BrainstormInput(BaseModel):
        topic: str = Field(description="Brainstorming topic")
        ideas: str = Field(default="", description="Comma-separated ideas to organize")

    class BrainstormTool(BaseTool):
        name: str = "brainstorm"
        description: str = "Structured brainstorming session. Categorizes ideas into opportunities, challenges, actions, resources."
        args_schema: type = BrainstormInput

        def _run(self, topic: str, ideas: str = "") -> str:
            skill = NotesSkill()
            idea_list = [i.strip() for i in ideas.split(",") if i.strip()] if ideas else []
            result = skill.brainstorm(topic, idea_list)
            return json.dumps(result, ensure_ascii=False)

    class QuickIdeaInput(BaseModel):
        idea: str = Field(description="Quick idea to capture")
        topic: str = Field(default="", description="Topic/category")

    class QuickIdeaTool(BaseTool):
        name: str = "quick_idea"
        description: str = "Capture a quick idea or thought."
        args_schema: type = QuickIdeaInput

        def _run(self, idea: str, topic: str = "") -> str:
            skill = NotesSkill()
            result = skill.add_idea(topic, idea)
            return json.dumps(result, ensure_ascii=False)

    return [CreateNoteTool(), SearchNotesTool(), BrainstormTool(), QuickIdeaTool()]
