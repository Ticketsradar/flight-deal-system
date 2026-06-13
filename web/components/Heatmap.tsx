import type { CheapFlight, Filters as F } from "@/lib/types";

// 月曆熱力圖:每個月最平價,綠(平)→紅(貴);撳格 = 篩去該月(保留其他 filter)。
export default function Heatmap({
  flights,
  current,
}: {
  flights: CheapFlight[];
  current: F;
}) {
  const byMonth = new Map<string, number>();
  for (const f of flights) {
    if (!f.month || f.price_hkd == null) continue;
    const cur = byMonth.get(f.month);
    if (cur == null || f.price_hkd < cur) byMonth.set(f.month, f.price_hkd);
  }
  const months = [...byMonth.entries()].sort(([a], [b]) => a.localeCompare(b));
  if (months.length === 0) return null;

  const prices = months.map(([, p]) => p);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const color = (p: number) => {
    const t = max === min ? 0 : (p - min) / (max - min); // 0=最平,1=最貴
    return `hsl(${Math.round(140 - 140 * t)}, 68%, 46%)`; // 140綠 → 0紅
  };

  const href = (m: string) => {
    const p = new URLSearchParams();
    if (current.origin) p.set("origin", current.origin);
    if (current.region) p.set("region", current.region);
    if (current.maxPrice) p.set("maxPrice", String(current.maxPrice));
    p.set("month", m);
    return `/?${p.toString()}`;
  };

  return (
    <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
      {months.map(([m, p]) => {
        const active = current.month === m;
        return (
          <a
            key={m}
            href={href(m)}
            className={`glass-card rounded-lg px-2 py-2 text-center ${active ? "ring-2 ring-white/70" : ""}`}
            style={{ borderTop: `3px solid ${color(p)}` }}
          >
            <div className="text-[11px] opacity-70">{m}</div>
            <div className="font-bold text-sm" style={{ color: color(p) }}>
              {p}
            </div>
          </a>
        );
      })}
    </div>
  );
}
