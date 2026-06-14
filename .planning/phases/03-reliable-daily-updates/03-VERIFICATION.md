---
phase: 03-reliable-daily-updates
verified: 2026-06-14T20:10:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification: null
---

# Phase 3: 可靠每日更新 — Verification Report

**Phase Goal:** 令平機票數據每日可靠自動更新一次(取代而家 ~3 日一次嘅東拼西湊),更新過程容錯(部分掃描失敗都照出已完成部分),並喺網站誠實顯示真實「最後更新」時間。

**Verified:** 2026-06-14T20:10:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 平機票數據每日自動更新一次,可靠完成 — DAILY-01 | VERIFIED | `scan.yml` has active cron `0 18 * * *` with 20-shard matrix; `--stale-first` ensures stalest routes go first; Plan 04 live dispatch run confirmed jobs go green with browser fallback |
| 2 | scan.yml 修好:upload.py step with `if: always()`, partial upload works — DAILY-03 | VERIFIED | `scan.yml` line 66: `if: always()` on upload step; scanner and upload are separate steps; concurrency guard present; Plan 04 confirmed live: partial upload ran on soft-blocked shards |
| 3 | `db.cheap_flight_rows()` 修好,UPDATE 時會寫 `scanned_at` — DAILY-02 基建 | VERIFIED | `db.py` line 103: `scanned_at = scan_doc.get("generated_at") or datetime.now().isoformat()`; stamped on every row; `test_db.py` asserts this offline (15/15 pass) |
| 4 | 網站顯示真實「最後更新」時間,反映 per-route 新鮮度 — DAILY-02 | VERIFIED | `web/lib/freshness.ts` exists with `freshnessLabel()`; `DestinationCard.tsx` computes `lastScan = max(scanned_at)` and renders it; `Header.tsx` renders `freshnessLabel(meta.last_updated_stream_a)` |

**Score: 4/4 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `db.py` | `scanned_at` in every cheap_flights row; `stale_routes()` ordering helper | VERIFIED | Lines 100-124: scanned_at stamped; lines 175-219: `_order_stale()` + `stale_routes()` present and tested |
| `upload.py` | `generated_at` passed from scan_doc into `set_meta` | VERIFIED | Lines 43-44: `set_meta("last_updated_stream_a", scan.get("generated_at") or scan.get("scan_date", ""))` |
| `test_db.py` | Offline assertions for scanned_at + stale ordering | VERIFIED | 15/15 assertions pass; scanned_at positive + fallback + `_order_stale` ordering + `stale_routes()` no-op all confirmed |
| `web/lib/freshness.ts` | Pure formatter: ISO timestamp → 廣東話 relative-age label | VERIFIED | File exists; exports `freshnessLabel`; contains "更新於", "今日更新", "更新時間未知" |
| `web/components/DestinationCard.tsx` | Per-route freshness label using `scanned_at` | VERIFIED | Line 2: imports `freshnessLabel`; line 77-79: `lastScan = max(scanned_at)` via ISO sort; line 111: renders label |
| `web/components/Header.tsx` | Global last-updated badge from `meta.last_updated_stream_a` | VERIFIED | Line 1: imports `freshnessLabel`; line 4: reads `meta.last_updated_stream_a`; line 14: renders human-readable label |
| `scanner.py` | `--stale-first`, `--budget`, `--grid-step` flags | VERIFIED | Lines 461, 475, 502, 505, 529-540: all three flags present with `reorder_stale()` and `budget_reached()` pure helpers |
| `.github/workflows/scan.yml` | 20-shard daily cron; split scan/upload steps; `if: always()` upload; concurrency guard; browser fallback | VERIFIED | cron `0 18 * * *` active; 20-shard matrix; Playwright install step; separate upload step with `if: always()`; concurrency group `scan-daily` |
| `.github/workflows/scan-weekly.yml` | Deleted (redundant after 20-shard full-daily upgrade) | VERIFIED | File absent — confirmed deleted by Plan 04 decision (full daily covers all 171 routes daily) |
| `test_scanner.py` | Offline assertions for `reorder_stale`, `budget_reached`, `grid-step` | VERIFIED | 19/19 assertions pass; tests 7, 8, 9 cover the new helpers |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `upload.py` → `db.push_cheap_flights` | `cheap_flights.scanned_at` | `scan_doc` carries `generated_at`; row builder reads it | VERIFIED | `db.py` line 103-124: `scanned_at` key explicit in every upserted row dict |
| `DestinationCard.tsx` | `CheapFlight.scanned_at` | `max(scanned_at)` across flights → `freshnessLabel` | VERIFIED | `web/lib/types.ts` line 29: `scanned_at: string | null`; component reads it and renders label |
| `Header.tsx` | `meta.last_updated_stream_a` | `freshnessLabel` on global timestamp | VERIFIED | `Header.tsx` line 4 + 14: reads meta field, renders human-readable output |
| `scanner.py --stale-first` | `db.stale_routes()` | import db; `reorder_stale(routes, stale_keys)` | VERIFIED | `scanner.py` line 529-533: `_db.stale_routes()` called when flag set; result passed to `reorder_stale()` |
| `scan.yml` upload step | `upload.py` | separate step with `if: always()` | VERIFIED | `scan.yml` line 63-67: distinct step, `if: always()` confirmed present |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `DestinationCard.tsx` freshness label | `lastScan` (max scanned_at) | `cheap_flights.scanned_at` column in Supabase, advanced by `db.cheap_flight_rows()` on every scan run | Yes — `db.py` explicitly writes `scanned_at = scan_doc["generated_at"]` into every upserted row | FLOWING |
| `Header.tsx` global badge | `meta.last_updated_stream_a` | `upload.py` calls `db.set_meta("last_updated_stream_a", scan["generated_at"])` after each scan | Yes — `upload.py` line 43-44 writes precise datetime | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `test_db.py` offline assertions pass | `uv run python test_db.py` | 15/15 assertions pass; scanned_at stamped correctly | PASS |
| `test_scanner.py` offline assertions pass | `uv run python test_scanner.py` | 19/19 pass; `reorder_stale`, `budget_reached`, `grid-step` all verified | PASS |
| `test_upload.py` unaffected | `uv run python test_upload.py` | 2/2 assertions pass; existing upload logic intact | PASS |
| `scan.yml` parses + has `if: always()` + concurrency | `grep -n "if: always\|concurrency\|cron"` | `if: always()` line 66; concurrency lines 28-30; cron line 24 (active) | PASS |

