#!/usr/bin/env python
"""Scan CityEstate codebase for code duplication patterns."""

import os
import re
from collections import defaultdict

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')

def get_py_files():
    py_files = []
    for root, dirs, files in os.walk(SRC_DIR):
        if '__pycache__' in root or '.pyc' in root:
            continue
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))
    return py_files

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def analyze_error_handling(py_files):
    """Find duplicated error handling patterns."""
    print_section("1. ERROR HANDLING PATTERNS (try/except/raise)")
    pattern = re.compile(r'(try\s*:|except\s+\w+|raise\s+)')
    file_counts = defaultdict(int)
    all_matches = defaultdict(list)

    for fp in py_files:
        with open(fp, 'r', errors='ignore') as fh:
            for lineno, line in enumerate(fh, 1):
                for m in pattern.finditer(line):
                    key = m.group(1).strip()
                    file_counts[fp] += 1
                    all_matches[key].append(f"{fp}:{lineno}")

    sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    for fp, count in sorted_files:
        print(f"  {count:3d}  {fp}")

    for key in sorted(all_matches.keys()):
        locs = all_matches[key]
        print(f"\n  '{key}' appears in {len(locs)} locations:")
        for loc in locs[:12]:
            print(f"    {loc}")
        if len(locs) > 12:
            print(f"    ... and {len(locs)-12} more")

def analyze_validation_functions(py_files):
    """Find duplicated validation/sanitization/clean functions."""
    print_section("2. VALIDATION/SANITIZATION/CLEAN FUNCTIONS")
    pattern = re.compile(r'^\s*def\s+(validate_\w+|sanitize_\w+|clean_\w+|format_\w+|parse_\w+|is_valid_\w+)')
    func_defs = defaultdict(list)

    for fp in py_files:
        with open(fp, 'r', errors='ignore') as fh:
            for lineno, line in enumerate(fh, 1):
                m = pattern.match(line)
                if m:
                    func_defs[m.group(1)].append((fp, lineno))

    print(f"  Found {sum(len(v) for v in func_defs.values())} validation/cleaning functions")
    for name in sorted(func_defs.keys()):
        locs = func_defs[name]
        print(f"\n  {name}: {len(locs)} occurrences")
        for fp, ln in locs:
            print(f"    {fp}:{ln}")

def analyze_db_patterns(py_files):
    """Find duplicated database query patterns."""
    print_section("3. DATABASE QUERY PATTERNS")
    db_patterns = [
        (r'\.query\(', 'ORM .query()'),
        (r'\.filter\(', 'ORM .filter()'),
        (r'\.filter_by\(', 'ORM .filter_by()'),
        (r'\.all\(', 'ORM .all()'),
        (r'\.first\(', 'ORM .first()'),
        (r'\.count\(', 'ORM .count()'),
        (r'cursor\.execute', 'cursor.execute'),
        (r'session\.add', 'session.add'),
        (r'session\.commit', 'session.commit'),
        (r'session\.rollback', 'session.rollback'),
        (r'connection\.execute', 'connection.execute'),
        (r'DatabaseSession|get_db|get_session', 'DB session accessor'),
    ]

    for pat_str, desc in db_patterns:
        pat = re.compile(pat_str)
        file_counts = defaultdict(int)
        for fp in py_files:
            with open(fp, 'r', errors='ignore') as fh:
                content = fh.read()
            matches = pat.findall(content)
            if matches:
                file_counts[fp] = len(matches)

        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        if sorted_files:
            print(f"\n  {desc}:")
            for fp, count in sorted_files:
                print(f"    {count:3d}  {fp}")

