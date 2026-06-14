# Roadmap: Flight Deal System — Amendments Milestone

## Overview

呢個係 **brownfield amendments milestone**:後端鏈(掃描 → 篩 → 核實 → Telegram → Supabase)同 Next.js 網站都已起好(見 PROJECT.md「Validated」)。今個 milestone 做三項改進 — 彈性行程日數、可靠每日更新、自家錯價偵測 — 加一項基建(price_history),再**保留(reserve)user 原計劃嘅兩個社交來源 scout add-on**(小紅書 Phase 5 + Facebook/Instagram Phase 6)。

呢個 milestone 係 **spike-gated**:user 揀咗「先試免費 Travelpayouts API → 唔夠 fallback 自己掃 ±N」。所以 **Phase 1 係一個決策閘(spike)**,先攞 Travelpayouts token 量度真實覆蓋率,出一個明確 GO(用 Travelpayouts)定 FALLBACK(fast-flights + ±N return-offset)建議。Phase 2(彈性行程)同 Phase 3(每日更新)嘅實作路徑都 **branch on 呢個決定**。Phase 4(自家錯價偵測)基本上同數據源決定無關 — 佢食邊個 pipeline 流出嚟嘅價都得 — 但邏輯上排喺 pipeline 形狀定咗之後。Phase 5/6 係 user 原始願景入面嘅 add-on 社交來源(原 CLAUDE.md Phase 5/6),reuse 同一條 scout → master → notifier → db plumbing。

唔重新 plan 任何現有 Validated 能力(包括已起好嘅 Reddit RSS scout,佢繼續由 MISP-03「保留現有 RSS」覆蓋)。

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Travelpayouts 覆蓋率 Spike（決策閘）** ✅ 2026-06-14 — 拍板 **FALLBACK**(Travelpayouts 來回數據太疏);詳見 `research/TRAVELPAYOUTS-SPIKE.md`
- [x] **Phase 2: 彈性行程日數** ✅ 2026-06-14 — 每個平價日標明行程日數 + 來回價,按價分層,撳跳對應 depart+return 嘅 Google Flights(NGO 實證出 4–8 日)
- [ ] **Phase 3: 可靠每日更新** - 每日可靠自動更新 + 容錯 partial upload + 網站顯示真實「最後更新」
- [ ] **Phase 4: 自家錯價偵測** - price_history 表 + 統計異常偵測,候選餵入現有 master,RSS 來源照行
- [ ] **Phase 5: 小紅書(RedNote)scout** - deploy 小紅書 scout(MediaCrawler + cookie/session 登入),收料 → 現有 Haiku 篩 → 餵現有 master → notifier → db(原計劃 add-on 來源)
- [ ] **Phase 6: Facebook / Instagram scout** - deploy FB/IG scout(Apify 或半人手),餵同一條 scout → master → notifier → db 路徑(原計劃 add-on 來源,反爬/ToS 最高故排最後)

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
**Branches on Phase 1**: ✅ **已定 = FALLBACK**(spike:Travelpayouts 來回數據太疏)。實作:喺現有 `--grid` 揾到嘅平價出發日上,加一個薄薄嘅 return-offset 內層(`dur−2…dur+2`,約 5 個)取最平,模仿參考網站 ±2 window(唔做 28×13 brute force)。〔可選優化:用 Travelpayouts month-matrix 單程數據做平價出發日 anchor,進一步減 query。〕
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
**Branches on Phase 1**: ✅ **已定 = FALLBACK**(自己掃,冇 cached API 捷徑)。實作:每日 incremental(staleness budget,先掃最舊嘅,coarse grid)+ 每週 full sweep,加多 shard / 減頻率,加 `concurrency:` guard 防 cron-delay 撞單。共通修復見下。
**Success Criteria** (what must be TRUE):

  1. 平機票數據 **每日自動更新一次**,可靠完成,唔再 ~3 日先 refresh 一次 — DAILY-01
  2. `scan.yml` 修好:`upload.py` 行做一個 `if: always()`-style 嘅獨立 step,就算掃描超時 / 失敗,已完成部分照樣 upload 出街(唔會成日 0 更新)— DAILY-03
  3. `db.cheap_flight_rows()` 修好,UPDATE 時會寫 `scanned_at`(用 scan 嘅 `generated_at`),per-route 新鮮度真實 — DAILY-02 基建
  4. 網站每張卡(或全站)顯示 **真實「最後更新」** 時間,反映實際 per-route 新鮮度(例如「更新於 2 日前」)— DAILY-02

**Plans**: 4 plans
Plans:

- [x] 03-01-PLAN.md — db scanned_at fix (DAILY-02 root cause) + db.stale_routes() primitive + offline tests
- [x] 03-02-PLAN.md — website per-route + global freshness display (DAILY-02 UI) + next build
- [x] 03-03-PLAN.md — scanner --stale-first/--budget/--grid-step (DAILY-01) + scan.yml split-step if:always upload + weekly sweep (DAILY-03)
- [ ] 03-04-PLAN.md — GitHub rollout: expectation + push/Secrets + dispatch & measure block rate -> cron decision (checkpoints)

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

### Phase 5: 小紅書(RedNote)scout

