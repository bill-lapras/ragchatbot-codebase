# Frontend Changes - Dark/Light Theme Toggle

## Overview
A sun/moon toggle in the top-right of the header switches between the dark (default) and light themes. Themes are driven by CSS custom properties, which are redefined when `data-theme="light"` is set on `<html>`.

## Files

### `frontend/index.html`
- Header has the `#themeToggle` button on the right (flex `space-between`), with sun and moon SVG icons (`aria-hidden="true"`) and an `aria-label`.
- Stylesheet cache-buster bumped to `v=13`.

### `frontend/style.css`
- `:root` holds the dark palette; `[data-theme="light"]` overrides it:
  - Background `#ffffff`, surface `#f8fafc`, surface hover `#e2e8f0`
  - Text primary `#0f172a` (~17:1 on white), text secondary `#475569` (~7.6:1)
  - Border `#cbd5e1`, lighter shadow (0.08 opacity); primary blue `#2563eb` unchanged
- Toggle button: round, bordered, hover scale and focus-visible ring. The icons cross-fade with a rotate/scale animation over 0.3s.
- Global 0.3s transitions on background, text and border colors, so switching themes is smooth.
- Light-theme fixes for elements that used hard-coded dark-theme colors:
  - Answer links use the primary/hover blue
  - Code/pre backgrounds use a subtle slate tint instead of `rgba(0,0,0,0.2)`
  - Blockquotes get a light blue tint
  - Error/success text is darker (`#b91c1c` / `#15803d`) for contrast on light backgrounds
- Fixed the blockquote border, which referenced the undefined `--primary` variable (now `--primary-color`).

### `frontend/script.js`
- `initializeTheme()` applies the saved theme from `localStorage` (defaults to dark).
- `toggleTheme()` flips the theme. `setTheme()` sets or removes `data-theme` on `<html>`, updates the `aria-label` ("Switch to light/dark theme") and saves the choice.
- The toggle is a native `<button>`, so Tab, Enter and Space work. There is also a Ctrl/Cmd+Shift+T shortcut.
