# CLAUDE.md — Flight Deal System 項目記憶

> **畀 Claude Code 嘅指示**:呢個檔係項目嘅 single source of truth。每次 session 先睇【進度】知道做到邊。**每完成一個 phase,主動更新【進度】section(剔 ✅ + 寫低完成日期),再話畀 user 知下一步係乜。** User 係非程式員,所有解釋用廣東話(中文),技術名詞保留英文。

---

## 項目目標

全自動每日跑嘅平機票 / error fare 偵測系統:
1. **掃描引擎**:掃 HKG / SZX / CAN 出發、未來 12 個月嘅航線,搵每條 route 每個月最平日子。
2. **偵測引擎**:scout agents 每日由 **Reddit、小紅書、Facebook、Instagram** 收料,篩出疑似錯價票;master agent 重新 query 核實價格 + 生成 booking link。(Telegram 唔做 — user 實測相關 group 唔多;sources.yaml 留咗註解,第時可加返。)
3. **網站**:Next.js on Vercel 顯示兩者,連免責聲明。
4. **零人手**:GitHub Actions cron 每日自動跑。

## 參考網站(目標體驗藍本)

**https://flight-deals-web.vercel.app**(「平機票 ✈️ 香港出發」)— 我哋網站嘅參照:來回 all-in base fare(含稅+燃油)參考價、地區/月份/預算篩選、「手提/寄艙」標示、「最後更新」時間戳、撳日子入 Google Flights 確認實時價。佢嘅航線清單就係我哋 routes.yaml 嘅基準(見 Phase 1A 步驟 2)。

## 架構(已鎖定,唔好擅自改)

```
GitHub Actions cron(每日)
├─ 引擎A: fast-flights(免費,逆向 Google Flights)→ 每route每月最平
└─ 引擎B: scouts收料
    • Reddit(.json後門,零API審批)← Phase 1B
    • 小紅書(MediaCrawler + cookie)← Phase 5
    • FB/IG(Apify 或半人手)← Phase 6
    → scout腦篩選 → consolidate dedup → master腦 triage+核實(fast-flights重query)
    → 生成 Google Flights tfs deep link + Trip.com link
→ 結果落 database → Next.js 網站
```

| 角色 | 試跑階段(而家) | Production(之後切) |
|---|---|---|
| Scout 腦 | `claude_code` provider,model `haiku`(行 user 個 Max plan,$0) | Claude Haiku(`anthropic` provider,API) |
| Master 腦 | `claude_code` provider,model `sonnet` | Claude Sonnet(`anthropic` provider,API) |
| 切換方法 | — | 只改 `.env` 路由四行,code 唔使掂 |

## 關鍵設計決定(背景:點解係咁)

- **`llm.py` 路由器**:所有 LLM call 經佢行,provider 由 `.env` 嘅 `SCOUT_PROVIDER`/`MASTER_PROVIDER` 決定。三個 provider:`claude_code`(subprocess call `claude -p`,用 Max plan)、`anthropic`、`minimax`(Anthropic 兼容接口,要過濾 thinking block — 已處理)。
- **Google Flights 用 `fast-flights`**(免費逆向 library),唔用付費 API;SerpApi 只做後備。掃描必須抽樣(每 route 每月 1 個代表價)+ 盡量用 calendar/date-range,唔准逐日掃 365 日。
- **Reddit 唔使官方 API**:URL 加 `.json`(如 `reddit.com/r/flightdeals/new.json`),要帶 `REDDIT_USER_AGENT`、每 request 隔 2–3 秒、處理 429。
- **路線清單以參考網站為基準**:由 https://flight-deals-web.vercel.app 抽取目的地(佢係 SPA,要搵佢載入嘅 JS/JSON data 檔先抽到 — 見 Phase 1A 步驟 2)。
- **收料來源全部喺 `sources.yaml`**:加減來源改 config,唔改 code。只用 verify 過嘅來源。
- **試跑模式資料先寫本地 `data/*.json`**;Supabase 留到 Phase 2 完成後、起網站之前先接。
- **Master 有 triage 閘**:只核實 confidence ≥ 70 嘅候選 — 呢個係控制 LLM 成本嘅主閘(production 時 Sonnet 佔成本八成)。
- **Error fare 常識**:錯價通常 15 分鐘至幾粒鐘內被改正,master 核實發現「票已死」係常態;網站必須有免責聲明。

## 鐵律(每個 phase 都要遵守)

1. 所有 key 只存在於 `.env`(本機)同 GitHub Secrets(CI)。`.gitignore` 必須包 `.env`、`data/`、`compare_log/`、(將來)MediaCrawler 嘅 cookie/session 檔。
2. **唔准喺全域 shell set 任何 API key**(會搶 Claude Code 嘅訂閱認證 / 同 MiniMax 衝突)。
3. Supabase `sb_secret_` 唔准入前端或 `NEXT_PUBLIC_` 變數。
4. 對外 request(Google/Reddit/參考網站)一律:隨機 delay、retry、尊重 rate limit。
5. 寫任何新 code 前,睇吓 `llm.py` / `sources.yaml` 有冇現成嘢可以重用。

