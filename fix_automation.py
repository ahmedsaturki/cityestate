with open('D:/cityestate/src/api/routes/automation.py', 'rb') as f:
    content = f.read()

# Fix PLW1510: add check=False to subprocess.run in automation.py
old = b'cwd=project_root,\r\n            )\r\n'
new = b'cwd=project_root,\r\n                check=False,\r\n            )\r\n'
if old in content:
    content = content.replace(old, new, 1)
    with open('D:/cityestate/src/api/routes/automation.py', 'wb') as f:
        f.write(content)
    print('Fixed automation.py')
else:
    print('Pattern not found in automation.py')
