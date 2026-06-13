import type { CheapFlight } from "@/lib/types";

export default function CheapFlightCard({ f }: { f: CheapFlight }) {
  const cur = f.currency ?? "HKD";
  return (
    <div className="glass-card rounded-xl p-3 flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <div className="font-semibold">
          {f.origin} <span className="opacity-50">→</span> {f.destination}
        </div>
        <div className="text-lg font-bold text-emerald-300 whitespace-nowrap">
          {cur} {f.price_hkd}
        </div>
      </div>
      <div className="text-xs opacity-75">
        {f.month} · {f.depart_date} → {f.return_date}
        {f.airline ? ` · ${f.airline}` : ""}
      </div>
      <div className="flex gap-2 text-xs mt-0.5">
        {f.gflights_url && (
          <a className="link-pill" href={f.gflights_url} target="_blank" rel="noopener noreferrer">
            Google Flights ↗
          </a>
        )}
        {f.tripcom_url && (
          <a className="link-pill" href={f.tripcom_url} target="_blank" rel="noopener noreferrer">
            Trip.com ↗
          </a>
        )}
      </div>
    </div>
  );
}
