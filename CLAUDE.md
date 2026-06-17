# CLAUDE.md

This file guides AI assistants (Claude Code and others) working in this repository.

## Project Overview

This repository hosts a **single-page marketing/landing site** for an embedded
engineering consulting service. The content is in **Korean (`lang="ko"`)** and
promotes expertise in automotive-grade **CAN / CAN FD communication and ECU
engineering**, repositioned for growth industries (robotics, battery/BMS,
EV charging, agricultural & construction machinery, drones/UAM, and special
vehicles).

The site's purpose is lead generation: every primary call-to-action links to an
external Google Form ("기술 문의하기" / "Contact for technical inquiry").

## Repository Structure

The entire project is **one self-contained file**:

```
.
├── index.html      # The complete landing page (HTML + inline CSS + inline SVG)
└── CLAUDE.md       # This file
```

There is **no build system, no package manager, no dependencies, and no
framework**. Earlier revisions briefly contained a `package.json` and a `src/`
directory, but these were removed — do not reintroduce a build pipeline unless
explicitly asked. Treat the project as a static, hand-edited single file.

## How It's Structured (inside `index.html`)

Everything lives in one file:

- **`<head>`** — meta tags (charset, viewport, SEO `description`, Open Graph
  tags, `theme-color`) and the page `<title>`. All copy here is Korean.
- **`<style>`** — all CSS is inline in a single `<style>` block. It uses:
  - CSS custom properties (`:root` variables) for the color palette
    (`--blue:#1d4ed8`, `--accent:#0891b2`, etc.), surfaces, and shadow.
  - A mobile-first responsive design with breakpoints at `1024px`, `900px`,
    `720px`, and `380px`.
  - Utility-style class names (`.container`, `.section`, `.grid-3`, `.grid-2`,
    `.btn`, `.btn-primary`, `.tool-chip`, `.cap-card`, etc.).
- **`<body>`** — a single `<section>` containing anchor-linked subsections:
  - `#home-section` — hero with nav and an inline **SVG diagram** (a central
    "CAN" hub radiating to six industry nodes).
  - `#capability-section` — 제공 역량 (capabilities), 2-column card grid + tool chips.
  - `#industry-section` — 적용 산업 (target industries), 6-card grid.
  - Pain-points subsection — 이런 경우에 도움이 됩니다.
  - `#process-section` — 진행 방식 (5-step process).
  - `#scope-section` — 의뢰 범위 (scope: included / excluded / engagement types)
    and the final CTA box.

The hero illustration is an **inline `<svg>`** (no external image assets),
using gradients/`<defs>` and `<text>` nodes for the industry labels.

## Development Workflow

### Viewing / testing changes

Because it's a static file, just open it in a browser:

```bash
# Open directly
xdg-open index.html        # Linux
open index.html            # macOS

# Or serve locally (useful for consistent behavior)
python3 -m http.server 8000
# then visit http://localhost:8000
```

There are **no tests, linters, or CI build steps** configured. Validate changes
by eye in a browser at multiple widths (mobile + desktop), since responsiveness
is a core concern.

### Git workflow

- Active development branch for this work: **`claude/claude-md-docs-a2szry`**.
- Default branch: `main`.
- Commit history shows frequent commits with terse messages (often just
  `index.html`). Prefer **clear, descriptive commit messages** describing the
  actual change (e.g. "hero: tighten mobile spacing", "industry: add UAM copy").
- Do not open a pull request unless explicitly requested.

## Conventions & Guidelines

When editing, match the existing style:

1. **Keep it a single file.** Add styles to the existing `<style>` block and
   markup to the existing structure. Don't split into separate CSS/JS files or
   add a bundler without being asked.
2. **No external dependencies.** No CDN scripts, web fonts beyond the system
   font stack already defined, or third-party libraries. Imagery is inline SVG.
3. **Korean-first copy.** User-facing text is Korean. Section labels use small
   uppercase English eyebrows (e.g. `CAPABILITY`, `TARGET INDUSTRIES`) followed
   by Korean headings. Preserve this bilingual pattern and `word-break:keep-all`
   on Korean text blocks (it prevents awkward mid-word line breaks).
4. **Reuse design tokens.** Use the existing `:root` CSS variables for colors
   and the established class names rather than hard-coding new values or
   one-off inline styles where a class exists.
5. **Responsive integrity.** Any layout change must hold up across the existing
   breakpoints (`1024 / 900 / 720 / 380`). Grids collapse from multi-column to
   single-column on small screens.
6. **Accessibility.** The hero SVG uses `role="img"` and `aria-label`; keep
   alt/aria text meaningful (and in Korean) when editing imagery. External
   links use `target="_blank" rel="noopener noreferrer"`.
7. **The contact CTA** points to a specific Google Forms URL repeated in
   several places (nav button, hero actions, final CTA). If the form URL
   changes, update **all** occurrences consistently.

## Notes for AI Assistants

- This is a content/marketing artifact more than a software project — most
  requests will be copy edits, layout tweaks, color/spacing adjustments, or
  SVG/diagram changes. Apply changes directly in `index.html`.
- Before large structural changes, confirm the intent, since the single-file
  layout makes broad edits easy to get subtly wrong across breakpoints.
- Preserve SEO/Open Graph meta tags when editing the `<head>`.
