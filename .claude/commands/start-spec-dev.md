---
description: Full spec lifecycle -- create, check deps, implement, and verify a spec in one go
argument-hint: spec-id [slug] (e.g., S1.1 dependency-declaration)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

Run the full spec development lifecycle for: $ARGUMENTS

## Execution Mode: Step-by-Step with Context Clearing

This command runs in step-by-step mode. Do NOT ask for permission between steps -- show results and continue automatically. Only stop if a step fails (blocked deps, test failures, etc.).

**Context clearing**: After Steps 1-2 (create + deps), run `/clear` to free up context. After Steps 3-4 (implement + verify), run `/clear` again.

---

## Phase A: Spec Setup (then /clear)

### Step 1: Create Spec

Run `/create-spec $ARGUMENTS`

This creates `specs/spec-{id}-{slug}/spec.md` and `checklist.md` from the roadmap, and updates roadmap.md status to `spec-written`.

After completion, show what was created and the spec folder path.

### Step 2: Check Dependencies

Run `/check-spec-deps {spec_id}`

Verify all prerequisite specs are implemented and their tests pass.

- If **BLOCKED**: Stop and report which dependencies need work first. Do NOT continue.
- If **READY**: Show the dependency report.

### After Phase A: Run `/clear`

After Steps 1-2 complete successfully, run `/clear` to free context before implementation.

---

## Phase B: Implementation (then /clear)

### Step 3: Implement Spec

Run `/implement-spec {spec_id}`

Follow TDD strictly: Red -> Green -> Refactor. Update checklist.md progressively.

After all tests pass, show the results.

### Step 4: Verify Spec

Run `/verify-spec {spec_id}`

Audit: code existence, tests, lint, tangible outcomes, integration wiring.

### After Phase B: Run `/clear`

After Steps 3-4 complete, run `/clear` to free context.

---

## Step 5: Final Report

After verification, print a summary:

```
=== Spec {spec_id} -- Full Lifecycle Complete ===
1. Create Spec:    DONE -- specs/spec-{id}-{slug}/
2. Check Deps:     DONE -- all dependencies satisfied
3. Implement:      DONE -- all tests passing
4. Verify:         {PASS/FAIL} -- see verification report above


Roadmap status: done
```

If verification returned FAIL, list the issues that need manual attention.

## Rules

1. Parse spec_id from $ARGUMENTS (first arg, e.g., S1.1)
2. If slug is provided, pass it to create-spec; otherwise create-spec will resolve it from roadmap
3. On any step failure (blocked deps, test failures that can't be fixed, lint errors that can't be auto-fixed), stop and report -- do not blindly continue
4. Always update checklist.md and roadmap.md as each sub-command requires
5. Do NOT ask for permission between steps -- show results and continue automatically. Only stop on failure.
