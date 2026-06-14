# Phase 3: 可靠每日更新 - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Source:** Orchestrator-synthesised(基於 `DAILY-UPDATES.md` research + Phase 1 FALLBACK 拍板 + Phase 2 已加 refine,未行 discuss-phase)

<domain>
## Phase Boundary

令**平機票(Stream A,cheap_flights)**每日可靠自動更新:更新過程容錯(部分掃描失敗/超時都照出已完成部分),並喺網站誠實顯示真實「最後更新」時間。範圍 = scanner 增量排程 + `scan.yml` 修復 + `db.py` `scanned_at` 修復 + 網站 freshness 顯示 + 謹慎 GitHub rollout。涵蓋 DAILY-01 / DAILY-02 / DAILY-03。

**唔屬於呢個 phase**:Stream B(錯價 scout/master)雲端自動化 —— 嗰個要 `anthropic` provider + API key(production 開支),已列 PROJECT.md Out of Scope;Phase 4 做嘅係「自家錯價偵測」邏輯,唔係將 scout 上雲。Vercel 網站 deploy 係另一條 go-live 線(CLAUDE.md),唔喺呢個 phase。
</domain>

<decisions>
## Implementation Decisions(locked unless marked discretion)

### 現實:全量每日掃 = 做唔到(self-scrape 太重)
- Phase 1 拍板 FALLBACK = 自己掃 Google。Phase 2 仲加咗 refine。全量 = 171 線 × 7 月 ×(grid ~28 + refine ~35)≈ **7.5 萬 query/日** → 就算 12 shard 都爆 GitHub 6 鐘 job 上限(`DAILY-UPDATES.md` 實測每 query ~10.8s,單 shard ~5-7h 已爆)。
- **所以「每日更新」嘅正確定義 = 系統每日跑、每日刷新最舊嗰批線、並誠實顯示每條線新鮮度**;唔係「每條線每 24 小時都重新查一次」(免費 self-scrape + Google 反爬下做唔到)。呢個 expectation 要喺 checkpoint 同 user 講清楚。

### 增量排程(DAILY-01)
- **增量 staleness-budgeted 每日** + **每週一次 full grid+refine sweep**(`DAILY-UPDATES.md` 推薦)。
- 每日 job:揀**最舊(scanned_at 最耐冇更新)**嗰批 route-month,喺一個 query/時間預算內掃(例如每 shard 封頂 ~400 query / ~75 分鐘,穩穩落喺 6 鐘以內),其餘留第二日。staleness signal 由 Supabase `cheap_flights.scanned_at` 讀(最舊優先)。
- 機制 = **Claude's discretion**:可以係 (a) scanner 加 `--stale-first --budget N`(開 job 時由 Supabase 查最舊 route 清單再掃),或 (b) 按 day-of-week round-robin 分片(較簡單,唔使 query Supabase)。planner 揀一個,寫明理由 + query 數估算,跟 `DAILY-UPDATES.md`。每週 full sweep 可用現有 `--slice K/N --grid`(連 refine)。

### 容錯 partial upload(DAILY-03)
- 修 `.github/workflows/scan.yml`:`scanner.py` 同 `upload.py` **拆做兩個 step**,`upload.py` 嗰 step 用 **`if: always()`**(或等效),咁就算 scan step 超時被 kill / 非零退出,已寫低嘅 `data/scan_*.json` 都會照 upload 出街。加 `concurrency:` guard 防 cron delay 撞單。
- scanner 本身已有 per-route atomic 寫檔 + `--resume`,partial 已保留 —— 真正缺口係 workflow step 結構。

### 誠實 freshness(DAILY-02)
- 修 `db.cheap_flight_rows()`(db.py L109-118):row dict **加 `scanned_at`** = scan 嘅 `generated_at`(ISO datetime;`upload.py` 傳入或由 scan_doc 讀)。而家冇呢個 key → upsert merge-duplicates 時 UPDATE 唔會郁 `scanned_at`,只有 INSERT 先 default `now()`,所以舊行永遠停喺第一次插入時間。修咗先有真 per-route 新鮮度。
- 網站:每張卡(或全站)顯示真實「最後更新」—— per-route 用 `scanned_at`(例如「更新於 N 日前」),全站用 `meta.last_updated_stream_a`。睇 `web/lib/data.ts` `getMeta()`(已有)+ `cheap_flights.scanned_at`(type 已有 `scanned_at: string|null`)。⚠️ 改 `web/` 前讀 `web/node_modules/next/dist/docs/`(AGENTS.md)。

