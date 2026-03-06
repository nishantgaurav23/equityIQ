# Spec-Driven Development -- Reusable Prompt Template

> Use this as a starting prompt when setting up spec-driven development on any new project.
> Adapted from the SehatSamjho methodology. Works with Claude Code.

---

## The Prompt (copy and customize)

```
I want to build [PROJECT_NAME] using spec-driven, test-driven development.

## Project Summary
[1-2 sentences describing what the project does]

## Tech Stack
- Backend: [e.g., Python 3.12 / FastAPI / uvicorn]
- Database: [e.g., PostgreSQL, SQLite, Firestore]
- Frontend: [e.g., Next.js + TypeScript + Tailwind]
- Deployment: [e.g., GCP Cloud Run, AWS EC2, Railway]
- Testing: [e.g., pytest + pytest-asyncio]
- Linting: [e.g., ruff, line-length: 100]

## Development Methodology

### 1. Create These Files First

**roadmap.md** -- Master plan with:
- Tech stack table with rationale for each choice
- Budget estimate (cloud costs)
- Phases overview table (phase name, spec count, key output)
- Detailed phase tables with columns: Spec | Spec Location | Depends On | Location | Feature | Notes | Status
- Master Spec Index (flat table of ALL specs with status tracking)

**design.md** -- Architecture document with:
- ASCII architecture diagram
- User flow (step-by-step)
- Data flow diagram
- Tech stack rationale table
- Security design table
- Deployment architecture
- Cost estimates

**.claude/CLAUDE.md** -- Claude Code context with:
- Project summary (2 lines)
- Key rules (NEVER do X, ALWAYS do Y)
- Tech stack table
- Project structure tree
- Spec folder convention
- Spec-driven development commands table
- Code standards (async, validation, error handling, etc.)
- Testing conventions

### 2. Create These Claude Code Commands

**.claude/commands/create-spec.md**
- Input: spec ID + slug (e.g., "S1.1 dependency-declaration")
- Action: Read roadmap.md, create specs/spec-{id}-{slug}/spec.md + checklist.md
- Output: Spec folder with filled-in templates, roadmap updated to "spec-written"

**.claude/commands/implement-spec.md**
- Input: spec ID (e.g., "S1.1")
- Action: Load spec.md + checklist.md, follow TDD (Red -> Green -> Refactor)
- Rules: Write tests FIRST, implement minimal code, update checklist progressively
- Output: Working code + passing tests, roadmap updated to "done"

**.claude/commands/verify-spec.md**
- Input: spec ID
- Action: Check code exists, run tests, check lint, audit tangible outcomes
- Output: Verification report (PASS/FAIL with details)

**.claude/commands/check-spec-deps.md**
- Input: spec ID
- Action: Check all prerequisite specs are "done" with passing tests
- Output: Dependency table (READY/BLOCKING per dep)

### 3. Spec Folder Structure

```
specs/
  spec-S1.1-{slug}/
    spec.md        <- Requirements, outcomes, TDD notes
    checklist.md   <- Phase-by-phase implementation tracker
```

### 4. spec.md Template

```markdown
# Spec {ID} -- {Feature Name}

## Overview
[From roadmap]

## Dependencies
[From roadmap "Depends On"]

## Target Location
[From roadmap "Location"]

## Functional Requirements
### FR-1: {Name}
- **What**: Behavior description
- **Inputs**: Parameters, types
- **Outputs**: Return type, side effects
- **Edge cases**: Invalid input, timeouts

## Tangible Outcomes
- [ ] Outcome 1 (testable)
- [ ] Outcome 2 (testable)

## Test-Driven Requirements
### Tests to Write First
1. test_{name}: Description
### Mocking Strategy
- Mock all external services
### Coverage
- All public functions tested
```

### 5. checklist.md Template

```markdown
# Checklist -- Spec {ID}: {Feature}

## Phase 1: Setup & Dependencies
- [ ] Verify deps are implemented
- [ ] Create target files

## Phase 2: Tests First (TDD)
- [ ] Write test file
- [ ] Write failing tests for each FR
- [ ] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [ ] Implement FR-1 -- pass tests
- [ ] Run tests -- expect pass (Green)
- [ ] Refactor if needed

## Phase 4: Integration
- [ ] Wire into app
- [ ] Run lint
- [ ] Run full test suite

## Phase 5: Verification
- [ ] All outcomes checked
- [ ] No hardcoded secrets
- [ ] Update roadmap status
```

### 6. Workflow

```
For each spec (in dependency order):
  1. /create-spec S{x}.{y} {slug}     <- generates spec.md + checklist.md
  2. /check-spec-deps S{x}.{y}        <- verify prerequisites met
  3. /implement-spec S{x}.{y}          <- TDD implementation
  4. /verify-spec S{x}.{y}            <- post-implementation audit
  5. Commit when spec is "done"
```

### 7. Status Flow

```
pending -> spec-written -> done
```

- `pending`: Spec exists in roadmap but no spec.md yet
- `spec-written`: spec.md + checklist.md created
- `done`: Code + tests passing, roadmap updated

## Key Principles

1. **Spec before code** -- Never write code without a spec
2. **Tests before implementation** -- Red -> Green -> Refactor
3. **One spec at a time** -- Complete fully before starting next
4. **Dependencies respected** -- /check-spec-deps before /implement-spec
5. **Progressive checklist** -- Update as you go, not at the end
6. **Roadmap is truth** -- Always reflects current project state
7. **Every FR is testable** -- If you can't test it, rewrite the requirement
8. **Mock externals** -- Tests never hit real APIs
9. **No hardcoded secrets** -- All config via environment
10. **Async by default** -- async def, await, non-blocking I/O

## Budget-Conscious Deployment Tips

### GCP (Under $50/month)
- Cloud Run: 2M requests free, scale to 0 when idle
- Firestore: 1GB + 50K reads/day free
- Secret Manager: 6 active versions free
- Artifact Registry: 500MB free
- GitHub Actions for CI/CD (free for public repos)
- Single container with all services (avoid multi-service overhead)

### AWS (Under $50/month)
- EC2 t3.micro: Free tier 12 months
- RDS db.t3.micro: Free tier 12 months
- S3: 5GB free
- Upstash Redis: Free tier (10K req/day)
- GitHub Actions for CI/CD
```

---

## Example: Applying to a New Project

```
I want to build "MealPlanAI" -- an AI meal planning app.

Tech Stack: Python 3.12 / FastAPI, PostgreSQL, Next.js, AWS EC2

Please create:
1. roadmap.md with phases: Project Setup, Data Layer, Recipe Engine,
   Meal Planning, User Preferences, API Layer, Frontend, Deployment
2. design.md with architecture diagram and data flow
3. .claude/CLAUDE.md with project context
4. .claude/commands/ with create-spec, implement-spec, verify-spec, check-spec-deps

Follow the spec-driven development methodology. Each spec should be
small enough to implement in 15-30 minutes. TDD throughout.
```
