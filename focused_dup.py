#!/usr/bin/env python
"""Focused deep dives into the most significant duplications."""
import os, re

SRC = 'D:\\cityestate\\src'

def read_file(path):
    with open(path, 'r', errors='ignore') as f:
        return f.read()

def show_function(filepath, func_name, context_lines=20):
    content = read_file(filepath)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if f'def {func_name}' in line and 'def ' in line.split(func_name)[0][-4:]:
            start = max(0, i - 1)
            end = min(len(lines), i + context_lines)
            print(f"\n=== {filepath}:{i+1} - {func_name}() ===")
            for j in range(start, end):
                prefix = ">>>" if j == i else "   "
                print(f"{prefix} {j+1:4d}: {lines[j]}")
            return True
    return False

print("1. normalize_phone - 3 files duplication")
print("=" * 60)
for fn in ['src/data/whatsapp_check.py', 'src/database/ingester.py', 'src/outreach/social_radar.py']:
    fp = os.path.join(SRC, fn)
    if os.path.exists(fp):
        content = read_file(fp)
        for m in re.finditer(r'def\s+normalize_phone.*?(?=\ndef\s|\nclass\s|\Z)', content, re.DOTALL):
            print(f"\n--- {fn} ---")
            print(m.group()[:600])

print("\n\n2. score_lead - 4 files duplication")
print("=" * 60)
for fn in ['src/api/bridge_handler.py', 'src/api/routes/skills.py', 'src/data/quality.py', 'src/skills/lead_scoring.py']:
    fp = os.path.join(SRC, fn)
    if os.path.exists(fp):
        content = read_file(fp)
        for m in re.finditer(r'def\s+score_lead.*?(?=\ndef\s|\nclass\s|\Z)', content, re.DOTALL):
            print(f"\n--- {fn} ---")
            print(m.group()[:600])

print("\n\n3. get_all_tools - 2 files duplication")
print("=" * 60)
for fn in ['src/ai_crew/tools.py', 'src/skills/__init__.py']:
    fp = os.path.join(SRC, fn)
    if os.path.exists(fp):
        content = read_file(fp)
        for m in re.finditer(r'def\s+get_all_tools.*?(?=\ndef\s|\nclass\s|\Z)', content, re.DOTALL):
            print(f"\n--- {fn} ---")
            print(m.group()[:800])

print("\n\n4. generate - 3 files duplication")
print("=" * 60)
for fn in ['src/automation/experts/writer.py', 'src/outreach/content_generator.py', 'src/outreach/llm_generator.py']:
    fp = os.path.join(SRC, fn)
    if os.path.exists(fp):
        content = read_file(fp)
        for m in re.finditer(r'def\s+generate.*?(?=\ndef\s|\nclass\s|\Z)', content, re.DOTALL):
            print(f"\n--- {fn} ---")
            print(m.group()[:600])

print("\n\n5. Duplicated try/except patterns in skills.py")
print("=" * 60)
skills_routes = os.path.join(SRC, 'src/api/routes/skills.py')
if os.path.exists(skills_routes):
    content = read_file(skills_routes)
    # Find repeated try/except error handling wrappers
    for m in re.finditer(r'(try:.*?except Exception as e:.*?logger\.error.*?\n)', content, re.DOTALL):
        print(m.group()[:300])
        print("---")

print("\n\n6. Duplicated error messages: crew.py and tools.py")
print("=" * 60)
crew_py = os.path.join(SRC, 'src/ai_crew/crew.py')
tools_py = os.path.join(SRC, 'src/ai_crew/tools.py')
for fn, fp in [('crew.py', crew_py), ('tools.py', tools_py)]:
    if os.path.exists(fp):
        content = read_file(fp)
        for m in re.finditer(r'raise\s+Exception\([^)]*failed[^)]*\)', content):
            print(f"{fn}: {m.group()}")

print("\n\n7. Webhook/Washington duplicated WhatsApp error messages")
print("=" * 60)
webhooks = os.path.join(SRC, 'src/api/routes/webhooks.py')
mcp_server = os.path.join(SRC, 'src/mcp/whatsapp_web_server.py')
for fn, fp in [('webhooks.py', webhooks), ('whatsapp_web_server.py', mcp_server)]:
    if os.path.exists(fp):
        content = read_file(fp)
        for m in re.finditer(r'logger\.\w+\([^)]*Failed[^)]*\)', content):
            print(f"{fn}: {m.group()[:120]}")

print("\n\n8. Duplicated 'except ImportError' patterns")
print("=" * 60)
import_errors = defaultdict(list)
from collections import defaultdict
for fp2 in []:
    pass  # just using this as a marker

# Actually do the import error check
all_py = []
for root, dirs, files in os.walk(SRC):
    if '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            all_py.append(os.path.join(root, f))

import_err_locations = defaultdict(list)
for fp in all_py:
    content = read_file(fp)
    for m in re.finditer(r'except ImportError.*', content):
        import_err_locations[os.path.basename(fp)].append(m.group().strip()[:100])

print("Files with 'except ImportError':")
for fn, errs in sorted(import_err_locations.items()):
    print(f"  {fn}: {len(errs)} occurrences")
    for e in errs:
        print(f"    {e}")
