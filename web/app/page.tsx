import { getErrorFares, getCheapFlights, getMeta } from "@/lib/data";
import BackgroundSlideshow from "@/components/BackgroundSlideshow";
import Header from "@/components/Header";
import DealsExplorer from "@/components/DealsExplorer";
import ErrorFareCard from "@/components/ErrorFareCard";
import TelegramCTA from "@/components/TelegramCTA";
import Disclaimer from "@/components/Disclaimer";
import { continentOf } from "@/lib/continents";
import { isStale, type DealGroup } from "@/lib/filtering";
import type { CheapFlight } from "@/lib/types";

// 每次 request 即時讀 Supabase(資料每日更新,要新鮮)
export const dynamic = "force-dynamic";

export default async function Page() {
  const [allFlights, fares, meta] = await Promise.all([
    getCheapFlights({}), // 全部出發地(≤2000 行;client 端再篩)
    getErrorFares(),
    getMeta(),
  ]);

  // 只保留最近 7 個月(遠月平機票未放飛,價偏高、冇參考價值)
  const now = new Date();
  const allowedMonths = new Set<string>();
  for (let y = now.getFullYear(), mo = now.getMonth() + 1, k = 0; k < 7; k++) {
    allowedMonths.add(`${y}-${String(mo).padStart(2, "0")}`);
    if (++mo > 12) {
      mo = 1;
      y++;
    }
  }
  const within7 = allFlights.filter((f) => f.month && allowedMonths.has(f.month));

  // 按 (出發地, 目的地) 分組
  const byPair = new Map<string, CheapFlight[]>();
  for (const f of within7) {
    const key = `${f.origin}-${f.destination}`;
    const arr = byPair.get(key) ?? [];
    arr.push(f);
    byPair.set(key, arr);
  }

  // 砌 groups + 隱藏過時數據(該組最新 scanned_at 舊過 STALE_DAYS 就唔顯示)
  const groups: DealGroup[] = [...byPair.values()]
    .map((fs) => ({
      origin: fs[0].origin,
      destination: fs[0].destination,
      continent: continentOf(fs[0].destination),
      min: Math.min(...fs.map((f) => f.price_hkd ?? Infinity)),
      flights: fs,
    }))
    .filter((g) => {
      const freshest =
        g.flights
          .map((f) => f.scanned_at)
          .filter(Boolean)
          .sort()
          .at(-1) ?? null;
      return !isStale(freshest, now);
    });

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

        {/* 平機票:每條航線一張卡,撳開睇晒月份 */}
        <section className="mt-9">
          <h2 className="text-2xl font-bold mb-1">
            💸 平機票{" "}
            <span className="text-sm font-normal opacity-60">({groups.length} 條航線)</span>
          </h2>
          <p className="text-xs opacity-60 mb-3">撳目的地展開 → 睇晒每個月最平價,撳邊個月跳去嗰月 Google Flights</p>

          <DealsExplorer groups={groups} />
        </section>

        <div className="mt-10">
          <Disclaimer />
        </div>
      </main>
    </>
  );
}
