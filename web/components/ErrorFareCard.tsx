import type { ErrorFare } from "@/lib/types";

const BADGE: Record<string, { label: string; cls: string }> = {
  live: { label: "已核實 · 仲買到", cls: "bg-emerald-500/90 text-white" },
  unverified: { label: "未核實 · 自己快手查", cls: "bg-amber-400/90 text-slate-900" },
  dead: { label: "已失效", cls: "bg-slate-500/80 text-white" },
};

export default function ErrorFareCard({ fare }: { fare: ErrorFare }) {
  const b = BADGE[fare.status] ?? BADGE.unverified;
  const cur = fare.currency ?? "HKD";
  return (
    <div className="glass-card rounded-2xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <div className="text-lg font-semibold">
          {fare.origin} <span className="opacity-50">→</span> {fare.destination}
        </div>
        <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${b.cls}`}>
          {b.label}
        </span>
      </div>
      <div className="text-sm opacity-80">
        {fare.depart_date} → {fare.return_date}
        {fare.airline ? ` · ${fare.airline}` : ""}
      </div>
      <div className="flex items-baseline gap-2">
        {fare.claimed_price_hkd != null && (
          <span className="text-2xl font-bold text-amber-300">
            {cur} {fare.claimed_price_hkd}
          </span>
        )}
        {fare.verified_price_hkd != null && (
          <span className="text-xs opacity-60">
            重查 {cur} {fare.verified_price_hkd}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-2 mt-1 text-xs">
        {fare.gflights_url && (
          <a className="link-pill" href={fare.gflights_url} target="_blank" rel="noopener noreferrer">
            Google Flights ↗
          </a>
        )}
        {fare.tripcom_url && (
          <a className="link-pill" href={fare.tripcom_url} target="_blank" rel="noopener noreferrer">
            Trip.com ↗
          </a>
        )}
        {fare.source_url && (
          <a className="link-pill" href={fare.source_url} target="_blank" rel="noopener noreferrer">
            原文 ↗
          </a>
        )}
      </div>
    </div>
  );
}
