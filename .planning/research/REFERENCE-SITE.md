# Reference Site Forensics — https://flight-deals-web.vercel.app

**Investigated:** 2026-06-14
**Method:** raw `curl` of HTML + `data.json` (WebFetch strips `<script>`, so curl was used for the real bytes), response-header analysis, full JSON shape inspection, host/route probing.

---

## VERDICT (confidence: HIGH)

**Prebuilt STATIC JSON, shipped as a flat file on Vercel. No live API. No backend DB. No Next.js. No external flight-data provider at runtime.**

The entire site is **one hand-written static HTML file** (10 KB) with inline vanilla JavaScript, plus **one static `data.json`** (115 KB). The page's *only* data call is:

```js
fetch("data.json").then(r=>r.json()).then(d=>{DATA=d;setup();render();})
```
— a same-origin static fetch. (`ref_index.html` line 199.)

### Evidence the data is static, not live
- **The only network references in the whole site** (grep of HTML): `fetch("data.json")` and `https://www.google.com/travel/flights` (outbound click-through deep links, not data fetches) + `/_vercel/insights/script.js` (Vercel analytics). **Zero** references to any API host, Supabase, Firebase, axios, or XMLHttpRequest. (HIGH)
- `data.json` served with `content-type: application/json`, `etag`, `last-modified: Thu, 11 Jun 2026 07:48:18 GMT`, `cache-control: public, max-age=0, must-revalidate`, `x-vercel-cache: HIT`, `age: 213343`. These are **static-asset headers**, not an API/SSR response. (HIGH)
- The HTML's `last-modified` (`07:48:13`) and `data.json`'s (`07:48:18`) are **5 seconds apart** → both were uploaded together in one deploy. Classic "regenerate file → redeploy" pipeline. (HIGH)
- `data.json` carries its own `"updated": "2026-06-11"` field, matching the deploy date. The freshness is **baked into the file at build time**, not computed live. (HIGH)

### Evidence it is NOT Next.js
- `https://flight-deals-web.vercel.app/_next/static/` → **HTTP 404**. (HIGH)
- **0** occurrences of `__NEXT_DATA__`, `/_next/`, or `self.__next_f` in the HTML. (HIGH)
- No `<script src>` to any framework bundle. The page is `<style>` + one inline `<script>`. It's plain HTML on Vercel static hosting (Vercel hosts any static site, not only Next.js). (HIGH)

### Other data files? (ruled out)
Probed `/routes.json`, `/deals.json`, `/api/data`, `/db.json`, `/index.json` → **all 404**. Only `/data.json` → 200. There is exactly one data file. (HIGH)

---

## DATA PROVIDER (confidence: MEDIUM-HIGH → Google Flights scrape, same as ours)

There is **no runtime data provider** — the data is pre-baked. The question is what produced `data.json` offline. The field shapes point to a **Google Flights scrape**, almost certainly the same `fast-flights`-style approach we already use — NOT Travelpayouts/Aviasales/Kiwi/Amadeus/Skyscanner/SerpApi.

**Fingerprint evidence:**
- The `airline` field contains **concatenated airline names with no separator**: `"Qatar AirwaysCathay Pacific"`, `"ScootSingapore Airlines"`. This is the signature of **scraping the Google Flights DOM**, where two adjacent carrier names get extracted as one string. A structured API (Travelpayouts `gate`/`airline`, Kiwi, Amadeus) returns clean **IATA carrier codes** (`QR`, `CX`) or single clean names — never run-together text. (MEDIUM-HIGH)
- The data fields are **`d` / `r` / `p` / `days`** (depart, return, price, trip-length) — a **bespoke compact schema**, not any provider's wire format. **None** of the Travelpayouts/Aviasales tell-tale fields are present (`value`, `trip_class`, `gate`, `found_at`, `distance`, `actual`, `depart_date`, `return_date`). If they used Travelpayouts, those field names would almost certainly survive into the JSON. Their absence argues **against** Travelpayouts/Aviasales. (MEDIUM)
- The click-through links point to `google.com/travel/flights` with `from HKG to {dest} on {d} through {r}` — consistent with a Google-Flights-centric workflow. (LOW as provider proof, but consistent.)
- The per-route `scraped` dates spread across **2026-06-06 … 2026-06-11** (a 5-day window) → an **incremental scraper run over several days**, batching routes, exactly like a rate-limited Google Flights scrape would behave. A paid API would let you pull everything in one shot. (MEDIUM)

**Bottom line on provider:** No paid/auth API is in use. The most likely source is a Google Flights scrape equivalent to our own `fast-flights` scanner. (MEDIUM-HIGH)

---

## HOW VARIABLE TRIP LENGTH IS ACHIEVED (confidence: HIGH) — key finding

This is the crux of the brief, and the answer **invalidates the "硬牆 / impossible" assumption in CLAUDE.md.**

### The data model
Top level: `{ updated, origin: "HKG", routes: [...] }`, **57 routes** (matches our routes.yaml basis).

Each route:
```
{ dest, name, region,
  dur,        // NOMINAL trip length for the route (e.g. 5, 6, 9, 10)
  cheap, cheapBand, med, spread, bag, airline, nCheap,
  scraped,    // date this route was scraped
  dates: [ { d, r, p, days }, ... ] }   // the per-departure-day samples
```

Each `dates[]` entry:
- `d` = departure date, `r` = return date, `p` = round-trip price, `days` = trip length.
- **`days` is exactly `r − d`** — verified **0 mismatches across all 1,929 date entries**. Trip length is simply *derived from the stored date pair*; it is not a separate query dimension. (HIGH)

