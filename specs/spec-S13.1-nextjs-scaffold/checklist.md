# Checklist -- Spec S13.1: Next.js Scaffold

## Phase 1: Setup & Dependencies
- [x] Verify S9.1 (analyze endpoint) is implemented and tests pass
- [x] Create `frontend/` directory
- [x] Initialize Next.js project with TypeScript + Tailwind CSS

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_nextjs_scaffold.py`
- [x] Write structural tests for project files (package.json, tsconfig, etc.)
- [x] Write tests for env config, API client, types
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] FR-1: Initialize Next.js app with App Router, TypeScript, Tailwind
- [x] FR-2: Create `.env.local.example` and `lib/config.ts`
- [x] FR-3: Create `lib/api.ts` with typed API client (analyzeStock, error handling)
- [x] FR-4: Create `types/api.ts` with FinalVerdict, AnalystReport, signal types
- [x] FR-5: Create `app/layout.tsx` with header/main/footer shell
- [x] FR-6: Create `app/page.tsx` with health check and app branding
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify `npm run build` succeeds in `frontend/`
- [x] Verify TypeScript compilation (`npx tsc --noEmit`)
- [x] Run Python test suite from project root

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets (API URL from env vars only)
- [x] Environment variables documented in `.env.local.example`
- [x] Update roadmap.md status: spec-written -> done