def analyze_api_routes(py_files):
    """Find duplicated API route structures."""
    print_section("4. API ROUTE STRUCTURES")
    route_patterns = [
        (r'@router\.', 'FastAPI router decorator'),
        (r'@app\.', 'FastAPI app decorator'),
        (r'@bp\.', 'Blueprint decorator'),
        (r'api_route', 'api_route decorator'),
        (r'@.+route', 'Route decorator catch-all'),
    ]

    for pat_str, desc in route_patterns:
        pat = re.compile(pat_str)
        file_counts = defaultdict(int)
        for fp in py_files:
            with open(fp, 'r', errors='ignore') as fh:
                content = fh.read()
            matches = pat.findall(content)
            if matches:
                file_counts[fp] = len(matches)

        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        if sorted_files:
            print(f"\n  {desc}:")
            for fp, count in sorted_files:
                print(f"    {count:3d}  {fp}")

    # Also look for repeated route function patterns
    print_section("4b. HTTP METHOD FUNCTION PATTERNS")
    http_patterns = [
        (r'def\s+(get_\w+|list_\w+|get_all_\w+)', 'GET/List pattern'),
        (r'def\s+(create_\w+|post_\w+|add_\w+)', 'POST/Create pattern'),
        (r'def\s+(update_\w+|put_\w+|edit_\w+)', 'PUT/Update pattern'),
        (r'def\s+(delete_\w+|remove_\w+|del_\w+)', 'DELETE/Remove pattern'),
    ]

    for pat_str, desc in http_patterns:
        pat = re.compile(pat_str)
        file_counts = defaultdict(int)
        for fp in py_files:
            with open(fp, 'r', errors='ignore') as fh:
                content = fh.read()
            matches = pat.findall(content)
            if matches:
                file_counts[fp] = len(matches)

        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        if sorted_files:
            print(f"\n  {desc}:")
            for fp, count in sorted_files:
                print(f"    {count:3d}  {fp}")

def analyze_crud_functions(py_files):
    """Find CRUD function patterns that may be duplicated."""
    print_section("5. CRUD FUNCTION PATTERNS (get/find/search/create/update/delete)")
    patterns = [
        (r'def\s+(get_\w+)', 'get_ functions'),
        (r'def\s+(set_\w+|put_\w+|update_\w+)', 'set/put/update functions'),
        (r'def\s+(create_\w+|add_\w+|new_\w+)', 'create/add/new functions'),
        (r'def\s+(delete_\w+|remove_\w+|del_\w+)', 'delete/remove functions'),
        (r'def\s+(find_\w+|search_\w+|lookup_\w+)', 'find/search/lookup functions'),
        (r'def\s+(list_\w+|fetch_\w+|retrieve_\w+|get_all_\w+)', 'list/fetch/retrieve functions'),
    ]

    for pat_str, desc in patterns:
        pat = re.compile(pat_str)
        func_names = defaultdict(list)
        for fp in py_files:
            with open(fp, 'r', errors='ignore') as fh:
                for lineno, line in enumerate(fh, 1):
                    m = pat.match(line)
                    if m:
                        func_names[m.group(1)].append((fp, lineno))

        print(f"\n  {desc}:")
        for name in sorted(func_names.keys()):
            locs = func_names[name]
            print(f"    {name}: {len(locs)} files")
            for fp, ln in locs[:5]:
                print(f"      {fp}:{ln}")
            if len(locs) > 5:
                print(f"      ... and {len(locs)-5} more files")

def analyze_utility_functions(py_files):
    """Find duplicated utility functions."""
    print_section("6. DUPLICATED UTILITY FUNCTION PATTERNS")
    # Look for functions with same name across files
    func_names = defaultdict(list)
    for fp in py_files:
        with open(fp, 'r', errors='ignore') as fh:
            for lineno, line in enumerate(fh, 1):
                m = re.match(r'^\s*def\s+(\w+)', line)
                if m:
                    func_names[m.group(1)].append((fp, lineno))

    # Show functions defined in multiple files
    print("\n  Functions defined in 3+ files (potential duplication):")
    multi_file_funcs = {name: locs for name, locs in func_names.items() if len(locs) >= 3}
    for name in sorted(multi_file_funcs.keys()):
        locs = multi_file_funcs[name]
        print(f"\n    {name} ({len(locs)} files):")
        for fp, ln in locs:
            print(f"      {fp}:{ln}")

    print("\n  Functions defined in 2 files (possible duplication):")
    two_file_funcs = {name: locs for name, locs in func_names.items() if len(locs) == 2}
    # Only show top ones by popularity
    sorted_two = sorted(two_file_funcs.items(), key=lambda x: x[0])[:30]
    for name, locs in sorted_two:
        print(f"\n    {name}:")
        for fp, ln in locs:
            print(f"      {fp}:{ln}")

