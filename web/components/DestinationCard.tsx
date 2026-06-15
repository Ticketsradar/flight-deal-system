import { airportInfo } from "@/lib/airports";
import { freshnessLabel } from "@/lib/freshness";
import { cardStats } from "@/lib/card-helpers";
import MonthGrid, { TierLegend } from "@/components/MonthGrid";
import type { CheapFlight } from "@/lib/types";

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
  const info = airportInfo(destination);
  const oInfo = airportInfo(origin);
  const cur = flights[0]?.currency ?? "HKD";
  const { min, cheapCount, stayRange, lastScan } = cardStats(flights);

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
            {cheapCount} 個最平日{stayRange ? ` · ${stayRange}` : ""}
          </div>
          <div className="text-[10px] opacity-50">{freshnessLabel(lastScan)}</div>
        </div>
        <span className="dc-caret text-sm opacity-60">▾</span>
      </summary>

      <div className="px-4 pb-4 pt-1">
        <TierLegend />
        <MonthGrid flights={flights} selectedDays={selectedDays} currency={cur} />
      </div>
    </details>
  );
}