## 現有檔案

`llm.py`(LLM 路由器)/ `test_llm.py`(通關測試)/ `sources.yaml`(收料來源+篩選signal;telegram section 已註解化)/ `.env`(由 env.example 嚟;TELEGRAM 變數可以照註解放住)/ `README.md`(starter kit 說明)

---

## 【進度】 ← Claude Code 負責維護呢個 section

- [x] Phase 0 — 環境準備(GitHub、Claude Code + Max 登入;Anthropic/MiniMax key 留 production 先開)
- [x] Phase 1.0 — project 地基 + `llm.py` + `test_llm.py` 全綠(兩個腦經 Max plan call 通)
- [x] **Phase 1A — routes.yaml(57 目的地)+ fast-flights 掃描器** ✅(`scanner.py`:`query_roundtrip` 雙層[HTTP fast-flights → Playwright 後備]、每 route×月最平、Google Flights deep link;**全量掃過 1057 route-month 入咗 Supabase**。2026-06-14 加咗:`--grid`(每月掃晒每一日 = 平價日子)、`--only HKG-MNL`、`--slice K/N`(Phase 4 matrix 分片)、`--months` 預設改 7;每月存 `periods`[平價日 list];Manila `--grid` demo 證實 198 個平價日入庫)
- [x] **Phase 1B — RSS scout(Reddit `.rss` + 錯價網 RSS)+ Haiku 篩 + consolidate** ✅ 2026-06-13(`feeds.py`/`scout.py`/`consolidate.py`/`run_scout.py`;reddit `.json` 被 403 → 改用官方 `.rss`;錯價網用 theflightdeal + fly4free;Haiku 正面測試捉到 HKG 錯價、live 跑通寫 `data/candidates_*.json`;計劃見 docs/superpowers/plans/2026-06-13-phase-1b-rss-scout.md。註:reddit `.rss` 有 429,每跑約 4/7 sub 成功,多次跑輪流覆蓋,夠用)
- [x] **Phase 2 — master 核實 agent** ✅ 2026-06-13(`master.py` + `run_master.py`;triage≥70 → reuse `scanner.query_roundtrip`(加咗 seat 參數)重查 → Sonnet 判 live/dead/unverified → Google Flights + Trip.com 連結 → `data/verified_*.json`;smoke 證實 Sonnet 正確判 fake $600 HKG-NRT 為 dead(實價 $2426);計劃 docs/superpowers/plans/2026-06-13-phase-2-master-verify.md)
- [x] **Phase 2.2 — Telegram 即時推送** ✅ 2026-06-13(`notifier.py`:format_deal(HTML 訊息:航線+傳聞/重查價+日期+狀態+airline+Google Flights/Trip.com/原文 三連結+免責)、send_message(httpx POST `sendMessage`,retry/429)、notify_verified(政策路由:live 推 owner+channel / unverified 推 owner / dead 唔推);駁入 `run_master.py`,加 `--no-notify`;6 項離線測試綠;**真機 live send 通過 — user 確認部電話收到測試卡片**。bot=@hkgcheapflightscannerbot,channel 暫留空只推 owner)
- [x] **Phase 2.5 — 接 Supabase** ✅ 2026-06-13(`schema.sql`(cheap_flights/error_fares/meta 三枱 + RLS 公開只讀)、`db.py`(PostgREST httpx upsert/select/delete + 行映射,未配置 no-op)、`upload.py`(純 code 合併器:最新 scan_*.json→cheap_flights、verified_*.json 三 bucket→error_fares + set_meta);**live 驗證:1057 平機票 + 1 錯價真寫入 Supabase 並讀返**;test_db / test_upload 全綠。Supabase project ref=vluyordxtflpqebzapgr;keys 喺 `.env`(SUPABASE_URL/PUBLISHABLE/SECRET))
- [~] **Phase 3 — Next.js 網站**:✅ 起好(`web/`,Next 16 + React 19 + Tailwind v4),❌ 未 deploy。喺 branch `phase-3-website`。詳見下面「網站現狀」。
- [~] **Phase 4 — GitHub Actions cron**:Stream A 掃描 workflow 已寫(`.github/workflows/scan.yml`,12-job matrix 平行全日曆),❌ 未啟動(要 push + GitHub Secrets)。詳見下面。
- [ ] Phase 5 — 小紅書 scout(MediaCrawler + cookie 登入)
- [ ] Phase 6 — Facebook / Instagram scout(Apify 或半人手,最後先做)

---

## 現狀交接(2026-06-14 寫;後端鏈做晒,網站 + Phase 4 起好未上線)

> **新 session 由呢度睇起。** 後端(掃描→篩→核實→Telegram→Supabase)完全通。網站起好喺本機驗證過,但**未 deploy、未 push**。全部 work 喺 branch **`phase-3-website`**(由 main 分支,本機行 work,~40 個 commit,未 push origin)。