---

### Probe Execution

Step 7c: SKIPPED — phase does not define probe scripts. Live CI dispatch was performed as part of Plan 04 (human-gated checkpoint) and outcomes recorded in 03-04-SUMMARY.md.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DAILY-01 | 03-03, 03-04 | 平機票數據每日自動更新一次,可靠完成 | SATISFIED | `scan.yml` cron `0 18 * * *` live; 20-shard full coverage; Plan 04 dispatch confirmed green with browser fallback |
| DAILY-02 | 03-01, 03-02 | 網站顯示真實「最後更新」時間,反映 per-route 新鮮度 | SATISFIED | `scanned_at` threaded into db rows; `freshnessLabel()` wired into `DestinationCard.tsx` and `Header.tsx` |
| DAILY-03 | 03-03, 03-04 | 更新過程容錯:部分掃描失敗照樣出街 | SATISFIED | Upload step separate from scan step with `if: always()`; live confirmed in Plan 04 (partial upload ran on soft-blocked shards) |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/verify_workflows.py` | (structural) | Two of its 6 assertions now FAIL due to intentional Plan 04 decisions (cron enabled, scan-weekly.yml deleted) | Info | Not a code smell — the validator was written in Plan 03 to gate the pre-rollout state; Plan 04 deliberately superseded both conditions. No action required. |

No TBD, FIXME, XXX, or placeholder patterns found in files modified by this phase.

---

### Plan 04 Deviation Note

`verify_workflows.py` (written in Plan 03) asserts: (1) daily cron is commented out; (2) `scan-weekly.yml` exists. Both assertions fail because Plan 04 intentionally reversed them after a live block-rate measurement:

- Daily cron was enabled (HTTP-only got soft-blocked on GitHub Azure IPs; Playwright browser fallback evaded it and returned green; user chose to enable full daily coverage).
- `scan-weekly.yml` was deleted (redundant once 20-shard daily covers all 171 routes every day).

These are recorded Plan 04 decisions, not regressions. The two failing verify_workflows.py checks reflect the validator being frozen at a pre-rollout state.

---

### Human Verification Required

None — all success criteria are verifiable programmatically or were verified via live CI dispatch in Plan 04.

---

### Gaps Summary

No gaps found. All four success criteria from the ROADMAP are met:

1. **DAILY-01 (daily auto-update)**: Active cron `0 18 * * *` with 20-shard matrix, browser fallback, and `--stale-first` ordering confirmed live.
2. **DAILY-03 (partial upload fault tolerance)**: `if: always()` upload step is separate from scan step; confirmed live that partial upload fired on soft-blocked shards.
3. **DAILY-02 infrastructure (`scanned_at` advances on UPDATE)**: `db.cheap_flight_rows()` explicitly writes `scanned_at = scan_doc["generated_at"]` into every upserted row; offline tests confirm correctness.
4. **DAILY-02 UI (honest freshness display)**: `freshnessLabel()` formatter wired into both `DestinationCard.tsx` (per-route) and `Header.tsx` (global).

---

## VERIFICATION PASSED

All 4/4 success criteria verified against actual codebase. Phase goal achieved.

---

_Verified: 2026-06-14T20:10:00Z_
_Verifier: Claude (gsd-verifier)_
