import os

for root, dirs, files in os.walk('src'):
    level = root.replace('src', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in sorted(files):
        if file.endswith('.py'):
            path = os.path.join(root, file)
            size = os.path.getsize(path)
            print(f'{subindent}{file} ({size} bytes)')
