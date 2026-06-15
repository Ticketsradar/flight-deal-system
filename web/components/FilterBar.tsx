"use client";

import { ORIGINS } from "@/lib/airports";
import { CONTINENTS } from "@/lib/continents";

function toggle<T>(arr: T[], v: T): T[] {
  return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={
        "px-3 py-1 rounded-full text-sm border transition " +
        (active
          ? "bg-emerald-500/30 border-emerald-400 text-emerald-100"
          : "bg-white/5 border-white/15 text-white/80 hover:bg-white/10")
      }
    >
      {children}
    </button>
  );
}

export default function FilterBar({
  origins,
  setOrigins,
  continents,
  setContinents,
  days,
  setDays,
  dayOptions,
  maxPrice,
  setMaxPrice,
  onReset,
}: {
  origins: string[];
  setOrigins: (v: string[]) => void;
  continents: string[];
  setContinents: (v: string[]) => void;
  days: number[];
  setDays: (v: number[]) => void;
  dayOptions: number[];
  maxPrice: number | undefined;
  setMaxPrice: (v: number | undefined) => void;
  onReset: () => void;
}) {
  return (
    <div className="glass rounded-xl p-3 flex flex-col gap-3 text-sm">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="opacity-70 text-xs w-14 shrink-0">出發地</span>
        {ORIGINS.map((o) => (
          <Chip
            key={o.code}
            active={origins.includes(o.code)}
            onClick={() => setOrigins(toggle(origins, o.code))}
          >
            {o.name}
          </Chip>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <span className="opacity-70 text-xs w-14 shrink-0">洲份</span>
        {CONTINENTS.map((c) => (
          <Chip
            key={c}
            active={continents.includes(c)}
            onClick={() => setContinents(toggle(continents, c))}
          >
            {c}
          </Chip>
        ))}
      </div>

      {dayOptions.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="opacity-70 text-xs w-14 shrink-0">行程日數</span>
          {dayOptions.map((d) => (
            <Chip
              key={d}
              active={days.includes(d)}
              onClick={() => setDays(toggle(days, d))}
            >
              {d}日
            </Chip>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-3 items-center">
        <label className="flex items-center gap-2">
          <span className="opacity-70 text-xs">預算上限 (HKD)</span>
          <input
            type="number"
            inputMode="numeric"
            placeholder="例:2000"
            value={maxPrice ?? ""}
            onChange={(e) => setMaxPrice(e.target.value ? Number(e.target.value) : undefined)}
            className="filter-input w-28"
          />
        </label>
        <button type="button" onClick={onReset} className="filter-reset">
          重設
        </button>
      </div>
    </div>
  );
}
