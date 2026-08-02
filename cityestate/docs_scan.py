"""Documentation scanner for CityEstate codebase."""
import ast
import os
import traceback
from pathlib import Path

RESULTS = []

def check_module_docstring(node, filepath):
    """Check if module has a docstring."""
    if not ast.get_docstring(node):
        RESULTS.append(f"{filepath}:1 -- Missing module docstring")

def doc_has_param(doc, param_name):
    """Check if a docstring mentions a parameter."""
    patterns = [
        f':param {param_name}:',
        f':param {param_name} ',
        f'Args\n    {param_name}',
        f'{param_name} :',
        f'{param_name} -',
    ]
    for p in patterns:
        if p in doc:
            return True
    return False

def check_function_docstring(node, filepath):
    """Check if function/method has a docstring, and check params/return."""
    name = getattr(node, 'name', '<lambda>')
    if name == '<lambda>':
        return

    doc = ast.get_docstring(node)
    if not doc:
        RESULTS.append(f"{filepath}:{node.lineno} -- Missing docstring for function '{name}'")
    else:
        if node.args.args or node.args.vararg or node.args.kwonlyargs or node.args.kwarg:
            params_missing = []
            for arg in node.args.args:
                if arg.arg == 'self':
                    continue
                if not doc_has_param(doc, arg.arg):
                    params_missing.append(arg.arg)
            if node.args.vararg and not doc_has_param(doc, f"*{node.args.vararg.arg}"):
                params_missing.append(f"*{node.args.vararg.arg}")
            if node.args.kwarg and not doc_has_param(doc, f"**{node.args.kwarg.arg}"):
                params_missing.append(f"**{node.args.kwarg.arg}")
            for kw in node.args.kwonlyargs:
                if not doc_has_param(doc, kw.arg):
                    params_missing.append(kw.arg)
            if params_missing:
                RESULTS.append(f"{filepath}:{node.lineno} -- Function '{name}' missing param docs: {', '.join(params_missing)}")

        has_return_annotation = node.returns is not None
        has_returns_doc = any(kw in doc.lower() for kw in ['return', 'returns', 'rtype'])
        if has_return_annotation and not has_returns_doc:
            RESULTS.append(f"{filepath}:{node.lineno} -- Function '{name}' has return type annotation but no return documentation in docstring")

def check_class_docstring(node, filepath):
    """Check if class has a docstring."""
    name = node.name
    doc = ast.get_docstring(node)
    if not doc:
        RESULTS.append(f"{filepath}:{node.lineno} -- Missing docstring for class '{name}'")
    else:
        init = None
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                init = item
                break
        if init and not ast.get_docstring(init):
            RESULTS.append(f"{filepath}:{init.lineno} -- Missing docstring for __init__ in class '{name}'")
        elif init:
            for arg in init.args.args:
                if arg.arg == 'self':
                    continue
                if not doc_has_param(doc, arg.arg):
                    RESULTS.append(f"{filepath}:{init.lineno} -- __init__ param '{arg.arg}' not documented in class '{name}' docstring")

def has_nearby_comment(source_lines, lineno):
    """Check if there's a comment on the line or the 2 lines before."""
    for i in range(max(0, lineno - 3), lineno):
        if i < len(source_lines):
            line = source_lines[i].strip()
            if line.startswith('#'):
                return True
    return False

def is_complex_conditional(node):
    """Determine if an if node has complex logic."""
    if isinstance(node.test, ast.BoolOp):
        return len(node.test.values) > 2 or (
            len(node.test.values) == 2 and any(isinstance(v, ast.Compare) for v in node.test.values)
        )
    if isinstance(node.test, ast.Compare):
        return len(node.test.ops) > 1
    return False

def is_complex_node(node):
    """Determine if an AST node is complex enough to warrant an inline comment."""
    if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
        return True
    if isinstance(node, ast.BoolOp) and len(node.values) >= 3:
        return True
    return False

def check_complex_logic_comments(node, filepath, source_lines):
    """Check for inline comments on complex logic patterns."""
    for child in ast.walk(node):
        if child is node:
            continue
        lineno = getattr(child, 'lineno', 0)
        if lineno == 0:
            continue
        if is_complex_node(child):
            if not has_nearby_comment(source_lines, lineno):
                RESULTS.append(f"{filepath}:{lineno} -- Complex expression without inline comment")
        elif isinstance(child, ast.If) and is_complex_conditional(child):
            if not has_nearby_comment(source_lines, child.lineno):
                RESULTS.append(f"{filepath}:{child.lineno} -- Complex conditional without inline comment")

