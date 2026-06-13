import { airportInfo } from "@/lib/airports";
import type { CheapFlight, Period } from "@/lib/types";

function monthLabel(m: string): string {
  return m ? `${parseInt(m.split("-")[1], 10)}月` : "";
}
function dayLabel(d: string | null): string {
  return d ? `${parseInt(d.split("-")[2], 10)}號` : "?";
}
function stayDays(p: Period): number | null {
  if (!p.depart || !p.return) return null;
  return Math.round((new Date(p.return).getTime() - new Date(p.depart).getTime()) / 86400000);
}

// 同一個月內,按價分層上色:最平(綠)/ 次平(青)/ 第三(黃)/ 較貴(灰)
const TIERS = [
  { text: "#34d399", bg: "rgba(16,185,129,0.16)", bd: "rgba(16,185,129,0.55)" },
  { text: "#5eead4", bg: "rgba(20,184,166,0.12)", bd: "rgba(20,184,166,0.42)" },
  { text: "#fcd34d", bg: "rgba(245,158,11,0.12)", bd: "rgba(245,158,11,0.4)" },
  { text: "#94a3b8", bg: "rgba(255,255,255,0.05)", bd: "rgba(255,255,255,0.12)" },
];
function priceTier(price: number, monthMin: number): number {
  if (price <= monthMin * 1.04) return 0;
  if (price <= monthMin * 1.12) return 1;
  if (price <= monthMin * 1.22) return 2;
  return 3;
}

export default function DestinationCard({
  origin,
  destination,
  flights,
}: {
  origin: string;
  destination: string;
  flights: CheapFlight[];
}) {
  const info = airportInfo(destination);
  const oInfo = airportInfo(origin);
  const cur = flights[0]?.currency ?? "HKD";

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

  const prices = all.map((x) => x.p.price ?? Infinity).filter((p) => p < Infinity);
  const min = prices.length ? Math.min(...prices) : 0;
  const cheapCount = all.filter((x) => (x.p.price ?? Infinity) <= min * 1.04).length;
  const stay = all.length ? stayDays(all[0].p) : null;

  const byMonth = new Map<string, Period[]>();
  for (const { month, p } of all) {
    const arr = byMonth.get(month) ?? [];
    arr.push(p);
    byMonth.set(month, arr);
  }
  const monthGroups = [...byMonth.entries()].sort(([a], [b]) => a.localeCompare(b));

  return (
    <details className="glass-card rounded-2xl overflow-hidden">
      <summary className="cursor-pointer list-none p-4 flex items-center gap-3">
        <span className="text-2xl leading-none">{info.flag}</span>
        <div className="min-w-0 flex-1">
          <div className="font-semibold leading-tight">{info.country || destination}</div>
          <div className="text-xs opacity-70">
            {info.city} · {destination}
            <span className="opacity-50"> · {oInfo.city}出發</span>
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-lg font-bold text-emerald-300">
            {cur} {min || "—"}
            <span className="text-[11px] font-normal opacity-60"> 來回</span>
          </div>
          <div className="text-[11px] opacity-60">
            {cheapCount} 個最平日{stay ? ` · ${stay}日` : ""}
          </div>
        </div>
        <span className="dc-caret text-sm opacity-60">▾</span>
      </summary>

      <div className="px-4 pb-4 pt-1">
        <div className="text-xs opacity-70 mb-2">
          每月按價分層:<span style={{ color: TIERS[0].text }}>綠最平</span> ·{" "}
          <span style={{ color: TIERS[1].text }}>青次平</span> ·{" "}
          <span style={{ color: TIERS[2].text }}>黃第三</span> · 灰較貴 — 撳跳該日 Google Flights
        </div>
        <div className="flex flex-col gap-2">
          {monthGroups.map(([month, ps]) => {
            const sorted = ps
              .slice()
              .sort((a, b) => (a.depart ?? "").localeCompare(b.depart ?? ""));
            const mMin = Math.min(...sorted.map((p) => p.price ?? Infinity));
            return (
              <div key={month} className="flex items-start gap-2">
                <div className="text-xs opacity-70 w-9 shrink-0 pt-2">{monthLabel(month)}</div>
                <div className="flex flex-wrap gap-1.5">
                  {sorted.map((p, i) => {
                    const c = TIERS[priceTier(p.price ?? Infinity, mMin)];
                    return (
                      <a
                        key={i}
                        href={p.google_flights ?? "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={`${p.depart} → ${p.return} · ${cur} ${p.price}`}
                        className="px-2 py-1 rounded-lg text-center leading-tight"
                        style={{ background: c.bg, border: `1px solid ${c.bd}` }}
                      >
                        <div className="text-sm font-semibold" style={{ color: c.text }}>
                          {dayLabel(p.depart)}
                          <span className="text-[10px] font-normal opacity-70">
                            {" "}
                            {stayDays(p) ?? "?"}日
                          </span>
                        </div>
                        <div className="text-[10px]" style={{ color: c.text, opacity: 0.85 }}>
                          ${p.price ?? "—"}
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </details>
  );
}
