---
description: Verify a spec is fully implemented -- tests, lint, outcomes, wiring
argument-hint: spec-id (e.g., S1.1, S4.2)
allowed-tools: Read, Bash, Grep, Glob
---

Verify that spec $ARGUMENTS is fully and correctly implemented.

## Step 1: Load Spec Context

1. Find spec folder: `specs/spec-$ARGUMENTS*/`
2. Read `spec.md` -- extract Tangible Outcomes and Functional Requirements
3. Read `checklist.md` -- note any unchecked items
4. Read `roadmap.md` row for this spec -- get Location, Feature, Notes

## Step 2: Code Existence

- Check every file listed in the spec's **Target Location** exists
- Check each file is non-empty and has the expected public functions/classes mentioned in FRs
- Report: files found, missing files, missing functions

## Step 3: Test Suite

1. Find test files: glob `tests/**/test_*.py` matching the module
2. Run tests: `python -m pytest {test_files} -v --tb=short`
3. Report: total tests, passed, failed, errors
4. If any failures: show the first 3 failure summaries

## Step 4: Lint

Run: `python -m ruff check --select E,F,W` on spec's target files only.
Report: clean or list issues.

## Step 5: Tangible Outcomes Audit

For each Tangible Outcome listed in spec.md:
- Check if there is a corresponding test that verifies it
- Check if the implementation satisfies it (read the relevant code)
- Mark: PASS / FAIL / UNCLEAR

## Step 6: Integration Check

- If spec involves a router: verify it's included in `app.py`
- If spec involves a FastAPI dependency: verify it's used where expected
- If spec involves a service function: verify it's importable from its module
- If spec involves config fields: verify they exist in `config/settings.py`

## Step 7: Report

```
Verification Report -- Spec {spec_id}: {feature}
----------------------------------------------------
Code files:      OK All present
Tests:           OK 8/8 passing
Lint:            OK Clean
Outcomes:        OK 3/3 verified
Integration:     OK Wired into app.py
Checklist:       WARN 1 unchecked item (Phase 4 -- lint)

VERDICT: PASS (with 1 minor item)
```

If PASS: suggest updating `roadmap.md` status from `pending` -> `done`.
If FAIL: list exactly what needs to be fixed, in priority order.
