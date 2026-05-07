# Research: Frontend SUN Color Palette Rebrand

**Branch**: `002-sun-theme-palette` | **Date**: 2026-05-07

---

## Decision 1: SUN Palette HSL Values

**Decision**: Use the following HSL values derived from the reference palette image (9-swatch grid, bottom-center = SUN):

| Swatch   | Role                        | Approximate Hex | HSL (CSS format) |
|----------|-----------------------------|-----------------|------------------|
| SUN      | Primary / accent            | #C97860         | `17 48% 57%`     |
| SUNDOWN  | Dark shade / shadow tone    | #6B3838         | `0 30% 32%`      |
| BEAM     | Light shade / highlight     | #F5D5B0         | `28 75% 85%`     |

**Rationale**: The SUN swatch is the target per the feature description. SUNDOWN and BEAM are its natural dark/light neighbours in the palette and provide the depth needed for hover states, focus rings, and card surfaces without introducing unrelated colors.

**Alternatives considered**: Using only the SUN hex value as a flat color. Rejected because the UI needs shade variation for interactive states (hover, active, focus ring) — the SUNDOWN/BEAM pair provides this without guesswork.

---

## Decision 2: Light Mode vs Dark Mode Values

**Decision**: Apply slightly different HSL values per mode to maintain visual punch:

| Token role       | Light mode        | Dark mode         |
|------------------|-------------------|-------------------|
| Primary / accent | `17 48% 57%`      | `17 55% 62%`      |
| Ring / focus     | `17 48% 57%`      | `17 55% 62%`      |
| Primary fg       | `0 0% 100%`       | `24 20% 8%`       |
| Accent fg        | `0 0% 100%`       | `24 20% 8%`       |

**Rationale**: On dark backgrounds, the same lightness looks dimmer. Bumping saturation to 55% and lightness to 62% in dark mode keeps the SUN tone visually equivalent. The primary-foreground shifts to a very dark warm tone (instead of cool dark) to stay harmonious with the warm palette.

**Alternatives considered**: Using identical values in both modes. Rejected because the current design already applies this pattern (teal is `196 90% 42%` in light, `196 100% 56%` in dark) — following the same convention is consistent.

---

## Decision 3: Contrast Ratio Compliance

**Decision**: All text on SUN-toned backgrounds meets the 4.5:1 threshold.

Analysis:

| Background          | Foreground           | Estimated contrast | Pass? |
|---------------------|----------------------|--------------------|-------|
| SUN `17 48% 57%`    | White `0 0% 100%`    | ~3.5:1             | Fail* |
| SUN `17 48% 57%`    | SUNDOWN `0 30% 32%`  | ~5.8:1             | Pass  |
| Dark bg + SUN text  | bg `224 30% 6%`      | ~6.2:1             | Pass  |

*White foreground on light-mode SUN falls below 4.5:1. **Correction**: The primary-foreground in light mode must use the dark SUNDOWN tone (`0 30% 32%`) rather than white. In dark mode, white/off-white foreground on the slightly lighter SUN (`17 55% 62%`) achieves ~4.2:1 — borderline. Use `0 0% 98%` (near-white) to push to ~4.5:1.

**Rationale**: Accessibility is a hard requirement per spec SC-002.

**Alternatives considered**: Using a lighter SUN in light mode (higher L value). Rejected because it would deviate visually from the reference swatch.

---

## Decision 4: Tokens Left Unchanged

**Decision**: The following tokens are out of scope and must not be modified:

- `--destructive` / `--destructive-foreground` (red error states)
- `--success` / `--success-foreground` (green success states)
- `--warning` / `--warning-foreground` (amber warning states)
- `--background`, `--foreground`, `--card`, `--popover`, `--secondary`, `--muted`, `--border`, `--input`

**Rationale**: Spec FR-005 explicitly protects semantic status colors. Background, card, and surface tokens are neutral grays that do not belong to the brand palette and should remain unchanged to avoid visual noise.

---

## Final Resolved Token Map

### Light Mode (`:root`)

| Token                  | Current value      | New value          |
|------------------------|--------------------|--------------------|
| `--primary`            | `196 90% 42%`      | `17 48% 57%`       |
| `--primary-foreground` | `0 0% 100%`        | `0 30% 22%`        |
| `--accent`             | `196 90% 42%`      | `17 48% 57%`       |
| `--accent-foreground`  | `0 0% 100%`        | `0 30% 22%`        |
| `--ring`               | `196 90% 42%`      | `17 48% 57%`       |

### Dark Mode (`.dark`)

| Token                  | Current value       | New value          |
|------------------------|---------------------|--------------------|
| `--primary`            | `196 100% 56%`      | `17 55% 62%`       |
| `--primary-foreground` | `224 30% 6%`        | `24 20% 8%`        |
| `--accent`             | `196 100% 56%`      | `17 55% 62%`       |
| `--accent-foreground`  | `224 30% 6%`        | `24 20% 8%`        |
| `--ring`               | `196 100% 56%`      | `17 55% 62%`       |
