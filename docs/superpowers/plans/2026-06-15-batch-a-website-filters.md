# Batch A — Website Filters & Freshness (Frontend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the 平機票 list filterable client-side with multi-select origin + 4-continent + trip-length filters, fix the masonry blank-gap, and hide outdated data — all in `web/`.

**Architecture:** `page.tsx` loads all 3 origins from Supabase (force-dynamic, ≤2000 rows), drops stale groups, computes each destination's continent, and hands plain data to a new client component `DealsExplorer` that filters instantly in the browser. Pure logic (continent map, filter predicates) lives in tested `web/lib` modules; UI is verified via `next build` + visual screenshots.

**Tech Stack:** Next 16 (App Router, Turbopack), React 19, Tailwind v4, vitest (new, for pure-logic unit tests).

Spec: `docs/superpowers/specs/2026-06-15-website-filters-and-data-freshness-design.md`

---

### Task 1: Add vitest for pure-logic unit tests

**Files:**
- Modify: `web/package.json`
- Create: `web/vitest.config.ts`

- [ ] **Step 1: Install vitest**

Run: `cd web && npm install -D vitest`
Expected: vitest added to devDependencies, no errors.

- [ ] **Step 2: Add config**

Create `web/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["lib/**/*.test.ts"],
    environment: "node",
  },
  resolve: {
    alias: { "@": new URL("./", import.meta.url).pathname },
  },
});
```

- [ ] **Step 3: Add test script**

In `web/package.json` `"scripts"`, add:

```json
"test": "vitest run"
```

- [ ] **Step 4: Verify runner works (no tests yet → exits 0 with "no test files")**

Run: `cd web && npm test`
Expected: exits 0 (or "No test files found" — acceptable; confirms vitest runs).

- [ ] **Step 5: Commit**

```bash
git add web/package.json web/package-lock.json web/vitest.config.ts
git commit -m "test(web): add vitest for pure-logic unit tests"
```

---

### Task 2: Continent mapping (TDD)

**Files:**
- Test: `web/lib/continents.test.ts`
- Create: `web/lib/continents.ts`
- Read first: `web/lib/airports.ts` (the 57 destination codes + 3 origins)

- [ ] **Step 1: Write the failing test**

Create `web/lib/continents.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { AIRPORTS } from "@/lib/airports";
import { CONTINENTS, continentOf } from "@/lib/continents";

describe("continents", () => {
  it("has exactly the 4 expected continents", () => {
    expect(CONTINENTS).toEqual(["亞洲", "歐洲", "北美洲", "大洋洲"]);
  });

  it("maps every airport in AIRPORTS to one of the 4 continents", () => {
    for (const code of Object.keys(AIRPORTS)) {
      expect(CONTINENTS).toContain(continentOf(code));
    }
  });

  it("places key edge cases correctly", () => {
    expect(continentOf("IST")).toBe("歐洲"); // 伊斯坦堡
    expect(continentOf("DXB")).toBe("亞洲"); // 杜拜
    expect(continentOf("MLE")).toBe("亞洲"); // 馬累
    expect(continentOf("NRT")).toBe("亞洲"); // 東京
    expect(continentOf("LHR")).toBe("歐洲"); // 倫敦
    expect(continentOf("JFK")).toBe("北美洲"); // 紐約
    expect(continentOf("YVR")).toBe("北美洲"); // 溫哥華
    expect(continentOf("SYD")).toBe("大洋洲"); // 悉尼
    expect(continentOf("AKL")).toBe("大洋洲"); // 奧克蘭
  });

  it("falls back to 亞洲 for unknown codes", () => {
    expect(continentOf("ZZZ")).toBe("亞洲");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run lib/continents.test.ts`
Expected: FAIL — `Cannot find module '@/lib/continents'`.

- [ ] **Step 3: Write minimal implementation**

Create `web/lib/continents.ts`:

