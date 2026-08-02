import sys

def fix_plw1510(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # Fix automation.py: add check=False to subprocess.run
    search = b'cwd=project_root,\n            )'
    replace = b'cwd=project_root,\n                check=False,\n            )'
    if search in content:
        content = content.replace(search, replace, 1)
        with open(filepath, 'wb') as f:
            f.write(content)
        print(f'Fixed {filepath}')
    else:
        print(f'Pattern not found in {filepath}')
        # Debug: show what we have
        idx = content.find(b'cwd=project_root')
        if idx >= 0:
            print(f'Found at byte {idx}: {repr(content[idx-20:idx+50])}')

def fix_jobs_plw1510(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # Fix jobs.py: add check=False to subprocess.run
    search = b'capture_output=True,\n                text=True,\n                timeout=300,\n                env={**os.environ, "PYTHONIOENCODING": "utf-8"},\n            )'
    replace = b'capture_output=True,\n                text=True,\n                timeout=300,\n                env={**os.environ, "PYTHONIOENCODING": "utf-8"},\n                check=False,\n            )'
    if search in content:
        content = content.replace(search, replace, 1)
        with open(filepath, 'wb') as f:
            f.write(content)
        print(f'Fixed {filepath}')
    else:
        print(f'Pattern not found in {filepath}')
        # Debug
        idx = content.find(b'capture_output=True')
        if idx >= 0:
            print(f'Found at byte {idx}: {repr(content[idx-20:idx+100])}')

if __name__ == '__main__':
    fix_plw1510('D:/cityestate/src/api/routes/automation.py')
    fix_jobs_plw1510('D:/cityestate/src/scheduler/jobs.py')
