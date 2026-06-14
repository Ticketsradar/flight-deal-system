import { supabase, supabaseConfigured } from "./supabase";
import type { CheapFlight, ErrorFare, Filters } from "./types";

const STATUS_RANK: Record<string, number> = { live: 0, unverified: 1, dead: 2 };

// 錯價:live → unverified → dead,同 status 內按 confidence 高至低
export async function getErrorFares(): Promise<ErrorFare[]> {
  if (!supabaseConfigured) return [];
  const { data, error } = await supabase.from("error_fares").select("*");
  if (error) {
    console.error("[data] error_fares:", error.message);
    return [];
  }
  return (data ?? []).sort(
    (a, b) =>
      (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9) ||
      (b.confidence ?? 0) - (a.confidence ?? 0),
  );
}

export async function getCheapFlights(filters: Filters = {}): Promise<CheapFlight[]> {
  if (!supabaseConfigured) return [];
  let q = supabase.from("cheap_flights").select("*");
  if (filters.origin) q = q.eq("origin", filters.origin);
  if (filters.region) q = q.eq("region", filters.region);
  if (filters.month) q = q.eq("month", filters.month);
  if (filters.maxPrice) q = q.lte("price_hkd", filters.maxPrice);
  const { data, error } = await q
    .order("price_hkd", { ascending: true })
    .limit(2000); // explicit limit; adjust as routes grow (Supabase default is 1000)
  if (error) {
    console.error("[data] cheap_flights:", error.message);
    return [];
  }
  if ((data?.length ?? 0) >= 1900) {
    console.warn("[data] cheap_flights result near row limit — consider pagination");
  }
  return data ?? [];
}

export async function getMeta(): Promise<Record<string, string>> {
  if (!supabaseConfigured) return {};
  const { data } = await supabase.from("meta").select("key,value");
  const m: Record<string, string> = {};
  for (const row of data ?? []) m[row.key] = row.value;
  return m;
}

// 畀篩選器用:有邊啲 origin / region / month 喺資料入面
export async function getFacets(): Promise<{
  origins: string[];
  regions: string[];
  months: string[];
}> {
  if (!supabaseConfigured) return { origins: [], regions: [], months: [] };
  const { data } = await supabase
    .from("cheap_flights")
    .select("origin,region,month");
  const origins = new Set<string>();
  const regions = new Set<string>();
  const months = new Set<string>();
  for (const r of data ?? []) {
    if (r.origin) origins.add(r.origin);
    if (r.region) regions.add(r.region);
    if (r.month) months.add(r.month);
  }
  return {
    origins: [...origins].sort(),
    regions: [...regions].sort(),
    months: [...months].sort(),
  };
}
