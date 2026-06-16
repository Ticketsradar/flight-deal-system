"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import DestinationCard from "@/components/DestinationCard";
import CompareCard from "@/components/CompareCard";
import FilterBar from "@/components/FilterBar";
import { ORIGINS } from "@/lib/airports";
import {
  applyFilters,
  availableDays,
  groupByDestination,
  splitColumns,
  type DealGroup,
} from "@/lib/filtering";

// 預設 3 個出發地(香港/深圳/廣州)全開 → 預設就係合併比價 view
const ALL_ORIGINS = ORIGINS.map((o) => o.code);

// 手機 1 欄 / ≥640px 2 欄。預設 1(mobile-first:SSR + 手機唔閃,desktop 上嚟先升 2 欄)
function useColumnCount(): number {
  const [n, setN] = useState(1);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 640px)");
    const update = () => setN(mq.matches ? 2 : 1);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return n;
}

// masonry:輪流入欄,每欄獨立 stack → 撳開一張只長嗰欄,隔籬欄唔郁、零留白
function Masonry<T>({
  items,
  colCount,
  keyOf,
  children,
}: {
  items: T[];
  colCount: number;
  keyOf: (t: T) => string;
  children: (t: T) => React.ReactNode;
}) {
  const columns = splitColumns(items, colCount);
  return (
    <div className="flex gap-3 items-start">
      {columns.map((col, ci) => (
        <div key={ci} className="flex-1 min-w-0 flex flex-col gap-3">
          {col.map((it) => (
            <Fragment key={keyOf(it)}>{children(it)}</Fragment>
          ))}
        </div>
      ))}
    </div>
  );
}

export default function DealsExplorer({ groups }: { groups: DealGroup[] }) {
  const [origins, setOrigins] = useState<string[]>(ALL_ORIGINS);
  const [continents, setContinents] = useState<string[]>([]);
  const [days, setDays] = useState<number[]>([]);
  const [maxPrice, setMaxPrice] = useState<number | undefined>(undefined);
  const colCount = useColumnCount();

  const dayOptions = useMemo(() => availableDays(groups), [groups]);
  const shown = useMemo(
    () => applyFilters(groups, { origins, continents, days, maxPrice }),
    [groups, origins, continents, days, maxPrice]
  );
  // 揀咗 2+ 出發地 → 合併比價(每個目的地一張卡,各出發地一行價)
  const compareMode = origins.length >= 2;
  const destGroups = useMemo(
    () => (compareMode ? groupByDestination(shown, days) : []),
    [compareMode, shown, days]
  );

  const reset = () => {
    setOrigins(ALL_ORIGINS); // 重設 = 返預設(3 個出發地全開)
    setContinents([]);
    setDays([]);
    setMaxPrice(undefined);
  };

  return (
    <>
      <div className="mb-4">
        <FilterBar
          origins={origins}
          setOrigins={setOrigins}
          continents={continents}
          setContinents={setContinents}
          days={days}
          setDays={setDays}
          dayOptions={dayOptions}
          maxPrice={maxPrice}
          setMaxPrice={setMaxPrice}
          onReset={reset}
        />
      </div>

      {shown.length === 0 ? (
        <div className="glass rounded-xl p-4 opacity-80 text-sm">
          冇符合條件嘅航線,試下放寬篩選。
        </div>
      ) : compareMode ? (
        <Masonry items={destGroups} colCount={colCount} keyOf={(g) => g.destination}>
          {(g) => <CompareCard group={g} selectedDays={days} />}
        </Masonry>
      ) : (
        <Masonry
          items={shown}
          colCount={colCount}
          keyOf={(g) => `${g.origin}-${g.destination}`}
        >
          {(g) => (
            <DestinationCard
              origin={g.origin}
              destination={g.destination}
              flights={g.flights}
              selectedDays={days}
            />
          )}
        </Masonry>
      )}
    </>
  );
}
