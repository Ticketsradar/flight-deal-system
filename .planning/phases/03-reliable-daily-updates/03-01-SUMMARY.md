---
phase: 03-reliable-daily-updates
plan: 01
subsystem: database
tags: [supabase, postgrest, python, freshness, staleness, scheduling]

requires:
  - phase: 02-flexible-trip-length
    provides: db.py with upsert/select helpers, upload.py pipeline, existing test_db.py harness

provides:
  - scanned_at field in every cheap_flights upsert row (sourced from scan generated_at)
  - _order_stale() pure helper for offline testing of stale-first ordering
  - stale_routes() read primitive returning routes ordered oldest-scanned-first
  - upload.py meta uses generated_at (datetime precision) instead of bare scan_date

affects:
  - 03-03 (stale-first scanner mode consumes stale_routes())
  - 03-04 (website per-route freshness badge reads scanned_at)

tech-stack:
  added: [datetime (stdlib)]
  patterns:
    - "Row builder reads scan_doc.get('generated_at') once at function top and stamps every row — ensures UPDATE advances scanned_at (INSERT-only default now() was the bug)"
    - "Pure aggregation helper (_order_stale) tested offline, real network call (stale_routes) delegates to it — keeps unit tests network-free"
    - "stale_routes no-op guard mirrors select()'s configured() pattern"

key-files:
  created: []
  modified:
    - db.py
    - upload.py
    - test_db.py

key-decisions:
  - "Thread generated_at from scan_doc into each row as scanned_at rather than relying on INSERT-only default — the only way to advance the timestamp on UPDATE"
  - "Factor pure ordering into _order_stale() so it can be unit-tested without any network access"
  - "stale_routes() fetches origin/destination/scanned_at columns only (bounded payload, T-03-03 mitigation)"
  - "upload.py prefers generated_at (ISO datetime) over scan_date (bare date) for more precise global freshness badge"

patterns-established:
  - "Offline tests for DB helpers: inject unordered rows, assert ordering without network"
  - "No-op guard in read helpers mirrors upsert pattern: configured() check returns [] immediately when unconfigured"

requirements-completed: [DAILY-02, DAILY-01]

duration: 15min
completed: 2026-06-14
---

# Phase 03 Plan 01: Reliable Daily Updates — scanned_at + stale_routes Summary

**Closed DAILY-02 root cause (scanned_at frozen on UPDATE) by threading scan's generated_at into every cheap_flights row; added _order_stale() + stale_routes() oldest-first scheduling primitive for DAILY-01**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-14T03:30:00Z
- **Completed:** 2026-06-14T03:44:47Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fixed DAILY-02: `cheap_flight_rows()` now computes `scanned_at = scan_doc.get("generated_at") or datetime.now().isoformat()` once and stamps every upserted row, so PostgREST merge-duplicates UPDATE truly advances the column (was frozen at first-INSERT default)
- Added `_order_stale(rows)` pure Python helper: collapses rows to one-per-(origin,destination) keeping oldest scanned_at, sorts null (never-scanned) first, then oldest-to-newest — fully testable offline
- Added `stale_routes(limit, c)`: queries cheap_flights via existing `select()`, delegates ordering to `_order_stale()`, returns [] when unconfigured (no-op safe) — this is the scheduling signal 03-03 will consume
- `upload.py` now sets `last_updated_stream_a` to `scan.get("generated_at") or scan.get("scan_date", "")` for datetime-precision meta (not bare date)
- Extended `test_db.py` with 5 new offline assertions (scanned_at positive, scanned_at fallback, _order_stale ordering, _order_stale key shape, stale_routes no-op); all 15 assertions exit 0

## Task Commits

1. **Task 1 + Task 2: Thread scanned_at + add stale_routes** - `5b86068` (feat)
   _(Both tasks committed together as they form one coherent data-layer change)_

**Plan metadata:** to be committed after SUMMARY

## Files Created/Modified
- `db.py` — `import datetime as dt`; `scanned_at` stamped on every row in `cheap_flight_rows()`; `_order_stale()` pure helper; `stale_routes()` read primitive
- `upload.py` — `set_meta("last_updated_stream_a", ...)` prefers `generated_at` over `scan_date`
- `test_db.py` — 5 new offline assertions covering scanned_at presence, fallback, stale ordering, key shape, no-op guard

## Decisions Made
- Thread `generated_at` at function top of `cheap_flight_rows()` (not per-row lookup) — one evaluation, consistent value across all rows in a single scan doc
- Keep `_order_stale` as a module-level function (not nested inside `stale_routes`) so tests can call it directly without any network dependency
- `stale_routes()` fetches only `origin,destination,scanned_at` columns (bounded payload) as T-03-03 threat mitigation

## Deviations from Plan

None - plan executed exactly as written. Tasks 1 and 2 were committed in a single atomic commit since the changes are tightly coupled (test assertions for Task 2 require `_order_stale` which is the implementation deliverable of Task 2).

## Issues Encountered
None. RED phase confirmed failures for all new assertions; GREEN phase passed all 15 assertions on first attempt.

## Known Stubs
None. This plan is pure data-layer Python — no UI rendering, no hardcoded placeholder values.

## Threat Surface Scan
No new network endpoints, auth paths, or file access patterns introduced. `stale_routes()` is read-only; `scanned_at` is sourced from existing `generated_at` field already in scan docs. T-03-01 through T-03-03 mitigations from plan threat register applied as designed.

## Self-Check

Files exist:
- db.py: YES (modified)
- upload.py: YES (modified)
- test_db.py: YES (modified)

Commits: 5b86068 — confirmed via `git rev-parse --short HEAD`

Test output:
```
✅ error_fare_row 映射欄位
✅ 冇 source_url → 跳過(回 None)
✅ cheap_flight_rows 展平+跳failed+砌tripcom: 2
✅ upsert 砌 URL/headers + 回行數
✅ delete 砌 URL
✅ delete 未配置 → False
✅ cfg URL 容錯(剝 /rest/v1): https://abc.supabase.co
✅ 未配置 → 0(no-op,唔當機)
✅ scanned_at == generated_at on every row: ['2026-06-14T09:00:00', '2026-06-14T09:00:00']
✅ scanned_at fallback(no generated_at) → non-empty ISO str: 2026-06-14T11:44:05
✅ _order_stale: null first, then oldest→newest: ['BKK', 'TPE', 'NRT']
✅ _order_stale keys: origin/destination/last present
✅ stale_routes() unconfigured → []: []
🎉 db 純邏輯測試通過
```

Grep counts: `grep -v '^#' db.py | grep -c 'scanned_at'` = 9 (≥2 required); `grep -c 'generated_at' upload.py` = 1 (≥1 required)

## Self-Check: PASSED

## Next Phase Readiness
- 03-02: Per-route freshness badge on website — can now read `scanned_at` from cheap_flights rows (it will be correctly set after next scan run)
- 03-03: Stale-first scanner mode — `db.stale_routes()` is ready to consume; `--stale-first` flag in scanner.py can call it directly
- 03-04: Workflow hygiene — no blockers from this plan

---
*Phase: 03-reliable-daily-updates*
*Completed: 2026-06-14*
