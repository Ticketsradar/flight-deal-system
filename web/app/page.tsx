import { getErrorFares, getCheapFlights, getMeta } from "@/lib/data";
import BackgroundSlideshow from "@/components/BackgroundSlideshow";
import Header from "@/components/Header";
import ErrorFareCard from "@/components/ErrorFareCard";
import CheapFlightCard from "@/components/CheapFlightCard";
import Disclaimer from "@/components/Disclaimer";

// 每次 request 即時讀 Supabase(資料每日更新,要新鮮)
export const dynamic = "force-dynamic";

export default async function Page() {
  const [fares, flights, meta] = await Promise.all([
    getErrorFares(),
    getCheapFlights(),
    getMeta(),
  ]);
  const topFlights = flights.slice(0, 60);

  return (
    <>
      <BackgroundSlideshow />
      <main className="max-w-5xl mx-auto px-4 pb-16">
        <Header meta={meta} />

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
              (最平 {topFlights.length} / 共 {flights.length})
            </span>
          </h2>
          {flights.length === 0 ? (
            <div className="glass rounded-xl p-4 opacity-80 text-sm">
              暫時冇掃描資料。
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {topFlights.map((f) => (
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
