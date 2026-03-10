# Spec S13.1 -- Next.js Scaffold

## Overview
Create the Next.js frontend application with TypeScript and Tailwind CSS. Set up API proxy to the FastAPI backend. Configure environment variables for backend URL and other settings. This is the foundation for all frontend pages (analysis, portfolio, history).

## Dependencies
- S9.1 (POST /analyze/{ticker} endpoint) -- done

## Target Location
- `frontend/` -- Next.js project root

---

## Functional Requirements

### FR-1: Next.js Project Initialization
- **What**: Initialize a Next.js 14+ app with App Router, TypeScript, and Tailwind CSS
- **Inputs**: None (project scaffold)
- **Outputs**: `frontend/` directory with standard Next.js structure (`app/`, `public/`, `next.config.js`, `tsconfig.json`, `tailwind.config.ts`, `package.json`)
- **Edge cases**: Ensure no conflicting dependencies with project root

### FR-2: Environment Configuration
- **What**: Configure environment variables for backend API URL and app settings
- **Inputs**: `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`), `NEXT_PUBLIC_APP_NAME` (defaults to `EquityIQ`)
- **Outputs**: `.env.local.example` with documented variables, `lib/config.ts` with typed config access
- **Edge cases**: Missing env vars fall back to sensible defaults

### FR-3: API Proxy / Client Setup
- **What**: Create a typed API client that proxies requests to the FastAPI backend. Uses Next.js API routes or direct fetch to avoid CORS issues in development.
- **Inputs**: Backend URL from env config
- **Outputs**: `lib/api.ts` with typed functions: `analyzeStock(ticker: string): Promise<FinalVerdict>`, error handling wrapper
- **Edge cases**: Network errors, timeout (60s match backend), non-200 responses mapped to typed errors

### FR-4: TypeScript Type Definitions
- **What**: Define TypeScript interfaces matching backend Pydantic models (FinalVerdict, AnalystReport variants, PortfolioInsight)
- **Inputs**: Backend data_contracts.py schemas
- **Outputs**: `types/api.ts` with all response types
- **Edge cases**: Optional fields, enum values for signals (BUY/HOLD/SELL/STRONG_BUY/STRONG_SELL)

### FR-5: Layout and Base Styling
- **What**: Create root layout with app shell -- header with app name, main content area, footer
- **Inputs**: None
- **Outputs**: `app/layout.tsx` with metadata, `app/globals.css` with Tailwind directives, responsive base layout
- **Edge cases**: Dark mode support via Tailwind class strategy

### FR-6: Health Check Page
- **What**: Root page (`/`) shows app name, brief description, and backend connection status indicator
- **Inputs**: Backend `/health` endpoint response
- **Outputs**: `app/page.tsx` with connection status badge (green/red), link to analyze page
- **Edge cases**: Backend unreachable shows "offline" status gracefully

---

## Tangible Outcomes

- [ ] **Outcome 1**: `frontend/package.json` exists with next, react, typescript, tailwindcss dependencies
- [ ] **Outcome 2**: `npm run build` completes without errors in `frontend/`
- [ ] **Outcome 3**: `frontend/lib/api.ts` exports `analyzeStock()` function with proper TypeScript types
- [ ] **Outcome 4**: `frontend/types/api.ts` defines FinalVerdict, AnalystReport, and signal enum types
- [ ] **Outcome 5**: `frontend/.env.local.example` documents all required environment variables
- [ ] **Outcome 6**: `frontend/app/layout.tsx` renders header, main content area, and footer
- [ ] **Outcome 7**: `frontend/app/page.tsx` displays app name and backend health status

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_frontend_project_structure**: Verify all required files exist (`package.json`, `tsconfig.json`, `tailwind.config.ts`, `next.config.mjs`, `app/layout.tsx`, `app/page.tsx`)
2. **test_package_json_dependencies**: Verify `package.json` contains required dependencies (next, react, react-dom, typescript, tailwindcss)
3. **test_env_example_exists**: Verify `.env.local.example` exists with `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_APP_NAME`
4. **test_api_client_exists**: Verify `lib/api.ts` exists and exports analyzeStock function
5. **test_types_file_exists**: Verify `types/api.ts` defines FinalVerdict interface with required fields
6. **test_layout_structure**: Verify `app/layout.tsx` contains html, body, header, main, footer elements
7. **test_homepage_content**: Verify `app/page.tsx` contains EquityIQ branding and health check component
8. **test_typescript_compiles**: Run `npx tsc --noEmit` and verify no type errors
9. **test_tailwind_configured**: Verify `tailwind.config.ts` includes `app/` and `components/` in content paths
10. **test_next_config_exists**: Verify `next.config.mjs` exists with API rewrites/proxy config

### Mocking Strategy
- Backend API calls: mock fetch/axios responses in tests
- Use Jest + React Testing Library for component tests
- Use file existence checks (Python tests) for structural validation

### Coverage Expectation
- All structural files verified to exist
- TypeScript compilation passes
- Build succeeds without errors

---

## References
- roadmap.md, design.md
- Backend data contracts: `config/data_contracts.py`
- Backend health endpoint: `app.py` `/health`
