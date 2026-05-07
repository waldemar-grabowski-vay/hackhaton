# Implementation Plan: Frontend SUN Color Palette Rebrand

**Branch**: `002-sun-theme-palette` | **Date**: 2026-05-07 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/002-sun-theme-palette/spec.md`

## Summary

Replace the frontend's current teal/cyan primary color (`196 90% 42%`) with the SUN warm terracotta palette across both light and dark modes. All changes are isolated to CSS custom property values in a single theme file. No application logic, component structure, or layout is affected.

## Technical Context

**Language/Version**: TypeScript 5.6.3  
**Primary Dependencies**: React 18.3.1, Tailwind CSS 3.4.13, shadcn/ui (New York style, baseColor: slate), tailwindcss-animate  
**Storage**: N/A  
**Testing**: No test suite detected in project  
**Target Platform**: Web browser (class-based dark mode; app defaults to `.dark` mode)  
**Project Type**: Web application (frontend only — Vite + React SPA)  
**Performance Goals**: No rendering performance impact; CSS-only change  
**Constraints**: Must meet 4.5:1 contrast ratio for all text on themed backgrounds; semantic colors (error, success, warning) must remain unchanged  
**Scale/Scope**: Single theme file (`src/theme/globals.css`) + one Tailwind config constant; affects all components using `primary`, `accent`, and `ring` tokens

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution is currently a blank template with no defined principles. No gates apply. No violations to justify.

**Post-design re-check**: Still clear — change is CSS-variable-only with no structural additions.

## Project Structure

### Documentation (this feature)

```text
specs/002-sun-theme-palette/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — palette values + contrast analysis
├── contracts/
│   └── color-tokens.md  # Phase 1 output — old → new token mapping
├── quickstart.md        # Phase 1 output — how to verify locally
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created here)
```

### Source Code (repository root)

```text
hackhaton/frontend/
├── src/
│   └── theme/
│       └── globals.css   ← sole change target (CSS custom properties)
└── tailwind.config.ts    ← no changes needed (reads from CSS vars)
```

**Structure Decision**: Single project, single file change. The entire color system is driven by CSS custom properties in `globals.css`. Tailwind reads these via `hsl(var(--*))` references, so the config file requires no edits.

## Complexity Tracking

No constitution violations. No complexity justification needed.
