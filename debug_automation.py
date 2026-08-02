with open('D:/cityestate/src/api/routes/automation.py', 'rb') as f:
    content = f.read()

idx = content.find(b'cwd=project_root')
print(f'Found at byte {idx}')
if idx >= 0:
    snippet = content[idx-5:idx+30]
    print(f'Snippet: {repr(snippet)}')
    print(f'Length: {len(snippet)}')
    # Check for CRLF
    if b'\r\n' in snippet:
        print('Has CRLF')
    if b'\n' in snippet:
        print('Has LF')
