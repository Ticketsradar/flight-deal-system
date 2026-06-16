import { describe, it, expect } from "vitest";
import { periodDays, groupMatchesDays, STALE_DAYS, isStale, splitColumns, groupByDestination, minForDays, type DealGroup } from "@/lib/filtering";
import type { CheapFlight, Period } from "@/lib/types";

// CheapFlight with periods, for day-aware tests
const cf = (origin: string, destination: string, periods: Period[]): CheapFlight =>
  ({ id: 0, origin, destination, region: null, depart_date: null, return_date: null,
     price_hkd: null, currency: "HKD", airline: null, baggage: null, month: "2026-08",
     gflights_url: null, tripcom_url: null, periods, scanned_at: "2026-06-15T00:00:00Z" });
const per = (days: number, price: number): Period =>
  ({ depart: "2026-08-01", return: "2026-08-01", price, days });

describe("minForDays", () => {
  const flights = [cf("HKG", "NRT", [per(5, 2000), per(9, 1200)])];
  it("no day filter → cheapest of all periods", () => {
    expect(minForDays(flights, [])).toBe(1200);
  });
  it("day filter → cheapest among matching-length periods only", () => {
    expect(minForDays(flights, [5])).toBe(2000); // 9-day @1200 excluded
  });
  it("no matching length → Infinity", () => {
    expect(minForDays(flights, [7])).toBe(Infinity);
  });
});

describe("groupByDestination day-aware", () => {
  it("drops origins with no matching-day period; min reflects the filter", () => {
    const groups: DealGroup[] = [
      { origin: "HKG", destination: "NRT", continent: "亞洲", min: 1200,
        flights: [cf("HKG", "NRT", [per(5, 2000), per(9, 1200)])] },
      { origin: "SZX", destination: "NRT", continent: "亞洲", min: 1100,
        flights: [cf("SZX", "NRT", [per(9, 1100)])] }, // only 9-day
    ];
    const out = groupByDestination(groups, [5]); // want 5-day trips
    const nrt = out.find((d) => d.destination === "NRT")!;
    expect(nrt.origins.map((o) => o.origin)).toEqual(["HKG"]); // SZX dropped (no 5-day)
    expect(nrt.origins[0].min).toBe(2000); // HKG's 5-day price, not its all-periods 1200
    expect(nrt.min).toBe(2000);
  });
});

describe("groupByDestination", () => {
  const g = (origin: string, destination: string, min: number): DealGroup => ({
    origin,
    destination,
    continent: "亞洲",
    min,
    flights: [cf(origin, destination, [per(7, min)])], // min 來自 flights 嘅 period 價
  });

  it("collapses by destination; origins cheapest-first; dest groups sorted by min", () => {
    const out = groupByDestination([
      g("HKG", "NRT", 2078),
      g("SZX", "NRT", 1950),
      g("HKG", "BKK", 1587),
    ]);
    expect(out.map((d) => d.destination)).toEqual(["BKK", "NRT"]); // 1587 < 1950
    const nrt = out.find((d) => d.destination === "NRT")!;
    expect(nrt.origins.map((o) => o.origin)).toEqual(["SZX", "HKG"]); // 1950 < 2078
    expect(nrt.min).toBe(1950);
    expect(nrt.continent).toBe("亞洲");
    const bkk = out.find((d) => d.destination === "BKK")!;
    expect(bkk.origins.map((o) => o.origin)).toEqual(["HKG"]); // single origin ok
  });
});

describe("splitColumns", () => {
  it("round-robins items into n columns preserving order within each", () => {
    expect(splitColumns([0, 1, 2, 3, 4, 5], 2)).toEqual([
      [0, 2, 4],
      [1, 3, 5],
    ]);
  });
  it("n=1 returns a single column in original order", () => {
    expect(splitColumns([0, 1, 2], 1)).toEqual([[0, 1, 2]]);
  });
  it("handles items fewer than columns (empty trailing columns)", () => {
    expect(splitColumns([0], 2)).toEqual([[0], []]);
  });
});

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
