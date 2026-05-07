# Quickstart: Verify SUN Palette Change

## What was changed

`hackhaton/frontend/src/theme/globals.css` — five CSS custom property values in `:root` and five in `.dark`.

## Run the frontend locally

```bash
cd hackhaton/frontend
npm install        # if first time
npm run dev        # starts Vite dev server, default http://localhost:5173
```

## Visual verification checklist

Open the app in a browser and check:

1. **Primary buttons** — should appear warm terracotta (no blue/teal visible)
2. **Active/selected states** — should use the same terracotta tone
3. **Focus rings** — tab through interactive elements; focus outline should be terracotta
4. **Gradient text** (`.gradient-text` class) — if present, should use warm tones
5. **Dark mode** (default) — open DevTools → Elements → confirm `.dark` class is on `<html>`; palette should be the slightly lighter/more vibrant dark-mode SUN value
6. **Light mode** — remove `.dark` class from `<html>` in DevTools and confirm light-mode palette is the correct SUN shade
7. **Semantic colors** — trigger any error or success states; they should remain red/green, unaffected

## Contrast quick-check

Using browser DevTools color picker on a primary button:
- Button background: should be approximately `hsl(17, 48%, 57%)` ≈ `#C97860`
- Button text: should be dark (`hsl(0, 30%, 22%)`) — **not white** in light mode
- In dark mode: button text uses `hsl(24, 20%, 8%)` against `hsl(17, 55%, 62%)` background

## Reference hex values

| Token role         | Light mode hex  | Dark mode hex   |
|--------------------|-----------------|-----------------|
| Primary / accent   | ~#C97860        | ~#D08B70        |
| Primary foreground | ~#5C2F2F        | ~#1A100D        |
