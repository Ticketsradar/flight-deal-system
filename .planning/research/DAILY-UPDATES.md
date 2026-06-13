# DAILY-UPDATES — Making the flight scanner refresh reliably every day

> Research deliverable. Scope: why the live site currently refreshes only ~every 3 days, and how to make daily updates reliable.
> Audience: orchestrator + non-programmer owner (decisions explained plainly; technical detail kept for the planner).
> Date: 2026-06-14. Confidence is marked per claim: **[High]** (code/log evidence or official docs), **[Med]** (sound inference), **[Low]** (assumption to verify).

---

## TL;DR

The daily cron in `.github/workflows/scan.yml` is **structurally too slow to finish in one day** at the current scope. Each of the 12 matrix jobs has to make **~2,100–2,700 Google Flights queries** in `--grid` mode, and the scanner's own anti-block pacing forces a real-world rate of **~11 seconds per query** (measured). That puts a single job at **~5–7 hours**, which **exceeds GitHub Actions' hard 6-hour per-job limit** `[High]`. Jobs that brush against the limit get killed mid-route, partial data trickles in, and the practical effect is a full refresh only every ~3 days.

**The single highest-leverage fix is the data-source decision (DATA-SOURCES.md).** If the project moves to a cached price API (Travelpayouts / Amadeus / Kiwi), the whole grid becomes a few hundred fast API calls, daily refresh becomes trivial (minutes, one job, no IP risk), and most of the options below stop mattering `[Med]`. **If we stay on `fast-flights` (scraping Google), daily-at-full-scope is not achievable on GitHub's shared runners** — we must cut scope (incremental/staleness scanning + fewer grid-days) and/or pay for residential proxies.

Recommended path: **(A) push the API decision first**; **(B) until then, ship an incremental daily policy** — daily = re-scan the freshest-value / most-volatile slice that fits a 2-hour window, full grid sweep weekly — plus a per-route `scanned_at` freshness timestamp the website already half-supports.

---

## 1. Root-cause analysis of the current ~3-day cadence

### 1.1 The numbers (empirical, not theoretical)

Route universe: **171 routes** = 3 origins (HKG/SZX/CAN) × 57 destinations, `exclude: []` (`routes.yaml`) `[High]`.

The workflow runs `scanner.py --slice K/12 --grid --no-browser` (`scan.yml` line 37). In `--grid` mode `sample_days = range(1,32)` (`scanner.py` line 380) — **every calendar day of each month is a departure**, over the default **7 months** (`--months` default, line 348). So per job:

```
routes/job        = 171 / 12          ≈ 14.2
queries/job (max)  = 14 × 7 × ~28 valid grid-days ≈ 2,744   [High — arithmetic on code]
queries/job (real) ≈ 2,100            (far/long-haul months short-circuit via beyond_data)  [Med]
```

The "real" figure is lower because the scanner skips remaining months once a route returns `beyond_data` twice (`BEYOND_SKIP_AFTER = 2`, lines 57 & 571) — far-future long-haul flights aren't loaded yet. From the full-scan log, **1,476 of 2,052 route-months had data (~72%)**, the rest short-circuited cheaply `[High, data/scan_20260613.full.json]`.

### 1.2 The real per-query cadence is ~11 seconds, not the nominal 3–8s

Measured from the actual grid run `data/scan_20260614.json` (HKG→MNL, 7 months, full grid):

```
201 queries  /  2,177 seconds  =  10.83 sec/query   [High — real run, status "completed"]
```

That 11s already folds in: the `delay_seconds: [3,8]` inter-query sleep (avg 5.5s, `routes.yaml`); the HTTP round-trip itself; the `COOL_EVERY = 30` rest of 20–40s every 30 queries (lines 55, 443); and occasional Tier-2 browser hits. The CI runs `--no-browser`, so it avoids the 14s Playwright timeouts (`_outcome` default `timeout_s=14.0`, line 138) — but it also means **HTTP failures are never rescued**, so failed grid-days just count as misses.

### 1.3 Per-job runtime vs the 6-hour wall

Projecting the measured cadence (HTTP-only model: 5.5s delay + ~1.8s round-trip + cooldowns + the occasional 10–15-min long-rest on a cold patch):

