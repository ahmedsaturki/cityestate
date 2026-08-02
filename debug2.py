with open('D:/cityestate/src/api/routes/automation.py', 'rb') as f:
    content = f.read()
idx = content.find(b'cwd=project_root')
print('Found at byte', idx)
if idx >= 0:
    snippet = content[idx-5:idx+30]
    print('Snippet:', repr(snippet))
