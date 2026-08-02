import ast
import os
from pathlib import Path

RESULTS = []

def check_module_docstring(node, filepath):
    if not ast.get_docstring(node):
        RESULTS.append(f"{filepath}:1 -- Missing module docstring")

def doc_has_param(doc, param_name):
    patterns = [
        f':param {param_name}:',
        f':param {param_name} ',
        f'Args\n    {param_name}',
        f'{param_name} :',
        f'{param_name} -',
    ]
    return any(p in doc for p in patterns)

def check_function_docstring(node, filepath):
    name = getattr(node, 'name', '<lambda>')
    if name == '<lambda>':
        return
    doc = ast.get_docstring(node)
    if not doc:
        RESULTS.append(f"{filepath}:{node.lineno} -- Missing docstring for function '{name}'")
    else:
        if node.args.args or node.args.vararg or node.args.kwonlyargs or node.args.kwarg:
            missing = []
            for arg in node.args.args:
                if arg.arg == 'self': continue
                if not doc_has_param(doc, arg.arg): missing.append(arg.arg)
            if node.args.vararg and not doc_has_param(doc, f"*{node.args.vararg.arg}"):
                missing.append(f"*{node.args.vararg.arg}")
            if node.args.kwarg and not doc_has_param(doc, f"**{node.args.kwarg.arg}"):
                missing.append(f"**{node.args.kwarg.arg}")
            for kw in node.args.kwonlyargs:
                if not doc_has_param(doc, kw.arg): missing.append(kw.arg)
            if missing:
                RESULTS.append(f"{filepath}:{node.lineno} -- Function '{name}' missing param docs: {', '.join(missing)}")
        has_ret_ann = node.returns is not None
        has_ret_doc = any(kw in doc.lower() for kw in ['return', 'returns', 'rtype'])
        if has_ret_ann and not has_ret_doc:
            RESULTS.append(f"{filepath}:{node.lineno} -- Function '{name}' has return type annotation but no return documentation")

def check_class_docstring(node, filepath):
    name = node.name
    doc = ast.get_docstring(node)
    if not doc:
        RESULTS.append(f"{filepath}:{node.lineno} -- Missing docstring for class '{name}'")
    else:
        init = None
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                init = item; break
        if init and not ast.get_docstring(init):
            RESULTS.append(f"{filepath}:{init.lineno} -- Missing docstring for __init__ in class '{name}'")
        elif init:
            for arg in init.args.args:
                if arg.arg == 'self': continue
                if not doc_has_param(doc, arg.arg):
                    RESULTS.append(f"{filepath}:{init.lineno} -- __init__ param '{arg.arg}' not documented in class '{name}' docstring")

def has_comment(source_lines, lineno):
    for i in range(max(0, lineno - 3), lineno):
        if i < len(source_lines) and source_lines[i].strip().startswith('#'):
            return True
    return False

def is_complex_conditional(node):
    if isinstance(node.test, ast.BoolOp):
        return len(node.test.values) > 2 or (len(node.test.values) == 2 and any(isinstance(v, ast.Compare) for v in node.test.values))
    if isinstance(node.test, ast.Compare):
        return len(node.test.ops) > 1
    return False

def is_complex_node(node):
    if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)): return True
    if isinstance(node, ast.BoolOp) and len(node.values) >= 3: return True
    return False

def check_complex(node, filepath, source_lines):
    for child in ast.walk(node):
        if child is node: continue
        ln = getattr(child, 'lineno', 0)
        if ln == 0: continue
        if is_complex_node(child):
            if not has_comment(source_lines, ln):
                RESULTS.append(f"{filepath}:{ln} -- Complex expression without inline comment")
        elif isinstance(child, ast.If) and is_complex_conditional(child):
            if not has_comment(source_lines, child.lineno):
                RESULTS.append(f"{filepath}:{child.lineno} -- Complex conditional without inline comment")

def scan_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f: source = f.read()
        lines = source.splitlines()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
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
            if isinstance(node.value, ast.Dict):
                nelems = len(node.value.keys)
            elif isinstance(node.value, (ast.List, ast.Set, ast.Tuple)):
                nelems = len(node.value.elts)
            else:
                nelems = 0
            if nelems > 3 and not has_comment(lines, node.lineno):
                RESULTS.append(f"{filepath}:{node.lineno} -- Complex data literal without inline comment")
    check_complex(tree, filepath, lines)

def main():
    src_dir = Path('src')
    docs_dir = Path('docs')
    py_files = sorted(src_dir.rglob('*.py'))
    for pf in py_files: scan_file(str(pf))
    by_file = {}
    for r in RESULTS:
        key = r.split('--')[0].split(':')[0] if ':' in r else r
        by_file.setdefault(key, []).append(r)
    lines = []
    lines.append("CITYESTATE DOCUMENTATION SCAN REPORT")
    lines.append("=" * 60)
    lines.append("")
    if not docs_dir.exists():
        lines.append("docs/ directory: DOES NOT EXIST")
    else:
        df = [f for f in docs_dir.rglob('*') if f.is_file()]
        if not df:
            lines.append("docs/ directory: EXISTS BUT IS EMPTY -- no API documentation found")
        else:
            lines.append(f"docs/ directory: {len(df)} file(s)")
    lines.append(f"")
    lines.append(f"Scanned {len(py_files)} Python files in src/")
    lines.append(f"")
    for fpath in sorted(by_file.keys()):
        lines.append(f"--- {fpath} ---")
        for item in by_file[fpath]:
            rest = item.split(':', 1)[1].strip() if ':' in item else item
            lines.append(f"  {rest}")
        lines.append("")
    unique = set(r.split(':')[0] for r in RESULTS)
    lines.append(f"SUMMARY")
    lines.append(f"Total issues: {len(RESULTS)}")
    lines.append(f"Files with issues: {len(unique)}")
    report = '\n'.join(lines)
    with open('docs_scan_final.txt', 'w') as f: f.write(report)
    # Also print to stdout
    print(report)

if __name__ == '__main__':
    main()