### 網站現狀(`web/`,Phase 3)
- Next.js 16 + React 19 + Tailwind v4(`web/`)。**force-dynamic**,即時讀 Supabase。
- 兩專區:**錯價雷達**(error_fares,狀態 badge + GF/Trip.com/原文 link)+ **平機票**(每個目的地一張可展開卡 `<details>`)。
- 平機票卡:`DestinationCard.tsx` — 國旗+國家 / 城市·代碼 / 出發地 / 最平價;展開見**平價日子 date 掣**(每月分組,每月按價分層上色:綠最平/青次/黃第三,**較貴灰色日已隱藏**),每掣 = 日號+行程日數+價,撳跳該日 Google Flights。只顯示**最近 7 個月**。
- `airports.ts`(57 目的地+3 出發地 → 國家/城市/國旗)、`Filters.tsx`(固定 3 出發地 HKG/SZX/CAN + 地區 + 預算)、`BackgroundSlideshow.tsx`(9 張 Wikimedia 風景相,**隨機次序 + Ken Burns 慢 zoom**,scrim 55%)、`TelegramCTA` / `Disclaimer`。
- `web/lib/{supabase,data,types}.ts`;`web/.env.local`(NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,gitignored)。
- **本機開發+截圖流程**(Claude Preview MCP 入唔到呢個 project path,用唔到):用 Bash 背景跑 `cd web && npx next dev -p 3000`(`dangerouslyDisableSandbox`),再用 scanner 個 Playwright 寫 script 截圖(`uv run python /tmp/shot.py`)。`next build` 過先算數。

### 後端 Phase 4(`.github/workflows/scan.yml`)
- Stream A 全日曆掃描:12-job matrix,每 job `scanner.py --slice K/12 --grid --no-browser` + `upload.py`,各 GitHub runner 各自 IP。每日 cron + 手動 dispatch。**未啟動**(要 push + Secrets)。
- ⚠️ 未知數:GitHub IP 係共用 pool,Google 可能封。要試;被封就減頻率/加 rotation/減 job。

### ⛔ 未決定 — 「2-14 日 trip length 完整 grid」(user 想要,但做唔到)
- User 想要參考網站咁:每個目的地每月,**所有出發日 × 所有 2-14 日行程長度**嘅最平/2nd/3rd 價(完整 depart×return 矩陣)。
- **硬牆**:fast-flights 一個 query 淨係問一對日期(`flights.proto` 得單一 `date`,冇 calendar)。Brute-force = 28 日 × 13 trip-length × 7 月 × 171 線 ≈ **436k query/日**,就算 20 雲端 job 都 ~33h/job,**做唔到**。
- **R&D 試過攞 Google 真 date-grid 都失敗**:HTTP 回應係空殼頁(冇 calendar)、截唔到 batchexecute XHR、Playwright 爬 price-graph DOM 唔穩。Google Flights 重度反爬。
- **建議方案 B(未做)**:每個目的地加一個「睇晒 2-14 日所有組合 →」掣,跳去 **Google Flights 自己嘅彈性日期 grid**(完整、即時、$0)。我哋卡照顯示搵到嘅平價日。**user 收尾時叫開新 section,呢個 decision 未拍板。**

### 去 Live(go-live)未做,步驟:
1. merge `phase-3-website` → `main`,push 上 GitHub `Ticketsradar/flight-deal-system`(origin 已設)。push 前掃過冇 secret 入 git(`.env` + `web/.env.local` 都 gitignored)。
2. **Vercel**:import repo → **Root Directory = `web`** → 環境變數 `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`(只 publishable,**唔好放 secret**)→ Deploy。
3. **GitHub repo Secrets**(畀 Actions):`SUPABASE_URL`、`SUPABASE_SECRET_KEY`、`REDDIT_USER_AGENT`。
4. **Stream B(錯價 scout/master)雲端自動**未做 — CI 用唔到 Max plan,要 `anthropic` provider + `ANTHROPIC_API_KEY`(production 開支)。而家錯價區得手動 demo 資料。

### 關鍵事實
- Supabase project ref = **vluyordxtflpqebzapgr**;`schema.sql` 跑咗(三枱 + RLS + `periods jsonb` 欄已加)。
- Telegram bot = **@hkgcheapflightscannerbot**;owner chat = 6783294847;**未有公開 channel**(`TELEGRAM_CHANNEL_ID` 空,只推 owner)。
- 所有 key 喺本機 `.env`(gitignored,連我嘅 Read/Bash 都 deny);部機有 **node v26 + npm**(/usr/local/bin);sandbox Bash 行 uv 前 `export PATH="$HOME/.local/bin:$PATH"`。
- 新檔:`notifier.py` `db.py` `upload.py` `airports.ts`(web)+ 全套 `web/`;test_*.py 全綠;`scan_20260613.full.json` = 1057 線完整備份。
