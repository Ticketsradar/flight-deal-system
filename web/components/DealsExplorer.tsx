"use client";

import { useMemo, useState } from "react";
import DestinationCard from "@/components/DestinationCard";
import FilterBar from "@/components/FilterBar";
import { applyFilters, availableDays, type DealGroup } from "@/lib/filtering";

export default function DealsExplorer({ groups }: { groups: DealGroup[] }) {
  const [origins, setOrigins] = useState<string[]>([]);
  const [continents, setContinents] = useState<string[]>([]);
  const [days, setDays] = useState<number[]>([]);
  const [maxPrice, setMaxPrice] = useState<number | undefined>(undefined);

  const dayOptions = useMemo(() => availableDays(groups), [groups]);
  const shown = useMemo(
    () => applyFilters(groups, { origins, continents, days, maxPrice }),
    [groups, origins, continents, days, maxPrice]
  );

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
        // 兩欄 grid(左右行排序);撳開一張卡會佔成行(見 globals.css .deals-grid),零留白
        <div className="grid gap-3 sm:grid-cols-2 items-start deals-grid">
          {shown.map((g) => (
            <DestinationCard
              key={`${g.origin}-${g.destination}`}
              origin={g.origin}
              destination={g.destination}
              flights={g.flights}
              selectedDays={days}
            />
          ))}
        </div>
      )}
    </>
  );
}
