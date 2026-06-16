import type { CheapFlight, Period } from "@/lib/types";
import { flatPeriods, stayDays } from "@/lib/card-helpers";

function monthLabel(m: string): string {
  return m ? `${parseInt(m.split("-")[1], 10)}月` : "";
}
function dayLabel(d: string | null): string {
  return d ? `${parseInt(d.split("-")[2], 10)}號` : "?";
}

// 同一個月內,按價分層上色:最平(綠)/ 次平(青)/ 第三(黃)/ 較貴(灰,隱藏)
export const TIERS = [
  { text: "#34d399", bg: "rgba(16,185,129,0.16)", bd: "rgba(16,185,129,0.55)" },
  { text: "#5eead4", bg: "rgba(20,184,166,0.12)", bd: "rgba(20,184,166,0.42)" },
  { text: "#fcd34d", bg: "rgba(245,158,11,0.12)", bd: "rgba(245,158,11,0.4)" },
  { text: "#94a3b8", bg: "rgba(255,255,255,0.05)", bd: "rgba(255,255,255,0.12)" },
];
function priceTier(price: number, monthMin: number): number {
  if (!isFinite(monthMin) || monthMin <= 0) return 3;
  if (price <= monthMin * 1.04) return 0;
  if (price <= monthMin * 1.12) return 1;
  if (price <= monthMin * 1.22) return 2;
  return 3;
}

// 分層上色說明(每張卡頭顯示一次)
export function TierLegend() {
  return (
    <div className="text-xs opacity-70 mb-2">
      每月只列平價日:<span style={{ color: TIERS[0].text }}>綠最平</span> ·{" "}
      <span style={{ color: TIERS[1].text }}>青次平</span> ·{" "}
      <span style={{ color: TIERS[2].text }}>黃第三平</span> — 撳跳該日 Google Flights
    </div>
  );
}

// 每月平價日子掣(綠/青/黃分層,撳跳該日 Google Flights)。一個出發地一個 grid。
export default function MonthGrid({
  flights,
  selectedDays = [],
  currency,
}: {
  flights: CheapFlight[];
  selectedDays?: number[];
  currency: string;
}) {
  // 先按 selectedDays 篩 periods,然後先計每月 mMin + 分層 → 最平嗰個符合日數嘅 period
  // 一定係 tier0(顯示),唔會出現「揀咗日數但成個月畀 tier filter 隱埋」嘅空 grid。
  let all = flatPeriods(flights);
  if (selectedDays.length) {
    all = all.filter((x) => {
      const d = stayDays(x.p);
      return d != null && selectedDays.includes(d);
    });
  }
  const byMonth = new Map<string, Period[]>();
  for (const { month, p } of all) {
    const arr = byMonth.get(month) ?? [];
    arr.push(p);
    byMonth.set(month, arr);
  }
  const monthGroups = [...byMonth.entries()].sort(([a], [b]) => a.localeCompare(b));

  return (
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
              {sorted
                .filter((p) => p.price != null && priceTier(p.price, mMin) < 3)
                .map((p, i) => {
                  const c = TIERS[priceTier(p.price!, mMin)];
                  return (
                    <a
                      key={i}
                      href={p.google_flights ?? "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={`${p.depart} → ${p.return} · ${currency} ${p.price}`}
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
  );
}
