// Supabase 兩張枱嘅 row 型別(對應 schema.sql)

export type FareStatus = "live" | "unverified" | "dead";

export interface Period {
  depart: string | null;
  return: string | null;
  price: number | null;
  airline?: string | null;
  google_flights?: string | null;
}

export interface CheapFlight {
  id: number;
  origin: string;
  destination: string;
  region: string | null;
  depart_date: string | null;
  return_date: string | null;
  price_hkd: number | null;
  currency: string | null;
  airline: string | null;
  baggage: string | null;
  month: string | null; // 'YYYY-MM'
  gflights_url: string | null;
  tripcom_url: string | null;
  periods: Period[] | null;
  scanned_at: string | null;
}

export interface ErrorFare {
  id: number;
  origin: string;
  destination: string;
  airline: string | null;
  depart_date: string | null;
  return_date: string | null;
  claimed_price_hkd: number | null;
  verified_price_hkd: number | null;
  currency: string | null;
  status: FareStatus;
  confidence: number | null;
  source_platform: string | null;
  source_url: string | null;
  gflights_url: string | null;
  tripcom_url: string | null;
  found_at: string | null;
  verified_at: string | null;
}

export interface Filters {
  origin?: string;
  region?: string;
  month?: string;
  maxPrice?: number;
}
