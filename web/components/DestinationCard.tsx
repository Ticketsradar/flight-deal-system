import { airportInfo } from "@/lib/airports";
import type { CheapFlight } from "@/lib/types";

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
          const p = f.price_hkd ?? 0;
          const isMin = p === min && p > 0;
          const col = priceColor(p, min, max);
          return (
            <a
              key={f.id}
              href={f.gflights_url ?? "#"}
              target="_blank"
              rel="noopener noreferrer"
              title={`${f.depart_date} → ${f.return_date}${f.airline ? " · " + f.airline : ""}`}
              className={`rounded-lg px-2 py-1.5 text-center ${isMin ? "ring-2 ring-emerald-300/80" : ""}`}
              style={{ background: "rgba(255,255,255,0.08)", borderTop: `3px solid ${col}` }}
            >
              <div className="text-[11px] opacity-70">{monthLabel(f.month)}</div>
              <div className="text-sm font-bold" style={{ color: col }}>
                {f.price_hkd ?? "—"}
              </div>
            </a>
          );
        })}
      </div>
    </details>
  );
}
