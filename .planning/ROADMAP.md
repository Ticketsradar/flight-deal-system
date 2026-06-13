# Roadmap: Flight Deal System — Amendments Milestone

## Overview

呢個係 **brownfield amendments milestone**:後端鏈(掃描 → 篩 → 核實 → Telegram → Supabase)同 Next.js 網站都已起好(見 PROJECT.md「Validated」)。今個 milestone 做三項改進 — 彈性行程日數、可靠每日更新、自家錯價偵測 — 加一項基建(price_history)。

呢個 milestone 係 **spike-gated**:user 揀咗「先試免費 Travelpayouts API → 唔夠 fallback 自己掃 ±N」。所以 **Phase 1 係一個決策閘(spike)**,先攞 Travelpayouts token 量度真實覆蓋率,出一個明確 GO(用 Travelpayouts)定 FALLBACK(fast-flights + ±N return-offset)建議。Phase 2(彈性行程)同 Phase 3(每日更新)嘅實作路徑都 **branch on 呢個決定**。Phase 4(自家錯價偵測)基本上同數據源決定無關 — 佢食邊個 pipeline 流出嚟嘅價都得 — 但邏輯上排喺 pipeline 形狀定咗之後。

唔重新 plan 任何現有 Validated 能力。

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Travelpayouts 覆蓋率 Spike（決策閘）** - 攞免費 token 量度真實覆蓋,出 GO vs FALLBACK 數據源建議(交付一個決定 + 文檔,唔係 UI)
- [ ] **Phase 2: 彈性行程日數** - 每個平價日標明行程日數 + 來回價,按價分層,撳跳對應 depart+return 嘅 Google Flights
- [ ] **Phase 3: 可靠每日更新** - 每日可靠自動更新 + 容錯 partial upload + 網站顯示真實「最後更新」
- [ ] **Phase 4: 自家錯價偵測** - price_history 表 + 統計異常偵測,候選餵入現有 master,RSS 來源照行

## Phase Details

### Phase 1: Travelpayouts 覆蓋率 Spike（決策閘）
**Goal**: 用真實 Travelpayouts token 量度我哋 171 條路線喺各月嘅實際數據覆蓋率 / 行程日數分佈 / 新鮮度,得出一個明確、可落地嘅數據源決定 — GO(採用 Travelpayouts `month-matrix` 做主力)定 FALLBACK(沿用 fast-flights,喺平價日加 ±N return-offset 內層)— 解鎖 Phase 2 嘅彈性行程實作路徑同 Phase 3 嘅每日更新策略。
**Depends on**: Nothing (first phase)
**Requirements**: 無直接 v1 requirement(spike / 決策閘 — 交付一個有證據嘅決定同文檔,解鎖 FLEX-* 同 DAILY-* 嘅實作選擇)
**Spike / Decision Gate**: 係 — 呢個 phase 唔出 user-facing 功能,只出一個拍板嘅數據源決定 + 量度結果文檔。Phase 2 / 3 嘅後續實作 branch on 呢個結果。
**Success Criteria** (what must be TRUE):
  1. User 已喺 Travelpayouts 開咗免費 affiliate 戶口並攞到 Data API token,token 只入 `.env`(`TRAVELPAYOUTS_TOKEN`),冇 commit 入 git
  2. 拉咗 `v2/prices/month-matrix` 涵蓋約 12 條代表路線(HKG 熱門如 BKK/NRT/TPE + SZX/CAN 冷門 long-tail + 一兩條 long-haul)× 未來 7 個月,並量度到每 route-month 嘅記錄密度、行程日數(nights)分佈、`found_at` 新鮮度、有冇空 `data`
  3. 有一份書面 finding 比較「Travelpayouts 覆蓋」vs「現有 fast-flights ±N 掃描」,清楚指出冷門 SZX/CAN 線係咪夠密
  4. 出咗一個明確的 **GO(採用 Travelpayouts)** 或 **FALLBACK(fast-flights + ±N return-offset)** 建議,並寫低拍板理由,更新 PROJECT.md Key Decisions 嘅「Pending」狀態
**Plans**: TBD

