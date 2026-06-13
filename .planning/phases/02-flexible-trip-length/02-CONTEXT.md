# Phase 2: 彈性行程日數 - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Source:** Orchestrator-synthesised(基於 Phase 1 spike 拍板 + 已有 research,未行 discuss-phase)

<domain>
## Phase Boundary

為每條 route × 月,產出「彈性行程日數」嘅平價日資料:**每個平價出發日帶自己嘅行程日數(trip length)**,而唔再係全部固定一種日數。數據經現有 `upload.py` → Supabase `cheap_flights.periods` (jsonb) → 網站 `DestinationCard.tsx` 顯示。涵蓋 FLEX-01 / FLEX-02 / FLEX-03。

**關鍵現狀(planner 必知)**:
- `scanner.py` 而家 `--grid` 模式:每月掃每個出發日,但 return 永遠 = depart + 固定 `stay_nights`(routes.yaml 每條線一個值)。所以 `periods` 入面全部同一種行程日數。
- `web/components/DestinationCard.tsx` **已經**用 `stayDays(p)`(= return − depart)逐個 period 計並顯示「N號 M日」+ 價,仲有每月按價分層(`priceTier`,綠/青/黃,灰色已隱藏)。**即係 UI 已經支援可變行程日數** —— 只要 `periods` 入面啲 period 有唔同 return,張卡自動顯示唔同日數。
- 所以呢個 phase **重心係 `scanner.py`(產出可變長度 periods)**,UI 改動極少(可選微調)。
</domain>

<decisions>
## Implementation Decisions(locked unless marked discretion)

### 數據源 / 方法(Phase 1 spike 拍板)
- **行 FALLBACK:fast-flights 自己掃 ±N 日 return-offset**(唔用 Travelpayouts;來回 cache 太疏,見 `TRAVELPAYOUTS-SPIKE.md`)。
- 做法跟參考網站(`REFERENCE-SITE.md` 證實):**每個平價出發日,試 `dur−2 … dur+2`(約 5 個)return,取最平嗰個**做嗰日嘅 period → 嗰日就帶自己嘅行程日數。範圍 clamp 落 [2,14] 日。
- **唔好做 28×13 全 brute-force**(43 萬 query 神話已破)。

### 控制 query 數量(關鍵 — 同 Phase 3 每日更新息息相關)
- ±N offset **只施加喺平價出發日**,唔係每一日。建議兩段式:先做現有 fixed-stay grid pass 揾出每月最平嗰批出發日(例如 top ~8–12 平日),再淨係喺嗰批日做 ±N return 內層。**目標:每 route-month query 數由 ~28 升到大約 ~60–70,唔好失控翻幾倍。** 具體「揀幾多個平日做 refine」「offset 闊度」= **Claude's discretion**,planner 揀合理預設並寫明。
- (可選優化,寫低但唔強制做)用 Travelpayouts month-matrix 嘅**單程**數據(免費、密、新鮮)做「平價出發日 anchor finder」代替 pass 1,進一步慳 query。`TRAVELPAYOUTS_TOKEN` 已喺 `.env`。

### 數據形狀
- 重用現有 `periods` list(每筆:`depart`/`return`/`price`/`airline`/`google_flights`)。每個平價日一筆,帶自己嘅 depart/return(= 可變長度)。
- 每月仍然按價排序,保留現有分層顯示(最平/次平/第三平;DestinationCard 已有 `priceTier`)。
- **Claude's discretion**:可選喺 `Period` 加一個顯式 `days` 欄(穩陣過靠前端計);若加,要同步 `web/lib/types.ts` + `DestinationCard.tsx`(`stayDays` fallback 照留)。
- 每筆 period 嘅 `google_flights` deep link 跟嗰個 depart+return 嘅 `tfs`(重用 `scanner.deep_link()`)。

### UI
- **`--skip-ui`**:DestinationCard 已逐 period 計並顯示行程日數 + 價 + 分層 + 撳跳 GF,基本唔使改。准許 planner 做**微調**(例如 summary 嗰句 `· {stay}日` 而家假設單一長度,可改成範圍或拿走)。
- ⚠️ `web/AGENTS.md`:「This is NOT the Next.js you know」—— 改 `web/` 任何 code 前,**先睇 `node_modules/next/dist/docs/`**,唔好靠記憶。

### Claude's Discretion
- 揀幾多個平價日做 ±N refine、offset 闊度(±2 定 ±3)、係咪加顯式 `days` 欄、pass1 vs Travelpayouts-anchor。
- 重掃策略:phase 2 可只重掃幾條 route 做 demo 驗證(唔使即刻全量重掃 171 條;全量留 Phase 3 每日更新處理)。
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 掃描引擎(主戰場)
- `scanner.py` — `scan_month()`(L460-529:grid pass + 砌 `periods`)、`query_roundtrip()`(L234-285:查一對 depart/return)、`deep_link()`、`--grid`/`SAMPLE_DAYS`/`upcoming_months`。Phase 2 主要喺度加 ±N return-offset 內層。
- `routes.yaml` — `stay_nights`(每條線基準長度,做 `dur` 中心)。

### 數據落庫 / 型別
- `upload.py` — 將最新 `scan_*.json` 嘅 `periods` 寫入 Supabase `cheap_flights`。
- `db.py` — `cheap_flight_rows()`(periods → jsonb;注意 Phase 3 會修 `scanned_at`)。
- `schema.sql` — `cheap_flights.periods jsonb` 欄已存在。

### 網站顯示(改動極少)
- `web/components/DestinationCard.tsx` — `stayDays()` L10-13、逐 period 渲染「N號 M日」+ 價 L113-136、`priceTier` 分層 L22-27。
- `web/lib/types.ts` — `Period` interface(L5-11)。
- `web/lib/data.ts` — `getCheapFlights()` 讀 `cheap_flights.*`(已 select `periods`)。
- `web/AGENTS.md` — Next.js 改動前必讀 `node_modules/next/dist/docs/`。

### Research(背景 + 拍板理由)
- `.planning/research/REFERENCE-SITE.md` — 參考網站做法 = dur±2 window(唔係真 2–14 grid)。
- `.planning/research/DATA-SOURCES.md` — sampling math、為何唔做全 brute-force。
- `.planning/research/TRAVELPAYOUTS-SPIKE.md` — Phase 1 拍板 FALLBACK 嘅證據 + 可選 anchor 優化。
</canonical_refs>

<specifics>
## Specific Ideas

- 效果目標 = 參考網站張相:同一個目的地同一個月,見到「11號 6日」「13號 4日」「23號 6日」咁,唔同出發日帶唔同行程日數,撳落去跳對應 depart+return 嘅 Google Flights。
- 驗證:跑 1–2 條 route(例如 HKG-KUL、HKG-NGO,即參考網站張相嗰兩條)行 grid + ±N,睇 `periods` 真係有 ≥2 種行程日數,再本機 `next build` + 截圖。
</specifics>

<deferred>
## Deferred Ideas

- 全量重掃 171 條 route(連 ±N)→ Phase 3(每日更新 / 增量排程)處理,唔喺 Phase 2 做。
- 用 Travelpayouts month-matrix 做 anchor 嘅優化 → 可選,唔阻 Phase 2 收貨。
- 付費 API 做硬性完整 2–14 grid → out of scope(GRID-01 / v2)。
</deferred>

---

*Phase: 02-flexible-trip-length*
*Context gathered: 2026-06-14 (orchestrator-synthesised from Phase 1 spike + research; discuss-phase skipped — design well-established by reference site)*