So variable trip length is achieved trivially: **each departure-day sample stores whatever depart/return pair was found, and the UI renders `days` from it** (`x.days` → "11號 6日"). Different days legitimately show different trip lengths because the cheapest fare for each departure day happened to use a different return.

### CRITICAL: it is NOT a full 2–14 day matrix
The "full 2–14 days" is **marketing copy, not what the data does.** Measured reality:
- **Overall trip-length range in the data: 4 to 11 days** (not 2–14).
- Distribution: 4d×402, 5d×340, 6d×221, 7d×109, 8d×436, 9d×276, 10d×106, 11d×39.
- **Per route, only 2–3 distinct trip lengths appear** (e.g. Manila `dur=5` → days seen {4,5,6}; Osaka `dur=6` → {5,6,7}).
- **100% of all 1,929 entries have `days` within `dur ± 2`.** (HIGH)

**Interpretation of the offline scrape strategy (HIGH confidence on the *pattern*, MEDIUM on exact loop):**
For each route they pick a nominal `dur`, then for a set of candidate **departure days** they query a **small window of return offsets (`dur−2 … dur+2`, ~5 options)** and keep the cheapest. That yields ~3 distinct trip lengths per route and a believable "every day tagged with its own length" UI — **without** any 28×13 brute force and **without** any Google calendar/date-grid endpoint.

This is **directly replicable with `fast-flights` one-pair-per-query**, which is what we already have.

---

## UPDATE CADENCE (confidence: MEDIUM-HIGH)

- `data.json` field `"updated": "2026-06-11"`; HTML + JSON `last-modified` both **2026-06-11 07:48 UTC**. (HIGH)
- Per-route `scraped` dates: 2026-06-06 (13), 06-07 (20), 06-09 (4), 06-10 (2), 06-11 (18). → scraping is **spread over a multi-day window**, then a single redeploy stamps everything `updated: 2026-06-11`. (HIGH)
- At investigation time the CDN `age` was ~213,000 s (~2.5 days) with `x-vercel-cache: HIT` → the file had not changed in days. (HIGH for "not real-time"; the regular interval is unproven from one snapshot.)
- **Cannot determine the exact refresh interval (daily? weekly?) from a single observation** — would need to poll `last-modified`/`updated` over time. The mechanism is clearly **batch-scrape → regenerate `data.json` → redeploy**, NOT ISR/revalidate and NOT live. (cadence value = LOW; mechanism = HIGH)

---

## WHAT THIS MEANS FOR MY REPLICATION

1. **I already have the right architecture.** They use the *exact* model we do: offline scrape → static-ish JSON → cheap frontend. We even go further (Supabase + force-dynamic vs their flat file). **No paid API, no auth, no provider cost to match them.** (HIGH)

2. **The variable-trip-length feature is cheap and achievable now — the "硬牆" is wrong.** I do NOT need a Google date-grid/calendar endpoint, and I do NOT need a 2–14 × 28-day brute force (the ~436k/day figure in CLAUDE.md). To match the reference site I only need, per candidate departure day, **~5 `fast-flights` queries** (return offsets `dur−2…dur+2`) and keep the min. That is the `days`-varies effect. (HIGH)
   - Rough budget to mirror them: their file has **1,929 date entries** across 57 routes (~34 kept days/route). At ~5 return-offset probes per kept day that's a few thousand to low-tens-of-thousands of queries for the whole catalog per refresh — comfortably within a sliced/multi-runner GitHub Actions scan, **not** the 436k/day wall. (MEDIUM — depends how many candidate departure days we probe.)
   - Cheaper still: my existing `--grid` already finds cheap **departure** days at a fixed length. Adding a thin **return-offset inner loop (±2 days)** on the already-cheap days reproduces the variable-`days` column at a fraction of a full matrix.

3. **My `days` column = `(return − depart)`, computed, stored per sample.** Mirror their schema directly: store `{d, r, p, days}` per sample (I already store `periods`; just retain the matched return date + offset so `days` can be shown). (HIGH)

4. **Do NOT chase "full 2–14 days."** The reference site doesn't actually deliver it (real range 4–11, per-route `dur±2`). Matching their *observed* behavior (2–3 lengths/route, ±2 window) is the pragmatic, low-cost target; the brute-force full matrix remains genuinely impractical and is also unnecessary. (HIGH)

5. **Their `airline` field is dirty** (`"ScootSingapore Airlines"`), confirming a raw Google Flights scrape with no cleaning. Our pipeline can do as well or better. No reason to buy a provider for cleaner airline data unless we want it. (MEDIUM-HIGH)

### If we ever DID want a structured paid API (not required to match this site)
Not used by the reference site, but for the record: Travelpayouts/Aviasales "cheap flights cache" API is free-tier/affiliate and returns `value/trip_class/gate/found_at/...`; Kiwi Tequila and Amadeus have test tiers. **None are needed** — the reference site proves a free Google-Flights scrape is sufficient for this exact product.

---

## Files / evidence captured
- Raw HTML: `/tmp/ref_index.html` (the single-file app; data call at line 199).
- Raw data: `/tmp/ref_data.json` (115 KB, 57 routes, 1,929 date entries).
- Headers: `/tmp/ref_headers.txt`, `/tmp/ref_data_headers.txt`.

## Open / unproven
- **Exact refresh interval** (daily vs weekly): not determinable from one snapshot — mechanism is batch-redeploy, cadence value unknown. (LOW)
- **Which scraper tool** specifically (our `fast-flights` vs a custom Playwright Google Flights scraper): the dirty-concatenated-airline fingerprint says "Google Flights DOM scrape," but the exact library is not provable from the output. (MEDIUM)
