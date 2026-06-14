# Flight Deal System — 平機票 / 錯價票偵測系統

## What This Is

全自動每日跑嘅平機票 + error fare 偵測系統:掃 HKG / SZX / CAN 出發、未來 7–12 個月航線最平價,並由 RSS/社交收料偵測疑似錯價票,核實後經 Telegram + Next.js 網站(Vercel)出畀香港旅客。後端鏈(掃描 → 篩 → 核實 → Telegram → Supabase)同網站都已起好;呢個 milestone 做三項改進(彈性行程日數、可靠每日更新、自家錯價偵測)並 reserve 返 user 原計劃嘅兩個社交來源 scout add-on(小紅書、FB/IG)。

## Core Value

畀香港用戶一個**可信、每日更新**嘅地方,快速搵到「值得買」嘅平機票同真·錯價票,並一撳跳去 Google Flights 對返實時價。

## Requirements

### Validated

<!-- 已 ship 嘅現有能力(brownfield,由現有 code 推斷)。-->

- ✓ fast-flights 雙層掃描器(HTTP → Playwright 後備),每 route×月最平 + Google Flights deep link — Phase 1A
- ✓ `--grid` 全日曆掃描(**固定**行程日數,每月掃每日)+ `periods` 平價日 list — Phase 1A
- ✓ RSS scout(Reddit `.rss` + 錯價網 theflightdeal/fly4free)+ Haiku 篩 + consolidate — Phase 1B
- ✓ master 核實 agent(triage ≥70 → 重查 → Sonnet 判 live/dead → GF/Trip.com 連結)— Phase 2
- ✓ Telegram 即時推送(`notifier.py`,政策路由)— Phase 2.2
- ✓ Supabase(cheap_flights / error_fares / meta 三枱 + RLS)+ `upload.py` 合併器 — Phase 2.5
- ✓ Next.js 16 網站(錯價雷達 + 平機票可展開卡,展開見平價日子分層)— Phase 3(已起,未 deploy)
- ✓ GitHub Actions 掃描 workflow(12-job matrix,`--grid --slice`)— Phase 4(已寫,未啟動)

### Active

<!-- 今個 milestone 嘅範圍。-->

- [x] 平機票顯示**彈性行程日數**(2–14 日範圍),每個平價日標明行程日數 + 來回價(似參考網站「11號 6日」)— ✅ Phase 2(2026-06-14)
- [ ] **每日可靠自動更新**(取代而家 ~3 日一次)+ 網站顯示真實「最後更新」時間
- [ ] 由**自家掃價數據**做統計異常偵測,自動捉疑似錯價票,餵現有 master 核實
- [ ] (基建)儲每日掃價**歷史**(`price_history`)畀異常偵測用
- [ ] **小紅書(RedNote)scout**(原 Phase 5,MediaCrawler + cookie/session 登入)— 收料餵現有 master 核實
- [ ] **Facebook / Instagram scout**(原 Phase 6,Apify 或半人手)— 收料餵現有 master 核實

### Out of Scope

<!-- 明確界線 + 原因,防止之後又加返。-->

- 付費 API 攞「硬性完整 2–14 日 grid」 — user 揀咗免費路線(Travelpayouts spike → fallback 自己掃);成本考量
- Twitter / X 收料 — 2026 Nitter 已死、X API 冇免費 tier,ROI 低
- 即時(real-time)每次入網站先查價 — 沿用 cache/靜態模型,成本 + 反爬考量

## Context

- 後端鏈完全通;網站起好喺 branch `phase-3-website`,**未 deploy、未 push**(go-live 步驟見 CLAUDE.md)。
- **數據源真相(2026-06-14 research)**:參考網站 `flight-deals-web.vercel.app` 其實係 **prebuilt static JSON**(放 Vercel),數據一樣由 Google Flights 掃返嚟;行程日數實際得 **4–11 日(±2 window)**,唔係真·2–14 grid。**CLAUDE.md 舊「硬牆(43 萬 query)」假設係錯** — 抄佢做法只需喺平價日多掃 ±2 offset,幾千 query 就得。
- Research 詳見 `.planning/research/`:`REFERENCE-SITE.md`、`DATA-SOURCES.md`、`DAILY-UPDATES.md`、`MISPRICING-SOURCES.md`。
- 已知 bug(research 揾到):`db.cheap_flight_rows()` 冇寫 `scanned_at` → UPDATE 唔會更新時間戳(影響「最後更新」誠實度);`scan.yml` 一步兩 command,scan 超時被 kill 就連 `upload.py` 都唔跑(= 部分更新出唔到街)。
- 用戶係非程式員,廣東話溝通,偏好自動執行、每個 milestone 報告一次。

## Constraints

- **Tech stack**: Python (uv) + fast-flights + Supabase (PostgREST httpx) + Next.js 16 / React 19 / Tailwind v4 on Vercel;LLM 經 `llm.py` 路由(試跑 `claude_code` Max plan,production 切 `anthropic`)。
- **Budget**: 盡量 $0;唔用付費 flight API(除非 spike 證實必要先再傾);LLM 成本由 master triage ≥70 閘控制。
- **鐵律(沿用)**: key 只喺 `.env` / GitHub Secrets;唔喺全域 shell set 任何 API key;`sb_secret_` 唔入前端 / `NEXT_PUBLIC_`;對外 request 一律隨機 delay / retry / 尊重 rate limit;加減來源改 config 唔改 code;寫新 code 前睇 `llm.py` / `sources.yaml` / `scanner.py` 有冇現成嘢重用。
- **CI 限制**: GitHub Actions 單 job 6 鐘硬上限;runner 共用 Azure IP,Google 可能 rate-limit / 封。
- **數據新鮮度**: Travelpayouts 數據係 cache(近 48h 真實搜尋),冷門線(尤其 SZX / CAN)可能稀疏 — 要 spike 驗證先拍板。

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 彈性行程日數行「先試免費 Travelpayouts API → 唔夠 fallback 自己掃 ±N」 | user 揀;$0、一個 call 攞全月彈性行程兼順手解決每日更新;有覆蓋率風險故 spike-gate | ✓ FALLBACK（2026-06-14 spike:Travelpayouts 來回數據太疏)→ 行 fast-flights 平價日 ±2 自掃 |
| 錯價票主力行「自家數據異常偵測」而非加外部來源 | 外部來源大多畀 Cloudflare 擋 / Twitter 死;自家數據 ROI 最高、reuse 現有 master | — Pending（Phase 4） |
| Reserve 返 user 原計劃嘅小紅書(Phase 5)/ FB·IG(Phase 6)社交 scout 做 committed scope | user 明確要求保留原始願景嘅 add-on 來源;補返 RSS 覆蓋唔到嘅 HKG-origin 本地 bug-fare 社群;reuse 同一條 scout → master plumbing | — Pending（Phase 5/6） |
| 唔用付費 API 做完整 grid | 成本;參考網站本身都唔係真 2–14 grid | ✓ Good |
| 保留並更新(唔覆蓋)現有 `CLAUDE.md` | 係 user 親自維護嘅 single source of truth | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-14 after initialization (amendments milestone) + 社交來源 scout(小紅書 / FB·IG)由 Out of Scope 升做 Active in-scope(Phase 5/6)*
