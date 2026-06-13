# Mispricing / Error-Fare Detection — Additional Sources & Self-Detection Design

> Research deliverable. Goal: capture mispriced/error-fare tickets **beyond** the current RSS scout
> (Reddit `.rss` + theflightdeal + fly4free → Haiku filter → Sonnet `master` verify → Telegram + Supabase).
> Origins of interest: **HKG / SZX / CAN** (Hong Kong + Greater Bay Area).
> Date of research: 2026-06-14. Live feed probes done with the same browser-UA `httpx`/curl path that `feeds.py` uses.

Two tracks:
- **TRACK A** — more *external* sources (verified fetchable-today, with method/cost/legality).
- **TRACK B** — *detect mispricing from our own scan data* with a statistical anomaly detector (no scraping). **This is the highest-ROI novel angle — developed in depth below.**

---

## Executive summary (read this first)

- **Most "famous" aggregators are NOT plain-HTTP fetchable.** Live-tested today: **Secret Flying** and **FlyerTalk** RSS both return **HTTP 403 Cloudflare JS-challenge** ("Just a moment…") even with a real browser User-Agent — the current `httpx`-based `feeds.py` *cannot* read them. **Airfarewatchdog** killed its RSS (now a React SPA + paywall). [confidence: high — directly probed]
- **What still works on plain HTTP:** `theflightdeal.com/feed/` (already used) and `fly4free.com/feed/` (already used) — but fly4free is **~85–90% Europe/US-origin**, so its HKG relevance is low (consistent with it already being `priority: medium`). [confidence: high — probed + content-sampled]
- **Twitter/X has no free ingestion path in 2026.** Nitter is effectively dead (discontinued Feb 2024, public instances collapsed); X API moved to **pay-per-use** ($0.005/read) Feb 2026, no free tier; RSS.app/RSSHub Twitter bridges require a logged-in session cookie and break often. [confidence: high]
- **Therefore the biggest external win is to make the *existing* error-fare sites reachable through the scanner's Playwright path** (we already run a real browser for Google Flights), rather than chasing many new RSS URLs that don't exist or are Cloudflared.
- **TRACK B is the strongest recommendation:** we already scan ~171 routes × 7 months daily. A per-route robust baseline (rolling median + MAD / p10) turns our own scanner into an error-fare radar with **zero scraping, zero ToS risk**. The one prerequisite: **start keeping price history** — the current `cheap_flights` table upserts on `(origin,destination,month)` and is **overwritten daily, storing no history** (`db.py` `push_cheap_flights`, `schema.sql` line 29). Add a snapshot table first.

---

# TRACK A — External sources (verified)

### A.1 Live-probe results (the load-bearing facts)

Probed 2026-06-14 with browser UA `Mozilla/5.0 … Chrome/126 Safari/537.36` (identical to `feeds.BROWSER_UA`):

| Feed | URL | Result today | Verdict |
|---|---|---|---|
| The Flight Deal | `https://www.theflightdeal.com/feed/` | **HTTP 200, 16 items, valid RSS** | ✅ works (already used) |
| Fly4Free (global) | `https://www.fly4free.com/feed/` | **HTTP 200, 50 items, valid RSS** | ✅ works (already used) but ~85–90% EU/US-origin |
| Fly4Free Asia category | `…/category/asia/feed/`, `…/flights/asia/feed/` | **HTTP 403** (Sucuri/WAF) | ❌ category feeds blocked |
| Secret Flying | `https://www.secretflying.com/feed/` | **HTTP 403 Cloudflare "Just a moment…"** | ❌ not via httpx |
| FlyerTalk Premium Fare Deals | `external.php?type=RSS2&forumids=740` | **HTTP 403 Cloudflare** | ❌ not via httpx |
| FlyerTalk Mileage Run Deals | `external.php?type=RSS2&forumids=372` | **HTTP 403 Cloudflare** | ❌ not via httpx |
| Airfarewatchdog | `/rss/*.xml`, `/feed/` | **HTTP 404 / SPA shell** | ❌ RSS retired, paywalled |