```ts
export type Continent = "亞洲" | "歐洲" | "北美洲" | "大洋洲";

export const CONTINENTS: Continent[] = ["亞洲", "歐洲", "北美洲", "大洋洲"];

// 機場代碼 → 洲份。歐洲(含伊斯坦堡);北美洲 = 美加;大洋洲 = 澳紐;其餘(含中東杜拜/馬累)= 亞洲。
const EUROPE = new Set([
  "AMS", "ATH", "BCN", "BUD", "CDG", "CPH", "FCO", "HEL", "LHR", "LIS",
  "MAD", "MUC", "MXP", "PRG", "VIE", "ZRH", "IST",
]);
const NORTH_AMERICA = new Set(["JFK", "LAX", "SFO", "YVR"]);
const OCEANIA = new Set(["AKL", "BNE", "CHC", "MEL", "SYD"]);

export function continentOf(code: string): Continent {
  if (EUROPE.has(code)) return "歐洲";
  if (NORTH_AMERICA.has(code)) return "北美洲";
  if (OCEANIA.has(code)) return "大洋洲";
  return "亞洲"; // 日本/韓/台/中/東南亞/中東 + fallback
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run lib/continents.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add web/lib/continents.ts web/lib/continents.test.ts
git commit -m "feat(web): 4-continent mapping with tests (#3)"
```

---

### Task 3: Pure filter logic (TDD)

**Files:**
- Test: `web/lib/filtering.test.ts`
- Create: `web/lib/filtering.ts`
- Read first: `web/lib/types.ts` (CheapFlight, Period)

This module holds the pure predicates the client component uses, so they are unit-tested without React.

- [ ] **Step 1: Write the failing test**

Create `web/lib/filtering.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { periodDays, groupMatchesDays, STALE_DAYS, isStale, type DealGroup } from "@/lib/filtering";
import type { Period } from "@/lib/types";

const p = (depart: string | null, ret: string | null, days?: number | null): Period => ({
  depart, return: ret, price: 1000, days: days ?? null,
});

describe("periodDays", () => {
  it("uses explicit days when present", () => {
    expect(periodDays(p("2026-08-01", "2026-08-06", 5))).toBe(5);
  });
  it("computes from dates when days missing", () => {
    expect(periodDays(p("2026-08-01", "2026-08-06"))).toBe(5);
  });
  it("returns null when dates missing", () => {
    expect(periodDays(p(null, null))).toBeNull();
  });
});

describe("groupMatchesDays", () => {
  const group: DealGroup = {
    origin: "HKG", destination: "BKK", continent: "亞洲", min: 1000,
    flights: [{ periods: [p("2026-08-01", "2026-08-06", 5), p("2026-08-02", "2026-08-05", 3)] } as never],
  };
  it("matches when any period has a selected day-length", () => {
    expect(groupMatchesDays(group, [5])).toBe(true);
    expect(groupMatchesDays(group, [3, 9])).toBe(true);
  });
  it("does not match when no period has a selected length", () => {
    expect(groupMatchesDays(group, [7])).toBe(false);
  });
  it("matches everything when no days selected", () => {
    expect(groupMatchesDays(group, [])).toBe(true);
  });
});

describe("isStale", () => {
  const now = new Date("2026-06-15T00:00:00Z");
  it("flags data older than STALE_DAYS", () => {
    const old = new Date(now.getTime() - (STALE_DAYS + 1) * 86400000).toISOString();
    expect(isStale(old, now)).toBe(true);
  });
  it("keeps fresh data", () => {
    const fresh = new Date(now.getTime() - 1 * 86400000).toISOString();
    expect(isStale(fresh, now)).toBe(false);
  });
  it("treats null scanned_at as stale", () => {
    expect(isStale(null, now)).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run lib/filtering.test.ts`
Expected: FAIL — `Cannot find module '@/lib/filtering'`.

- [ ] **Step 3: Write minimal implementation**

Create `web/lib/filtering.ts`:

