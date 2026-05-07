# Color Token Contract: SUN Palette

**File**: `hackhaton/frontend/src/theme/globals.css`  
**Scope**: CSS custom properties under `:root` (light mode) and `.dark` (dark mode)  
**Change type**: Value-only replacement — token names, structure, and Tailwind config are unchanged

---

## Light Mode Token Changes (`:root`)

```css
/* BEFORE */
--primary: 196 90% 42%;
--primary-foreground: 0 0% 100%;
--accent: 196 90% 42%;
--accent-foreground: 0 0% 100%;
--ring: 196 90% 42%;

/* AFTER */
--primary: 17 48% 57%;
--primary-foreground: 0 30% 22%;
--accent: 17 48% 57%;
--accent-foreground: 0 30% 22%;
--ring: 17 48% 57%;
```

---

## Dark Mode Token Changes (`.dark`)

```css
/* BEFORE */
--primary: 196 100% 56%;
--primary-foreground: 224 30% 6%;
--accent: 196 100% 56%;
--accent-foreground: 224 30% 6%;
--ring: 196 100% 56%;

/* AFTER */
--primary: 17 55% 62%;
--primary-foreground: 24 20% 8%;
--accent: 17 55% 62%;
--accent-foreground: 24 20% 8%;
--ring: 17 55% 62%;
```

---

## Tokens Explicitly Unchanged

These tokens must not be modified. Any PR touching them for this feature is a scope violation.

```
--background       --foreground
--card             --card-foreground
--popover          --popover-foreground
--secondary        --secondary-foreground
--muted            --muted-foreground
--border           --input
--destructive      --destructive-foreground
--success          --success-foreground
--warning          --warning-foreground
--radius
```

---

## Reference Palette

| Swatch   | HSL               | Role in this implementation       |
|----------|-------------------|-----------------------------------|
| SUN      | `17 48% 57%`      | Primary / accent (light mode)     |
| SUN+     | `17 55% 62%`      | Primary / accent (dark mode)      |
| SUNDOWN  | `0 30% 22%`       | Foreground on SUN backgrounds     |
| BEAM     | `28 75% 85%`      | Available for future use as tint  |
