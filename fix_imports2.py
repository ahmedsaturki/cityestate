import os

domains = ['database', 'whatsapp', 'web', 'properties', 'data', 'content', 'phone', 'market']
imports = 'from typing import Optional\nfrom pydantic import BaseModel, Field\nfrom crewai.tools import BaseTool\n'

for domain in domains:
    filepath = f'src/ai_crew/tools/{domain}.py'
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        # Remove old imports
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('from pydantic') or stripped.startswith('from crewai.tools') or stripped.startswith('from typing import'):
                continue
            new_lines.append(line)
        # Find where to insert new imports (after closing docstring)
        insert_at = 0
        for i, line in enumerate(new_lines):
            if line.strip() == '"""' and i > 0:
                insert_at = i + 1
                break
        final_lines = new_lines[:insert_at] + ['', imports] + new_lines[insert_at:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(final_lines))
        print(f'Fixed {filepath}')