```ts
import type { CheapFlight, Period } from "@/lib/types";
import { type Continent } from "@/lib/continents";

export const STALE_DAYS = 3; // 數據舊過咁多日就當過時,隱藏(可調)

export interface DealGroup {
  origin: string;
  destination: string;
  continent: Continent;
  min: number;
  flights: CheapFlight[];
}

export function periodDays(p: Period): number | null {
  if (p.days != null) return p.days;
  if (!p.depart || !p.return) return null;
  return Math.round(
    (new Date(p.return).getTime() - new Date(p.depart).getTime()) / 86400000
  );
}

export function groupMatchesDays(g: DealGroup, days: number[]): boolean {
  if (days.length === 0) return true;
  return g.flights.some((f) =>
    (f.periods ?? []).some((p) => {
      const d = periodDays(p);
      return d != null && days.includes(d);
    })
  );
}

export function isStale(scannedAt: string | null, now: Date): boolean {
  if (!scannedAt) return true;
  const age = now.getTime() - new Date(scannedAt).getTime();
  return age > STALE_DAYS * 86400000;
}

// 用喺 client:套用所有 filter(origins/continents/days/maxPrice),回篩後 + 排序嘅 groups
export function applyFilters(
  groups: DealGroup[],
  f: { origins: string[]; continents: string[]; days: number[]; maxPrice?: number }
): DealGroup[] {
  return groups
    .filter((g) => f.origins.length === 0 || f.origins.includes(g.origin))
    .filter((g) => f.continents.length === 0 || f.continents.includes(g.continent))
    .filter((g) => !f.maxPrice || g.min <= f.maxPrice)
    .filter((g) => groupMatchesDays(g, f.days))
    .sort((a, b) => a.min - b.min);
}

// 抽出資料中所有出現過嘅行程日數(畀 days filter chips 用),升序
export function availableDays(groups: DealGroup[]): number[] {
  const s = new Set<number>();
  for (const g of groups)
    for (const fl of g.flights)
      for (const p of fl.periods ?? []) {
        const d = periodDays(p);
        if (d != null && d >= 1) s.add(d);
      }
  return [...s].sort((a, b) => a - b);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run lib/filtering.test.ts`
Expected: PASS (all describe blocks green).

- [ ] **Step 5: Commit**

```bash
git add web/lib/filtering.ts web/lib/filtering.test.ts
git commit -m "feat(web): pure filter logic (days/stale/continent) with tests (#2,#5)"
```

---

### Task 4: Load all origins + build stale-filtered groups in page.tsx

**Files:**
- Modify: `web/app/page.tsx`
- Read first: `web/lib/data.ts` (getCheapFlights signature), `web/lib/filtering.ts`, `web/lib/continents.ts`

- [ ] **Step 1: Replace single-origin load + grouping with all-origins + groups**

In `web/app/page.tsx`, replace the data-loading and grouping block (the `current`, `Promise.all`, `within7`, `regions`, `shown`, `byDest`, `groups` section, lines ~22–69) with:

```tsx
  const [allFlights, fares, meta] = await Promise.all([
    getCheapFlights({}), // 全部出發地(≤2000 行;client 端再篩)
    getErrorFares(),
    getMeta(),
  ]);

  // 只保留最近 7 個月
  const now = new Date();
  const allowedMonths = new Set<string>();
  for (let y = now.getFullYear(), mo = now.getMonth() + 1, k = 0; k < 7; k++) {
    allowedMonths.add(`${y}-${String(mo).padStart(2, "0")}`);
    if (++mo > 12) { mo = 1; y++; }
  }
  const within7 = allFlights.filter((f) => f.month && allowedMonths.has(f.month));

  // 按 (出發地, 目的地) 分組
  const byPair = new Map<string, CheapFlight[]>();
  for (const f of within7) {
    const key = `${f.origin}-${f.destination}`;
    const arr = byPair.get(key) ?? [];
    arr.push(f);
    byPair.set(key, arr);
  }

  const groups: DealGroup[] = [...byPair.values()]
    .map((fs) => ({
      origin: fs[0].origin,
      destination: fs[0].destination,
      continent: continentOf(fs[0].destination),
      min: Math.min(...fs.map((f) => f.price_hkd ?? Infinity)),
      flights: fs,
    }))
    // 隱藏過時數據:該組最新 scanned_at 舊過 STALE_DAYS 就唔顯示
    .filter((g) => {
      const freshest = g.flights
        .map((f) => f.scanned_at)
        .filter(Boolean)
        .sort()
        .at(-1) ?? null;
      return !isStale(freshest, now);
    });
```