**Goal**: Deploy 一個小紅書(RedNote / Xiaohongshu)scout — 用 MediaCrawler + cookie/session 登入拉貼文,經**現有 Haiku scout filter** 評分,將疑似錯價候選以**現有 `scout.REQUIRED` dict 形狀**產出,令**現有 master → notifier → db 路徑**核實並出街(零新核實 code)。呢個係 user 原始計劃嘅 add-on 本地來源(原 CLAUDE.md Phase 5),補返 RSS 覆蓋唔到嘅大陸/HK bug-fare 社群。
**Depends on**: Phase 4（reuse Phase 4 settle 好嘅 scout → master plumbing 同候選 dict 形狀)
**Requirements**: MISP-04
**Reserved (original-plan add-on source)**: 係 — 由 user 原始願景(CLAUDE.md Phase 5)reserve 返做 committed scope,唔係 spike。
**Constraints / Notes**:

  - 需要 cookie/session 登入 — session / cookie 檔必須 gitignored(鐵律 1:key/session 只喺本機 + Secrets,唔入 git)。
  - 反爬:隨機 delay / retry / 尊重 rate limit(鐵律 4),低 volume 慢 cadence。
  - 來源(小紅書 search 詞 / 帳號 / hashtag)加喺 `sources.yaml`,唔改 code(鐵律:加減來源改 config)。
  - 重用 `scout.py`(Haiku 篩)、`master.py`(核實)、`notifier.py`、`db.py` — 唔寫新核實 / 推送 / 入庫 code。

**Success Criteria** (what must be TRUE):

  1. Scout 成功由小紅書拉到貼文(經 MediaCrawler + 已登入 session),並可重複跑 — MISP-04
  2. 現有 Haiku scout filter 對拉到嘅貼文評分,輸出符合 `scout.REQUIRED` dict 形狀嘅候選 — MISP-04
  3. Live 測試入面,**至少 1 個小紅書候選由 scout → master 核實 → notifier(Telegram)/ db(Supabase error_fares)行通晒** end-to-end,零新核實 code — MISP-04
  4. 小紅書 session / cookie secrets 只喺本機(gitignored),冇 commit 入 git;來源 config 喺 `sources.yaml`

**Plans**: TBD

### Phase 6: Facebook / Instagram scout

**Goal**: Deploy 一個 Facebook / Instagram scout(用 Apify actors 或半人手 ingestion 攞 FB/IG flight-deal 來源嘅料),餵入**同一條 scout → master → notifier → db 路徑**,令 FB/IG 上嘅疑似錯價經現有 Haiku 篩 + 現有 master 核實後出街。呢個係 user 原始計劃嘅 add-on 本地來源(原 CLAUDE.md Phase 6),HKG-origin 信號(Flyday.hk / Flyagain.la / 又飛啦等)最強。
**Depends on**: Phase 5（沿用同一條 scout → master plumbing;FB/IG 反爬/ToS friction 最高,故照原計劃排最後)
**Requirements**: MISP-05
**Reserved (original-plan add-on source)**: 係 — 由 user 原始願景(CLAUDE.md Phase 6)reserve 返做 committed scope,唔係 spike。
**Constraints / Notes**:

  - FB/IG 冇公開 API → 用 **Apify actors** 或**半人手** ingestion(原計劃既定路線)。
  - 反爬/ToS friction 最高 → 照原計劃**排最後**(Phase 6),低 volume、尊重 rate limit(鐵律 4)。
  - 任何 Apify token / 登入 credential 只喺 `.env`(本機)同 GitHub Secrets(CI),唔入 git(鐵律 1)。
  - 來源(FB group / IG 帳號)加喺 `sources.yaml`,唔改 code;重用現有 scout / master / notifier / db。

**Success Criteria** (what must be TRUE):

  1. FB/IG flight-deal 來源嘅 items 經選定方法(Apify 或半人手)成功 ingest 入 pipeline — MISP-05
  2. Ingest 到嘅 items 經現有 Haiku scout filter 篩,輸出符合 `scout.REQUIRED` dict 形狀嘅候選 — MISP-05
  3. Live 測試入面,**至少 1 個 FB/IG 候選由 scout → master 核實 → notifier / db 行通晒** end-to-end,零新核實 code — MISP-05
  4. 任何 Apify / 登入 credential、key 只喺 `.env` / GitHub Secrets,冇 commit 入 git;來源 config 喺 `sources.yaml`

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

(Phase 1 是決策閘:Phase 2 同 Phase 3 嘅實作路徑 branch on Phase 1 結果。Phase 4 邏輯上排現有 pipeline 之後。Phase 5/6 係 user 原計劃嘅 add-on 社交來源,reuse 同一條 scout → master plumbing;FB/IG 反爬/ToS friction 最高,照原計劃排最後。)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Travelpayouts 覆蓋率 Spike（決策閘) | 1/1 | ✅ Complete (FALLBACK) | 2026-06-14 |
| 2. 彈性行程日數 | 1/1 | ✅ Complete | 2026-06-14 |
| 3. 可靠每日更新 | 3/4 | In Progress (Wave 3 = GitHub rollout 待 user) | - |
| 4. 自家錯價偵測 | 0/TBD | Not started | - |
| 5. 小紅書(RedNote)scout | 0/TBD | Not started | - |
| 6. Facebook / Instagram scout | 0/TBD | Not started | - |
