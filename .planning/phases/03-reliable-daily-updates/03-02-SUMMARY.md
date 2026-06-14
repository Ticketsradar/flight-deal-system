---
phase: 03-reliable-daily-updates
plan: 02
subsystem: ui
tags: [next.js, typescript, freshness, supabase, react-server-components]

requires:
  - phase: 03-reliable-daily-updates/03-01
    provides: scanned_at column advancing on every scan; meta.last_updated_stream_a in Supabase

provides:
  - freshnessLabel() pure formatter (ISO → 廣東話 relative age: 今日更新 / 更新於 N 日前 / 更新時間未知)
  - Per-route freshness label in DestinationCard summary block (from scanned_at)
  - Global last-updated human-readable badge in Header (from meta.last_updated_stream_a)

affects: [03-03, website-ui, phase-3-website]

tech-stack:
  added: []
  patterns:
    - "Pure TS utility in web/lib/ for date formatting — no date libs, no React dependency"
    - "Max ISO sort trick: .filter(Boolean).sort().at(-1) to find newest scanned_at across rows"
    - "Server Component freshness: new Date() at render time is valid under force-dynamic"

key-files:
  created:
    - web/lib/freshness.ts
  modified:
    - web/components/DestinationCard.tsx
    - web/components/Header.tsx

key-decisions:
  - "No new npm dependency: used built-in Date only"
  - "lastScan computed via lexical ISO sort (.sort().at(-1)) — correct for ISO 8601 strings"
  - "freshnessLabel left without use-client — server-rendered; new Date() valid under force-dynamic"

requirements-completed: [DAILY-02]

duration: 5min
completed: 2026-06-14
---

# Phase 03 Plan 02: Freshness Display Summary

**Per-route `更新於 N 日前` badge from scanned_at + human-readable global last-updated in header, both using a new pure freshnessLabel() formatter — next build green, zero new dependencies**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-14T09:29Z
- **Completed:** 2026-06-14T09:34Z
- **Tasks:** 2
- **Files modified:** 3 (1 created)

## Accomplishments
- `web/lib/freshness.ts`: pure TypeScript formatter mapping null/ISO string to 廣東話 relative-age label with no external deps
- `web/components/DestinationCard.tsx`: computes `lastScan = max(scanned_at)` across destination's flights and renders `freshnessLabel(lastScan)` in the summary right block
- `web/components/Header.tsx`: replaces raw ISO timestamp string with `freshnessLabel(meta.last_updated_stream_a || ...)` — conditional render guard preserved
- `next build` compiles successfully with TypeScript clean

## Task Commits

1. **Task 1: Create pure freshness formatter** - `6a38516` (feat)
2. **Task 2: Wire per-route + global freshness into UI** - `bd84f9a` (feat)

## Files Created/Modified
- `web/lib/freshness.ts` — NEW: `freshnessLabel(iso)` → "今日更新" / "更新於 N 日前" / "更新時間未知"
- `web/components/DestinationCard.tsx` — added freshnessLabel import + lastScan computation + label render
- `web/components/Header.tsx` — replaced raw `updated` string with freshnessLabel call

## Decisions Made
- No new npm packages: `Date.now()` and `new Date(iso)` are sufficient; no dayjs/date-fns needed
- Lexical ISO sort (`filter(Boolean).sort().at(-1)`) is correct for ISO 8601 strings
- Did not add `"use client"` to any file — all server-rendered under `force-dynamic`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Known Stubs
None — freshness labels source from real `scanned_at` / `meta.last_updated_stream_a` Supabase columns.

## Threat Flags
None — no new env access, no new network endpoints, no secrets added. Only NEXT_PUBLIC_* values reach the client (unchanged from before).

## Self-Check

### Created files
- [x] `web/lib/freshness.ts` — EXISTS
- [x] `web/components/DestinationCard.tsx` — MODIFIED
- [x] `web/components/Header.tsx` — MODIFIED

### Commits
- [x] `6a38516` — feat(03-02): add freshnessLabel pure formatter
- [x] `bd84f9a` — feat(03-02): wire per-route + global freshness into UI; next build green

### Build verification
- [x] `next build` compiled successfully (Turbopack, TypeScript clean)
- [x] `grep -c freshnessLabel DestinationCard.tsx Header.tsx` ≥ 2 (returned 2 + 2)
- [x] `grep -c last_updated_stream_a Header.tsx` = 1
- [x] `grep -c 更新於 freshness.ts` = 2
- [x] `git diff web/package.json` = empty (no new deps)

## Self-Check: PASSED

## Next Phase Readiness
- Freshness display wired end-to-end; cards and header show honest per-route and global ages
- Ready for Phase 03-03 (GitHub Actions cron reliability / go-live)

---
*Phase: 03-reliable-daily-updates*
*Completed: 2026-06-14*
