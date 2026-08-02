import os, re, sys

BASE = "D:/cityestate/src"

files = []
for root, dirs, fns in os.walk(BASE):
    for f in fns:
        if f.endswith(".py"):
            files.append(os.path.join(root, f))

out = []
out.append("=" * 70)
out.append("TYPE SAFETY AUDIT — CityEstate src/")
out.append("=" * 70)

# Category 1: Missing return type hints
missing_return = []
for fp in sorted(files):
    rel = fp.replace(BASE + "/", "")
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                s = line.strip()
                if re.match(r"^\s*def\s+\w+\s*\(", s) and "->" not in s:
                    fn = re.search(r"def\s+(\w+)\s*\(", s)
                    if fn and not fn.group(1).startswith("__"):
                        missing_return.append((rel, i, s[:120]))
    except:
        pass

out.append(f"\n1. MISSING RETURN TYPE HINTS: {len(missing_return)}")
for f, n, l in missing_return[:50]:
    out.append(f"   {f}:{n}: {l}")
if len(missing_return) > 50:
    out.append(f"   ... and {len(missing_return)-50} more")

# Category 2: Any type usage
uses_any = []
for fp in sorted(files):
    rel = fp.replace(BASE + "/", "")
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                s = line.strip()
                if re.search(r"\bAny\b", s) and not s.startswith("#") and not s.startswith("import") and not s.startswith("from"):
                    uses_any.append((rel, i, s[:150]))
    except:
        pass

out.append(f"\n2. USES Any TYPE: {len(uses_any)}")
for f, n, l in uses_any[:40]:
    out.append(f"   {f}:{n}: {l}")
if len(uses_any) > 40:
    out.append(f"   ... and {len(uses_any)-40} more")

# Category 3: Optional without default in Pydantic models
opt_no_default = []
for fp in sorted(files):
    rel = fp.replace(BASE + "/", "")
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except:
        continue
    in_basemodel = False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if "BaseModel" in s:
            in_basemodel = True
        if in_basemodel and re.match(r"^\s*class\s+\w+", s) and "BaseModel" not in s:
            in_basemodel = False
        if "Optional[" in s and in_basemodel and not s.startswith("#") and not s.startswith("import") and not s.startswith("from"):
            has_default = "=None" in s or "default=" in s or "default_factory=" in s
            if not has_default:
                opt_no_default.append((rel, i, s[:120]))

out.append(f"\n3. Optional WITHOUT DEFAULT in Pydantic models: {len(opt_no_default)}")
for f, n, l in opt_no_default[:20]:
    out.append(f"   {f}:{n}: {l}")
if len(opt_no_default) > 20:
    out.append(f"   ... and {len(opt_no_default)-20} more")

# Category 4: Pydantic field validation gaps
pydantic_gaps = []
for fp in sorted(files):
    rel = fp.replace(BASE + "/", "")
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except:
        continue
    in_basemodel = False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if "BaseModel" in s:
            in_basemodel = True
        if in_basemodel and re.match(r"^\s*class\s+\w+", s) and "BaseModel" not in s:
            in_basemodel = False
        if in_basemodel and "Field(" in s and not s.startswith("#") and not s.startswith("import") and not s.startswith("from"):
            has_constraint = any(kw in s for kw in ["ge=", "le=", "gt=", "lt=", "min_length=", "max_length=", "regex=", "pattern="])
            has_default = "default=" in s or "default_factory=" in s
            is_required = "..." in s
            if not has_constraint and not has_default and not is_required and "description=" not in s:
                pydantic_gaps.append((rel, i, s[:150]))

out.append(f"\n4. PYDANTIC FIELDS WITHOUT VALIDATION: {len(pydantic_gaps)}")
for f, n, l in pydantic_gaps[:20]:
    out.append(f"   {f}:{n}: {l}")
if len(pydantic_gaps) > 20:
    out.append(f"   ... and {len(pydantic_gaps)-20} more")

# Category 5: Untyped function parameters
untyped_params = []
for fp in sorted(files):
    rel = fp.replace(BASE + "/", "")
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                s = line.strip()
                m = re.match(r"^\s*def\s+(\w+)\s*\((.*)\)\s*:", s)
                if m and "->" not in s:
                    fn_name = m.group(1)
                    if fn_name.startswith("__"):
                        continue
                    params = m.group(2)
                    for p in params.split(","):
                        p = p.strip()
                        if p in ("self", "cls", ""):
                            continue
                        if ":" not in p and "=" not in p:
                            untyped_params.append((rel, i, fn_name, p, s[:120]))
                            break
    except:
        pass

out.append(f"\n5. UNTYPED FUNCTION PARAMETERS: {len(untyped_params)}")
for f, n, fn, p, l in untyped_params[:30]:
    out.append(f"   {f}:{n}: func={fn} param='{p}' : {l}")
if len(untyped_params) > 30:
    out.append(f"   ... and {len(untyped_params)-30} more")

# Category 6: Untyped dict returns (bare dict)
dict_returns = []
for fp in sorted(files):
    rel = fp.replace(BASE + "/", "")
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except:
        continue
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if re.match(r"^return\s+\{", s) or re.match(r"^return\s+dict\(", s):
            # Check if function has return type annotation
            has_ret = False
            for j in range(max(0, i-6), i):
                if "->" in lines[j]:
                    has_ret = True
                    break
            if not has_ret:
                dict_returns.append((rel, i, s[:120]))

out.append(f"\n6. UNTYPED DICT RETURNS (no return type annotation): {len(dict_returns)}")
for f, n, l in dict_returns[:30]:
    out.append(f"   {f}:{n}: {l}")
if len(dict_returns) > 30:
    out.append(f"   ... and {len(dict_returns)-30} more")

# Category 7: Unsafe casts
casts = []
for fp in sorted(files):
    rel = fp.replace(BASE + "/", "")
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                s = line.strip()
                if re.search(r"\bcast\s*\(", s):
                    casts.append((rel, i, s[:120]))
    except:
        pass

out.append(f"\n7. UNSAFE CASTS: {len(casts)}")
for f, n, l in casts:
    out.append(f"   {f}:{n}: {l}")

# Write results
result_text = "\n".join(out)
with open("D:/cityestate/type_safety_report.txt", "w", encoding="utf-8") as fh:
    fh.write(result_text)

out.append(f"\n{'=' * 70}")
out.append("TOTAL ISSUES BY CATEGORY")
out.append("=" * 70)
out.append(f"Missing return type hints: {len(missing_return)}")
out.append(f"Uses Any type: {len(uses_any)}")
out.append(f"Optional without default (Pydantic): {len(opt_no_default)}")
out.append(f"Pydantic field validation gaps: {len(pydantic_gaps)}")
out.append(f"Untyped dict returns (no annotation): {len(dict_returns)}")
out.append(f"Untyped function parameters: {len(untyped_params)}")
out.append(f"Unsafe casts: {len(casts)}")
out.append(f"TOTAL (approximate): {len(missing_return) + len(uses_any) + len(opt_no_default) + len(pydantic_gaps) + len(dict_returns) + len(untyped_params) + len(casts)}")

print(result_text)
print("\nReport saved to D:/cityestate/type_safety_report.txt")
