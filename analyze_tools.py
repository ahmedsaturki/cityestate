with open("src/ai_crew/tools.py", "r", encoding="utf-8") as f:
    content = f.read()
lines = content.split("\n")
for i, line in enumerate(lines[:50]):
    print(f"{i+1}: {line}")