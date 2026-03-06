---
description: Create spec.md and checklist.md for an EquityIQ spec
argument-hint: spec-id [slug] or spec-id-slug (e.g., S1.1 dependency-declaration or S1.1-dependency-declaration)
allowed-tools: Read, Write, Edit, Grep
---

Create spec documentation for: $ARGUMENTS

## Step 1: Resolve Spec Identity

Parse from arguments:
- Two args (e.g. S1.1 dependency-declaration): spec_id=$1, slug=$2
- One arg (e.g. S1.1-dependency-declaration): parse as spec-Sx.y-slug, extract spec_id and slug

Read `roadmap.md` Master Spec Index or phase tables to get:
- **Spec Location** (e.g., specs/spec-S1.1-dependency-declaration/)
- **Feature** (short name)
- **Location** (code files)
- **Depends On** (prerequisites)
- **Notes** (constraints, details)

## Step 2: Create spec.md and checklist.md

Create the spec folder (e.g. specs/spec-S1.1-dependency-declaration/) and write both files. Use the templates below, substituting SPEC_ID, SLUG, and FEATURE_NAME (slug with hyphens->spaces).

**spec.md template:**
```markdown
# Spec SPEC_ID -- FEATURE_NAME

## Overview
[One paragraph from roadmap Feature + Notes]

## Dependencies
[From roadmap "Depends On" column]

## Target Location
[From roadmap "Location" column]

---

## Functional Requirements

### FR-1: [Requirement name]
- **What**: Clear description of the behavior
- **Inputs**: Parameters, types, sources
- **Outputs**: Return type, side effects
- **Edge cases**: Invalid input, timeouts, empty results

### FR-2: [Add more as needed]

---

## Tangible Outcomes

- [ ] **Outcome 1**: Observable result (testable)
- [ ] **Outcome 2**: Verifiable state (testable)
- [ ] **Outcome 3**: Test assertion (testable)

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_{name}**: Description
2. **test_{name}**: ...

### Mocking Strategy
- External services (Polygon, FRED, NewsAPI, SEC, Gemini): mock in tests
- Use pytest-mock and pytest-asyncio for async test support

### Coverage Expectation
- All public functions have at least one test; edge cases covered

---

## References
- roadmap.md, design.md
```

**checklist.md template:**
```markdown
# Checklist -- Spec SPEC_ID: FEATURE_NAME

## Phase 1: Setup & Dependencies
- [ ] Verify dependencies (Sx.y) are implemented
- [ ] Create or locate target files
- [ ] Add any new imports/dependencies to pyproject.toml if needed

## Phase 2: Tests First (TDD)
- [ ] Write test file: tests/.../test_{module}.py
- [ ] Write failing tests for each FR
- [ ] Run make local-test -- expect failures (Red)

## Phase 3: Implementation
- [ ] Implement FR-1 -- minimal code to pass its tests
- [ ] Implement FR-2 -- ...
- [ ] Run tests -- expect pass (Green)
- [ ] Refactor if needed

## Phase 4: Integration
- [ ] Wire into app (router, dependency, lifespan) if applicable
- [ ] Run make local-lint
- [ ] Run full test suite: make local-test

## Phase 5: Verification
- [ ] All tangible outcomes checked
- [ ] No hardcoded secrets
- [ ] Logging includes request_id where applicable
- [ ] Update roadmap.md status: pending -> done (when ready)
```

## Step 3: Populate from Roadmap

Fill in the placeholders using roadmap data. Ensure:

- Overview, Dependencies, Target Location -- from roadmap
- Functional Requirements -- concrete, testable behaviors from Notes
- Tangible Outcomes -- each must be testable
- Tests to Write First -- derived from FRs

## Step 4: Update Roadmap Status

After creating spec.md and checklist.md, update `roadmap.md`:
1. Find the spec row in **both** the Phase table and the Master Spec Index table
2. Change the Status column from `pending` to `spec-written` for this spec in **both** tables
3. Verify the edit -- ensure no other rows were accidentally modified

## Rules

1. Extract from roadmap -- do not invent; use Feature and Notes
2. Every FR must map to at least one test
3. Checklist items should be completable in 15-30 min
4. Spec folder path must match roadmap (e.g., specs/spec-S1.1-dependency-declaration/)
5. Always update roadmap.md status to `spec-written` -- never leave it as `pending` after creating a spec

Report what was created, the path to the spec folder, and confirm roadmap.md was updated.
