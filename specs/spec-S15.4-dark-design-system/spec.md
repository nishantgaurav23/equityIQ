# S15.4 -- Frontend Dark Design System

## Feature
Dark glassmorphism design system with Framer Motion

## Location
- `frontend/app/globals.css`
- `frontend/tailwind.config.ts`
- `frontend/package.json`

## Depends On
- S13.1 (Next.js scaffold)

## Description
Install framer-motion and lucide-react. Create dark theme with glassmorphism cards
(semi-transparent backgrounds, backdrop-blur, gradient borders). Define color palette:
dark slate backgrounds (#0a0a0f base), blue/cyan accents, green for BUY, red for SELL,
yellow for HOLD. Add custom Tailwind classes: glass, glass-dark, gradient-text, glow
shadows. Add subtle animated background effects (gradient orbs with blur). Custom
scrollbar styling.

## Acceptance Criteria
1. framer-motion and lucide-react installed
2. globals.css has glass, glass-dark, gradient-text utility classes
3. Tailwind config extended with dark-950 color, glow shadows, shimmer animation
4. Background has subtle animated gradient orbs
5. Custom scrollbar styling
6. Dark theme is default (no light mode toggle needed)
