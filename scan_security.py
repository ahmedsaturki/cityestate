import os, re

issues = []

key_files = [
    'src/api/main.py',
    'src/api/auth.py',
    'src/api/routes/auth.py',
    'src/api/routes/webhooks.py',
    'src/api/routes/websocket.py',
    'src/api/routes/leads.py',
    'src/api/routes/properties.py',
    'src/api/routes/requests.py',
    'src/api/routes/data.py',
    'src/api/routes/scheduler.py',
    'src/api/routes/automation.py',
    'src/api/routes/dashboard.py',
    'src/api/routes/content.py',
    'src/api/routes/skills.py',
    'src/api/routes/webhooks.py',
]

for fname in key_files:
    if not os.path.exists(fname):
        continue
    with open(fname, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if re.search(r'(password|secret|api_key|token)\s*=\s*["\x27][^"\x27]{8,}["\x27]', line, re.IGNORECASE):
            if 'example' not in fname.lower() and 'test' not in fname.lower() and 'ENV' not in line and 'os.getenv' not in line:
                issues.append(f'HARDCODED_SECRET: {fname}:{i}: {line.strip()[:80]}')
        if 'eval(' in line or 'exec(' in line:
            issues.append(f'EVAL_EXEC: {fname}:{i}')
        if 'pickle' in line.lower():
            issues.append(f'PICKLE: {fname}:{i}')
        if 'shell=True' in line:
            issues.append(f'SHELL_INJECTION: {fname}:{i}')
        if 'allow_origins' in line and '"*"' in line:
            issues.append(f'CORS_WILDCARD: {fname}:{i}')
        if 'debug=True' in line and 'env' not in line.lower():
            issues.append(f'DEBUG_MODE: {fname}:{i}')

for root, dirs, files in os.walk('src/api/routes'):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('def ') and '-> ' not in stripped and 'def __' not in stripped:
                if any(kw in stripped for kw in ['router', 'login', 'register', 'get_', 'list_', 'create_', 'update_', 'delete_', 'websocket']):
                    issues.append(f'MISSING_RETURN_TYPE: {fpath}:{i}: {stripped[:80]}')

for root, dirs, files in os.walk('src'):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'asyncio.create_task' in line and 'await' not in line:
                issues.append(f'FIRE_FORGET_ASYNC: {fpath}:{i}')
            if 'requests.' in line and 'timeout' not in line:
                issues.append(f'MISSING_TIMEOUT: {fpath}:{i}')

issues = sorted(set(issues))
print(f'Total issues found: {len(issues)}')
for issue in issues:
    print(f'  {issue}')