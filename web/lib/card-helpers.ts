// 卡片共用嘅純計算(DestinationCard + CompareCard + MonthGrid 共享)
import type { CheapFlight, Period } from "@/lib/types";

export function stayDays(p: Period): number | null {
  if (p.days != null) return p.days;
  if (!p.depart || !p.return) return null;
  return Math.round(
    (new Date(p.return).getTime() - new Date(p.depart).getTime()) / 86400000
  );
}

// 把一個目的地(某出發地)嘅 flights 攤平做 {month, period} list。
// 冇 periods 嘅 fallback:用該月單一最平價(legacy 欄位)砌一個 period。
export function flatPeriods(flights: CheapFlight[]): { month: string; p: Period }[] {
  const all: { month: string; p: Period }[] = [];
  for (const f of flights) {
    const ps =
      f.periods && f.periods.length
        ? f.periods
        : [
            {
              depart: f.depart_date,
              return: f.return_date,
              price: f.price_hkd,
              airline: f.airline,
              google_flights: f.gflights_url,
            },
          ];
    for (const p of ps) all.push({ month: f.month ?? "", p });
  }
  return all;
}

export interface CardStats {
  min: number;
  cheapCount: number;
  stayRange: string | null;
  lastScan: string | null;
}

export function cardStats(flights: CheapFlight[]): CardStats {
  const all = flatPeriods(flights);
  const prices = all.map((x) => x.p.price ?? Infinity).filter((p) => p < Infinity);
  const min = prices.length ? Math.min(...prices) : 0;
  const cheapCount = all.filter((x) => (x.p.price ?? Infinity) <= min * 1.04).length;
  const allDays = all.map((x) => stayDays(x.p)).filter((d): d is number => d != null);
  const minStay = allDays.length ? Math.min(...allDays) : null;
  const maxStay = allDays.length ? Math.max(...allDays) : null;
  const stayRange =
    minStay != null && maxStay != null
      ? minStay === maxStay
        ? `${minStay}日`
        : `${minStay}–${maxStay}日`
      : null;
  const lastScan =
    flights
      .map((f) => f.scanned_at)
      .filter(Boolean)
      .sort()
      .at(-1) ?? null;
  return { min, cheapCount, stayRange, lastScan };
}
