import os, subprocess, ast

# Check for TODO/FIXME comments (with encoding handling)
print("=== TODO/FIXME COUNT ===")
count = 0
for root, dirs, files in os.walk('src'):
    if '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                    for i, line in enumerate(fh, 1):
                        if 'TODO' in line or 'FIXME' in line or 'HACK' in line or 'XXX' in line:
                            print(f"  {path}:{i} - {line.strip()[:100]}")
                            count += 1
            except:
                pass
print(f"Total TODO/FIXME items: {count}")

# Check for functions without docstrings
print("\n=== PUBLIC FUNCTIONS WITHOUT DOCSTRINGS ===")
no_doc_count = 0
for root, dirs, files in os.walk('src'):
    if '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not ast.get_docstring(node):
                            if not node.name.startswith('_') and node.name != '__init__':
                                print(f"  {path}:{node.lineno} - {node.name}")
                                no_doc_count += 1
            except:
                pass
print(f"Total public functions without docstrings: {no_doc_count}")

# Check for functions with too many parameters (>5)
print("\n=== FUNCTIONS WITH >5 PARAMETERS ===")
big_params = 0
for root, dirs, files in os.walk('src'):
    if '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = node.args
                        total_args = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
                        if total_args > 5 and not node.name.startswith('_'):
                            print(f"  {path}:{node.lineno} - {node.name} ({total_args} params)")
                            big_params += 1
            except:
                pass
print(f"Total functions with >5 params: {big_params}")
