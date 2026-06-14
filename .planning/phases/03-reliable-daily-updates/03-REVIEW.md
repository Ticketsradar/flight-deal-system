---
phase: 03-reliable-daily-updates
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - db.py
  - upload.py
  - scanner.py
  - test_db.py
  - test_scanner.py
  - web/lib/freshness.ts
  - web/components/DestinationCard.tsx
  - web/components/Header.tsx
  - web/app/page.tsx
  - .github/workflows/scan.yml
  - scripts/verify_workflows.py
findings:
  critical: 2
  warning: 5
  info: 4
  total: 11
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-06-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 3 adds incremental daily-scan infrastructure: `scanned_at` propagation through the DB layer, `stale_routes()` for staleness-ordered scanning, `--stale-first`/`--budget`/`--grid-step` CLI flags in the scanner, and per-route freshness labels in the UI. The backend logic is mostly sound, but two issues are blockers: the CI workflow validator (`verify_workflows.py`) permanently fails with a wrong assertion about the cron schedule state, and the `--slice` argument in `scanner.py` has no input validation and crashes unrecoverably on malformed input. Five warnings cover dead code, a counter undercounting, an unnecessary secret injection, a fragile Supabase row-limit assumption, and a null-price display edge case.

---

## Critical Issues

### CR-01: `verify_workflows.py` permanently fails — check logic is inverted relative to current codebase state

**File:** `scripts/verify_workflows.py:110-121`

**Issue:** `check_daily_cron_commented` asserts that `scan.yml` must NOT have an active `schedule` block (i.e., the cron should be commented out). The docstring says: *"4. scan.yml(daily)cron 係 comment 咗(唔係 active schedule),只有 workflow_dispatch"*. However, Phase 4 explicitly uncommented the cron (`0 18 * * *`) to activate daily runs — the CLAUDE.md confirms *"cron 已 uncomment"*. Running `verify_workflows.py` now always exits with code 1 due to this one check alone.

A second permanent failure occurs at line 139/145: `scan-weekly.yml` was deleted as part of Phase 4 (CLAUDE.md: *"原 weekly 安全網因 daily 已全覆蓋而刪走"*), so `load_yaml(WEEKLY)` raises `FileNotFoundError`, `fail()` is called, and `weekly_doc = None` silences all subsequent weekly checks without any "file not found, skipping" path. The validator reports a failure count of at least 2 every time it runs, making it useless as a CI gate.

**Fix:** Update the validator to match the current production state.

```python
def check_daily_cron_active(raw: str, label: str) -> None:
    """Daily scan.yml must have an active schedule/cron (production state)."""
    doc_check = yaml.safe_load(raw)
    on_block = get_on(doc_check)
    has_active_schedule = "schedule" in on_block
    if has_active_schedule:
        ok(f"{label}: has active cron schedule (production state)")
    else:
        fail(f"{label}: 缺少 active cron schedule — daily scan 唔會自動跑")

# Replace the weekly check with an existence guard:
if not WEEKLY.exists():
    ok("scan-weekly.yml: 已刪走(daily 全量已取代,唔需要)")
else:
    weekly_doc = load_yaml(WEEKLY)
    # ... run weekly checks ...
```

---

### CR-02: `--slice` argument crashes with `ValueError` on malformed input, no validation

**File:** `scanner.py:526`

**Issue:** The `--slice` parsing does:
```python
k, n = (int(x) for x in args.slice.split("/"))
```
If `--slice` is passed without a `/` (e.g., `--slice 5`), Python raises `ValueError: not enough values to unpack`. If `n=0` is passed (e.g., `--slice 0/0`), `routes[k::0]` raises `ValueError: slice step cannot be zero`. If `k >= n` (e.g., `--slice 25/20`), the result is silently an empty list — the shard scans nothing and uploads an empty file, potentially overwriting prior good data with a scan that has 0 routes. Since the scan output file name is date-based and `upload.py` uses the latest `scan_*.json`, an empty-shard file from a concurrent GitHub Actions job could win the file sort and zero out Supabase.

In the matrix workflow this is controlled, but the CLI is also used manually and in future automation.

**Fix:**
```python
if args.slice:
    parts = args.slice.split("/")
    if len(parts) != 2:
        ap.error(f"--slice 格式應係 K/N(如 2/20),得到: {args.slice!r}")
    k, n = int(parts[0]), int(parts[1])
    if n <= 0:
        ap.error(f"--slice N 必須 > 0,得到: {n}")
    if k >= n:
        ap.error(f"--slice K 必須 < N(K={k}, N={n})")
    routes = routes[k::n]
```

