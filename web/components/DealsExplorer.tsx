"use client";

import { useEffect, useMemo, useState } from "react";
import DestinationCard from "@/components/DestinationCard";
import FilterBar from "@/components/FilterBar";
import { applyFilters, availableDays, splitColumns, type DealGroup } from "@/lib/filtering";

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

export default function DealsExplorer({ groups }: { groups: DealGroup[] }) {
  const [origins, setOrigins] = useState<string[]>([]);
  const [continents, setContinents] = useState<string[]>([]);
  const [days, setDays] = useState<number[]>([]);
  const [maxPrice, setMaxPrice] = useState<number | undefined>(undefined);
  const colCount = useColumnCount();

  const dayOptions = useMemo(() => availableDays(groups), [groups]);
  const shown = useMemo(
    () => applyFilters(groups, { origins, continents, days, maxPrice }),
    [groups, origins, continents, days, maxPrice]
  );
  // masonry:輪流入欄,每欄獨立 stack → 撳開一張只長嗰欄,隔籬欄唔郁、零留白
  const columns = useMemo(() => splitColumns(shown, colCount), [shown, colCount]);

  const reset = () => {
    setOrigins([]);
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
      ) : (
        <div className="flex gap-3 items-start">
          {columns.map((col, ci) => (
            <div key={ci} className="flex-1 min-w-0 flex flex-col gap-3">
              {col.map((g) => (
                <DestinationCard
                  key={`${g.origin}-${g.destination}`}
                  origin={g.origin}
                  destination={g.destination}
                  flights={g.flights}
                  selectedDays={days}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