def scan_file(filepath):
    """Scan a single Python file for documentation issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        source_lines = source.splitlines()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError) as e:
        RESULTS.append(f"{filepath} -- PARSE ERROR: {e}")
        return

    check_module_docstring(tree, filepath)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            check_function_docstring(node, filepath)
        elif isinstance(node, ast.ClassDef):
            check_class_docstring(node, filepath)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    check_function_docstring(item, filepath)
        elif isinstance(node, ast.Assign):
            if isinstance(node.value, (ast.Dict, ast.List, ast.Set, ast.Tuple)):
                nelems = 0
                if isinstance(node.value, ast.Dict):
                    nelems = len(node.value.keys)
                elif isinstance(node.value, (ast.List, ast.Set, ast.Tuple)):
                    nelems = len(node.value.elts)
                if nelems > 3:
                    if not has_nearby_comment(source_lines, node.lineno):
                        RESULTS.append(f"{filepath}:{node.lineno} -- Complex data literal without inline comment")

    check_complex_logic_comments(tree, filepath, source_lines)

def main():
    src_dir = Path('src')
    docs_dir = Path('docs')

    docs_exists = docs_dir.exists()
    docs_files = []
    if docs_exists:
        docs_files = list(docs_dir.rglob('*'))
        docs_files = [f for f in docs_files if f.is_file()]

    api_doc_files = []
    if docs_files:
        api_doc_files = [f for f in docs_files if any(
            name in f.name.lower() for name in ['api', 'reference', 'endpoint', 'route']
        )]

    print("=" * 60, flush=True)
    print("CityEstate Documentation Scan Report", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    if not docs_exists:
        print("docs/ directory: DOES NOT EXIST", flush=True)
    elif not docs_files:
        print("docs/ directory: EXISTS BUT IS EMPTY -- no API documentation found", flush=True)
    else:
        print(f"docs/ directory: contains {len(docs_files)} file(s)", flush=True)
        for df in sorted(docs_files):
            is_api = 'api' in df.name.lower() or 'reference' in df.name.lower()
            tag = " [API DOC]" if is_api else ""
            print(f"  {df}{tag}", flush=True)
        if not api_doc_files:
            print("  WARNING: No API documentation files found in docs/", flush=True)
    print(flush=True)

    py_files = sorted(src_dir.rglob('*.py'))
    print(f"Scanned {len(py_files)} Python files in src/", flush=True)
    print(flush=True)

    for py_file in py_files:
        scan_file(str(py_file))

    by_file = {}
    for r in RESULTS:
        key = r.split(' --')[0].split(':')[0] if ':' in r else r
        by_file.setdefault(key, []).append(r)

    for fpath in sorted(by_file.keys()):
        print(f"\n{'-' * 60}", flush=True)
        print(f"FILE: {fpath}", flush=True)
        print(f"{'-' * 60}", flush=True)
        for item in by_file[fpath]:
            rest = item.split(':', 1)[1].strip() if ':' in item else item
            print(f"  - {rest}", flush=True)

    unique_files = set()
    for r in RESULTS:
        fname = r.split(':')[0]
        unique_files.add(fname)

    print(f"\n{'=' * 60}", flush=True)
    print(f"SUMMARY", flush=True)
    print(f"{'=' * 60}", flush=True)
    print(f"Total documentation issues found: {len(RESULTS)}", flush=True)
    print(f"Files with at least one issue: {len(unique_files)}", flush=True)

    report_path = Path('docs_scan_report.txt')
    with open(report_path, 'w') as f:
        f.write("CityEstate Documentation Scan Report\n")
        f.write("=" * 60 + "\n\n")
        if not docs_exists:
            f.write("docs/ directory: DOES NOT EXIST\n\n")
        elif not docs_files:
            f.write("docs/ directory: EXISTS BUT IS EMPTY\n\n")
        else:
            f.write(f"docs/ directory: {len(docs_files)} file(s)\n\n")
        f.write(f"Scanned {len(py_files)} Python files\n\n")
        for r in RESULTS:
            f.write(r + "\n")
        f.write(f"\nTotal issues: {len(RESULTS)}\n")
        f.write(f"Files with issues: {len(unique_files)}\n")

    print(f"\nFull report written to: {report_path}", flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR: {e}", flush=True)
