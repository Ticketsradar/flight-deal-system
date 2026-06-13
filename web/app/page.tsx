import { getErrorFares, getCheapFlights, getMeta } from "@/lib/data";
import BackgroundSlideshow from "@/components/BackgroundSlideshow";
import Header from "@/components/Header";
import Filters from "@/components/Filters";
import ErrorFareCard from "@/components/ErrorFareCard";
import DestinationCard from "@/components/DestinationCard";
import TelegramCTA from "@/components/TelegramCTA";
import Disclaimer from "@/components/Disclaimer";
import type { CheapFlight, Filters as F } from "@/lib/types";

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
    origin: one(sp.origin) || "HKG", // 預設香港(避開 Supabase 1000 行上限)
    region: one(sp.region),
    maxPrice: one(sp.maxPrice) ? Number(one(sp.maxPrice)) : undefined,
  };

  const [fares, originFlights, meta] = await Promise.all([
    getErrorFares(),
    getCheapFlights({ origin: current.origin }), // 淨係攞呢個出發地(<1000 行)
    getMeta(),
  ]);

  // 由資料抽地區選項
  const regions = [...new Set(originFlights.map((f) => f.region).filter(Boolean) as string[])].sort();

  // 套地區 + 預算篩選
  let shown = originFlights;
  if (current.region) shown = shown.filter((f) => f.region === current.region);
  if (current.maxPrice) shown = shown.filter((f) => (f.price_hkd ?? Infinity) <= current.maxPrice!);

  // 按目的地分組 → 照最平價排
  const byDest = new Map<string, CheapFlight[]>();
  for (const f of shown) {
    const arr = byDest.get(f.destination) ?? [];
    arr.push(f);
    byDest.set(f.destination, arr);
  }
  const groups = [...byDest.entries()]
    .map(([dest, fs]) => ({
      dest,
      fs,
      min: Math.min(...fs.map((f) => f.price_hkd ?? Infinity)),
    }))
    .sort((a, b) => a.min - b.min);

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

        {/* 平機票:每個目的地一張卡,撳開睇晒月份 */}
        <section className="mt-9">
          <h2 className="text-2xl font-bold mb-1">
            💸 平機票{" "}
            <span className="text-sm font-normal opacity-60">({groups.length} 個目的地)</span>
          </h2>
          <p className="text-xs opacity-60 mb-3">撳目的地展開 → 睇晒每個月最平價,撳邊個月跳去嗰月 Google Flights</p>

          <div className="mb-4">
            <Filters current={current} regions={regions} />
          </div>

          {groups.length === 0 ? (
            <div className="glass rounded-xl p-4 opacity-80 text-sm">
              冇符合條件嘅目的地,試下放寬篩選或者轉出發地。
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 items-start">
              {groups.map((g) => (
                <DestinationCard
                  key={g.dest}
                  origin={current.origin!}
                  destination={g.dest}
                  flights={g.fs}
                />
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
