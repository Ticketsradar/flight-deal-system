---
phase: 03-reliable-daily-updates
plan: "03"
subsystem: scanner + ci-workflows
tags: [incremental-scan, stale-first, budget, ci, daily, weekly]
dependency_graph:
  requires: ["03-01"]
  provides: ["03-04"]
  affects: [scanner.py, test_scanner.py, .github/workflows/scan.yml, .github/workflows/scan-weekly.yml]
tech_stack:
  added: [scripts/verify_workflows.py, .github/workflows/scan-weekly.yml]
  patterns: [stale-first scheduling, query-budget early-stop, coarse-grid daily, if:always upload, concurrency guard]
key_files:
  created:
    - .github/workflows/scan-weekly.yml
    - scripts/verify_workflows.py
  modified:
    - scanner.py
    - test_scanner.py
    - .github/workflows/scan.yml
decisions:
  - "budget_reached() checks after each full route (not mid-route) to preserve per-route atomic write invariant"
  - "scripts/verify_workflows.py handles YAML 1.1 'on' -> True boolean quirk in PyYAML (get_on() helper checks both 'on' and True keys)"
  - "daily cron stays COMMENTED OUT in scan.yml — enabled only after 03-04 measures real Google block rate"
  - "scan-weekly.yml has active Sunday cron (0 2 * * 0) as full-grid safety net"
metrics:
  duration: 25 min
  completed: "2026-06-14"
  tasks_completed: 2
  files_changed: 5
---

# Phase 03 Plan 03: Scanner Incremental Flags + Reliable Workflows Summary

**One-liner:** Added `--stale-first`/`--budget`/`--grid-step` incremental flags to scanner + restructured CI workflows with separate `if: always()` upload step and concurrency guard; daily cron stays commented until 03-04 rollout.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | scanner --stale-first / --budget / --grid-step + offline tests | `970da3e` | scanner.py, test_scanner.py |
| 2 | Restructure scan.yml (daily) + add scan-weekly.yml + verify_workflows.py | `6371407` | scan.yml, scan-weekly.yml, scripts/verify_workflows.py |

## What Was Built

### Task 1: Scanner Incremental Flags

Three new pure helpers + three argparse flags added to `scanner.py`:

**`reorder_stale(routes, stale_keys)`** — pure function, no IO. Given a list of `"ORIGIN-DEST"` keys from `db.stale_routes()` (oldest-first), reorders the route list so never-scanned routes come first, then by ascending index in `stale_keys`. Used by `--stale-first`.

**`budget_reached(q_done, budget)`** — pure function. Returns `False` when `budget` is falsy (0/None = no cap). Returns `True` when `q_done >= budget`. Budget check happens *after* each complete route to preserve per-route atomic write invariant.

**`--stale-first`** flag: after `--slice` reduction, calls `db.stale_routes()` and reorders via `reorder_stale()`. No-op offline (empty list when Supabase unconfigured).

**`--budget N`** flag: checks `budget_reached(pace["q"], args.budget)` after every route completes. When reached: logs remaining count, calls `save("completed")`, returns 0. Does not abort mid-route.

**`--grid-step K`** flag: in `--grid` mode, applies `list(range(1, 32, K))` for sample days. Default `K=1` = existing full-month behaviour. `K=3` = ~11 days/month instead of 31 (daily coarse grid).

### Task 2: Workflow Restructure

**`scan.yml` (daily incremental)** — completely rewritten:
- 6-shard matrix (down from 12; lowers Azure footprint per DAILY-UPDATES.md section 3.2)
- Run: `scanner.py --slice K/6 --grid --grid-step 3 --no-refine --stale-first --budget 400 --no-browser`
- `timeout-minutes: 90` (6 shards x ~400 queries x ~10s ≈ 67 min, with buffer)
- `concurrency: group: scan-daily, cancel-in-progress: false` (DAILY-03)
- Scanner step and upload step are **SEPARATE** (DAILY-03 bug fix)
- Upload step has `if: always()` — publishes partial results even on scan timeout
- **Daily cron is COMMENTED OUT** — enabled only after 03-04 block-rate measurement

**`scan-weekly.yml` (new)** — weekly full sweep:
- 12-shard matrix
- Run: `scanner.py --slice K/12 --grid --resume --no-browser` (full grid + refine ON + resume)
- `timeout-minutes: 350`
- Active cron `"0 2 * * 0"` (Sun 02:00 UTC) + `workflow_dispatch`
- `concurrency: group: scan-weekly, cancel-in-progress: false`
- Separate `if: always()` upload step

**`scripts/verify_workflows.py`** — 10-assertion structural validator:
- `yaml.safe_load` both files (format check)
- Concurrency guard present in both
- Upload step has `if: always()` in both
- Scanner + upload are separate steps in both
- Daily cron is commented (not an active `schedule` key)
- Weekly has active cron `'0 2 * * 0'`
- Handles PyYAML YAML 1.1 quirk where `on:` is parsed as boolean `True`

## Verification Results

```
test_scanner.py: 19 passed, 0 failed
scripts/verify_workflows.py: 10 passed, 0 failed

grep -c 'if: always' scan.yml scan-weekly.yml → 2 + 1 = 3 (>= 2 ✓)
grep -c 'stale_routes' scanner.py → 3 (>= 1 ✓)
grep -c 'concurrency' scan.yml → 1 (>= 1 ✓)
```

Daily cron confirmed commented out — no GitHub run triggered by this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PyYAML YAML 1.1 'on' → boolean True quirk**
- **Found during:** Task 2 verification (verify_workflows.py initially failed check 6)
- **Issue:** `yaml.safe_load` in PyYAML treats bare `on:` as boolean `True` per YAML 1.1 spec. `doc.get("on")` returns `None`; the schedule block was unreachable.
- **Fix:** Added `get_on(doc)` helper in `verify_workflows.py` that checks `doc.get("on") or doc.get(True)`.
- **Files modified:** scripts/verify_workflows.py
- **Commit:** included in `6371407`

## Known Stubs

None — no UI rendering or data display in this plan.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All secrets referenced via `${{ secrets.* }}` only (T-03-08 mitigated). Concurrency guard added (T-03-09 mitigated). Separate if:always upload step (T-03-07 mitigated). Budget + coarse grid cap aggregate daily footprint (T-03-06 mitigated).

## Self-Check: PASSED

- scanner.py: FOUND
- test_scanner.py: FOUND
- .github/workflows/scan.yml: FOUND
- .github/workflows/scan-weekly.yml: FOUND
- scripts/verify_workflows.py: FOUND
- Commit 970da3e: FOUND
- Commit 6371407: FOUND
