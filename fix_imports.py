import os

domains = ['database', 'whatsapp', 'web', 'properties', 'data', 'content', 'phone', 'market']
imports = 'from pydantic import BaseModel, Field\nfrom crewai.tools import BaseTool\n'

for domain in domains:
    filepath = f'src/ai_crew/tools/{domain}.py'
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Add imports after the closing docstring
        lines = content.split('\n')
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip() == '"""' and i > 0:
                insert_at = i + 1
                break
        new_lines = lines[:insert_at] + ['', imports] + lines[insert_at:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print(f'Fixed {filepath}')