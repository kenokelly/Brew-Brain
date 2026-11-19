# Brew-Brain redesign — "Brewhouse" direction

Chosen direction for the Brew-Brain UI refresh (Nov 2026). It's friendly and vessel-led, with
bold outlined cards and pill labels. Breww's production pages were the inspiration, but nothing is copied from them.

Live design canvas (owner only): https://claude.ai/artifact/NU9a9mvbMiJu9N7GtAvr1R

## Files

| File | What it is |
|---|---|
| `Brewhouse.dc.html` | **D**: the main brew-day screen (desktop/laptop, 1280 wide) |
| `HopYard.dc.html` | D2: same layout, olive/lime palette |
| `Stout.dc.html` | D3: dark mode |
| `Tablet.dc.html` | D4: portrait tablet layout (834 wide) |

The `.dc.html` files are design sources from the Claude design canvas. They need the canvas runtime
(`support.js`), so they won't render in a plain browser. Use them as the visual and markup reference
when implementing in `web/`. All data in them (Batch 042, "Sample Best Bitter", readings) is placeholder.

## Tokens

### Light (default)

| Token | Hex | Use | Maps to `globals.css` |
|---|---|---|---|
| ink | `#0F3B36` | text, borders, hard shadows, primary button | `--foreground`, `--primary`, `--border`, `--ring` |
| ground | `#F7F3EA` | page background, inset tiles | `--background`, `--muted`, `--primary-foreground` |
| card | `#FFFDF8` | card surfaces | `--card`, `--popover` |
| copper (text) | `#B85C1E` | highlighted numbers in headlines | new `--highlight` |
| copper (fill) | `#E8963A` | active pill / active vessel ring | `--accent` (with ink text) |
| malt | `#F3D27A` | mash fill, warning band | new `--malt` / `--warn` |
| hop | `#A9D27E` | fermenter fill, "fine" band | new `--hop` / `--ok` |
| hop-soft | `#DCEBC8` | "in range" chip, done steps | new `--ok-soft` |
| water | `#9CC7E0` | HLT fill | new `--water` |
| danger band | `#EDB3AB` | out-of-tolerance band | `--destructive` (soft) |
| panel | `#0F3B36` / `#164841` / `#2E5A54` | dark live panel, vessel bg, divider | new `--panel*` |
| panel muted text | `#BFD3CE` | secondary text on dark panel | — |

### Dark ("Stout")

ink `#F3E9DA` · ground `#16120F` · card `#211B16` · highlight `#E8963A` · ok-soft `#2F4A22` ·
panel inverts to cream (`#F3E9DA`, vessel bg `#E6D9C4`, divider `#CDBFA9`, muted `#5C4E42`).
Text on copper/accent fills stays dark (`#16120F`).

### Hop yard (alt palette)

ink `#26361C` · ground `#F3F1E4` · card `#FDFCF5` · highlight `#A33A2A` · accent `#C9DB6A`.

## Typography

- **Bricolage Grotesque** (Google Fonts, variable 400–800): all UI text and headlines.
  Headlines are 800 weight with tight tracking (`-0.035em`) and line-height ~0.95.
- **DM Mono** (400/500): every number, reading, time and batch ID, plus small uppercase eyebrows.
- The hero headline reads as a sentence: "Holding at **66.4°C** for another 38 min."

## Components

- **Card:** `2px solid ink`, radius 22px, hard shadow `5px 5px 0 ink` (no blur). The dark live panel uses a copper shadow.
- **Pill:** radius 999px, 2px ink border. Variants are accent (current step), ok-soft (in range / done), and dashed (upcoming).
- **Buttons:** pills, min height 52px (wet-hands touch target). Primary is ink-filled, secondary is card-filled with an ink border.
- **Tolerance band:** a rounded bar split danger · warn · fine (×2) · warn · danger, with a 4px ink marker at the live value and mono scale labels underneath.
- **Vessel:** 64×104, radius `16px 16px 30px 30px` (conical bottom), fill level as a %-height block. Temperature above, name and status below. The active vessel gets an accent border and a 4px glow ring.
- **Stat tile:** ground-coloured inset, radius 14px, label 13px/600, value in DM Mono 26px.
- **Step strip:** a row of pills across the bottom, ticked off as the brew progresses.

## Layout

- Desktop: header (wordmark, pill nav, batch pill), then a two-up row with the hero mash card (`flex: 999 1 560px`) and the brewhouse live panel (`flex: 1 1 380px`), then the step strip. Everything wraps, so it stacks on tablets and phones.
- Tablet portrait: the same components stacked. See `Tablet.dc.html`.
