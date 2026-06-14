# Spec — 網站篩選增強 + 數據新鮮度(5 items)

**Date:** 2026-06-15
**Status:** Design approved, ready for implementation plan
**Scope:** Website (`web/`) filter UX + layout, plus a backend refill pass for blocked routes.

---

## Problem / Context

User reviewed the live local site and raised 5 items (2 bugs + 3 features). Investigation findings:

- **#1 Missing data** — Verified against real Supabase: popular routes (東京 NRT = 0 grid periods, scanned 2 days ago; 新加坡 SIN = 4) are exactly the ones Google blocks hardest, so the scraper (even with browser fallback) gets little/nothing. Less-popular routes scrape fully (福岡 83, 上海 63, 名古屋 55). "20 shards green" ≠ every route has data — a shard exits green even when its popular routes are fully blocked. `db.cheap_flight_rows` skips all-failed months (to avoid overwriting good data with nothing), so blocked routes keep OLD sparse data → look stale. **Not a website bug — a scraping limitation.**
- **#2–#5** — All frontend, doable in `web/`.

## Decisions (locked with user)

| # | Decision |
|---|----------|
| #1 | **Backend gentle refill pass** for sparse/stale hot routes (re-scan them less aggressively) **+ hide outdated data** on the site so stale prices never show. **Travelpayouts rejected** — spike (2026-06-14, `.planning/research/TRAVELPAYOUTS-SPIKE.md`) proved its round-trip cache is too sparse, incl. HKG–NRT returning 0. SearchApi.io `google_flights_calendar` (paid, live Google grid) noted as the real future fix if budget is approved — out of scope here. |
| #2 | Filters become **client-side, multi-select**. 出發地 (origin) + 洲份 (continent) both multi-select. Multi within one filter = **OR**; across filters = **AND**. |
| #3 | Region → **4 continents**: 亞洲 / 歐洲 / 北美洲 / 大洋洲. Edge cases: 伊斯坦堡(土耳其)→ 歐洲; 杜拜(阿聯酋)、馬累(馬爾代夫)→ 亞洲. |
| #4 | Two-column wall: CSS grid → **CSS columns (masonry)** so expanding one card no longer leaves a blank gap in the other column. Tradeoff: card order flows column-by-column (cheapest down col 1, then col 2). |
| #5 | New **行程日數 (trip-length) filter**, multi-select. When days selected: (a) **hide** destinations with no matching-day deal; (b) within remaining cards, show **only** the day-buttons whose trip length matches. |

## Batches (ship independently)

