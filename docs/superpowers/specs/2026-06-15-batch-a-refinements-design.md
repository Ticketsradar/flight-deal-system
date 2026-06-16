# Spec — Batch A Refinements (filter UI, continents, expand layout)

**Date:** 2026-06-15
**Status:** Design approved, ready for plan
**Scope:** Revisions to Batch A (`web/`) after user reviewed it on localhost. All frontend, small.

## Context
User tested Batch A and gave 3 pieces of feedback:
1. Filter chips look ugly (perfect circles from `rounded-full`), and there's no clear "selected" indication — user couldn't tell multi-select worked (it does functionally; the active emerald was too subtle).
2. Continent buckets should be **亞洲 / 歐洲 / 美洲 / 大洋洲** (was 亞洲/歐洲/北美洲/大洋洲). (User said "africa" but there are no African destinations; there ARE Australia/NZ = 大洋洲. Resolved with user → use 美洲 + 大洋洲.)
3. Prefer the old 2-col grid order (row-major), but fix the expand-gap. Resolution (user-chosen): keep grid, and an **opened card spans full width** (pure CSS `:has`), so the neighbour stays unchanged and drops to the next row — zero gap. (Reverts the CSS-columns masonry from Batch A.)

## Decisions (locked with user)
- **① Chips**: pill shape (`rounded-lg`, not circle); selected = solid emerald fill + white text + leading ✓; unselected = subtle outline; each filter row shows a "已揀 N" count. Multi-select unchanged (already works).
- **② Continents**: `CONTINENTS = ["亞洲","歐洲","美洲","大洋洲"]`. `continentOf`: 美加 → 美洲; 澳紐 → 大洋洲; 歐洲 16 城 (incl. 伊斯坦堡) → 歐洲; everything else (日韓台中 + 東南亞 + 杜拜/馬累) → 亞洲.
- **③ Expand layout**: revert masonry → `grid sm:grid-cols-2 items-start`; add CSS so a grid cell containing `details[open]` spans both columns (`grid-column: 1 / -1`) at ≥sm. Pure CSS, no JS.

## File changes
- `web/components/FilterBar.tsx` — restyle Chip (pill + selected fill + ✓); add per-row "已揀 N" count.
- `web/lib/continents.ts` — `CONTINENTS` and `continentOf` use 美洲/大洋洲.
- `web/lib/continents.test.ts` — update expectations (北美洲→美洲; CONTINENTS array).
- `web/components/DealsExplorer.tsx` — grid wrapper (revert columns); add `deals-grid` class + per-card cell.
- `web/app/globals.css` — `.deals-grid > *:has(details[open]) { grid-column: 1 / -1 }` inside `@media (min-width:640px)`.

## Testing
- Unit: `continents.test.ts` updated + green (`npm test`).
- Build: `next build` passes.
- Visual (Playwright screenshots on local dev): chips are pills with obvious selected state + ✓ + count; multi-select two continents shows union; continent labels are 亞洲/歐洲/美洲/大洋洲; collapsed cards tile 2-per-row (row-major); opening a card makes it full-width with no gap beside it.

## Out of scope
- Batch B backend refill (#1 data) — separate.
- Error-fare section, data loading — unchanged.

## Verification (goal-backward)
- ① chips obviously selectable + multi (✓ + fill + count).
- ② exactly 亞洲/歐洲/美洲/大洋洲, all destinations correctly categorised.
- ③ row-major grid; opened card full-width; no gap beside unopened neighbour.
