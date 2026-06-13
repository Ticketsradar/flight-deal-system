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
  const a = new Date(p.depart).getTime();
  const b = new Date(p.return).getTime();
  return Math.round((b - a) / 86400000);
}

// 參考網站風格:一個目的地一張卡,展開見「平價日子」date 掣(按月分組,綠=平)。
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

  // 每個月嘅 periods 攤平做 (month, period);冇 periods 就用單一最平做 fallback
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
  const threshold = min * 1.08; // 8% 內當「平價日」
  const cheapCount = all.filter((x) => (x.p.price ?? Infinity) <= threshold).length;
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
            {cheapCount} 個平價日{stay ? ` · ${stay}日` : ""}
          </div>
        </div>
        <span className="dc-caret text-sm opacity-60">▾</span>
      </summary>

      <div className="px-4 pb-4 pt-1">
        <div className="text-xs opacity-70 mb-2">
          綠色 = 平價日子(~{cur} {min} 來回),撳跳該日 Google Flights
        </div>
        <div className="flex flex-col gap-2">
          {monthGroups.map(([month, ps]) => (
            <div key={month} className="flex items-start gap-2">
              <div className="text-xs opacity-70 w-9 shrink-0 pt-2">{monthLabel(month)}</div>
              <div className="flex flex-wrap gap-1.5">
                {ps
                  .slice()
                  .sort((a, b) => (a.depart ?? "").localeCompare(b.depart ?? ""))
                  .map((p, i) => {
                    const cheap = (p.price ?? Infinity) <= threshold;
                    return (
                      <a
                        key={i}
                        href={p.google_flights ?? "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={`${p.depart} → ${p.return} · ${cur} ${p.price}`}
                        className="px-2 py-1 rounded-lg text-center leading-tight"
                        style={{
                          background: cheap ? "rgba(16,185,129,0.14)" : "rgba(255,255,255,0.06)",
                          border: `1px solid ${cheap ? "rgba(16,185,129,0.55)" : "rgba(255,255,255,0.14)"}`,
                        }}
                      >
                        <div
                          className="text-sm font-semibold"
                          style={{ color: cheap ? "#34d399" : "#cbd5e1" }}
                        >
                          {dayLabel(p.depart)}
                        </div>
                        <div className="text-[10px]" style={{ color: cheap ? "#6ee7b7" : "#94a3b8" }}>
                          {p.price ?? "—"}
                        </div>
                      </a>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </details>
  );
}
