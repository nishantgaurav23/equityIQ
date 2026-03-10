# S15.4 -- Dark Design System Checklist

## TDD Checklist

- [x] **Red**: Write tests for glass/glass-dark/gradient-text CSS classes existence
- [x] **Red**: Write tests for Tailwind config extensions (dark-950, glow, shimmer)
- [x] **Red**: Write tests for framer-motion and lucide-react in package.json dependencies
- [x] **Red**: Write tests for animated background gradient orbs
- [x] **Red**: Write tests for custom scrollbar styling
- [x] **Green**: Install framer-motion and lucide-react
- [x] **Green**: Add glass, glass-dark, gradient-text utility classes to globals.css
- [x] **Green**: Extend Tailwind config with dark-950 color, glow shadows, shimmer animation
- [x] **Green**: Add animated gradient orb background effects
- [x] **Green**: Add custom scrollbar styling to globals.css
- [x] **Green**: Set dark theme as default (no light mode toggle)
- [x] **Refactor**: Verify all tests pass
- [x] **Refactor**: Run ruff lint (line-length: 100)
- [x] **Refactor**: Update checklist -- all boxes checked

## Typography Enhancement (post-initial)
- [x] Replace Geist/Geist Mono with Plus Jakarta Sans + JetBrains Mono
- [x] Add typography scale (h1-h6 with letter-spacing, line-height)
- [x] Add .data-value class (tabular nums, font-feature-settings: "tnum", "zero")
- [x] Add .label-text class (10px uppercase tracking)
- [x] Add .section-title class (11px uppercase tracking)
- [x] Add .body-text class (13px, line-height 1.65)
- [x] Add @tailwindcss/typography plugin
- [x] Update layout.tsx to use Plus Jakarta Sans + JetBrains Mono font variables
- [x] Apply font-extrabold + tracking-tight to headings across all pages
