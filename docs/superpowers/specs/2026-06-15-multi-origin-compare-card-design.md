# Spec — Multi-origin merged compare card

**Date:** 2026-06-15
**Status:** Design approved (user picked option B), ready to implement
**Scope:** `web/` only.

## Context
When the user selects 2+ departure cities (e.g. 香港 + 深圳), they want the same destination's prices from each origin together so they can compare at a glance. Current behaviour: each (origin, destination) is a separate card, sorted by price, so 東京-from-HKG and 東京-from-SZX are scattered.

Also fixed this round (operational, not a feature): the local dev server had been killed on session resume — restarted; localhost:3000 is back.

## Decision (locked with user — option B)
When **2 or more origins are selected**, switch the 平機票 list to **one merged card per destination**. Each merged card lists every selected origin's price for that destination on its own line, cheapest flagged 「最平」. Expanding shows each origin's cheap-day grid in a labelled section. When **0 or 1 origin** is selected, keep the current per-origin cards (price-sorted masonry) unchanged.

Rationale: merged card gives the cleanest price comparison, is gap-free (one `<details>` per destination → existing masonry, no row-coupling gap), and is robust to uneven origin coverage (a destination missing one origin simply shows fewer lines). Chosen over "two cards side by side" (option A), which would re-introduce the expand-gap and mis-pair when origin coverage is uneven.

## Trigger
`origins.length >= 2` → compare/merged mode. Otherwise (0 or 1) → current mode. (Default view = no selection = current price-sorted masonry, unchanged.)

## Data model (pure, in `web/lib/filtering.ts`)
- `OriginEntry = { origin: string; flights: CheapFlight[]; min: number }`
- `DestCompareGroup = { destination: string; continent: Continent; origins: OriginEntry[]; min: number }`
- `groupByDestination(groups: DealGroup[]): DestCompareGroup[]`
  - Collapse origin×destination `DealGroup[]` by `destination`.
  - `origins` sorted by `min` ascending (cheapest origin first).
  - `continent` from the destination (all entries share it).
  - group `min` = min across its origins; result sorted by `min` ascending.
  - Pure, unit-tested.

## Components
- **Extract `web/components/MonthGrid.tsx`** — the "每月只列平價日 …" header + per-month tiered date-button rows, currently inside `DestinationCard`. Props: `flights: CheapFlight[]`, `selectedDays: number[]`, `currency: string`. Behaviour-preserving extraction (tier colours, null-price guard, day-filter all unchanged).
- **`web/components/DestinationCard.tsx`** (single-origin) — refactor to render `<MonthGrid>` in its body; summary/header unchanged. Must look identical to today.
- **`web/components/CompareCard.tsx`** (new, multi-origin) — `<details class="glass-card …">` root so masonry + expand work.
  - Summary (collapsed): flag + 國家 · 城市 · CODE (no single origin); then one row per origin `「{城市}出發   HKD {min}」`, cheapest row flagged 「最平」 + emphasised; freshest scanned_at label.
  - Body (expanded): for each origin (cheapest first) a labelled section header `「{出發地名}出發」` followed by `<MonthGrid flights={originEntry.flights} selectedDays currency>`.
- **`web/components/DealsExplorer.tsx`** — when `origins.length >= 2`: `groupByDestination(shown)` → `splitColumns(destGroups, colCount)` → render `CompareCard` per group. Else: current `DestinationCard` path. Masonry/`splitColumns`/responsive columns unchanged.

## Filter interaction (unchanged semantics)
`applyFilters` still runs first on origin×destination groups (origin/continent/days/maxPrice). In compare mode, the surviving groups are then regrouped by destination. A destination appears if ≥1 of its origin groups survives; each surviving origin becomes a line. `selectedDays` continues to filter day-buttons inside each origin's `MonthGrid`.

## Testing
- Unit (`filtering.test.ts`): `groupByDestination` — collapses by destination, origins sorted cheapest-first, dest groups sorted by min, carries continent. (`npm test`.)
- Build: `next build` passes.
- Visual (Playwright): select 香港+深圳 → 東京 (and others) render as ONE card with two price lines, cheapest flagged; expand → two labelled 出發地 sections each with its date grid; no gap on expand; select a single origin → reverts to per-origin cards identical to before; the single-origin `DestinationCard` is visually unchanged after the MonthGrid extraction.
- Adversarial review (ultracode): after implementation, run a code-review workflow over the changed web files (correctness, regressions in DestinationCard, edge cases: destination with only 1 origin in compare mode, empty origins, null prices).

## Out of scope
- Backend / data (#1 refill), error-fare section, continents/days/origin filter logic (done).

## Verification (goal-backward)
- Selecting 2+ origins shows one card per destination with each origin's price together, cheapest flagged → easy comparison.
- Expanding a merged card shows each origin's cheap days, labelled; no layout gap.
- Selecting 0/1 origin is unchanged from current behaviour; single-origin card visually identical post-refactor.
