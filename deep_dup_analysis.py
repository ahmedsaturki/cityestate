#!/usr/bin/env python
"""Deep duplication analysis for CityEstate codebase."""
import os, re
from collections import defaultdict

SRC_DIR = 'D:\\cityestate\\src'

def get_py_files():
    py_files = []
    for root, dirs, files in os.walk(SRC_DIR):
        if '__pycache__' in root or '.pyc' in root:
            continue
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))
    return py_files

py_files = get_py_files()

# === Import patterns ===
print("=== Commonly imported names (from 5+ files) ===")
import_pattern = re.compile(r'^\s*from\s+([\w.]+)\s+import\s+([\w,\s]+)')
import_map = defaultdict(lambda: defaultdict(int))
for fp in py_files:
    with open(fp, 'r', errors='ignore') as fh:
        for line in fh:
            m = import_pattern.match(line)
            if m:
                module = m.group(1)
                imports = [i.strip() for i in m.group(2).split(',')]
                for imp in imports:
                    import_map[imp][module] += 1

for name in sorted(import_map.keys()):
    sources = import_map[name]
    total = sum(sources.values())
    if total >= 5:
        print(f"  {name} ({total} uses): {dict(sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5])}")

# === Duplicate string messages ===
print("\n=== Duplicate error/message strings (2+ occurrences) ===")
string_pattern = re.compile(r'["\']([^"\']{20,})["\']')
string_counts = defaultdict(list)
for fp in py_files:
    with open(fp, 'r', errors='ignore') as fh:
        for lineno, line in enumerate(fh, 1):
            for m in string_pattern.finditer(line):
                text = m.group(1)
                if any(word in text.lower() for word in ['error', 'not found', 'success', 'failed', 'invalid', 'required', 'already exists', 'permission', 'access denied', 'timeout', 'created', 'updated', 'deleted']):
                    string_counts[text].append((fp, lineno))

for text, locs in sorted(string_counts.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
    if len(locs) >= 2:
        print(f'  "{text}" ({len(locs)}x)')
        for fp, ln in locs:
            print(f'    {fp}:{ln}')

# === Classes in multiple files ===
print("\n=== Classes defined in 2+ files ===")
class_pattern = re.compile(r'^\s*class\s+(\w+)')
class_defs = defaultdict(list)
for fp in py_files:
    with open(fp, 'r', errors='ignore') as fh:
        for lineno, line in enumerate(fh, 1):
            m = class_pattern.match(line)
            if m:
                class_defs[m.group(1)].append((fp, lineno))

for name in sorted(class_defs.keys()):
    locs = class_defs[name]
    if len(locs) > 1:
        print(f"  {name} ({len(locs)} files):")
        for fp, ln in locs:
            print(f"    {fp}:{ln}")

# === Route file structure analysis ===
print("\n=== Route file structure analysis ===")
route_files = [
    'src/api/routes/auth.py',
    'src/api/routes/leads.py',
    'src/api/routes/properties.py',
    'src/api/routes/requests.py',
    'src/api/routes/skills.py',
    'src/api/routes/dashboard.py',
    'src/api/routes/webhooks.py',
    'src/api/routes/automation.py',
    'src/api/routes/content.py',
    'src/api/routes/data.py',
    'src/api/routes/scheduler.py',
]

for rf in route_files:
    full = os.path.join(SRC_DIR, rf)
    if not os.path.exists(full):
        continue
    with open(full, 'r', errors='ignore') as fh:
        content = fh.read()
    router_decos = len(re.findall(r'@router\.', content))
    get_funcs = len(re.findall(r'def\s+get_', content))
    post_funcs = len(re.findall(r'def\s+(create_\w+|post_\w+)', content))
    put_funcs = len(re.findall(r'def\s+(update_\w+|put_\w+)', content))
    del_funcs = len(re.findall(r'def\s+(delete_\w+|remove_\w+)', content))
    db_queries = len(re.findall(r'\.query\(|\.filter\(|\.filter_by\(', content))
    try_except = len(re.findall(r'try\s*:|except\s', content))
    return_dict = len(re.findall(r'return\s+\{', content))
    print(f"\n  {rf}:")
    print(f"    Router decorators: {router_decos}, DB queries: {db_queries}, Try/except blocks: {try_except}")
    print(f"    GET: {get_funcs}, POST: {post_funcs}, PUT: {put_funcs}, DELETE: {del_funcs}, Return dicts: {return_dict}")