| queries/job | base (delay+fetch) | cooldowns | long-rests | **total** |
|---|---|---|---|---|
| 2,000 | 243 min | 33 min | ~25 min | **~5.0 h** |
| 2,500 | 304 min | 42 min | ~38 min | **~6.4 h** |
| 2,744 (max) | 334 min | 46 min | ~38 min | **~6.9 h** |

`[Med — model calibrated to the 10.83s/q measurement]`

**GitHub Actions hard limit: each job may run up to 6 hours; on hitting it the job is terminated and fails** `[High, GitHub docs — Actions limits]`. The workflow sets `timeout-minutes: 350` (= 5h50m, `scan.yml` line 20), so the scanner is guillotined at ~5h50m even before the platform's 6h. **A job in the 2,500–2,744-query band runs out of clock and is killed mid-sweep.** That is the root cause.

### 1.4 Why it lands at "~every 3 days" specifically

- Jobs that exceed the timeout die with **partial routes uploaded** — `scanner.py` writes after every route and `upload.py` runs only *after* the scan step in the same shell step, so **a timed-out job uploads nothing for that run** (the `&&`-style sequential `run:` block means `upload.py` never executes if `scanner.py` is killed) `[High — reading scan.yml step + scanner save/exit logic]`. So a killed shard contributes **zero** new rows that day, not "partial."
- With `fail-fast: false` (line 22) the other shards still run, but the slowest/most-data-rich shards (lots of Japan/SE-Asia near-term grid-days = the *most* queries) are exactly the ones most likely to time out — so the richest data is the most likely to be missing on any given day.
- Net effect: on a typical day a few shards finish and a few die, so the DB is a patchwork; it takes 2–3 daily runs before every shard has had a "lucky" fast run, which the owner perceives as "refreshes every ~3 days." `[Med — consistent with the symptom, not directly logged]`
- **Compounding factor — cron delay:** scheduled workflows do **not** fire at the exact minute. During busy periods GitHub queues them, and **10–30 minute delays are common, occasionally >1 hour** `[High, community/Earthly/OneUptime reporting; GitHub docs say schedule "may be delayed during periods of high loads"]`. This doesn't break daily on its own, but it eats into any tight window and makes "did it run today?" non-obvious.

> **Secondary risk, not yet the bottleneck:** shared-IP rate-limiting (see §2). Today the visible failure is *time*, not *blocking* — but if we shrink the time budget by going faster/more-parallel, blocking becomes the next wall.

---

## 2. Shared-IP rate-limiting risk (GitHub runners vs Google Flights)

**Setup:** Ubuntu GitHub-hosted runners are **hosted in Azure and use Azure datacenter IP ranges** `[High, GitHub Docs — About GitHub-hosted runners]`. The IPs are **dynamic**, drawn from a shared pool, and GitHub states the published meta IP list "is not intended to be an exhaustive list" `[High, GitHub community #26441]`.