def analyze_import_patterns(py_files):
    """Find duplicated import/utility patterns."""
    print_section("7. COMMON IMPORT PATTERNS")
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

    # Show imports that come from multiple source files (potential shared utilities)
    print("\n  Commonly imported names (from 5+ files):")
    for name in sorted(import_map.keys()):
        sources = import_map[name]
        total = sum(sources.values())
        if total >= 5:
            print(f"\n    {name} (used in {total} files):")
            for mod, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      from {mod}: {count} files")

def analyze_string_templates(py_files):
    """Find duplicated string templates and messages."""
    print_section("8. DUPLICATED STRING TEMPLATES & MESSAGES")
    # Look for repeated error messages, status messages
    string_pattern = re.compile(r'["\']([^"\']{20,})["\']')
    string_counts = defaultdict(list)

    for fp in py_files:
        with open(fp, 'r', errors='ignore') as fh:
            for lineno, line in enumerate(fh, 1):
                for m in string_pattern.finditer(line):
                    text = m.group(1)
                    # Only count strings that look like messages (not URLs, not random)
                    if any(word in text.lower() for word in ['error', 'not found', 'success', 'failed', 'invalid', 'required', 'already exists', 'permission', 'access denied', 'timeout']):
                        string_counts[text].append((fp, lineno))

    print("\n  Duplicate error/message strings (appearing in 2+ files):")
    for text, locs in sorted(string_counts.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
        if len(locs) >= 2:
            print(f"\n    '{text}' ({len(locs)} occurrences):")
            for fp, ln in locs:
                print(f"      {fp}:{ln}")

def analyze_class_patterns(py_files):
    """Find duplicated class patterns."""
    print_section("9. CLASS PATTERNS")
    class_pattern = re.compile(r'^\s*class\s+(\w+)')
    class_defs = defaultdict(list)

    for fp in py_files:
        with open(fp, 'r', errors='ignore') as fh:
            for lineno, line in enumerate(fh, 1):
                m = class_pattern.match(line)
                if m:
                    class_defs[m.group(1)].append((fp, lineno))

    print("\n  Classes defined in multiple files:")
    for name in sorted(class_defs.keys()):
        locs = class_defs[name]
        if len(locs) > 1:
            print(f"\n    {name} ({len(locs)} files):")
            for fp, ln in locs:
                print(f"      {fp}:{ln}")

def analyze_return_patterns(py_files):
    """Find duplicated return patterns (common error return shapes)."""
    print_section("10. COMMON RETURN/RESPONSE PATTERNS")
    patterns = [
        (r'return\s+\{\s*[\'"]error[\'"]', 'error dict return'),
        (r'return\s+\{\s*[\'"]message[\'"]', 'message dict return'),
        (r'return\s+response\.', 'response return'),
        (r'return\s+jsonify', 'jsonify return'),
        (r'return\s+{\s*[\'"]data[\'"]', 'data dict return'),
        (r'return\s+{\s*[\'"]status[\'"]', 'status dict return'),
    ]

    for pat_str, desc in patterns:
        pat = re.compile(pat_str)
        file_counts = defaultdict(int)
        for fp in py_files:
            with open(fp, 'r', errors='ignore') as fh:
                content = fh.read()
            matches = pat.findall(content)
            if matches:
                file_counts[fp] = len(matches)

        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        if sorted_files:
            print(f"\n  {desc}:")
            for fp, count in sorted_files:
                print(f"    {count:3d}  {fp}")

def main():
    py_files = get_py_files()
    print(f"CityEstate Codebase Analysis: {len(py_files)} Python files scanned\n")
    print(f"Source directory: {SRC_DIR}")

    analyze_error_handling(py_files)
    analyze_validation_functions(py_files)
    analyze_db_patterns(py_files)
    analyze_api_routes(py_files)
    analyze_crud_functions(py_files)
    analyze_utility_functions(py_files)
    analyze_import_patterns(py_files)
    analyze_string_templates(py_files)
    analyze_class_patterns(py_files)
    analyze_return_patterns(py_files)

    print("\n\n" + "="*70)
    print("  SCAN COMPLETE")
    print("="*70)

if __name__ == '__main__':
    main()
