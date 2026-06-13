# Flight-Data Sources for Variable-Trip-Length Cheapest-Price Grids

**Research date:** 2026-06-14
**Goal:** For each of ~57 destinations × ~7 forward months, show cheapest / 2nd / 3rd round-trip prices where **trip length is ANY value 2–14 days** (not fixed), with the specific **departure date + trip length** per cheap option — like Google Flights' date grid or flight-deals-web.vercel.app.
**Origins:** HKG (Hong Kong), SZX (Shenzhen), CAN (Guangzhou).

**The wall (verified in our own repo):** `fast-flights`' protobuf (`.venv/.../fast_flights/flights.proto`) has only `FlightData.date` (a single date), `Trip`, `Seat`, `Passenger`. There is **no** trip-length range, **no** calendar/month field, **no** grid. One query = one (depart, return) pair. Brute-forcing the full 28×13×7×171 grid ≈ 436k calls/day is infeasible. So we need a source that returns a **variable-trip-length monthly grid in few calls**, or a clean Plan B that offloads to Google.

---

## Comparison table

| Option | Variable trip length? | Calls per route-month | Free / cost | Auth friction | Freshness | HKG/SZX/CAN coverage | ToS / legal risk | Confidence |
|---|---|---|---|---|---|---|---|---|
| **1. Travelpayouts `month-matrix`** | **YES** — each record has independent `depart_date` + `return_date` | **1 call** = whole month, all stored depart×return combos | **Free** (affiliate token), 100 req/min | **Medium** — free signup instant, but Data API is "moderated"; no MAU floor (the 50k MAU rule is the *separate* real-time Search API) | Cached, last **48 h** of real Aviasales/Jetradar searches | Good — IATA city/country codes; Asia heavily covered by Aviasales | **Low** — official affiliate API, intended for static pages | **High** |
| **2. Amadeus Flight Cheapest Date Search** | **YES** — `viewBy=DURATION`, `duration=2,14`; each result has `departureDate`+`returnDate`+`price.total` | **1 call** = many date/duration combos for a route | **Free test tier** (~no monthly cost in test); paid in prod | **Medium** — register, get key instantly; **test env has cached/limited airport set** | Daily-refreshed cache (trending routes only) | Uncertain for HKG cache depth in **test** env; global in prod | **Low** — official API | **Medium-High** |
| **3. SearchApi.io `google_flights_calendar`** | **YES** — `outbound_date_start/end` + `return_date_start/end` → up to **200 outbound×return combos**; cells have `departure`,`return`,`price`,`is_lowest_price` | **1 call** ≈ one month grid (≤200 combos) | **Paid** — 100 free credits; Developer **$40 / 10k = $4/1k**; Production $100/35k = $3/1k | **Low** — instant key, no approval | **Live** Google Flights data (scraped) | Global (180+ countries, geo-targeting) — Google Flights is worldwide | **Medium** — 3rd-party Google scraper (Google ToS grey area, but *you* don't scrape) | **High** (capability), Medium (cost) |
| **4. SerpApi `google_flights`** | **NO** — one (depart, return) pair per search; no grid/calendar engine; "flexible dates" must be looped client-side | ~28–200 calls to fake a grid | Paid — 250 free/mo; **$25/1k → $9/1k** | Low | Live Google data | Global | Medium (Google scraper) | High (that it does NOT solve grid) |
| **5. RapidAPI Sky-Scrapper `getPriceCalendar`** | **Partial** — "cheapest fare per day across a date range" but **per-day (departure axis only)**, not depart×return; trip length not native | 1 call/month but **departure-only** | Free 100/mo; PRO paid (price undisclosed) | Low (RapidAPI key) | Live-ish Skyscanner scrape | Global | Medium-High (unofficial Skyscanner mirror, reliability varies) | Medium |
| **6. Official Skyscanner partner API** | (Browse Quotes had cheapest-per-month) | — | Partner-only | **Very High** — closed; business review + commercial agreement, weeks | — | — | Low if approved | **Closed** — not realistic |
| **7. Kiwi.com Tequila API** | **YES natively** — `nights_in_dst_from`/`nights_in_dst_to` (min/max trip length) | Few | Was free for partners | **Closed (2024)** — Kiwi dropped public API/affiliate; selected partners only | Live | Global | Low if approved | **Closed** — not realistic for new signups |
| **8. Keep `fast-flights`, reduced sampling** | Synthesized by sampling | **~hundreds–few thousand/day** (see math below) | Free | None (already built) | Live Google | Already working for HKG/SZX/CAN | Medium (we scrape Google) — same as today | Medium |
| **Plan B. Offload to Google Flights date-grid via deep link** | **YES** — Google's own grid shows variable trip length, live | **0 backend calls** | **Free** | None | Live | Global | **Low** — just a link to Google | High (link works), Medium (exact flexible-grid URL) |

---

## TOP RECOMMENDATION

### Primary: **Travelpayouts `v2/prices/month-matrix`** (+ `prices/latest` for breadth), with **Plan B Google-Flights deep links** as the always-correct escape hatch.

**Why:**
1. **It directly answers the requirement in ONE call per route-month.** `month-matrix` returns an array where **each record carries its own `depart_date` and `return_date`** — so trip length = `return_date − depart_date` is derivable per record, and records span many different lengths. That *is* a variable-trip-length monthly grid. We then group by month, derive trip-length, and pick cheapest / 2nd / 3rd. (Docs: month-matrix returns daily prices grouped by transfers for a month, with `depart_date`,`return_date`,`value`,`number_of_changes`,`trip_class`,`found_at`,`distance`,`actual`.)
2. **Free and high-volume.** Free affiliate token; **100 requests/minute per marker**. Our whole catalog = 171 routes × 7 months ≈ **1,200 calls** → ~12 min at the rate limit. Trivially fits a daily GitHub Actions cron. No per-search cost (vs SerpApi/SearchApi which would cost real money at this volume).
3. **Cached + static-friendly by design.** Travelpayouts explicitly intends this data for generating static pages — exactly our use case (we already cache scan results into Supabase and serve a `force-dynamic` Next.js site).
4. **Asia coverage is its home turf** (Aviasales/Jetradar are large in CIS + Asia; HKG/SZX/CAN are standard IATA city codes).

**Honest caveats (must verify at signup):**
- The data is the **catalogue/cache of the last 48 h of real user searches**, NOT a live quote. Coverage per route-month depends on how many real users searched it. **Popular routes (HKG→BKK/NRT/TPE/SIN) will be dense; thin/obscure routes may have sparse or stale cells.** This is the #1 thing to validate with a real token across our 171 routes.
- Access is **"moderated."** Free signup + token is instant, but Travelpayouts reserves the right to gate Data API usage; this is *not* the harsh 50k-MAU rule (that's the separate real-time **Flight Search API**). Expect to state your use case. **Verify the token actually returns data before committing.**
- Prices are indicative (check `expires_at`; don't show expired). Our UI already says "click to confirm on Google Flights," which matches this perfectly.

### Realistic #2 fallback: **SearchApi.io `google_flights_calendar`** (paid, live, Google-native).

If Travelpayouts cache turns out too sparse for our long tail, SearchApi's `google_flights_calendar` returns a **true depart×return grid (≤200 combos) of LIVE Google Flights prices in one request**, with `is_lowest_price` flags. At Developer tier ($40/mo, $4/1k): one call per route-month ≈ 1,200 calls/day ≈ **~$144/mo if run daily** (or far less if we cache 2–3 days, or only refresh popular routes daily + long tail weekly). It's the cleanest "full live grid without us scraping Google" option, and removes the anti-bot risk entirely. Use it **selectively** for routes where Travelpayouts is thin, not for all 171 daily.

> **Amadeus** is a very close #2 on *capability* (it natively does `viewBy=DURATION`, `duration=2,14`, returns `departureDate`+`returnDate`+`price`) and is **free in test** — but the test environment serves a **limited cached airport set**, so HKG/SZX/CAN depth must be verified; full coverage needs the paid production tier. Worth a 30-minute spike in parallel with Travelpayouts because the free key is instant.

---

## TOP PICK — concrete next steps

### 1. Sign up (free)
- Register at Travelpayouts (`travelpayouts.com`) → affiliate account.
- Get the Data API token: **Profile → API token**, or `https://www.travelpayouts.com/programs/100/tools/api`.
- Token goes in `.env` as e.g. `TRAVELPAYOUTS_TOKEN=...` (never commit; follow our existing `.env` rule).

### 2. The exact endpoint
```
GET https://api.travelpayouts.com/v2/prices/month-matrix
Headers: X-Access-Token: <token>        # or ?token=<token>
         Accept-Encoding: gzip, deflate  # docs strongly recommend
Query:   origin=HKG
         destination=BKK
         month=2026-07-01                # YYYY-MM-01, the month start
         currency=hkd
         show_to_affiliates=true         # true = partner prices; false = all
```
One call per (origin, destination, month). Loop our 3 origins × 57 destinations × 7 months.

### 3. Example response shape — where trip length appears
```jsonc
{
  "success": true,
  "data": [
    {
      "origin": "HKG",
      "destination": "BKK",
      "depart_date": "2026-07-03",     // <-- departure
      "return_date": "2026-07-10",     // <-- return  => trip length = 7 nights
      "value": 1480,                    // <-- price (currency as requested)
      "number_of_changes": 0,
      "trip_class": 0,                  // 0=economy
      "show_to_affiliates": true,
      "distance": 1700,
      "found_at": "2026-06-13T09:12:00",
      "actual": true
    },
    {
      "origin": "HKG", "destination": "BKK",
      "depart_date": "2026-07-05",
      "return_date": "2026-07-09",     // 4 nights — DIFFERENT trip length, same month
      "value": 1620, "number_of_changes": 1, "trip_class": 0, "actual": true
    }
    // ... many more records, each its own depart/return pair
  ],
  "error": null
}
```
**Trip-length logic for our pipeline:**
```
for rec in data:
    nights = (date(return_date) - date(depart_date)).days
    if 2 <= nights <= 14 and trip_class == 0:
        keep rec  # group by month, sort by value -> cheapest / 2nd / 3rd
```
This slots straight into our existing `scanner.py` shape (`periods` = list of cheap days per month) and `upload.py` → Supabase `cheap_flights.periods` jsonb. The deep link per record stays exactly as today (`deep_link(tfs, currency)` from the specific depart/return pair).

### 4. Validation spike (do this BEFORE rewiring the pipeline)
- Pull `month-matrix` for ~10 representative routes (HKG→BKK busy; HKG→KIX mid; SZX/CAN→some long-tail) × next 7 months.
- Measure: how many records/route-month? what spread of trip-lengths (do we actually get 2–14 coverage)? how stale is `found_at`? any empty `data`?
- **Decision gate:** if dense → adopt as primary. If long-tail routes come back near-empty → keep month-matrix for the busy routes and route the sparse ones to **SearchApi.io calendar** (paid, selective) or **Plan B deep links**.

---

## PLAN B — offload to Google Flights' own grid (always ship this regardless)

Google Flights' **Date grid** natively shows "cheapest fares for **different length trips** across different dates" (verified — depart on one axis, return on the other, variable trip length, green = cheapest, month arrows). Sending the user there gives the **complete, live, $0** 2–14-day grid on Google's side.

**What's confirmed:** we already build working Google Flights deep links via the `tfs` base64-protobuf (`scanner.py: deep_link()`, `GF_URL = https://www.google.com/travel/flights`). A `tfs` link for a route + month opens Google Flights pre-filled.

**What's uncertain (flag):** Google does **not** publicly document the URL field that force-opens the *Date-grid / flexible-dates* tab, and our prior R&D could not reliably reach Google's calendar XHR. The robust, low-risk approach is a deep link that lands the user on the route with dates pre-filled, where the **"Date grid" / "Price graph" tabs are one click away** — rather than betting on an undocumented param that auto-opens the grid. (The fully flexible "cheapest month / I don't know yet" view is also in the standard UI but is even less reliably deep-linkable.)

**Recommendation for Plan B:** add a per-destination **"See all 2–14 day combos on Google Flights →"** button that opens our existing `tfs` deep link (origin→dest, a representative date in the month). Our cards keep showing the cheap days we *did* find (from Travelpayouts/Amadeus); the button covers the full grid for free. This is the decision the previous session left open ("方案 B 未拍板") — research says it's sound and cheap; just don't promise an auto-opened grid tab.

---

## Options we can rule out now
- **Kiwi Tequila** — natively perfect (`nights_in_dst_from/to`) but **closed to new partners since 2024**. Not realistic.
- **Official Skyscanner partner API** — closed; weeks-long business review. Not realistic.
- **SerpApi `google_flights`** — no grid/calendar engine; would need ~28+ looped searches per route-month at $9–25/1k = far too expensive and doesn't beat fast-flights. (SerpApi's roadmap issue #2216 for `tfs` support is still open.)

## Sampling math if we stayed on `fast-flights` (Option 7, fallback-of-fallback)
Full grid = 28 depart × 13 lengths × 7 months × 171 routes ≈ 436k/day = infeasible.
Reduced: trip lengths {3,5,7,10,14} (5) × weekend-anchored depart days (~8/month) × 7 months × 171 = **~48k/day**. Still heavy and quality is patchy (you miss the true min between sampled lengths). 2-stage coarse→refine (coarse months first, refine only the cheapest month/length) gets it to low-thousands/day but adds a lot of code and still relies on scraping Google. **Only pursue if every API option fails** — and even then, Plan B deep links are a better use of effort.

---

## Sources (verified against current web / official docs / our repo)
- Travelpayouts Data API (endpoints, month-matrix, cache 48h, token): https://support.travelpayouts.com/hc/en-us/articles/203956163-Aviasales-Data-API and https://travelpayouts.github.io/slate/ and https://travelpayouts-data-api.readthedocs.io/
- Travelpayouts rate limit (100 req/min) & moderation requirement: https://support.travelpayouts.com/hc/en-us/articles/4402565416594-API-rate-limits and https://support.travelpayouts.com/hc/en-us/articles/203956083-Requirements-for-Aviasales-data-API-access
- Amadeus Flight Cheapest Date Search (duration, viewBy, response): https://developers.amadeus.com/self-service/category/flights/api-doc/flight-cheapest-date-search and response example https://github.com/amadeus4dev/amadeus-code-examples/blob/master/flight_cheapest_date_search/v1/get/response.json ; rate limits/quota https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/api-rate-limits/
- SearchApi.io Google Flights Calendar (depart×return grid, fields, params): https://www.searchapi.io/docs/google-flights-calendar-api ; pricing https://www.searchapi.io/pricing
- SerpApi google_flights (no calendar engine, pricing): https://serpapi.com/google-flights-api and https://serpapi.com/pricing ; tfs roadmap https://github.com/serpapi/public-roadmap/issues/2216
- RapidAPI Sky-Scrapper getPriceCalendar + Skyscanner partner-closed: https://apihiver.com/blog/skyscanner-api-tutorial and https://rapidapi.com/apiheya/api/sky-scrapper
- Kiwi Tequila closed to public/affiliate (2024): https://media.kiwi.com/articles-and-interviews/better-for-business-kiwi-com-takes-a-new-approach-to-partnerships/ and https://tequila.kiwi.com/
- Google Flights Date Grid = variable trip length, native UI: https://www.going.com/guides/how-to-use-google-flights ; tfs deep-link format (base64 protobuf): our repo `scanner.py` + `fast_flights/flights.proto`

## Could not fully verify (flagged)
- Exact **per-route-month density/freshness** of Travelpayouts cache for our *specific* 171 routes (esp. SZX/CAN long-tail) — requires a live token spike. **This is the make-or-break unknown.**
- Whether **Amadeus test env** caches HKG/SZX/CAN deeply enough — needs a live test-key spike.
- Whether **SearchApi `google_flights_calendar`** bills 1 credit/request or more for the ≤200-combo response — confirm at signup (pricing page says "pay per success/ per request", not per-cell, but verify).
- A **documented** Google Flights URL param that auto-opens the *Date-grid* tab — not publicly documented; Plan B should land on the route and let the user click the grid tab rather than rely on an undocumented param.