- **Batch A — Frontend** (#2, #3, #4, #5, + hide-outdated): all in `web/`. Verify on local dev server, then deploy.
- **Batch B — Backend** (#1 refill pass): `scanner.py` / `db.py` / new workflow.

---

## Batch A — Frontend design

### Data loading (`web/app/page.tsx`)
- Load **all 3 origins** (HKG/SZX/CAN) in one pass (currently loads only the selected origin). `getCheapFlights` already has `.limit(2000)`; 3 origins × 57 dest × 7 months ≈ ~1,200 rows < 2,000. ✓
- Keep the existing 7-month window filter.
- **Hide outdated**: drop any (origin,destination) group whose freshest `scanned_at` is older than `STALE_DAYS` (default **3**, a tunable constant). This removes stale NRT-style cards until the refill pass repopulates them. Reversible (data not deleted; just not rendered).
- Build groups keyed by **(origin, destination)** (not destination alone), since multi-origin shows e.g. 東京 from HKG and from SZX as separate cards. Each group carries its continent (computed via `continentOf`).
- Pass all groups + metadata to a new client component.

### `web/lib/airports.ts`
- Add `continent` to each airport (`亞洲|歐洲|北美洲|大洋洲`) and export `CONTINENTS` (ordered list) + `continentOf(code): string`.
- Continent is derived **client-side from the airport code**, replacing reliance on the data's `region` field for the filter.

### New `web/components/DealsExplorer.tsx` (`"use client"`)
- Receives all groups (serializable plain data).
- Holds filter state: `origins: string[]`, `continents: string[]`, `days: number[]`, `maxPrice?: number`.
- Renders the **filter bar** + the **masonry card wall**, filtering client-side & instantly (no reload):
  - origins: group.origin ∈ selected (empty = all)
  - continents: continentOf(group.destination) ∈ selected (empty = all)
  - maxPrice: group.min ≤ maxPrice
  - days: group has ≥1 period whose `days` ∈ selected (empty = all)
- Sort groups by min price ascending (unchanged).

### Filter bar (replaces `web/components/Filters.tsx`)
- Origin: 3 toggle chips (香港/深圳/廣州), multi.
- Continent: 4 toggle chips (亞洲/歐洲/北美洲/大洋洲), multi.
- 行程日數: toggle chips for the distinct `days` values present in the loaded data (e.g. 3/4/5/6/7…), multi.
- 預算上限: number input (unchanged behavior, now applied client-side).
- 重設 button clears all.
- Pure client state; no `method=get` form, no page reload.

### `web/components/DestinationCard.tsx`
- Accept optional `selectedDays: number[]` prop.
- When non-empty, filter the per-month period-buttons to those whose trip length (`days`, or computed from depart/return) ∈ selectedDays. (Destination-level hiding is done by DealsExplorer not rendering the card.)
- Existing tier-colour / null-price guards (WR-05) unchanged.

### Layout (#4 masonry)
- Replace `grid gap-3 sm:grid-cols-2 items-start` with CSS multi-column: `columns-1 sm:columns-2` (gap via `gap`/`column-gap`), each card `break-inside-avoid` + bottom margin.
- Applies to the 平機票 wall. (錯價雷達 grid can stay as-is — few cards, no expand.)

### Out of scope (Batch A)
- No change to error-fare section.
- No hard-delete of DB rows (hide-only).

---

## Batch B — Backend design (#1 refill pass)

### `db.py`
- Add `sparse_routes(min_periods, stale_days, limit, c)` → returns `"ORIGIN-DEST"` keys for routes whose **total periods are below `min_periods`** OR whose `scanned_at` is older than `stale_days`. Reuses the `select()` + no-op-when-unconfigured pattern. Read-only.

### `scanner.py`
- Add `--refill` mode: queries `db.sparse_routes(...)`, scans **only** those routes, with **gentle settings** — `workers=1`, longer per-query delays, more browser retries / longer browser timeout. Rationale (from the data): the main scan fails on hot routes *because* it is aggressive (workers=2 + tight delays → blocked); a slower pass scanning fewer routes has a better chance.
- Refill reuses the existing `--grid --grid-step --offset --refine-days` pipeline + atomic per-route save + `upload.py` merge.

### New `.github/workflows/scan-refill.yml`
- Runs `scanner.py --refill ...` (gentle) + `upload.py` (`if: always()`), on a schedule a few hours offset from the main daily scan, plus `workflow_dispatch`. Same `concurrency: scan-daily` group? → NO: use a **separate concurrency group** (`scan-refill`) so it can run without blocking/being-blocked by the main scan. Browser fallback ON (`playwright install`).

### Honest caveat (record in SUMMARY)
- Google blocking persists; the refill pass will help some routes but does NOT guarantee 東京 fills. The reliable fix remains a paid live-grid API (SearchApi.io) — deferred.

---

## Testing

- **Batch A**: `next build` passes; local dev server visual check (the established Playwright screenshot flow) — verify multi-select origin+continent, days filter (cards + day-buttons), masonry has no blank gaps on expand, stale routes hidden. Add a small unit test for `continentOf` mapping (all 57 destinations map to exactly one continent).
- **Batch B**: offline unit tests for `sparse_routes` ordering/threshold (inject rows, assert selection) following `test_db.py` style; `--refill` route-selection smoke (monkeypatched query). Manual GitHub dispatch of `scan-refill.yml` to measure how many sparse routes it actually fills.

## Verification (goal-backward)

- #1: hot routes no longer show stale prices (hidden until fresh); refill workflow runs and repopulates ≥ some sparse routes.
- #2: both origin + continent filter multi-select, instant, OR-within / AND-across.
- #3: continent filter shows exactly 亞洲/歐洲/北美洲/大洋洲; every destination categorised.
- #4: expanding a card leaves no blank gap beside it.
- #5: selecting days hides non-matching destinations and trims day-buttons to matching lengths.
