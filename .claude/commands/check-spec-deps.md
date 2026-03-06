---
description: Verify all prerequisite specs for a given spec are implemented and passing
argument-hint: spec-id (e.g., S4.1, S7.4)
allowed-tools: Read, Bash, Grep, Glob
---

Check whether all dependencies for spec $ARGUMENTS are satisfied.

## Step 1: Resolve Spec

1. Read `roadmap.md` and find the row for spec $ARGUMENTS
2. Extract the **Depends On** column (e.g., "S1.3, S2.4")
3. If "--" or empty, report "No dependencies -- ready to implement" and stop

## Step 2: For Each Dependency Spec

For each dependency spec ID (e.g., S1.3):

### 2a. Check roadmap status
- Read the spec's row in `roadmap.md` -> check Status column
- If not "done": flag as **BLOCKING**

### 2b. Check code file exists
- Read the spec's **Location** column (e.g., `config/settings.py`)
- Glob for the file -- if missing: flag as **BLOCKING**

### 2c. Check test file exists
- Glob for `tests/**/test_*.py` files that correspond to the code location
- If no matching test file: flag as **WARNING** (some specs like data files don't have tests)

### 2d. Check tests pass
- If test file exists, run: `python -m pytest {test_file} -v --tb=short -q`
- If tests fail: flag as **BLOCKING**

## Step 3: Report

Print a summary table:

```
Dependency Check for {spec_id}
------------------------------
| Dep   | Status  | Code | Tests | Result    |
|-------|---------|------|-------|-----------|
| S1.3  | done    | OK   | OK 5/5| READY     |
| S2.4  | pending | OK   | FAIL  | BLOCKING  |
```

Final verdict:
- **READY**: All deps satisfied -> safe to implement
- **BLOCKED**: List which deps need work first, in dependency order
