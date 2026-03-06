---
description: Implement an EquityIQ spec following TDD and best practices
argument-hint: spec-id (e.g., S1.1, S4.2, S10.3)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

Implement spec: $1

## Step 1: Load Spec Context

1. Find the spec folder: search for `specs/spec-$1*` or look up in `roadmap.md` Master Spec Index
2. Read `specs/spec-{id}-{slug}/spec.md` -- requirements, outcomes, TDD notes
3. Read `specs/spec-{id}-{slug}/checklist.md` -- phases to follow
4. Read `roadmap.md` phase table row for this spec
5. Read `.claude/CLAUDE.md` for project rules (async, caching, Pydantic, etc.)

## Step 2: Verify Prerequisites

- Dependencies (Depends On) are implemented
- Target files/locations exist or can be created

## Step 3: Follow TDD Strictly

**Red -> Green -> Refactor**

1. **Red**: Write failing tests first in `tests/` (mirror app structure). Mock all external services (Polygon, FRED, NewsAPI, SEC, Gemini). Run `make local-test` -- expect failures.
2. **Green**: Implement minimal code to pass tests. No extra features beyond spec.
3. **Refactor**: Clean up; re-run tests after each change.

**Checklist updates**: After completing each phase (Setup, Tests, Implementation, Integration), immediately update `checklist.md` -- change `- [ ]` to `- [x]` for every item completed in that phase. Do not wait until the end.

## Step 4: Implementation Rules

| Rule | Action |
|------|--------|
| Async | Use async def, await, httpx.AsyncClient, aiosqlite |
| Config | All secrets from settings.py / .env, never hardcode |
| Caching | TTLCache on all external API calls (Polygon 5min, FRED 1hr) |
| Models | Pydantic v2 for all in/out; use config/data_contracts.py |
| Validation | field_validator for clamping (confidence [0,1], momentum [-1,1]) |
| Errors | try/except wraps all external calls, never crash an agent |
| Logging | Structured logging with request_id where applicable |
| Lint | Ruff, line length 100; run `make local-lint` before done |

## Step 5: Verification

- [ ] All tests pass: `make local-test`
- [ ] Lint passes: `make local-lint`
- [ ] All Tangible Outcomes from spec.md are met

## Step 6: Update Checklist & Roadmap

After all tests pass and verification is complete:

### 6a. Finalize checklist.md
1. Mark all remaining Phase 5 (Verification) items as `- [x]` in `checklist.md`
2. Confirm every item across all phases is `- [x]` -- no unchecked items should remain
3. If any item was skipped (not applicable), change it to `- [x] N/A -- {reason}`

### 6b. Update roadmap.md
1. Find the spec row in **both** the Phase table and the Master Spec Index table
2. Change the Status column from `spec-written` (or `pending`) to `done` for this spec in **both** tables
3. Verify the edit -- ensure no other rows were accidentally modified

Work through checklist.md phases in order. Do not skip "Tests First". Update checklist.md progressively as each phase completes -- not all at once at the end. When done, report completion and confirm both checklist.md and roadmap.md were updated.