### Phase 2: 彈性行程日數
**Goal**: 用 Phase 1 拍板嘅路徑,為每 route×月 產出「彈性行程日數」嘅最平 / 次平 / 第三平資料(每個平價日帶自己嘅 trip length),落 Supabase,並更新網站令每張目的地卡嘅平價日子掣顯示行程日數 + 來回價,撳就跳對應 depart+return 嘅 Google Flights。
**Depends on**: Phase 1（數據源決定)
**Requirements**: FLEX-01, FLEX-02, FLEX-03
**Branches on Phase 1**: GO → 由 `month-matrix` records 計 `nights = return − depart`,group by 月選 cheapest/2nd/3rd 落 `periods`。FALLBACK → 喺現有 `--grid` 揾到嘅平價出發日上,加一個薄薄嘅 return-offset 內層(`dur−2…dur+2`,約 5 個)取最平,模仿參考網站 ±2 window(唔做 28×13 brute force)。
**Success Criteria** (what must be TRUE):
  1. 每張目的地卡展開後,同一個月可以見到 **多種行程日數**(2–14 範圍內,實際似參考網站嘅 dur±2)嘅平價出發日,唔再淨係固定一種日數 — FLEX-01
  2. 每個平價日子掣清楚標明 **行程日數 + 來回價**(似「11號 6日」),並按價分層(最平 / 次平 / 第三平)顯示 — FLEX-02
  3. 撳任何一個平價日子,跳去對應 **depart + return** 日期嘅 Google Flights,可對返實時價 — FLEX-03
  4. `web/components/DestinationCard.tsx` 同 `web/lib/` 已更新讀新 `periods`(每筆帶 depart/return/price/days),Supabase `cheap_flights.periods` jsonb 有對應資料,`next build` 過
**Plans**: TBD
**UI hint**: yes

### Phase 3: 可靠每日更新
**Goal**: 令平機票數據每日可靠自動更新一次(取代而家 ~3 日一次嘅東拼西湊),更新過程容錯(部分掃描失敗都照出已完成部分),並喺網站誠實顯示真實「最後更新」時間。
**Depends on**: Phase 1（每日更新策略 branch on 數據源決定)
**Requirements**: DAILY-01, DAILY-02, DAILY-03
**Branches on Phase 1**: GO → 一個簡單每日 cron,約 1,200 個 cached API call,單 job 幾分鐘完成,冇 IP 風險。FALLBACK → 每日 incremental(staleness budget,先掃最舊嘅,coarse grid)+ 每週 full sweep,加多 shard / 減頻率,加 `concurrency:` guard 防 cron-delay 撞單。兩條路都要做共通修復(見下)。
**Success Criteria** (what must be TRUE):
  1. 平機票數據 **每日自動更新一次**,可靠完成,唔再 ~3 日先 refresh 一次 — DAILY-01
  2. `scan.yml` 修好:`upload.py` 行做一個 `if: always()`-style 嘅獨立 step,就算掃描超時 / 失敗,已完成部分照樣 upload 出街(唔會成日 0 更新)— DAILY-03
  3. `db.cheap_flight_rows()` 修好,UPDATE 時會寫 `scanned_at`(用 scan 嘅 `generated_at`),per-route 新鮮度真實 — DAILY-02 基建
  4. 網站每張卡(或全站)顯示 **真實「最後更新」** 時間,反映實際 per-route 新鮮度(例如「更新於 2 日前」)— DAILY-02
**Plans**: TBD
**UI hint**: yes

### Phase 4: 自家錯價偵測
**Goal**: 由自己每日掃嘅價做統計異常偵測,自動捉「某條線異常平」嘅疑似錯價,候選以現有 `scout.REQUIRED` dict 形狀產出,餵入現有 master → notifier → db 路徑(零新核實 code),同時穩固現有 RSS 來源並行。基建上加一個 append-only `price_history` 表畀偵測用。
**Depends on**: Phase 3（pipeline 形狀定咗;Phase 4 基本上同數據源決定無關,食邊個流出嚟嘅價都得)
**Requirements**: MISP-01, MISP-02, MISP-03, DATA-01
**Cold-start caveat**: 異常偵測需要約 1 星期歷史先準;由現有 dated `scan_*.json` backfill 做 bootstrap,歷史唔夠嘅路線只發 low-confidence「watch」,唔 auto-flag。
**Success Criteria** (what must be TRUE):
  1. 系統由自己每日掃嘅價,**自動偵測** 某條線異常平嘅疑似錯價(per route×月×艙,rolling-median + MAD z-score + %-drop 閘 + per-region 校準 + cold-start watch mode)— MISP-01
  2. 偵測到嘅候選以現有 `scout.REQUIRED` 形狀產出,**餵入現有 master agent** 核實 live/dead,再經現有 Telegram + 網站錯價區出,**零新核實 code** — MISP-02
  3. 現有 RSS 來源(theflightdeal / fly4free / Reddit `.rss`)保留並穩固,與自家偵測並行運作 — MISP-03
  4. 加咗 append-only `price_history` 表(schema.sql + `db.py` writer + `upload.py` 接駁),並由現有 dated `scan_*.json` backfill 出基線 — DATA-01
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

(Phase 1 是決策閘:Phase 2 同 Phase 3 嘅實作路徑 branch on Phase 1 結果。Phase 4 邏輯上排最後。)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Travelpayouts 覆蓋率 Spike（決策閘) | 0/TBD | Not started | - |
| 2. 彈性行程日數 | 0/TBD | Not started | - |
| 3. 可靠每日更新 | 0/TBD | Not started | - |
| 4. 自家錯價偵測 | 0/TBD | Not started | - |
