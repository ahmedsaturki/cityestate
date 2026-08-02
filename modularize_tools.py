import re
import os

with open("src/ai_crew/tools.py.bak", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# Extract the shared imports (before first class definition)
first_class = content.find("\nclass ")
shared_imports = content[:first_class].rstrip()

# Extract all class definitions with their names
class_pattern = re.compile(r'(class (\w+)\(.*?\):.*?)(?=\nclass |\ndef get_all_tools|\Z)', re.DOTALL)
classes = {}
for m in class_pattern.finditer(content):
    cls_name = m.group(2)
    cls_body = m.group(1)
    classes[cls_name] = cls_body

# Extract get_all_tools function
get_all_tools_match = re.search(r'(def get_all_tools\(\).*?)(?=\n\n# ===|\n# ---------------------------------------------------------------------------|\Z)', content, re.DOTALL)
get_all_tools = get_all_tools_match.group(1) if get_all_tools_match else ""

# Define domain groupings
domains = {
    "database": ["DatabaseQueryInput", "DatabaseQueryTool"],
    "whatsapp": ["WhatsAppSendInput", "WhatsAppSendTool", "WhatsAppCheckInput", "WhatsAppCheckTool"],
    "web": ["WebSearchInput", "WebSearchTool", "WebCrawlerInput", "WebCrawlerTool"],
    "properties": ["PropertySearchInput", "PropertySearchTool"],
    "data": ["DataExtractionInput", "DataExtractionTool", "DataEnrichmentInput", "DataEnrichmentTool", "DataQualityInput", "DataQualityTool"],
    "content": ["ContentSaveInput", "ContentSaveTool"],
    "phone": ["PhoneValidatorInput", "PhoneValidatorTool"],
    "market": ["MarketResearchInput", "MarketResearchTool"],
}

# Create the tools package directory (already exists)
tools_dir = "src/ai_crew/tools"
os.makedirs(tools_dir, exist_ok=True)

# Write __init__.py
init_lines = [
    '"""',
    'CityEstate AI Crew Tools',
    '==========================',
    'Modular tool package for the CrewAI agent system.',
    '"""',
    '',
    'import json',
    'import logging',
    'from typing import Optional',
    '',
    'from crewai.tools import BaseTool',
    'from pydantic import BaseModel, Field',
    '',
    'logger = logging.getLogger("cityestate.crew.tools")',
    '',
]

# Add imports for skill tools
skill_imports = [
    "from src.skills.computer_use import get_computer_use_tools",
    "from src.skills.google_search import get_search_tools",
    "from src.skills.web_scraper import get_scraper_tools",
    "from src.skills.google_maps import get_maps_tools",
    "from src.skills.email_skill import get_email_tools",
    "from src.skills.document_processing import get_document_tools",
    "from src.skills.image_analysis import get_image_tools",
    "from src.skills.voice_speech import get_voice_tools",
    "from src.skills.task_manager import get_task_tools",
    "from src.skills.goal_tracker import get_goal_tools",
    "from src.skills.checklist_builder import get_checklist_tools",
    "from src.skills.decision_matrix import get_decision_tools",
    "from src.skills.kanban_board import get_kanban_tools",
    "from src.skills.time_tracker import get_time_tools",
    "from src.skills.report_generator import get_report_tools",
    "from src.skills.notes_brainstorming import get_notes_tools",
    "from src.skills.translator import get_translator_tools",
    "from src.skills.lead_scoring import get_lead_scoring_tools",
]
init_lines.extend(skill_imports)
init_lines.append('')

# Add domain imports
for domain in domains:
    init_lines.append(f'from src.ai_crew.tools.{domain} import *')
init_lines.append('')

# Add get_all_tools function
init_lines.append(get_all_tools)
init_lines.append('')

with open(os.path.join(tools_dir, "__init__.py"), "w", encoding="utf-8") as f:
    f.write("\n".join(init_lines))
print("Created __init__.py")

# Write domain-specific modules
for domain, cls_names in domains.items():
    lines = [
        f'"""',
        f'{domain.capitalize()} Tools',
        f'{"=" * (len(domain) + 8)}',
        f'"""',
        '',
    ]

    for cls_name in cls_names:
        if cls_name in classes:
            lines.append(classes[cls_name])
            lines.append('')

    filepath = os.path.join(tools_dir, f"{domain}.py")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Created {filepath} with {len(cls_names)} classes")

# Create tools.py as a compatibility shim
shim = '"""Compatibility shim — imports from the modular tools package."""\n\nfrom src.ai_crew.tools import *\n\n__all__ = ["get_all_tools"]\n'
with open("src/ai_crew/tools.py", "w", encoding="utf-8") as f:
    f.write(shim)
print("Created tools.py compatibility shim")

# Remove backup
os.remove("src/ai_crew/tools.py.bak")
print("Removed backup")

print("Done!")