import type { CheapFlight, Period } from "@/lib/types";
import { type Continent } from "@/lib/continents";

export const STALE_DAYS = 2; // 數據舊過咁多日就當過時,隱藏。每日 cron → 健康 route ≤1 日;≥2 日 = 連續幾晚失敗(可調)

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

// client 用:套所有 filter(origins/continents/days/maxPrice),回篩後 + 價升序
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