**Why this is risky against Google specifically:** anti-bot systems maintain reputation lists of cloud/datacenter ranges (AWS, GCP, **Azure**) and **flag requests from those ranges as likely-automated before any other signal is checked**; because thousands of unrelated scrapers cycle through the same shared addresses, those IPs "accumulate block history fast, and users inherit that history the moment they connect" `[High, scraping-industry sources — ZenRows/IPBurger/Firecrawl]`. Google Flights is among the **most aggressively anti-scraped** surfaces (the project's own CLAUDE.md notes Google "重度反爬" and that direct date-grid R&D failed) `[High, CLAUDE.md]`.

**Likelihood at the current cadence:** **Moderate-to-high over time** `[Med]`. The scanner's pacing (3–8s, cooldowns, long-rests, random browser impersonation via `Client(impersonate="random")`, line 85) is *good etiquette* and is why single-machine runs mostly succeed. But:
- 12 concurrent jobs each opening fresh `primp` HTTP clients means **12 Azure IPs hammering `google.com/travel/flights` in the same hour, daily**. Even if each is polite, the *aggregate* footprint from Google's view is one operator doing ~25k–32k Google queries/day from Azure space.
- The full-scan log already shows **187 hard failures and heavy `beyond_data`/shell-page churn** `[High, log]` — some of that "empty shell page" behaviour (`ShellPage`, line 60) is exactly how Google soft-blocks datacenter traffic (returns a contentless "Loading results…" page instead of a 429) `[Med]`. So we may *already* be partially soft-blocked and reading it as "no data."
- Evidence that GitHub-Actions shared IPs get **429-banned by third parties** is well-documented (JetBrains IJPL-214348; githubusercontent 429 threads) `[High]` — Google won't be gentler than githubusercontent.

**Known mitigations** (ordered by effort):
1. **Lower aggregate rate** — fewer concurrent jobs, more spacing (cheap, helps reputation). `[High]`
2. **Respect `Retry-After` / exponential backoff** — scanner already backs off on `Blocked` (lines 258–261) but treats the silent shell-page as retryable rather than as a soft-block signal; could add a per-IP circuit-breaker. `[Med]`
3. **Residential/rotating proxies** — the real fix for datacenter-IP reputation, but cost + ToS (see §3.3). `[High]`
4. **Switch to an API** — eliminates the problem entirely (you're a paying client, not a scraper). `[High]`

---

## 3. Strategies for reliable daily refresh (ranked, with tradeoffs)

> Each option notes whether it **depends on the data-source decision**. Read §3.0 first — it dominates everything.

### 3.0 ⭐ COUPLING: the cached-price-API decision changes the whole answer

If DATA-SOURCES.md lands on **Travelpayouts (Aviasales) "cheapest tickets / calendar" endpoints, Amadeus Flight Cheapest Date Search, or Kiwi/Tequila**, then:

- A month-grid for a route comes back in **one call** (these APIs return a price-per-day calendar), not 28 scraped queries. Whole 171-route × 7-month grid ≈ **a few hundred to low-thousands of API calls**, finishable in **single-digit minutes, one job, daily, trivially** `[Med — based on documented endpoint shapes]`.
- **No shared-IP risk** (authenticated API client), **no 6-hour problem**, **no proxies needed**.
- Tradeoff: data is **cached** (hours-to-days old) and **less precise** than live Google Flights; some APIs are paid or require attribution/affiliate terms. The site already says "撳入去 Google Flights 確認實時價," so cached headline + live confirm-link fits the existing UX.

**Implication for this report:** Options 3.1–3.4 below are the **"if we stay on `fast-flights`/scraping" plan**. If the API decision is yes, jump straight to a trivial daily cron and treat 3.1 (staleness tracking) as a nice-to-have, not a necessity. **Recommend resolving DATA-SOURCES.md before investing in the scraping-side scheduling rework.** `[High — strategic]`

---

### 3.1 Incremental / staleness-based scanning (daily partial, weekly full)

**Idea:** Don't re-scan all 171 routes every day. Each day, scan only the **stalest** and **most price-volatile** routes that fit a safe ~2-hour window; do a **full grid sweep weekly** (e.g. Sunday).

**How to track per-route freshness:**
- The DB already stamps `cheap_flights.scanned_at timestamptz default now()` (`schema.sql`) `[High]`. Add a query at scan start: `SELECT origin,destination,max(scanned_at) FROM cheap_flights GROUP BY 1,2` → pick the N oldest. A small helper in `db.py` (mirrors existing `select()`).
- Volatility weighting: near-term months and popular regions (Japan/SE-Asia/Korea) move more and matter more to users → scan weekly-or-better; long-haul far months (Europe/US/AUS, lots of `beyond_data`) → scan every 5–7 days. Encode as a per-region cadence in `routes.yaml` (`refresh_days: 1|3|7`).
- Cap each daily run by **query budget, not route count**: keep adding routes until projected queries ≈ 1h-of-runtime (~330 queries/job at 11s), then stop. Guarantees the job never approaches the 6h wall.

**Effort:** Med (new freshness query + a budget-loop in `main()`; ~half a day).
**Cost:** $0.
**Risk:** Low. Worst case a route is a few days stale — and the new freshness timestamp (see §4) lets the site *show* that honestly.
**Depends on data source?** **Independent** — useful either way, but **only necessary if we stay on scraping.**

### 3.2 More shards / spread across the day (multiple cron times)

**Idea:** Instead of one 12-job burst at 18:00 UTC, split into e.g. **3 cron times** (e.g. 02:00 / 10:00 / 18:00 UTC), each running a **smaller** slice (more shards, fewer queries each), so no single job nears 6h and the per-hour Google footprint from Azure drops.

- e.g. `--slice K/24` across two staggered launches, or 3 launches each doing one-third of the routes.
- Reduces both the **timeout risk** (smaller jobs finish well under the limit) and the **block risk** (lower burst concurrency).

**Effort:** Low (edit matrix list + `--slice` denominator + add cron lines; the code already supports any N via `routes[k::n]`, line 375).
**Cost:** $0 (well within Free plan's 20 concurrent-job ceiling `[High]` as long as a single launch ≤20 jobs; staggering avoids overlap).
**Risk:** Med — **cron delay (10–30 min, sometimes >1h) `[High]`** means staggered launches can drift into each other; mitigate with `concurrency:` groups so a late run doesn't double-fire. Doesn't fix the fundamental volume problem, just repackages it — pairs best with §3.1.
**Depends on data source?** Independent; **only relevant for scraping.**

### 3.3 Proxy / residential IP rotation

**Idea:** Route `fast-flights` HTTP (and Playwright) through a **residential/rotating proxy** so requests don't originate from flagged Azure ranges.

- Wiring: `fast_flights`/`primp` `Client` would need a proxy param, or front it with a proxy env (`HTTPS_PROXY`). Some refactor of `fetch_http()` (line 83) and the Playwright `launch` args.
- Providers (rough 2026 pricing, **[Low] — verify at purchase**): residential proxies ~**$3–$15 / GB**; a daily full grid scrapes a lot of HTML, so plausibly **$20–$100+/month**. Datacenter proxies are cheaper (~$0.5–$2/GB) but share the same reputation problem as Azure and won't help against Google.
- **ToS / legal risk:** scraping Google Flights is **against Google's ToS**; residential proxies add their own ToS exposure and (for some providers) ethically grey sourcing. This is the **highest-risk** option and runs counter to the project's "be polite / respect rate limits" 鐵律. `[Med]`

**Effort:** Med–High (proxy integration + secret management + cost monitoring).
**Cost:** **$20–$100+/month** `[Low]`.
**Risk:** High (ToS, cost creep, still cat-and-mouse with Google).
**Depends on data source?** **Becomes moot if we move to an API** — strongly prefer the API over paying for proxies to keep scraping. `[High]`

### 3.4 Reduce query volume (sample fewer grid-days / trip-lengths)

**Idea:** Stop scanning all ~28 grid-days. Daily scan uses a **coarse grid** (e.g. every 3rd day, or the SAMPLE_DAYS approach of 2–4 representative days/month); the **weekly full sweep** fills the complete per-day calendar.

- `scanner.py` already supports this: drop `--grid` and use `--samples 2..4` (lines 349, 52). 171 × 7 × 2 ≈ **2,394 queries total across all 12 shards** = **~200/shard = ~35 min/job** — comfortably daily `[High — this is literally the non-grid mode, and the full-scan ran 1,184 effective queries in the past]`.
- Tradeoff: fewer "cheap-day" dots on each destination card between weekly sweeps. The site already groups periods by price tier; a sparser daily grid + full weekly grid is a reasonable freshness/coverage trade.

**Effort:** Low (flag change in the workflow + optional `--grid-step N` arg).
**Cost:** $0.
**Risk:** Low.
**Depends on data source?** Independent; **only relevant for scraping.** (An API returns the full calendar per call, so you'd never need to thin the grid.)

---

### Ranking (assuming we must decide *now*, before DATA-SOURCES.md)

| Rank | Option | Effort | Cost | Risk | Daily-reliable? | Data-source dependent |
|---|---|---|---|---|---|---|
| **1** | **§3.0 Switch to cached price API** | Med (new integration) | API fees (often free tier) | Low | **Yes, trivially** | **Is the decision** |
| **2** | **§3.1 + §3.4 combined** (staleness budget + coarse daily grid, weekly full) | Med | $0 | Low | Yes | Stop-gap if scraping |
| **3** | **§3.2 Spread across day / more shards** | Low | $0 | Med (cron drift) | Partial (pair w/ 1–2) | Scraping only |
| **4** | **§3.3 Residential proxies** | High | $20–100+/mo | High (ToS) | Yes-ish | Avoid if API chosen |

---

## 4. Supabase upsert/merge correctness for PARTIAL daily updates + honest freshness

The DB is already **upsert-merge by natural key**, which is exactly right for partial daily writes — so the merge mechanics are sound, with two gaps to close.

**What works `[High, db.py + schema.sql]`:**
- `cheap_flights` upserts `on_conflict = origin,destination,month` with `Prefer: resolution=merge-duplicates` (`db.py` lines 193, 55; unique constraint `cheap_flights_route_month` in `schema.sql`). A daily partial run touching only some routes **updates those rows and leaves untouched routes intact** — correct. No DELETE-all-then-insert, so partial runs don't wipe other shards' data.
- `error_fares` upserts on `source_url` — same story.
- A timed-out shard simply doesn't upload (it never reaches `upload.py`), so it leaves yesterday's rows for its routes untouched — **stale, but not corrupt** `[High]`.

**Gaps to fix:**

1. **`scanned_at` is not being refreshed on upsert.** `cheap_flight_rows()` (`db.py` line 109) **does not include `scanned_at`** in the row, so on an UPDATE the column keeps its original `default now()` from first insert and **does not advance**. To track per-route freshness honestly, **explicitly set `scanned_at` in the upserted row** (or to the scan's `generated_at`). Without this, a "freshness" query reads the wrong time. `[High — read the row builder; the default only fires on INSERT, not UPDATE]`
   - Fix: add `"scanned_at": scan_doc.get("generated_at") or <now ISO>` to each row in `cheap_flight_rows()` (it has the doc in scope — pass it through). One-line-ish.

2. **The site shows one global `last_updated_stream_a`, not per-route freshness.** `upload.py` line 43 writes a single `meta` timestamp = the scan **date**. For honest "this route last checked X ago" UX, the website should read **per-row `scanned_at`** (now correct after fix #1) and render e.g. "更新於 2 日前" per card, greying out anything older than the route's `refresh_days`. The `meta` global can stay as a coarse "last run" badge.

3. **Staleness query for incremental policy (enables §3.1):** add to `db.py`:
   ```sql
   select origin, destination, max(scanned_at) as last
   from cheap_flights group by origin, destination order by last asc nulls first
   ```
   Drives "scan the stalest N first." Cheap to add via the existing `select()` helper. `[High]`

4. **Minor — `error_fares` upsert key collision:** keyed on `source_url` only; if two different deals share a URL (rare) one overwrites the other. Out of scope for daily-cheap-flights but worth a note for Stream B. `[Low]`

**Net:** partial-update merge is **already correct**; the only real bug for honest freshness is #1 (`scanned_at` never advances on UPDATE). Fix that + surface per-row freshness on the site, and the website can tell users the truth even when daily only refreshes a slice.

---

## 5. Concrete recommended scheduling design

**Decision gate first:** resolve DATA-SOURCES.md. If a cached API is adopted → design **5a**. If we stay on `fast-flights` → design **5b**. `[High]`

### 5a. If we adopt a cached price API (preferred)
- **One** workflow, **one** job (no matrix), **daily** `cron: "0 18 * * *"`, plus `workflow_dispatch`.
- Pull each route's month-calendar via the API's cheapest-date/calendar endpoint → write full `periods` → `upload.py`.
- Runs in minutes; well under all limits; no IP risk. Keep the Google Flights deep-link per cheap day for the user's live confirm. **Daily is solved.**

### 5b. If we stay on `fast-flights` (scraping) — staleness budget + tiered cron
Combine §3.1 + §3.4 + §3.2:

- **Daily incremental** (`scan-daily.yml`), `cron: "0 18 * * *"`:
  - Each shard scans the **stalest routes first** (query from §4.3) under a **runtime budget of ~75 min** (≈ 400 queries/shard at 11s — leaves a huge margin below the 6h wall and well under the 350-min timeout).
  - Use a **coarse grid** daily: `--grid-step 3` (every 3rd day) or `--samples 4`, not the full 28-day grid.
  - Keep **6–8 shards** (not 12) to lower the per-hour Azure footprint; staggered isn't needed for one launch.
- **Weekly full sweep** (`scan-weekly.yml`), `cron: "0 2 * * 0"` (Sun 02:00 UTC):
  - Full `--grid`, 12 shards, the current heavy run — but now it only has to succeed **once a week**, so occasional timeouts/blocks are tolerable and `--resume` mops up.
- **Hygiene on both:**
  - Set per-shard `timeout-minutes` to its budget + slack (daily: 90; weekly: 350).
  - Add `concurrency: { group: scan-${{ github.workflow }}, cancel-in-progress: false }` so a **cron-delayed** run (10–30 min, sometimes >1h `[High]`) can't double-fire onto a still-running one.
  - **Move `upload.py` into its own step that runs even if the scan step times out** (`if: always()`), or have the scan step trap the timeout and still upload — so a clipped daily job **still publishes the routes it did finish** (today a killed step uploads nothing). `[High — current scan.yml loses all partial work on timeout]`
  - Keep `fail-fast: false`.
  - Apply the §4 `scanned_at`-on-upsert fix so freshness is truthful.

**Why this is reliable:** every daily job is provably short (budget-capped), so it **cannot** hit the 6h wall; the weekly sweep guarantees no route goes more than 7 days stale; the site shows real per-route freshness so "daily" is honest even when daily only touches the stale slice.

---

## Citations

- **GitHub job time limit (6h), workflow max (35 days), concurrency (Free 20 / Pro 40 / Team 60 / Enterprise 500), matrix max (256 jobs/run):** GitHub Docs — Actions limits. `[High]`
  https://docs.github.com/en/actions/reference/actions-limits
- **GitHub-hosted runners run in Azure with Azure datacenter IP ranges; macOS in GitHub's cloud:** GitHub Docs — About GitHub-hosted runners. `[High]`
  https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners
- **Runner IPs are dynamic / meta list "not exhaustive":** GitHub community discussion #26441 (Stable IP addresses range for Actions). `[High]`
  https://github.com/orgs/community/discussions/26441
- **Scheduled (cron) workflows are delayed during high load — 10–30 min common, occasionally >1h:** OneUptime / Earthly / devactivity community reporting (consistent with GitHub's own "may be delayed during periods of high loads"). `[High]`
  https://oneuptime.com/blog/post/2025-12-20-scheduled-workflows-cron-github-actions/view ·
  https://earthly.dev/blog/cronjobs-for-github-actions/
- **Datacenter (AWS/GCP/Azure) IP ranges are pre-flagged by anti-bot systems; shared scraper IPs inherit block history:** ZenRows / IPBurger / Firecrawl scraping guides. `[High for the mechanism; Med applied to Google Flights specifically]`
  https://www.zenrows.com/blog/429-too-many-requests ·
  https://www.ipburger.com/blog/scaling-web-scraper-bypass-captcha-data-scraping/
- **GitHub Actions shared IPs get 429-banned by third parties (precedent):** JetBrains IJPL-214348; githubusercontent 429 community threads. `[High]`
  https://youtrack.jetbrains.com/issue/IJPL-214348 ·
  https://github.com/orgs/community/discussions/157887
- **Empirical scanner cadence & failures:** `data/scan_20260614.json` (201 q / 2177 s = 10.83 s/q, grid, completed); `data/scan_20260613.full.json` (1,184 q, 187 failed, 1,476/2,052 months OK); `data/fullscan_20260613_v3b.log`. `[High — this repo]`
- **Code/config:** `scanner.py` (grid=range(1,32) L380, COOL_EVERY=30 L55, ABORT_AFTER long-rest L53/449, BEYOND_SKIP_AFTER L57); `routes.yaml` (171 routes, delay [3,8]); `.github/workflows/scan.yml` (12-job matrix, timeout 350, cron 0 18 * * *, scan+upload one step L36–38); `db.py` (upsert merge-duplicates L193/55, `scanned_at` absent from row builder L109); `schema.sql` (`scanned_at default now()`). `[High — this repo]`
