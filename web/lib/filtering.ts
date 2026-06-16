import type { CheapFlight, Period } from "@/lib/types";
import { type Continent } from "@/lib/continents";
import { flatPeriods, stayDays } from "@/lib/card-helpers";

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

// 一個 route(某出發地)喺 selectedDays 之下嘅最平價:只計行程日數符合(空 = 全部)、
// 而且有價嘅 period。冇符合 → Infinity(代表呢個 route 喺呢個 days filter 下冇嘢顯示)。
// 用佢令 headline 價 / 排序 / 預算 / 顯示與否 全部跟 days filter 一致(唔會出現 advertised
// 價係一個冇顯示嘅行程日數,或者空 section)。
export function minForDays(flights: CheapFlight[], selectedDays: number[]): number {
  const all = flatPeriods(flights);
  const matching =
    selectedDays.length === 0
      ? all
      : all.filter((x) => {
          const d = stayDays(x.p);
          return d != null && selectedDays.includes(d);
        });
  const prices = matching.map((x) => x.p.price ?? Infinity).filter((p) => p < Infinity);
  return prices.length ? Math.min(...prices) : Infinity;
}

// client 用:套所有 filter(origins/continents/days/maxPrice),回篩後 + 價升序。
// days/budget/排序 全部用 day-aware 最平價(minForDays),冇符合日數嘅 route 直接隱藏。
export function applyFilters(
  groups: DealGroup[],
  f: { origins: string[]; continents: string[]; days: number[]; maxPrice?: number }
): DealGroup[] {
  return groups
    .filter((g) => f.origins.length === 0 || f.origins.includes(g.origin))
    .filter((g) => f.continents.length === 0 || f.continents.includes(g.continent))
    .map((g) => ({ g, m: minForDays(g.flights, f.days) }))
    .filter((x) => isFinite(x.m)) // 有符合日數 + 有價嘅 period 先顯示
    .filter((x) => !f.maxPrice || x.m <= f.maxPrice!) // 預算對 day-aware 最平
    .sort((a, b) => a.m - b.m)
    .map((x) => x.g);
}

// 多出發地比價:把 origin×destination 嘅 DealGroup[] 收成「每個目的地一組」,
// 組內每個出發地一行(最平出發地排頭),目的地之間按最平價排序。
export interface OriginEntry {
  origin: string;
  flights: CheapFlight[];
  min: number;
}
export interface DestCompareGroup {
  destination: string;
  continent: Continent;
  origins: OriginEntry[];
  min: number;
}

export function groupByDestination(
  groups: DealGroup[],
  selectedDays: number[] = []
): DestCompareGroup[] {
  const byDest = new Map<string, DestCompareGroup>();
  for (const g of groups) {
    const m = minForDays(g.flights, selectedDays); // day-aware 最平價
    if (!isFinite(m)) continue; // 冇符合日數嘅 priced period → 唔顯示呢個出發地(避免空 section)
    let d = byDest.get(g.destination);
    if (!d) {
      d = { destination: g.destination, continent: g.continent, origins: [], min: Infinity };
      byDest.set(g.destination, d);
    }
    d.origins.push({ origin: g.origin, flights: g.flights, min: m });
    d.min = Math.min(d.min, m);
  }
  const out = [...byDest.values()];
  for (const d of out) d.origins.sort((a, b) => a.min - b.min); // 最平出發地排頭
  out.sort((a, b) => a.min - b.min); // 目的地由平到貴
  return out;
}

// Masonry:把 items 輪流分入 n 欄(item i → 欄 i%n),欄內保持原順序。
// → 最平兩張並排喺頂、左右行排序;每欄獨立 stack,撳開一張只長嗰欄,零留白。
export function splitColumns<T>(items: T[], n: number): T[][] {
  const cols: T[][] = Array.from({ length: Math.max(1, n) }, () => []);
  items.forEach((it, i) => cols[i % cols.length].push(it));
  return cols;
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
