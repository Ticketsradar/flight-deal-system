import { airportInfo } from "@/lib/airports";
import { freshnessLabel } from "@/lib/freshness";
import MonthGrid, { TierLegend } from "@/components/MonthGrid";
import type { DestCompareGroup } from "@/lib/filtering";

// 多出發地比價卡:一個目的地一張卡,每個出發地一行價(最平標「最平」)。
// 撳開逐個出發地分段顯示平價日子 grid。
export default function CompareCard({
  group,
  selectedDays = [],
}: {
  group: DestCompareGroup;
  selectedDays?: number[];
}) {
  const info = airportInfo(group.destination);
  const cur = group.origins[0]?.flights[0]?.currency ?? "HKD";
  const multi = group.origins.length > 1;
  const lastScan =
    group.origins
      .flatMap((o) => o.flights.map((f) => f.scanned_at))
      .filter(Boolean)
      .sort()
      .at(-1) ?? null;

  return (
    <details className="glass-card rounded-2xl overflow-hidden">
      <summary className="cursor-pointer list-none p-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl leading-none">{info.flag}</span>
          <div className="min-w-0 flex-1">
            <div className="font-semibold leading-tight">{info.country || group.destination}</div>
            <div className="text-xs opacity-70">
              {info.city} · {group.destination}
            </div>
          </div>
          <span className="dc-caret text-sm opacity-60">▾</span>
        </div>

        <div className="mt-2 flex flex-col gap-1">
          {group.origins.map((o, i) => {
            const oInfo = airportInfo(o.origin);
            const cheapest = i === 0;
            return (
              <div key={o.origin} className="flex items-center justify-between text-sm">
                <span className={cheapest ? "" : "opacity-80"}>
                  {oInfo.city}出發
                  {cheapest && multi && (
                    <span className="ml-1.5 text-[10px] text-emerald-300 border border-emerald-500/50 rounded-full px-1.5 align-middle">
                      最平
                    </span>
                  )}
                </span>
                <span className={"font-bold " + (cheapest ? "text-emerald-300" : "opacity-80")}>
                  {Number.isFinite(o.min) ? `${cur} ${o.min}` : "—"}
                </span>
              </div>
            );
          })}
        </div>
        <div className="text-[10px] opacity-50 mt-1">{freshnessLabel(lastScan)}</div>
      </summary>

      <div className="px-4 pb-4 pt-1">
        <TierLegend />
        <div className="flex flex-col gap-3">
          {group.origins.map((o) => {
            const oInfo = airportInfo(o.origin);
            return (
              <div key={o.origin}>
                <div className="text-xs font-semibold opacity-80 mb-1.5">
                  {oInfo.city}出發{Number.isFinite(o.min) ? ` · ${cur} ${o.min}` : ""}
                </div>
                <MonthGrid flights={o.flights} selectedDays={selectedDays} currency={cur} />
              </div>
            );
          })}
        </div>
      </div>
    </details>
  );
}