---

## Warnings

### WR-01: `beyond_before` is a dead variable — assigned but never read

**File:** `scanner.py:665`

**Issue:** Inside `scan_month`, line 665 sets `beyond_before = beyond` immediately before incrementing `beyond`. The variable `beyond_before` is never referenced again anywhere in the file. This suggests the author intended to use the pre-increment value for some comparison (perhaps to check if `beyond` changed per iteration) but the logic was not completed.

**Fix:** Remove the dead assignment:
```python
# Delete line 665:
# beyond_before = beyond
if r["status"] == "beyond_data":
    beyond += 1
on_query(r)
```
If the intent was to detect per-query `beyond_data` transitions, implement the check explicitly or leave a comment explaining why the variable is unused.

---

### WR-02: `tier2_used` counter undercounts — browser `beyond_data` responses are not counted

**File:** `scanner.py:634-641`

**Issue:** In `on_query`, `tier2_used` is incremented only when `r.get("via") == "browser"`. However, when `query_roundtrip` returns `beyond_data` from the browser path (line 311: `return {"status": "beyond_data", "tfs": tfs}`), the returned dict has no `"via"` key. The result: every browser `beyond_data` response is silently uncounted. The `tier2_used` statistic under-reports actual browser invocations, which is important for cost/usage monitoring (the comment in `scan.yml` explicitly worries about fair-use limits).

**Fix:** Add `"via": "browser"` to all browser return paths in `query_roundtrip`:
```python
if status == "beyond":
    return {"status": "beyond_data", "tfs": tfs, "via": "browser"}  # add via
if status == "no_flights":
    return {"status": "no_flights", "tfs": tfs, "via": "browser"}   # add via
```

---

### WR-03: `REDDIT_USER_AGENT` secret injected into the scan step but `scanner.py` never uses it

**File:** `.github/workflows/scan.yml:56`

**Issue:** The scan step injects `REDDIT_USER_AGENT: ${{ secrets.REDDIT_USER_AGENT }}` as an environment variable. `scanner.py` performs no Reddit HTTP requests and never reads this environment variable. This injects a secret into a job context that does not need it. If the scan step were ever compromised or if debug output ever printed all environment variables, this would expose the secret unnecessarily. The principle of least privilege requires secrets be injected only into steps that need them.

**Fix:** Remove `REDDIT_USER_AGENT` from the scan step env block. It belongs in the scout/feeds pipeline, not the scanner:
```yaml
      - name: 掃描分片 ${{ matrix.k }}/20(全量,粗格 step3,refine ON,browser 後備)
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SECRET_KEY: ${{ secrets.SUPABASE_SECRET_KEY }}
          # REDDIT_USER_AGENT not needed by scanner.py — remove
        run: |
          uv run python scanner.py ...
```

---

### WR-04: `getCheapFlights` has no explicit row-count limit — silently truncated by Supabase default

**File:** `web/lib/data.ts:22-34`

**Issue:** `getCheapFlights` builds a query with no `.limit()` call. Supabase PostgREST applies its own default row limit (typically 1000). `page.tsx` comments acknowledge this: *"避開 Supabase 1000 行上限"* — the origin filter keeps result sets small for now (~57 destinations × 7 months ≈ 399 rows per origin). However, this is an implicit load-bearing constraint: if routes expand to 3 origins × 70 destinations × 12 months = 2520 rows, the query silently returns only 1000 and the UI shows a random subset of destinations with no error. There is no assertion, error, or log entry if truncation occurs.

**Fix:** Add an explicit limit or add a row-count assertion:
```typescript
const { data, error } = await q
  .order("price_hkd", { ascending: true })
  .limit(2000);   // explicit; adjust as routes grow; at least surfaces the constraint
if (error) { ... }
// Optional: warn if data length approaches the limit
if ((data?.length ?? 0) >= 1900) {
  console.warn("[data] cheap_flights result near row limit — consider pagination");
}
```

---

### WR-05: `priceTier` renders null-price periods as green (tier 0) instead of hiding them

**File:** `web/components/DestinationCard.tsx:24-29`

**Issue:** When `p.price` is `null`, `priceTier(p.price ?? Infinity, mMin)` evaluates as `priceTier(Infinity, mMin)`. If `mMin` is also `Infinity` (all prices null in a month), then `Infinity <= Infinity * 1.04` is `true`, returning tier 0 (green). These entries pass the `< 3` filter and render as green buttons showing `$—` (null price). This is visually misleading: a period with no price data appears as the "cheapest" in green.

