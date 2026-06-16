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
        // 圓形;選中 = 綠色發光(綠填充 + 綠光暈 + 綠邊),唔用 ✓
        "px-3 py-1.5 rounded-full text-sm font-medium border transition " +
        (active
          ? "bg-emerald-500 border-emerald-300 text-white shadow-[0_0_12px_2px_rgba(16,185,129,0.7)]"
          : "bg-white/5 border-white/25 text-white/80 hover:bg-white/10 hover:border-white/45")
      }
    >
      {children}
    </button>
  );
}

// 一行 = 固定闊度 label 欄 + 右邊獨立 wrap 區。
// label 同 chip 分欄,chip 換行時喺自己個區 wrap(對齊第一個 chip 下面),
// 唔會 wrap 返 label 底下 → 7–12日、預算輸入框全部左邊對齊。
function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <span className="opacity-70 text-xs shrink-0 w-16 pt-1.5">{label}</span>
      <div className="flex flex-wrap gap-2 items-center flex-1 min-w-0">{children}</div>
    </div>
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
      <FilterRow label="出發地">
        {ORIGINS.map((o) => (
          <Chip
            key={o.code}
            active={origins.includes(o.code)}
            onClick={() => setOrigins(toggle(origins, o.code))}
          >
            {o.name}
          </Chip>
        ))}
      </FilterRow>

      <FilterRow label="洲份">
        {CONTINENTS.map((c) => (
          <Chip
            key={c}
            active={continents.includes(c)}
            onClick={() => setContinents(toggle(continents, c))}
          >
            {c}
          </Chip>
        ))}
      </FilterRow>

      {dayOptions.length > 0 && (
        <FilterRow label="行程日數">
          {dayOptions.map((d) => (
            <Chip
              key={d}
              active={days.includes(d)}
              onClick={() => setDays(toggle(days, d))}
            >
              {d}日
            </Chip>
          ))}
        </FilterRow>
      )}

      <FilterRow label="預算上限">
        <input
          type="number"
          inputMode="numeric"
          placeholder="例:2000 HKD"
          value={maxPrice ?? ""}
          onChange={(e) => setMaxPrice(e.target.value ? Number(e.target.value) : undefined)}
          className="filter-input w-28"
          aria-label="預算上限 (HKD)"
        />
        <button type="button" onClick={onReset} className="filter-reset">
          重設
        </button>
      </FilterRow>
    </div>
  );
}
