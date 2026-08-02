"""
Content Tools
===============
"""

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ContentSaveInput(BaseModel):
    content: str = Field(description="Generated content to save")
    property_title: str = Field(description="Property title for filename")
    channel: str = Field(default="all", description="Channel: facebook, instagram, whatsapp")



class ContentSaveTool(BaseTool):
    """Save generated content to output directory."""
    name: str = "content_save"
    description: str = (
        "Save marketing content to a file in the output directory. "
        "Input: content text, property title, and channel name."
    )
    args_schema: type = ContentSaveInput

    def _run(self, content: str, property_title: str, channel: str = "all") -> str:
        try:
            import re
            from pathlib import Path

            output_dir = Path("output/content")
            output_dir.mkdir(parents=True, exist_ok=True)

            safe_title = re.sub(r'[^\w\s-]', '', property_title)[:50].strip().replace(' ', '_')
            filename = f"{safe_title}_{channel}.md"
            filepath = output_dir / filename

            filepath.write_text(content, encoding="utf-8")
            return json.dumps({"status": "saved", "file": str(filepath)})
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})


# ---------------------------------------------------------------------------
# Get All Tools
# ---------------------------------------------------------------------------
