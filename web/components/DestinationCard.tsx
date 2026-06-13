import { airportInfo } from "@/lib/airports";
import type { CheapFlight, Period } from "@/lib/types";

function monthLabel(m: string | null): string {
  if (!m) return "";
  const mm = m.split("-")[1];
  return `${parseInt(mm, 10)}月`;
}

function priceColor(p: number, min: number, max: number): string {
  const t = max === min ? 0 : (p - min) / (max - min); // 0=最平,1=最貴
  return `hsl(${Math.round(140 - 140 * t)}, 68%, 50%)`;
}

// 一個目的地一張卡:預設精簡(國家/城市·代碼 + 最平月份/價),撳開先展開全部月份。
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
  const months = [...flights].sort((a, b) =>
    (a.month ?? "").localeCompare(b.month ?? ""),
  );
  const valid = flights.filter((f) => f.price_hkd != null);
  const prices = valid.map((f) => f.price_hkd as number);
  const min = prices.length ? Math.min(...prices) : 0;
  const max = prices.length ? Math.max(...prices) : 0;
  const cheapest = valid.find((f) => f.price_hkd === min);
  const cur = cheapest?.currency ?? "HKD";

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
          <div className="text-[11px] opacity-60">最平 {cheapest ? monthLabel(cheapest.month) : "—"}</div>
          <div className="text-lg font-bold text-emerald-300">
            {cur} {min || "—"}
          </div>
        </div>
        <span className="dc-caret text-sm opacity-60">▾</span>
      </summary>

      <div className="px-4 pb-4 pt-1 grid grid-cols-3 sm:grid-cols-4 gap-2">
        {months.map((f) => {
          const col = priceColor(f.price_hkd ?? 0, min, max);
          const periods: Period[] =
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
          const pmin = Math.min(...periods.map((x) => x.price ?? Infinity));
          return (
            <div
              key={f.id}
              className="rounded-lg px-2 py-1.5"
              style={{ background: "rgba(255,255,255,0.07)", borderTop: `3px solid ${col}` }}
            >
              <div className="text-[11px] opacity-70 text-center mb-1">{monthLabel(f.month)}</div>
              <div className="flex flex-col gap-0.5">
                {periods.map((pp, i) => (
                  <a
                    key={i}
                    href={pp.google_flights ?? "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={`${pp.depart} → ${pp.return}${pp.airline ? " · " + pp.airline : ""}`}
                    className="block text-center text-sm font-bold leading-tight rounded hover:bg-white/10"
                    style={{ color: pp.price === pmin ? "#34d399" : "#94a3b8" }}
                  >
                    {pp.price ?? "—"}
                  </a>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </details>
  );
}
