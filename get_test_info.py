import sys
from collections import Counter

lines = [l.strip() for l in sys.stdin if l.strip()]
print('Total tests:', len(lines))
files = Counter()
for l in lines:
    f = l.split('::')[0]
    files[f] += 1
for f, c in sorted(files.items()):
    print(f'{c:3d} {f}')