- [ ] **Step 2: Update imports**

At the top of `web/app/page.tsx`, ensure these imports exist (add what's missing, remove `Filters` import — it's replaced by `DealsExplorer`):

```tsx
import { continentOf } from "@/lib/continents";
import { isStale, type DealGroup } from "@/lib/filtering";
import DealsExplorer from "@/components/DealsExplorer";
```

Remove `import Filters from "@/components/Filters";` and `import DestinationCard ...` (DestinationCard is now rendered inside DealsExplorer).

- [ ] **Step 3: Replace the filter + cards JSX with DealsExplorer**

Replace the `<div className="mb-4"><Filters .../></div>` block AND the `{groups.length === 0 ? ... : <div className="grid ...">{groups.map(...DestinationCard...)}</div>}` block (lines ~107–126) with:

```tsx
          <DealsExplorer groups={groups} />
```

(The `<h2>💸 平機票 ...</h2>` heading and the intro `<p>` stay. Update the count: change `({groups.length} 個目的地)` to `({groups.length} 條航線)` since groups are now origin×destination.)

- [ ] **Step 4: Verify build passes**

Run: `cd web && npm run build`
Expected: ✓ Compiled successfully, TypeScript passes, route `/` is `ƒ (Dynamic)`.

- [ ] **Step 5: Commit**

```bash
git add web/app/page.tsx
git commit -m "feat(web): load all origins + group by origin×dest + hide stale (#1-hide,#2)"
```

---

### Task 5: DealsExplorer client component

**Files:**
- Create: `web/components/DealsExplorer.tsx`
- Read first: `web/lib/filtering.ts`, `web/components/DestinationCard.tsx`, `web/components/FilterBar.tsx` (created in Task 6)

> Note: Task 6 creates `FilterBar`. Implement DealsExplorer now referencing it; build is verified at the end of Task 6.

- [ ] **Step 1: Create the component**

Create `web/components/DealsExplorer.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import DestinationCard from "@/components/DestinationCard";
import FilterBar from "@/components/FilterBar";
import { applyFilters, availableDays, type DealGroup } from "@/lib/filtering";

export default function DealsExplorer({ groups }: { groups: DealGroup[] }) {
  const [origins, setOrigins] = useState<string[]>([]);
  const [continents, setContinents] = useState<string[]>([]);
  const [days, setDays] = useState<number[]>([]);
  const [maxPrice, setMaxPrice] = useState<number | undefined>(undefined);

  const dayOptions = useMemo(() => availableDays(groups), [groups]);
  const shown = useMemo(
    () => applyFilters(groups, { origins, continents, days, maxPrice }),
    [groups, origins, continents, days, maxPrice]
  );

  const reset = () => {
    setOrigins([]); setContinents([]); setDays([]); setMaxPrice(undefined);
  };

  return (
    <>
      <div className="mb-4">
        <FilterBar
          origins={origins} setOrigins={setOrigins}
          continents={continents} setContinents={setContinents}
          days={days} setDays={setDays} dayOptions={dayOptions}
          maxPrice={maxPrice} setMaxPrice={setMaxPrice}
          onReset={reset}
        />
      </div>

      {shown.length === 0 ? (
        <div className="glass rounded-xl p-4 opacity-80 text-sm">
          冇符合條件嘅航線,試下放寬篩選。
        </div>
      ) : (
        <div className="columns-1 sm:columns-2 gap-3">
          {shown.map((g) => (
            <div key={`${g.origin}-${g.destination}`} className="mb-3 break-inside-avoid">
              <DestinationCard
                origin={g.origin}
                destination={g.destination}
                flights={g.flights}
                selectedDays={days}
              />
            </div>
          ))}
        </div>
      )}
    </>
  );
}
```

