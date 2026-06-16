# Spec — Masonry layout + circle chips (Batch A round 2 refinements)

**Date:** 2026-06-15
**Status:** Design approved, ready to implement
**Scope:** `web/` only — `DealsExplorer.tsx`, `FilterBar.tsx`, `filtering.ts` (+test), `globals.css`.

## Context
After the previous refinement, two issues remain (user-verified on localhost):
1. **Gap still appears.** The "opened card spans full width" approach was confirmed (by screenshot) to fail for **right-column** cards: opening a col2 card drops it to a full-width row below, leaving an empty gap in its old top-right slot. Full-width cannot solve the right-column case.
2. **Chips:** user now wants **circular** chips that **light up green** when selected (a green glow), **not** a ✓ tick, and **no "已揀 N" count**.

## Root cause (item 1)
A row-aligned CSS grid couples the two cells' heights → expanding one leaves a gap beside the shorter one. Full-width-on-open only fixes left-column opens. The only layout that gives "open a card → it grows in place, the other column stays exactly the same, zero gap" is **masonry** (two independent columns).

## Decisions (locked with user)
- **① Masonry**: two independent columns, cards distributed **round-robin** in price order (item i → column `i % colCount`), so the cheapest two sit side-by-side at the top and reading order stays left-right (0,1 / 2,3 / …). Each column is a vertical flex stack → opening a card grows only its column; the other column is untouched; zero gap. `colCount` = 1 on mobile (<640px), 2 on ≥640px. Mobile single-column keeps strict price order.
- **② Chips**: `rounded-full` circular pills; selected = emerald fill + **green glow** (`box-shadow`) + emerald ring; unselected = subtle outline. **No ✓ tick. No "已揀 N" count** (RowLabel shows just the label text).

## File changes
- `web/lib/filtering.ts` — add `splitColumns<T>(items: T[], n: number): T[][]` (round-robin). Pure, testable.
- `web/lib/filtering.test.ts` — test `splitColumns` (order within columns, round-robin distribution, n=1 passthrough).
- `web/components/DealsExplorer.tsx` — responsive `colCount` via `matchMedia` (default 1, →2 at ≥640px); `splitColumns(shown, colCount)`; render `flex gap-3 items-start` with N `flex-1 min-w-0 flex flex-col gap-3` columns; cards rendered directly (expand-in-place is natural flex flow).
- `web/components/FilterBar.tsx` — Chip: `rounded-full`, selected = emerald fill + green glow + ring, no ✓; RowLabel drops the count badge.
- `web/app/globals.css` — remove the now-unused `.deals-grid > details[open]` rule.

## Testing
- Unit: `splitColumns` test green (`npm test`).
- Build: `next build` passes.
- Visual (Playwright): chips are circles that glow green when selected (no tick, no count); **open a RIGHT-column card → it grows in place, left column unchanged, NO gap** (the key proof); open a left card → same; mobile = single column in price order.

## Out of scope
- Continents/days/origin filter logic (done), Batch B backend, error-fare section, data loading.

## Verification (goal-backward)
- ① Opening any card (left or right) grows it in place with zero gap beside the untouched neighbour; cheapest two side-by-side; mobile single-column.
- ② Circular chips, green-glow selected state, no tick, no count.
