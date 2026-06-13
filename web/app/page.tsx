import { getErrorFares, getCheapFlights, getMeta } from "@/lib/data";
import BackgroundSlideshow from "@/components/BackgroundSlideshow";
import Header from "@/components/Header";
import Filters from "@/components/Filters";
import Heatmap from "@/components/Heatmap";
import ErrorFareCard from "@/components/ErrorFareCard";
import CheapFlightCard from "@/components/CheapFlightCard";
import TelegramCTA from "@/components/TelegramCTA";
import Disclaimer from "@/components/Disclaimer";
import type { Filters as F } from "@/lib/types";

// 每次 request 即時讀 Supabase(資料每日更新,要新鮮)
export const dynamic = "force-dynamic";

type SP = Record<string, string | string[] | undefined>;

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams; // Next.js 16:searchParams 係 Promise
  const one = (v: string | string[] | undefined) =>
    (Array.isArray(v) ? v[0] : v) || undefined;
  const current: F = {
    origin: one(sp.origin),
    region: one(sp.region),
    month: one(sp.month),
    maxPrice: one(sp.maxPrice) ? Number(one(sp.maxPrice)) : undefined,
  };

  // 熱力圖用 origin/region/budget(唔含 month),畀用戶喺 12 個月之間揀
  const baseFilters: F = {
    origin: current.origin,
    region: current.region,
    maxPrice: current.maxPrice,
  };
  const [fares, flights, meta] = await Promise.all([
    getErrorFares(),
    getCheapFlights(baseFilters),
    getMeta(),
  ]);
  const listed = (
    current.month ? flights.filter((f) => f.month === current.month) : flights
  ).slice(0, 60);

  return (
    <>
      <BackgroundSlideshow />
      <main className="max-w-5xl mx-auto px-4 pb-16">
        <Header meta={meta} />
        <div className="mb-6">
          <TelegramCTA />
        </div>

        {/* 錯價雷達(置頂主打)*/}
        <section className="mt-2">
          <h2 className="text-2xl font-bold mb-3">
            🚨 錯價雷達{" "}
            <span className="text-sm font-normal opacity-60">({fares.length})</span>
          </h2>
          {fares.length === 0 ? (
            <div className="glass rounded-xl p-4 opacity-80 text-sm">
              暫時未偵測到錯價。系統每日掃,有貨會即刻 Telegram 通知。
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {fares.map((f) => (
                <ErrorFareCard key={f.id} fare={f} />
              ))}
            </div>
          )}
        </section>

        {/* 平機票 */}
        <section className="mt-9">
          <h2 className="text-2xl font-bold mb-3">
            💸 平機票{" "}
            <span className="text-sm font-normal opacity-60">
              (顯示 {listed.length} / 符合 {flights.length})
            </span>
          </h2>

          <div className="mb-4">
            <Filters current={current} />
          </div>

          {flights.length > 0 && (
            <div className="mb-5">
              <div className="text-sm opacity-70 mb-2">📅 各月最平(撳格睇該月)</div>
              <Heatmap flights={flights} current={current} />
            </div>
          )}

          {listed.length === 0 ? (
            <div className="glass rounded-xl p-4 opacity-80 text-sm">
              冇符合條件嘅航班,試下放寬篩選。
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {listed.map((f) => (
                <CheapFlightCard key={f.id} f={f} />
              ))}
            </div>
          )}
        </section>

        <div className="mt-10">
          <Disclaimer />
        </div>
      </main>
    </>
  );
}