**Fix:** Explicitly check for null price before rendering:
```tsx
.filter((p) => p.price != null && priceTier(p.price, mMin) < 3)
```
And update `priceTier` to guard the `monthMin === 0` or `Infinity` case:
```typescript
function priceTier(price: number, monthMin: number): number {
  if (!isFinite(monthMin) || monthMin <= 0) return 3; // no valid baseline
  if (price <= monthMin * 1.04) return 0;
  // ...
}
```

---

## Info

### IN-01: `stale_routes(limit=N)` uses `limit * 10` fetch multiplier — inadequate for small limits

**File:** `db.py:215-216`

**Issue:** When called with `limit=1`, `stale_routes` fetches 10 DB rows (`limit * 10`). If the stalest route has 10+ months (plausible at 7–12 months per route), those 10 rows might represent only 1 unique route. After `_order_stale` deduplication, `[:1]` would correctly return 1 route. At `limit=2` with 7 months per route, 20 rows = ~2.8 unique routes — marginal but usually sufficient. The multiplier is under-documented and callers cannot predict when it will fail to return the requested number of routes.

In production, `stale_routes()` is called with no `limit` argument, so this is not currently a real bug. But the API contract is misleading.

**Fix:** Add a docstring clarification or raise the multiplier:
```python
params += f"&limit={limit * 20}"  # 20x headroom: 7 months/route × 20 = 140 rows for limit=7
```

---

### IN-02: `freshnessLabel` does not handle timezone-naive ISO strings consistently across environments

**File:** `web/lib/freshness.ts:11`

**Issue:** `new Date(iso)` where `iso` is a Python-generated naive timestamp like `"2026-06-14T10:00:00"` (no `Z`, no offset) is parsed as **local time** in browsers but as **UTC** on many Node.js server environments. Since `scanned_at` is produced by `dt.datetime.now().isoformat()` (local time, no TZ), and the Next.js page is rendered server-side, the effective timezone of parsing depends on the server's locale. On a UTC server (GitHub Actions, Vercel), a 10:00 HKT timestamp is parsed as 10:00 UTC — 8 hours off. This causes a freshness display error of up to ~1 day at certain hour boundaries (e.g., scan at 02:00 HKT = 18:00 previous day UTC → shows "1 日前" instead of "今日更新").

**Fix:** Emit timezone-aware timestamps in Python:
```python
"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
# e.g. "2026-06-14T18:00:00+00:00"
```
`new Date("2026-06-14T18:00:00+00:00")` is unambiguous in all environments.

---

### IN-03: `test_9_grid_step` tests the formula, not the scanner's actual `sample_days` assignment

**File:** `test_scanner.py:393-414`

**Issue:** Test 9 verifies the Python `range(1, 32, step)` formula in isolation — but the test does not call into `scanner.py`'s `main()` or even reference `args.grid_step`. It just checks that `list(range(1,32,3)) == expected_step3`. This is a tautology: the formula being tested is the same formula used to compute the expected value. If the `scanner.py` line `sample_days = list(range(1, 32, step))` were changed (e.g., accidentally became `range(0, 31, step)`), this test would still pass.

**Fix:** Import and exercise the actual computation path, or test an observable behaviour (e.g., monkeypatch `upcoming_months` and verify `sample_days` passed to it):
```python
# Instead of testing the formula, test that --grid-step 3 produces 11 sample days,
# not 31, by calling the code path that produces sample_days in scanner.main().
```

---

### IN-04: Hardcoded shard count (`/20`) in `scan.yml` must stay in sync with matrix size — no enforcement

**File:** `.github/workflows/scan.yml:59`

**Issue:** The run command contains a hardcoded `--slice ${{ matrix.k }}/20`. The denominator `20` must equal the length of the `k:` array in the matrix. If the matrix is ever resized (e.g., to 10 shards to reduce usage), only changing the `k:` list without updating `/20` causes each shard to scan only half the routes, and `routes[k::20]` with k=[0..9] would leave routes 10–19, 30–39, etc. uncovered. No CI check catches this mismatch.

**Fix:** Either use a matrix variable for `N`:
```yaml
matrix:
  include:
    - { k: 0, n: 20 }
    # ... or use env var
```
Or add a step that validates the denominator matches the matrix size. At minimum, add a comment directly adjacent to the denominator that says "this must match len(k list) above".

---

_Reviewed: 2026-06-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