(This is also where the **#4 masonry** fix lands: `columns-1 sm:columns-2` + per-card `mb-3 break-inside-avoid`.)

- [ ] **Step 2: Commit** (build verified at end of Task 6)

```bash
git add web/components/DealsExplorer.tsx
git commit -m "feat(web): DealsExplorer client component + masonry layout (#2,#4,#5)"
```

---

### Task 6: FilterBar client component (multi-select chips)

**Files:**
- Create: `web/components/FilterBar.tsx`
- Delete: `web/components/Filters.tsx` (replaced)
- Read first: `web/lib/airports.ts` (ORIGINS), `web/lib/continents.ts` (CONTINENTS)

- [ ] **Step 1: Create the component**

Create `web/components/FilterBar.tsx`:

```tsx
"use client";

import { ORIGINS } from "@/lib/airports";
import { CONTINENTS } from "@/lib/continents";

function toggle<T>(arr: T[], v: T): T[] {
  return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
}

function Chip({ active, onClick, children }: {
  active: boolean; onClick: () => void; children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={
        "px-3 py-1 rounded-full text-sm border transition " +
        (active
          ? "bg-emerald-500/30 border-emerald-400 text-emerald-100"
          : "bg-white/5 border-white/15 text-white/80 hover:bg-white/10")
      }
    >
      {children}
    </button>
  );
}

export default function FilterBar({
  origins, setOrigins, continents, setContinents,
  days, setDays, dayOptions, maxPrice, setMaxPrice, onReset,
}: {
  origins: string[]; setOrigins: (v: string[]) => void;
  continents: string[]; setContinents: (v: string[]) => void;
  days: number[]; setDays: (v: number[]) => void; dayOptions: number[];
  maxPrice: number | undefined; setMaxPrice: (v: number | undefined) => void;
  onReset: () => void;
}) {
  return (
    <div className="glass rounded-xl p-3 flex flex-col gap-3 text-sm">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="opacity-70 text-xs w-14 shrink-0">出發地</span>
        {ORIGINS.map((o) => (
          <Chip key={o.code} active={origins.includes(o.code)}
            onClick={() => setOrigins(toggle(origins, o.code))}>{o.name}</Chip>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <span className="opacity-70 text-xs w-14 shrink-0">洲份</span>
        {CONTINENTS.map((c) => (
          <Chip key={c} active={continents.includes(c)}
            onClick={() => setContinents(toggle(continents, c))}>{c}</Chip>
        ))}
      </div>

      {dayOptions.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="opacity-70 text-xs w-14 shrink-0">行程日數</span>
          {dayOptions.map((d) => (
            <Chip key={d} active={days.includes(d)}
              onClick={() => setDays(toggle(days, d))}>{d}日</Chip>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-3 items-center">
        <label className="flex items-center gap-2">
          <span className="opacity-70 text-xs">預算上限 (HKD)</span>
          <input
            type="number" inputMode="numeric" placeholder="例:2000"
            value={maxPrice ?? ""}
            onChange={(e) => setMaxPrice(e.target.value ? Number(e.target.value) : undefined)}
            className="filter-input w-28"
          />
        </label>
        <button type="button" onClick={onReset} className="filter-reset">重設</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Delete the old Filters component**

Run: `git rm web/components/Filters.tsx`
Expected: file removed (page.tsx no longer imports it after Task 4).

- [ ] **Step 3: Verify build passes**

Run: `cd web && npm run build`
Expected: ✓ Compiled successfully, TypeScript passes. (Catches any prop-type mismatch between DealsExplorer ↔ FilterBar ↔ DestinationCard.)

- [ ] **Step 4: Commit**

```bash
git add web/components/FilterBar.tsx web/components/Filters.tsx
git commit -m "feat(web): multi-select chip FilterBar; remove old Filters (#2,#3,#5)"
```

---

### Task 7: DestinationCard — trip-length filtering of day-buttons

**Files:**
- Modify: `web/components/DestinationCard.tsx`
- Read first: `web/components/DestinationCard.tsx` (current period-button render), `web/lib/filtering.ts` (periodDays)

- [ ] **Step 1: Add the selectedDays prop**

In `web/components/DestinationCard.tsx`, change the component signature to accept `selectedDays`:

```tsx
export default function DestinationCard({
  origin,
  destination,
  flights,
  selectedDays = [],
}: {
  origin: string;
  destination: string;
  flights: CheapFlight[];
  selectedDays?: number[];
}) {
```

- [ ] **Step 2: Filter the per-month day-buttons by selected days**

In the month-group render, the existing line filters periods:

```tsx
                  {sorted
                    .filter((p) => p.price != null && priceTier(p.price, mMin) < 3)
```

Change it to also require a matching trip length when `selectedDays` is non-empty:

```tsx
                  {sorted
                    .filter((p) => p.price != null && priceTier(p.price, mMin) < 3)
                    .filter((p) => selectedDays.length === 0 || (stayDays(p) != null && selectedDays.includes(stayDays(p)!)))
```

(`stayDays(p)` is the existing helper in this file; it already returns the period's trip length or null.)

- [ ] **Step 3: Verify build passes**

Run: `cd web && npm run build`
Expected: ✓ Compiled successfully, TypeScript passes.

- [ ] **Step 4: Commit**

```bash
git add web/components/DestinationCard.tsx
git commit -m "feat(web): DestinationCard filters day-buttons by selected trip length (#5)"
```

---

### Task 8: Full verification (build + unit tests + visual)

**Files:** none (verification only)
**Read first:** `/tmp/shot.py` and `/tmp/shot2.py` (existing screenshot scripts), spec verification section.

- [ ] **Step 1: Run all unit tests**

Run: `cd web && npm test`
Expected: PASS — continents + filtering suites green.

- [ ] **Step 2: Build**

Run: `cd web && npm run build`
Expected: ✓ Compiled successfully; route `/` dynamic.

- [ ] **Step 3: Start dev server (if not running) + screenshot**

Run (background, sandbox disabled per project flow):
`cd web && npx next dev -p 3000` then `uv run python /tmp/shot.py` and `uv run python /tmp/shot2.py`.

- [ ] **Step 4: Visually confirm each spec requirement**

Read the screenshots and confirm:
- #2: 出發地 + 洲份 are multi-select chips; toggling filters instantly (no reload). Selecting 香港+深圳 shows both origins' cards.
- #3: continent chips are exactly 亞洲/歐洲/北美洲/大洋洲.
- #4: expand a card → no blank gap beside it (masonry).
- #5: select e.g. 5日 → non-matching destinations drop; remaining cards show only 5-day buttons.
- #1-hide: a known-stale route (e.g. 東京 NRT if >3 days old) is not shown.

If any fails: fix the relevant component, re-run steps 1–4.

- [ ] **Step 5: Commit any fixes, then final commit marker**

```bash
git add -A
git commit -m "test(web): verify batch A — filters, masonry, days, hide-stale" --allow-empty
```

---

## Self-Review (completed by author)

- **Spec coverage:** #2 (Tasks 5,6 multi-select chips) ✓; #3 (Task 2 continents + Task 6 chips) ✓; #4 (Task 5 masonry) ✓; #5 (Tasks 3,5,6,7 days filter both levels) ✓; #1-hide (Tasks 3,4 isStale) ✓. #1 backend refill = Batch B (separate plan). ✓
- **Placeholders:** none — all steps have concrete code/commands.
- **Type consistency:** `DealGroup` shape consistent across filtering.ts ↔ page.tsx ↔ DealsExplorer; `selectedDays` prop consistent DealsExplorer → DestinationCard; FilterBar prop names match DealsExplorer call site; `continentOf`/`CONTINENTS` consistent.

## Out of scope (this plan)
- Batch B backend refill pass (#1) — separate plan.
- Travelpayouts / SearchApi.io — rejected / deferred per spec.
- Error-fare section unchanged.
