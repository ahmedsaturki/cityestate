import os, re, sys
from collections import defaultdict

BASE = "D:/cityestate/src"

def find_py_files():
    files = []
    for root, dirs, fns in os.walk(BASE):
        for f in fns:
            if f.endswith(".py"):
                files.append(os.path.join(root, f))
    return sorted(files)

def scan_file(fp):
    issues = []
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception as e:
        return [f"  ERROR reading file: {e}"]

    rel_path = fp.replace(BASE + "/", "")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip imports and comments for most checks
        is_import = stripped.startswith("import") or stripped.startswith("from")
        is_comment = stripped.startswith("#")

        # 1. Missing return type hint on function def
        if re.match(r"^\s*def\s+\w+\s*\(", stripped) and "->" not in stripped:
            func_name = re.search(r"def\s+(\w+)\s*\(", stripped)
            if func_name and not func_name.group(1).startswith("__"):
                issues.append(f"{rel_path}:{i}: MISSING_RETURN_TYPE: {stripped[:150]}")

        # 2. Any type usage (not in import lines)
        if re.search(r"\bAny\b", stripped) and not is_import and not is_comment:
            issues.append(f"{rel_path}:{i}: USES_ANY: {stripped[:150]}")

        # 3. Optional without default value = None
        if "Optional[" in stripped and not is_import and not is_comment:
            # Check if it's a function parameter with Optional but no default
            # Pattern: param_name: Optional[Something] or param_name: Optional[Something] = None
            if ":" in stripped and "=" not in stripped.split("Optional")[0].split(":")[-1]:
                # It's a param with Optional but no default
                issues.append(f"{rel_path}:{i}: OPTIONAL_NO_DEFAULT: {stripped[:150]}")

        # 4. Untyped dict return (return {} with no return type annotation nearby)
        if re.match(r"^return\s+\{", stripped) or re.match(r"^return\s+dict\(", stripped):
            # Look back up to 10 lines for a return type annotation
            has_return_type = False
            for j in range(max(0, i - 10), i):
                if "->" in lines[j]:
                    has_return_type = True
                    break
            if not has_return_type:
                issues.append(f"{rel_path}:{i}: UNTYPED_DICT_RETURN: {stripped[:150]}")

        # 5. Unsafe cast
        if re.search(r"\bcast\s*\(", stripped):
            issues.append(f"{rel_path}:{i}: UNSAFE_CAST: {stripped[:150]}")

        # 6. Function with no param type annotations (at least one param untyped)
        m = re.match(r"^\s*def\s+(\w+)\s*\((.*)\)", stripped)
        if m and "->" not in stripped:
            func_name = m.group(1)
            if func_name.startswith("__") and func_name.endswith("__"):
                continue
            params_str = m.group(2)
            # Split params, skip self/cls
            params = [p.strip() for p in params_str.split(",")]
            for p in params:
                if p in ("self", "cls", ""):
                    continue
                # Check if param has type annotation (contains ':' and ')' or end)
                if ":" not in p and not p.endswith(")"):
                    issues.append(f"{rel_path}:{i}: UNTYPED_PARAM: {stripped[:150]} (param: {p})")
                    break  # One untyped param is enough

    return issues

def check_pydantic_fields():
    """Check Pydantic models for field validation gaps"""
    issues = []
    files = find_py_files()
    for fp in files:
        rel_path = fp.replace(BASE + "/", "")
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.split("\n")
        except:
            continue

        in_class = False
        class_name = ""
        has_basemodel = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if "BaseModel" in stripped:
                has_basemodel = True

            # Track class scope
            class_match = re.match(r"^\s*class\s+(\w+)", stripped)
            if class_match:
                in_class = True
                class_name = class_match.group(1)

            # Check for Field() without validation constraints
            if has_basemodel and in_class and "Field(" in stripped and "..." not in stripped:
                # Check if Field has validation like ge, le, gt, lt, min_length, max_length, regex, etc.
                field_call = stripped
                has_validation = any(kw in field_call for kw in [
                    "ge=", "le=", "gt=", "lt=", "min_length=", "max_length=",
                    "regex=", "pattern=", "exclude=", "discriminator=",
                    "validate_default=", "frozen=", "allow_reuse="
                ])
                # Check if Field has ... ellipsis (required field, which is fine)
                if not has_validation and "..." not in field_call:
                    # Check if it's a Field with just default values (no constraints)
                    issues.append(f"{rel_path}:{i}: PYDANTIC_FIELD_NO_VALIDATION: {stripped[:150]}")

            # Check for untyped class attributes (no annotation)
            if in_class and not is_import_line(stripped) and not is_comment_line(stripped):
                # Match attr = value without type annotation
                attr_match = re.match(r"^\s*(\w+)\s*=\s*", stripped)
                if attr_match and ":" not in stripped.split("=")[0]:
                    attr_name = attr_match.group(1)
                    # Skip private/dunder and methods
                    if not attr_name.startswith("_") and not attr_name.startswith("__"):
                        # Check if this is inside a Pydantic model class
                        if has_basemodel:
                            issues.append(f"{rel_path}:{i}: PYDANTIC_UNTYPED_ATTR: {stripped[:150]}")

    return issues

def is_import_line(stripped):
    return stripped.startswith("import") or stripped.startswith("from")

def is_comment_line(stripped):
    return stripped.startswith("#")

def main():
    files = find_py_files()
    all_issues = defaultdict(list)
    pydantic_issues = []

    print(f"Scanning {len(files)} Python files for type safety issues...\n")

    for fp in files:
        issues = scan_file(fp)
        if issues:
            for issue in issues:
                # Categorize
                if "MISSING_RETURN_TYPE" in issue:
                    all_issues["missing_return_type"].append(issue)
                elif "USES_ANY" in issue:
                    all_issues["uses_any"].append(issue)
                elif "OPTIONAL_NO_DEFAULT" in issue:
                    all_issues["optional_no_default"].append(issue)
                elif "UNTYPED_DICT_RETURN" in issue:
                    all_issues["untyped_dict_return"].append(issue)
                elif "UNSAFE_CAST" in issue:
                    all_issues["unsafe_cast"].append(issue)
                elif "UNTYPED_PARAM" in issue:
                    all_issues["untyped_param"].append(issue)

    pydantic_issues = check_pydantic_fields()

    # Print results
    print("=" * 80)
    print("TYPE SAFETY SCAN RESULTS")
    print("=" * 80)

    categories = {
        "missing_return_type": "Missing Return Type Hints",
        "uses_any": "Uses Any Type",
        "optional_no_default": "Optional Without Default Values",
        "untyped_dict_return": "Untyped Dict Returns",
        "unsafe_cast": "Unsafe Casts",
        "untyped_param": "Untyped Function Parameters",
    }

    total = 0
    for key, title in categories.items():
        items = all_issues.get(key, [])
        total += len(items)
        print(f"\n--- {title} ({len(items)}) ---")
        for item in items[:80]:  # Limit per category
            print(item)
        if len(items) > 80:
            print(f"  ... and {len(items) - 80} more")

    print(f"\n--- Pydantic Field Validation Gaps ({len(pydantic_issues)}) ---")
    for item in pydantic_issues[:50]:
        print(item)
    if len(pydantic_issues) > 50:
        print(f"  ... and {len(pydantic_issues) - 50} more")

    print(f"\n{'=' * 80}")
    print(f"TOTAL ISSUES: {total + len(pydantic_issues)}")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