> Note: the **RSS feed URLs themselves are real and correct** (FlyerTalk `forumids=740`/`372` are the right Premium-Fare / Mileage-Run feeds, confirmed via FlyerTalk's own forum threads). They are simply **Cloudflare-gated**, so reaching them needs a JS-capable browser (our Playwright `BrowserFetcher`) or a paid proxy — *not* a config-only `sources.yaml` add.

### A.2 Source-by-source assessment

| Source | Method to fetch today | Structured? | Cost | ToS / legal risk | HKG relevance | Confidence |
|---|---|---|---|---|---|---|
| **The Flight Deal** `theflightdeal.com/feed/` | Native RSS, plain httpx (in use) | Yes (RSS) | $0 | Low (public RSS) | Med — global incl. occasional Asia-origin | High (probed) |
| **Fly4Free** `fly4free.com/feed/` | Native RSS, plain httpx (in use) | Yes (RSS) | $0 | Low | **Low** — ~85–90% EU/US-origin | High (probed) |
| **Secret Flying** `secretflying.com/feed/` | Cloudflare-gated → **Playwright** (reuse scanner browser) or paid proxy/ScraperAPI | Yes (RSS once fetched) | $0 via our browser; ~$30–50/mo if managed proxy | **Med** — bypassing CF is against their ToS; low volume + slow cadence keeps it grey | **Med-High** — #1 global error-fare brand, posts mistake fares worldwide incl. ex-Asia | High (403 probed; brand value high) |
| **FlyerTalk — Premium Fare Deals** `external.php?type=RSS2&forumids=740` | Cloudflare-gated → Playwright or proxy | Yes (RSS) | $0 via browser | Med (CF + forum ToS) | **Med-High** — premium-cabin mistake fares; J/F ex-HKG/Asia surface here first | High (URL confirmed, 403 probed) |
| **FlyerTalk — Mistake/Mileage Run Deals** `…forumids=372` | same | Yes (RSS) | $0 via browser | Med | Med — global, some HKG threads | High |
| **Reddit r/flightdeals + r/awardtravel** (in use) | `.rss`, plain httpx (in use) | Yes | $0 | Low (public `.rss`; 429-throttled) | Low-Med — US-centric; HKG mostly as *destination* | High |
| **Reddit r/awardtravel / r/churning** | `.rss` add to `sources.yaml` | Yes | $0 | Low | Low — points/award, US-issuer focus, HKG rarely *origin* | High |
| **Reddit Asia subs** (r/HongKong already in use; r/travel, r/JapanTravelTips, r/chinalife) | `.rss` | Yes | $0 | Low | Low-Med — occasional ex-HKG deal threads, noisy | Med |
| **Going (ex-Scott's Cheap Flights)** | App/email only; **no public API/RSS**; affiliate program exists but not a deal feed | No | Free tier exists but not machine-readable; paid Premium | High to scrape app | **Low** — US-origin focus, no HKG departures | High |
| **Jack's Flight Club** | Email/app + members site (login) | No public feed | Paid membership | High to scrape | **Low** — US/UK/EU departures only, **no HKG origin** | High |
| **HolidayPirates / Travel Pirates** | Site + app; some country RSS historically, mostly EU markets | Partial | $0 if RSS exists | Med | **Low** — EU-origin | Med |
| **X/Twitter @SecretFlying @TheFlightDeal @airfarewatchdog** | Nitter (dead); X API pay-per-use ($0.005/read, no free tier, Feb 2026); RSS.app/RSSHub bridge needs session cookie, fragile | Semi | API: metered, easily $tens/mo at useful volume; bridges $0 but brittle | **High** — API ToS for scraping/bridges; account-ban risk | Med (mirror of the sites above; little *unique* HKG signal) | High |
| **Little Steps Asia** `littlestepsasia.com/hong-kong/…` | HTML scrape (Playwright/httpx) or check for `/feed/`; family-travel site | Likely WP RSS | $0 | Low-Med | **Med** — genuinely **HKG-origin** (Cathay / HK Express new routes & promos) | Med (HKG-origin confirmed; feed not yet probed) |
| **HK FB flight-deal groups** (Flyday.hk, Flyagain.la, 又飛啦) | FB has no public-page API → **Apify or half-manual** (Phase 6) | No | Apify ~$30–50/mo, or $0 manual | **High** (FB ToS) | **High** — local, ex-HKG, Cantonese | Med |
| **WhatsApp / LINE HK deal channels** | No API for public broadcast; manual or unofficial bridge | No | $0 manual | High | **High** — Secret Flying's *error-fare* tier is now WhatsApp-only; Flyday.hk pushes WhatsApp | Med |
| **Xiaohongshu (小紅书)** (Phase 5) | MediaCrawler + cookie login (already planned) | Semi | $0 (self-host) | **High** (no public API, cookie scraping) | **High** — big 大陸/HK bug-fare community | Med |

### A.3 Reading of Track A

1. **No cheap new RSS URL meaningfully raises HKG signal.** The plain-HTTP feeds that work (theflightdeal, fly4free) are already wired and are EU/US-skewed. The high-value brands (Secret Flying, FlyerTalk) are Cloudflare-walled.
2. **The realistic external upgrade is one capability, not many URLs:** route the two or three Cloudflare-gated feeds through the **Playwright `BrowserFetcher` we already maintain** for Google Flights. `feeds.py` currently only has an `httpx` path; add a browser fallback when a fetch returns a CF challenge page. This unlocks Secret Flying + FlyerTalk Premium/Mileage at $0, low incremental code. (ToS: grey — keep volume tiny, cadence slow, respect `robots`; we only read, never republish wholesale, and we link back to source.)
3. **Genuinely HKG-origin external signal lives on local channels** (HK FB groups, WhatsApp/LINE, Xiaohongshu) — exactly the Phase 5/6 backlog. Those are higher ToS-risk and need Apify/MediaCrawler/manual, so they stay later-phase.
4. **Twitter is not worth building** in 2026: it's a *mirror* of the sites we can already read, with no free path and high ban risk.

---

# TRACK B — Detect mispricing from OUR OWN price data (recommended, build first)

We already scan ~171 routes × 7 months/day. That daily stream is a **price time series we are currently throwing away**. Mining it turns the scanner itself into an error-fare radar with **no scraping and no ToS exposure** — the cleanest new signal available.

### B.0 Prerequisite — we must START keeping history (current blocker)

`db.push_cheap_flights` upserts `cheap_flights` on key `(origin, destination, month)` (`schema.sql:29`), so **every daily run overwrites the prior price — there is no history to baseline against.** Two fixes, both small:

- **Option 1 (recommended): append-only snapshot table.** New table, never upserted:
  ```sql
  create table if not exists price_history (
      id          bigint generated always as identity primary key,
      origin      text not null,
      destination text not null,
      month       text not null,            -- 'YYYY-MM' (the travel month, same key dimension as cheap_flights)
      depart_date date,
      return_date date,
      price_hkd   numeric not null,
      airline     text,
      seat        text default 'economy',
      scanned_on  date not null default current_date,
      constraint price_history_daily unique (origin, destination, month, scanned_on)
  );
  create index if not exists idx_ph_route_month on price_history (origin, destination, month, scanned_on);
  ```
  Write one row per route-month per day from the same `scan_*.json` `upload.py` already loads (add a `db.push_price_history(scan_doc)` mirroring `cheap_flight_rows`). Cheap, additive, keeps `cheap_flights` exactly as the website expects.
- **Option 2 (zero-DB-change bootstrap):** we already keep dated `data/scan_YYYYMMDD.json` files (e.g. `scan_20260613.full.json`). The detector can read the trailing N daily JSON files directly off disk to build a baseline before any schema change ships. Good for a first prototype; move to Option 1 for production.

> **Important data caveat:** today's scan samples only `samples_per_month` (1–4) representative depart days per month — *not* a stable fixed date. So consecutive days' "cheapest of month" can move because the sampled depart day moved, not because the fare changed. The detector must **baseline a comparable unit** (see B.2). The `--grid` mode (every-day scan) gives a much denser, fixed-date series and is the ideal input where available.

### B.1 What is actually detectable from our data (vs not)

Classic mistake-fare signatures and whether our scan can see them:

| Signature | Detectable from our data? | How |
|---|---|---|
| **Sudden brand-new low** (price craters vs its own recent history) | **Yes — primary signal** | Trailing-window robust baseline per route-month (B.2) |
| **Fare far below the fuel+tax floor** | **Partially** | We don't itemize tax/fuel, but we can set a **per-route absolute floor** = historical p1, and/or a distance-based cents-per-km floor (B.4); a price below physical floor is a strong flag |
| **J/F priced at/below economy** (cabin mispricing — biggest 2025 cause) | **Yes, if we scan business** | We pass `seat` to `query_roundtrip`. Run a periodic business-class pass on long-haul routes and compare `business_price / economy_price`; ratio ≤ ~1.3 ⇒ flag. Worth adding. |
| **Odd currency / routing artifact** | **No** (single-currency HKD, GF hides routing internals) | Out of scope for self-detection; stays an external-source signal |
| **New route / partner-pricing teething** | **Indirectly** | A route appearing with abnormally low first prices = cold-start handled as "watch", not auto-flag (B.5) |

So the self-detector's bread and butter is **"sudden brand-new low vs the route's own recent baseline"**, hardened with an **absolute physical floor** and an optional **business-vs-economy ratio** check.

### B.2 The algorithm (robust, per route-month)

For each scanned price point keyed by **`(origin, destination, month, seat)`** (the unit that's comparable day-to-day):

1. **Build the trailing baseline** from `price_history` over a **trailing window W = 30 days** (configurable), excluding today's point:
   - `med` = median of window prices (robust center)
   - `MAD` = median(|price − med|) over window; **robust σ ≈ 1.4826 × MAD**
   - `p10`, `p1` = 10th / 1st percentile of window
   - `n` = number of distinct scan-days in window
2. **Compute today's deviation:**
   - **Robust z-score** `z = (today − med) / max(σ_robust, σ_floor)` where `σ_floor` = a small absolute floor (e.g. 5% of `med`) to avoid divide-by-tiny on flat routes.
   - **Percent drop** `drop = (med − today) / med`.
3. **Flag as anomaly if ALL gate conditions hold:**
   - `n ≥ N_min` (enough history; see cold-start B.5), **and**
   - `z ≤ −Z_thresh` (default **−3.5**, robust-MAD), **and**
   - `drop ≥ D_min` (default **35%** below trailing median; tune per region B.4), **and**
   - `today ≤ p10` (it's genuinely in the cheap tail), **and**
   - `today ≥ sanity_floor` (reject scrape garbage like $0/HK$1; e.g. `today ≥ max(200 HKD, 0.2 × med)`).
4. **Score → confidence (0–100)** so it slots into the existing `master.triage` gate (which keeps only `confidence ≥ 70`, `master.py:16`). A simple monotonic map:
   - `confidence = clamp( 50 + 8×(|z| − Z_thresh) + 40×(drop − D_min), 0, 100 )`
   - plus bonuses: **+15** if `today < p1` (extreme tail), **+15** if a business-class pass shows `business ≤ 1.3×economy`, **−20** if the route is in a known **seasonal-sale window** (B.3).
   - Tune constants so a clean mistake fare lands ≥ 80 and a normal seasonal dip stays < 70 (below the master gate).

> Why robust MAD + p10 (not mean/stdev): airfare distributions are skewed and sale-spiky; a single promo day would inflate a mean/σ and hide the next real anomaly. Median/MAD/percentiles resist that.

### B.3 False positives — legit seasonal sale vs true mistake fare

The hard part. Mitigations, layered:

- **Magnitude split.** Real flash sales are typically 20–40% off; genuine mistake fares are usually **50–90% off** *or* below the physical floor. Setting `D_min ≈ 35%` already filters most sales; `today < p1` and the absolute floor catch the truly broken ones.
- **Breadth check (sale vs glitch).** A *sale* moves **many routes of the same airline/region together**; a *mistake fare* is **one route/one airline, isolated**. Compute, on the same day, the fraction of that **airline's** (or region's) other routes also flagged. If a large share dipped together → it's a sale → **down-weight confidence** (subtract, or route to a low-priority "sale" bucket, not the error-fare alert).
- **Persistence/half-life.** Mistake fares die in minutes–hours; sales persist for days. Our daily cadence can't see the minutes, but **a flag that's still abnormal on the *next* daily scan is more likely a real sale** (or a durable price drop), whereas a one-day spike that's gone next day is the classic mistake-fare shape. Use as a *posterior* label, not a pre-filter (we still want to alert fast on day 1).
- **Holiday calendar.** Maintain a small per-region seasonal/holiday list (CNY, Golden Week, summer) and apply the `−20` confidence penalty inside those windows so predictable cheap periods don't spam.
- **Let the existing Sonnet `master` be the final FP filter** (B.6) — it re-queries the live price and judges live/dead/unverified. A self-detected candidate that's a mundane sale will simply verify as a normal price and Sonnet marks it accordingly; the statistical layer only needs to be good enough to keep the master's LLM volume sane.

### B.4 Per-region / per-distance calibration

One global threshold misfires: short-haul (HKG–TPE) is cheap and volatile in %, long-haul (HKG–JFK) is dear and steadier.

- **Calibrate `D_min` and `Z_thresh` per `region`** (the `region` field already exists on every route — `routes.yaml`, `cheap_flights.region`). Suggested starting points: short-haul Asia `D_min ≈ 45%` (noisier), long-haul `D_min ≈ 30%` (a 30%-off long-haul is already remarkable).
- **Distance/duration-aware physical floor.** We capture `duration` per result (`scanner.py:514`). Derive a crude **cents-per-minute (or per-km) floor per region** from historical p1; a fare implying an implausibly low rate is a strong independent flag (proxy for "below fuel+tax floor").
- **Per-airline baseline option.** If an airline tag is stable, baseline `(origin,destination,month,airline)` so a single ULCC's structurally-low fares don't drag the route median and mask a legacy carrier's mistake.

### B.5 Cold-start (little/no history)

- `n < N_min` (default **N_min = 7** scan-days): **do NOT auto-flag.** Emit a low-confidence "watch" only; let history accumulate. This directly prevents new routes / first-ever scans from firing false anomalies (the "new route teething" case becomes a watch, not an alert).
- **Backfill from disk.** Bootstrap the first baselines from existing dated `data/scan_*.json` files (Option 2 in B.0) so we're not blind for the first month.
- **Regional prior as fallback.** Until a route has its own `N_min` history, compare against a **pooled regional baseline** (median of all routes in that region/distance band) with a *stricter* threshold (e.g. require `drop ≥ 55%`), so we can still catch an egregious mistake on a thin-history route without crying wolf.
- **Seat cold-start.** Business-class history will be sparse (we mostly scan economy); treat the business-vs-economy *ratio* check as a bonus signal, never a sole trigger.

### B.6 Handoff to the EXISTING Sonnet `master` verifier (no new verify code)

The detector's only job is to emit candidate dicts in **exactly the scout-candidate shape** so the rest of the pipeline is reused unchanged. The required keys (from `scout.REQUIRED`) are:
`origin, destination, depart_date, return_date, price, currency, airline, source_platform, source_url, confidence` (+ `reason`).

Mapping from a flagged scan point:
```python
candidate = {
    "origin": origin, "destination": destination,
    "depart_date": depart_date, "return_date": return_date,   # from the flagged scan row / its `periods` entry
    "price": today_price, "currency": "HKD",
    "airline": airline,
    "source_platform": "self-anomaly",                         # marks provenance
    "source_url": gflights_url,                                # the GF deep link we already built (unique → good upsert key)
    "confidence": confidence_0_100,                            # from B.2 scoring
    "reason": f"price {today_price} is {drop:.0%} below trailing median {med} (z={z:.1f}, n={n})",
}
```
Then **no new verification logic is needed**:
- Feed these candidates into the same file/flow `run_master.py` reads, **or** call `master.triage([...])` → `master.verify_one(c, browser)` directly. Triage keeps `confidence ≥ 70` (the existing cost gate), and `verify_one`:
  1. `requery()` re-queries the *live* price via `scanner.query_roundtrip` (the very function the scanner uses — closes the loop: did the anomaly survive a fresh live query?),
  2. Sonnet judges **live / dead / unverified** (mistake fares usually verify **dead** within hours — expected and fine),
  3. builds Google Flights + Trip.com links,
  4. flows to `notifier.notify_verified` (Telegram) and `db.push_error_fares` (Supabase `error_fares`) — identical to RSS-sourced candidates.
- `source_platform="self-anomaly"` lets the website/notifier distinguish "our radar" from "scout sites" if desired; `source_url` = the GF deep link gives `error_fares` a unique upsert key (`schema.sql:52`).

**One subtlety:** the existing master prompt assumes a "claimed price from a post." A self-anomaly candidate's "claimed" price *is* our own scanned price, so re-query may match it (→ Sonnet says **live**) — which is actually the strongest possible signal (an abnormally-low fare we can re-confirm live). No prompt change is strictly required; optionally add one line noting some candidates are self-detected so a live match is treated as high-value rather than suspicious.

### B.7 Where this code lives (fits existing structure)

- New `anomaly.py`: pure functions `baseline(history_rows)`, `score(today, baseline, region)`, `to_candidates(scan_doc, history)`. Mirror the no-LLM, testable style of `consolidate.py`.
- New `run_anomaly.py`: load latest `scan_*.json` + trailing history (disk or `price_history`), emit `data/candidates_self_YYYYMMDD.json` in the **same schema** `run_master.py` already consumes — so `run_master.py --file data/candidates_self_*.json` verifies them with zero changes.
- Schema: add `price_history` (B.0) + `db.push_price_history`; call it from `upload.py` alongside `push_cheap_flights`.
- Tests: offline `test_anomaly.py` with synthetic series (flat → inject a −60% point → assert flagged ≥ 80; inject a −25% seasonal dip → assert < 70; thin history → assert "watch", not flagged).

---

# Prioritized recommendation (best ROI first)

| Rank | Action | Build cost | Signal / value | Risk |
|---|---|---|---|---|
| **1** | **TRACK B self-anomaly detector** — add `price_history` table + `anomaly.py`/`run_anomaly.py`, hand off to existing `master`. | **Low–Med** (pure-python + 1 table + 1 db fn; reuses entire verify/notify/db chain) | **High & unique** — turns the asset we already pay to collect into an error-fare radar; **$0 marginal, zero ToS risk**; finds HKG-origin fares the RSS sites never cover | Very low |
| 2 | **Bootstrap B from disk** (read trailing `scan_*.json`) to ship detection *before* the schema change | Very low | Lets #1 produce signal week 1 | None |
| 3 | **Add Playwright fallback to `feeds.py`** → unlock **Secret Flying** + **FlyerTalk Premium/Mileage** (the only high-value external feeds, currently CF-blocked) | Med (reuse `BrowserFetcher`; detect CF challenge → browser fetch) | Med-High — premium-cabin & global mistake fares; some ex-Asia | **Med ToS** (CF bypass) — keep low-volume, slow, link-back |
| 4 | **Add business-class periodic pass** on long-haul routes + J/F-vs-Y ratio flag (extends B) | Low–Med (scanner already takes `seat`) | Med-High — cabin mispricing was the top 2025 cause | Low |
| 5 | **Add Reddit r/awardtravel, r/churning, a few Asia subs** to `sources.yaml` | Trivial (config only) | Low-Med — mostly HKG-as-destination, noisy | Low |
| 6 | **Probe + add Little Steps Asia** (`/feed/`?) — genuine HKG-origin (Cathay/HK Express) | Low (probe feed, else light scrape) | Med (HKG-origin, but promo/route-launch, not error fares) | Low-Med |
| 7 | **Phase 5/6 as planned** — Xiaohongshu (MediaCrawler) then HK FB groups / WhatsApp-LINE (Apify/manual): the real *local* error-fare chatter | High | High HKG relevance | High ToS |
| — | **Skip Twitter/X, Going, Jack's Flight Club, Airfarewatchdog** | — | Low/none for HKG; no free machine-readable path | — |

**Bottom line:** build **TRACK B first** — it is the cheapest, lowest-risk, and only source that produces *HKG-origin* error-fare signal we don't already have, and it plugs into the existing Sonnet `master` verifier with no new verification code. The single best external add-on (Secret Flying + FlyerTalk via the browser path) is rank 3, gated behind accepting a grey-area Cloudflare bypass at low volume.

---

## Sources (confidence noted inline above)

- Live HTTP probes (browser UA, 2026-06-14): theflightdeal/fly4free `200`; secretflying.com/feed/, flyertalk forumids=740 & 372 `403 Cloudflare`; airfarewatchdog `/rss/*` `404`/SPA; fly4free Asia category `403`. [primary, high confidence]
- Code read: `scanner.query_roundtrip`/return shape (`scanner.py:234,510`), `scout.REQUIRED` (`scout.py:13`), `master.triage`/`verify_one`/`MIN_CONFIDENCE=70` (`master.py`), `db.push_cheap_flights` upsert key & `schema.sql:29,52`, `upload.py`. [primary]
- [Secret Flying — Flight Deal Alerts](https://www.secretflying.com/alerts/) and [error fares page](https://www.secretflying.com/error-fares/) — RSS exists but no origin filter; error-fare tier moved to WhatsApp Channel. [high]
- [FlyerTalk — Premium Fare Deals RSS thread](https://www.flyertalk.com/forum/technical-support-feedback/2108182-rss-feed-premium-fare-deals-broken.html) and [Mileage Run RSS thread](https://www.flyertalk.com/forum/mileage-run-discussion/1711453-rss-feed.html) — confirm `forumids=740`/`372` feed URLs. [high]
- [Nitter status report 2026](https://blog.thefix.it.com/is-nitter-still-working-the-definitive-2026-status-report/) and [Nitter — Wikipedia](https://en.wikipedia.org/wiki/Nitter) — discontinued Feb 2024, public instances collapsed. [high]
- [X (Twitter) API cost 2026](https://twitterapi.io/blog/x-api-cost-breakdown-2026) and [X API pay-per-use, Feb 2026](https://www.wearefounders.uk/the-x-api-price-hike-a-blow-to-indie-hackers/) — pay-per-use default, no free tier, ~$0.005/read. [high]
- [RSS.app Twitter feeds](https://help.rss.app/en/articles/10628517-how-to-create-rss-feeds-from-x-formerly-twitter) and [RSSHub Twitter needs session — HN](https://news.ycombinator.com/item?id=42731782) — bridges require login cookie, brittle. [high]
- [Going (company) — Wikipedia](https://en.wikipedia.org/wiki/Going_(company)) and [Scott's Cheap Flights affiliate (Travelpayouts)](https://www.travelpayouts.com/blog/scotts-cheap-flights-affiliate-program/) — app/email only, no public deal API; US-origin focus. [high]
- [Jack's Flight Club — Wikipedia](https://en.wikipedia.org/wiki/Jack's_Flight_Club) and [members site](https://members.jacksflightclub.com/flights) — US/UK/EU departures, paywalled, no HKG origin. [high]
- [Airfarewatchdog RSS blog (legacy)](https://www.airfarewatchdog.com/blog/3801823/airfarewatchdog-feeds-for-rss/) vs current [SPA/signup](https://www.airfarewatchdog.com/signup) — RSS retired, now paywalled SPA. [high]
- [Little Steps Asia — HK flights/deals](https://www.littlestepsasia.com/hong-kong/play/staycations-and-travel/hong-kong-news-deals-flights/) — HKG-origin (Cathay/HK Express) family-travel content. [med]
- Mistake-fare signatures (cabin mispricing as leading 2025 cause; non-US carriers; <50% of normal; minutes-to-hours lifetime): consolidated from `sources.yaml` `filters.signals` (project's own 2025 empirical notes) + Secret Flying error-fare guidance. [med]
