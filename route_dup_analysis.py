#!/usr/bin/env python
"""Deep duplication analysis - route files and specific duplicated functions."""
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

# === Route file structure analysis (use absolute paths) ===
print("=== Route file structure analysis ===")
route_files = [
    'D:\\cityestate\\src\\api\\routes\\auth.py',
    'D:\\cityestate\\src\\api\\routes\\leads.py',
    'D:\\cityestate\\src\\api\\routes\\properties.py',
    'D:\\cityestate\\src\\api\\routes\\requests.py',
    'D:\\cityestate\\src\\api\\routes\\skills.py',
    'D:\\cityestate\\src\\api\\routes\\dashboard.py',
    'D:\\cityestate\\src\\api\\routes\\webhooks.py',
    'D:\\cityestate\\src\\api\\routes\\automation.py',
    'D:\\cityestate\\src\\api\\routes\\content.py',
    'D:\\cityestate\\src\\api\\routes\\data.py',
    'D:\\cityestate\\src\\api\\routes\\scheduler.py',
]

for rf in route_files:
    if not os.path.exists(rf):
        print(f"  NOT FOUND: {rf}")
        continue
    with open(rf, 'r', errors='ignore') as fh:
        content = fh.read()
    router_decos = len(re.findall(r'@router\.', content))
    get_funcs = len(re.findall(r'def\s+get_\w+', content))
    post_funcs = len(re.findall(r'def\s+(create_\w+|post_\w+)', content))
    put_funcs = len(re.findall(r'def\s+(update_\w+|put_\w+)', content))
    del_funcs = len(re.findall(r'def\s+(delete_\w+|remove_\w+)', content))
    db_queries = len(re.findall(r'\.query\(|\.filter\(|\.filter_by\(', content))
    try_blocks = len(re.findall(r'\btry\s*:', content))
    except_blocks = len(re.findall(r'\bexcept\s', content))
    return_dicts = len(re.findall(r'return\s+\{[^}]*\}', content))
    print(f"\n  {os.path.basename(rf)}:")
    print(f"    Router: {router_decos} | DB queries: {db_queries} | Try/except: {try_blocks}/{except_blocks}")
    print(f"    GET: {get_funcs} | POST: {post_funcs} | PUT: {put_funcs} | DELETE: {del_funcs} | Return-dicts: {return_dicts}")
    print(f"    Lines: {content.count(chr(10))}")

# === Duplicate function body analysis ===
print("\n\n=== Function body similarity: get_entity pattern ===")
# Many route files have the same pattern: get by ID, check if exists, raise 404
get_pattern = re.compile(r'def\s+(get_\w+)\(.*?\):.*?("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')?\s*\n((?:\s{4}.*\n){3,20})', re.MULTILINE)

for fp in route_files:
    if not os.path.exists(fp):
        continue
    with open(fp, 'r', errors='ignore') as fh:
        content = fh.read()
    for m in get_pattern.finditer(content):
        func_name = m.group(1)
        body = m.group(3)[:400]
        if 'not found' in body.lower() or '404' in body or 'raise HTTPException' in body:
            print(f"\n  {os.path.basename(fp)}: {func_name}()")
            print(f"    {body[:300]}")

# === Duplicated error-handling blocks ===
print("\n\n=== Duplicated error handling patterns ===")
# Look for identical try/except blocks across files
error_handling_blocks = defaultdict(list)
for fp in py_files:
    with open(fp, 'r', errors='ignore') as fh:
        content = fh.read()
    # Find try blocks with similar structure
    blocks = re.findall(r'(try:.*?except\s+\w+.*?(?=\ntry:|\n\n|\Z))', content, re.DOTALL)
    for block in blocks:
        # Normalize the block for comparison (remove whitespace, variable names)
        normalized = re.sub(r'\b\w+\b', 'VAR', block.strip()[:200])
        if len(normalized) > 50:  # Skip trivial blocks
            error_handling_blocks[normalized].append(fp)

print("Blocks appearing in 2+ files:")
for block_key, files in sorted(error_handling_blocks.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
    if len(files) >= 2:
        print(f"  {len(files)} files: {', '.join(os.path.basename(f) for f in files[:5])}")
        print(f"    Preview: {block_key[:120]}")