### 謹慎 rollout(最大未知數 = GitHub 共用 IP 會唔會畀 Google 封)
- `DAILY-UPDATES.md`:GitHub runner 用共用 Azure IP,anti-bot 預先標記,12 shard 每日撞 Google = 中-高封鎖風險,要試先知。
- **唔好一開就 set 每日 cron**。先 **手動 `workflow_dispatch` 跑一次**,睇 scanner stats(failed / shell page / beyond_data 比例)量度真實封鎖率,**再決定**啟唔啟用 daily cron(或要唔要減頻率 / 加 rotation)。呢個係一個 human-verify checkpoint。

### 用戶動作(setup checkpoint)
- 要 push code 上 GitHub `Ticketsradar/flight-deal-system`(origin 已設)+ set repo **Secrets**:`SUPABASE_URL`、`SUPABASE_SECRET_KEY`、`REDDIT_USER_AGENT`。push 前掃過冇 secret 入 git(`.env` / `web/.env.local` 已 gitignored)。呢個要 user 做(或明確授權我 push)。係 blocking setup checkpoint。

### Claude's Discretion
- 增量機制 (a) stale-first 查 Supabase vs (b) day-of-week round-robin;每日 query/時間預算;shard 數;cron 佈局(單 cron vs 多時段);refine 係咪只喺每週 full sweep 做(每日增量用唔用 refine)。
</decisions>

<canonical_refs>
## Canonical References

### CI / 排程(主戰場)
- `.github/workflows/scan.yml` — 12-job matrix(`--slice K/12 --grid --no-browser` + `upload.py` 同一 run step);`timeout-minutes: 350`;cron `0 18 * * *`(未啟動)。要拆 step + `if: always()` + concurrency。
- `scanner.py` — `--slice K/N`、`--grid`、`--resume`、`--months`、stats(queries/failed/beyond/ok)、`on_query` pacing(Phase 2 加)、refine(`--offset/--refine-days/--no-refine`)。增量模式可能喺度加 flag。

### 落庫 / freshness
- `db.py` L97-119 `cheap_flight_rows()` — **加 `scanned_at`**;`set_meta()` L200。
- `upload.py` — `_latest("scan_*.json")`、`db.set_meta("last_updated_stream_a", scan_date)`;可能要傳 `generated_at` 落 cheap_flight_rows。
- `schema.sql` — `cheap_flights.scanned_at`(default now();確認欄存在)。

### 網站 freshness 顯示
- `web/lib/data.ts` `getMeta()`(已讀 meta)+ `getCheapFlights`(已 select `scanned_at`)。
- `web/lib/types.ts` `CheapFlight.scanned_at: string|null`(已有)。
- `web/components/Header.tsx` 或主頁 — 加「最後更新」顯示位。`web/AGENTS.md` 必讀。

### Research / 背景
- `.planning/research/DAILY-UPDATES.md` — root cause、ranked options、推薦排程設計、GitHub 限制引用、IP 風險。**主要依據。**
- `CLAUDE.md` — go-live 步驟(push / Secrets)、鐵律(Secrets 只喺 .env/GitHub Secrets、對外 request pace/retry)。
</canonical_refs>

<specifics>
## Specific Ideas
- 目標:每日 GitHub Actions 跑一次、每日刷新最舊嗰批線、容錯出街、網站見到真「更新於 X 前」。
- 先手動 dispatch 跑一次量度 Google 封鎖率,夠穩先開 daily cron。
- 本機可測嘅嘢盡量本機測:db scanned_at(可寫離線 test)、scan.yml 結構(yaml lint / act 或人手 review)、web build + freshness 顯示。GitHub 上跑嗰部分要 checkpoint。
</specifics>

<deferred>
## Deferred Ideas
- Stream B(錯價 scout/master)上雲自動 → 要 ANTHROPIC_API_KEY,out of scope(go-live 後再決定)。
- Proxy / 住宅 IP rotation → 只喺手動 dispatch 證實封鎖率高先考慮(成本 + ToS)。
- Vercel 網站 deploy → 另一條 go-live 線(CLAUDE.md),唔喺呢個 phase。
- 用 Travelpayouts month-matrix 單程數據做 anchor 減 query → 可選優化,Phase 2 已記低。
</deferred>

---

*Phase: 03-reliable-daily-updates*
*Context gathered: 2026-06-14 (orchestrator-synthesised from DAILY-UPDATES.md + FALLBACK + Phase 2; discuss-phase skipped)*
