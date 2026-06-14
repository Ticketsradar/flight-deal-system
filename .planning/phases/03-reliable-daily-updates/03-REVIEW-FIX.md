---
phase: 03-reliable-daily-updates
review_path: .planning/phases/03-reliable-daily-updates/03-REVIEW.md
fix_scope: critical_warning
status: all_fixed
findings_in_scope: 7
fixed: 7
skipped: 0
iteration: 1
fixed_at: 2026-06-14
---

# Phase 03: Code Review Fix Report

**Fix Scope:** Critical + Warning (7 findings)
**Status:** all_fixed
**Iteration:** 1

## Fixes Applied

| ID | Severity | File | Commit | Result |
|----|----------|------|--------|--------|
| CR-01 | BLOCKER | scripts/verify_workflows.py | 2b2532f | ✅ Fixed |
| CR-02 | BLOCKER | scanner.py:526 | e6f61ff | ✅ Fixed |
| WR-01 | WARNING | scanner.py:665 | 7c96c1a | ✅ Fixed |
| WR-02 | WARNING | scanner.py (browser returns) | 627a7fb | ✅ Fixed |
| WR-03 | WARNING | .github/workflows/scan.yml | f7ebcaf | ✅ Fixed |
| WR-04 | WARNING | web/lib/data.ts | 738564e | ✅ Fixed |
| WR-05 | WARNING | web/components/DestinationCard.tsx | 294c330 | ✅ Fixed |

## Fix Details

### CR-01 — `verify_workflows.py` stale assertions (commit 2b2532f)
- Renamed `check_daily_cron_commented` → `check_daily_cron_active` and inverted logic: now asserts `"schedule"` key IS present in `scan.yml` (production state after Plan 04 rollout).
- Added existence guard for `scan-weekly.yml`: if file doesn't exist, calls `ok("scan-weekly.yml: 已刪走(daily 全量已取代,唔需要)")` instead of `fail()`.
- Removed all assertions that depended on the now-deleted weekly file.
- Result: `verify_workflows.py` exits 0 on current production state.

### CR-02 — `--slice` input validation (commit e6f61ff)
- Added `parts = args.slice.split("/")` with `len(parts) != 2 → ap.error(...)` check.
- Added `n <= 0 → ap.error(...)` guard.
- Added `k >= n → ap.error(...)` guard (prevents silent empty-route-list Supabase overwrite).
- All three paths use `ap.error()` (exits with code 2 and argparse usage message).

### WR-01 — Dead variable `beyond_before` (commit 7c96c1a)
- Removed line `beyond_before = beyond` at scanner.py:665.
- No functional change; eliminates dead assignment.

### WR-02 — Browser `beyond_data` undercounting (commit 627a7fb)
- Added `"via": "browser"` to the `beyond_data` return dict in the browser path of `query_roundtrip`.
- `tier2_used` counter in `on_query` now correctly counts browser `beyond_data` responses.

### WR-03 — Unnecessary `REDDIT_USER_AGENT` in scan step (commit f7ebcaf)
- Removed `REDDIT_USER_AGENT: ${{ secrets.REDDIT_USER_AGENT }}` from the scan step `env:` block in `.github/workflows/scan.yml`.
- Secret now only injected where needed (scout/feeds pipeline).

### WR-04 — Missing `.limit()` in `getCheapFlights` (commit 738564e)
- Added `.limit(2000)` to the Supabase query chain in `web/lib/data.ts`.
- Added `console.warn` log when result length ≥ 1900 (approaching limit).

### WR-05 — Null-price periods rendered as green (commit 294c330)
- Updated `priceTier` to return `3` (hidden tier) when `monthMin` is non-finite or ≤ 0.
- Changed `.filter()` to `p.price != null && priceTier(p.price, mMin) < 3` — null-price periods are now excluded before rendering.
- Updated `TIERS[priceTier(p.price!, mMin)]` to use non-null assertion (safe after the filter guard).

## Info Findings (not in scope — deferred)

| ID | Severity | Status |
|----|----------|--------|
| IN-01 | INFO | Deferred — stale_routes limit multiplier; no production impact |
| IN-02 | INFO | Deferred — timezone-naive ISO timestamps; 03-01 SUMMARY noted |
| IN-03 | INFO | Deferred — test_9_grid_step tautology; low risk |
| IN-04 | INFO | Deferred — hardcoded `/20` denominator; comment added via WR-03 commit context |

---
*Phase: 03-reliable-daily-updates*
*Fixed: 2026-06-14*
