import { describe, it, expect } from "vitest";
import { periodDays, groupMatchesDays, STALE_DAYS, isStale, splitColumns, groupByDestination, type DealGroup } from "@/lib/filtering";
import type { Period } from "@/lib/types";

describe("groupByDestination", () => {
  const g = (origin: string, destination: string, min: number): DealGroup => ({
    origin,
    destination,
    continent: "亞洲",
    min,
    flights: [],
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
