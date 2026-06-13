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
- [ ] **Phase 1A — routes.yaml(由參考網站抽)+ fast-flights 掃描器** ← 而家做緊(2026-06-13 已做:抽到參考網站全部 57 個目的地入 routes.yaml、scanner.py 寫好、smoke 3 條 route 通過、加咗第二輪補掃;待:user 確認清單 + 人手對 2 條 link,再揀時間跑全量 171 條)
- [x] **Phase 1B — RSS scout(Reddit `.rss` + 錯價網 RSS)+ Haiku 篩 + consolidate** ✅ 2026-06-13(`feeds.py`/`scout.py`/`consolidate.py`/`run_scout.py`;reddit `.json` 被 403 → 改用官方 `.rss`;錯價網用 theflightdeal + fly4free;Haiku 正面測試捉到 HKG 錯價、live 跑通寫 `data/candidates_*.json`;計劃見 docs/superpowers/plans/2026-06-13-phase-1b-rss-scout.md。註:reddit `.rss` 有 429,每跑約 4/7 sub 成功,多次跑輪流覆蓋,夠用)
- [x] **Phase 2 — master 核實 agent** ✅ 2026-06-13(`master.py` + `run_master.py`;triage≥70 → reuse `scanner.query_roundtrip`(加咗 seat 參數)重查 → Sonnet 判 live/dead/unverified → Google Flights + Trip.com 連結 → `data/verified_*.json`;smoke 證實 Sonnet 正確判 fake $600 HKG-NRT 為 dead(實價 $2426);計劃 docs/superpowers/plans/2026-06-13-phase-2-master-verify.md)
- [x] **Phase 2.2 — Telegram 即時推送** ✅ 2026-06-13(`notifier.py`:format_deal(HTML 訊息:航線+傳聞/重查價+日期+狀態+airline+Google Flights/Trip.com/原文 三連結+免責)、send_message(httpx POST `sendMessage`,retry/429)、notify_verified(政策路由:live 推 owner+channel / unverified 推 owner / dead 唔推);駁入 `run_master.py`,加 `--no-notify`;6 項離線測試綠;**真機 live send 通過 — user 確認部電話收到測試卡片**。bot=@hkgcheapflightscannerbot,channel 暫留空只推 owner)
- [ ] Phase 2.5 — 接 Supabase(本地 JSON 遷移過去)← 而家做緊(code 起緊;待 user 提供 SUPABASE_URL + 喺 Supabase 跑 schema.sql)
- [ ] Phase 3 — Next.js 網站 + deploy Vercel
- [ ] Phase 4 — GitHub Actions 每日 cron + Secrets
- [ ] Phase 5 — 小紅書 scout(MediaCrawler + cookie 登入)
- [ ] Phase 6 — Facebook / Instagram scout(Apify 或半人手,最後先做)

---

## 下一步:Phase 1A — routes.yaml + fast-flights 掃描器

**任務**:
1. **由參考網站抽目的地清單**:fetch https://flight-deals-web.vercel.app — 佢係 SPA,homepage HTML 淨係「載入中」;要搵佢個 JS bundle 或 data JSON(curl homepage 攞 `<script src>` / 常見路徑如 `data.json`,或者由 JS bundle 入面 grep 航點),抽出**全部目的地**(機場代碼 + 城市名),寫入 `routes.yaml`(origins: HKG/SZX/CAN × 抽到嘅 destinations)。抽完 print 個清單畀 user 過目確認。如果真係抽唔到,先用 30–50 條熱門航點預設頂住,並話畀 user 知。
2. 裝 `fast-flights` library,寫 `scanner.py`:對每條 route × 未來 12 個月,每月攞最平來回價(盡量用 calendar / date-range 方式減 request;唔得就每月抽 2–4 個代表日期)。
3. 隨機 delay 3–8 秒、retry、進度 log;被 block 時優雅降級(skip + 記低)。
4. 每條結果生成 Google Flights deep link(`tfs` 參數)。
5. 輸出 `data/scan_YYYYMMDD.json`。
6. 先用 3 條 route 做 smoke test,跑通先放大到成個清單。

**完成標準**:`routes.yaml` 有齊參考網站嘅目的地;跑一次 scanner,`data/` 有 JSON(route × 月份 × 最平價 × deep link);隨機抽兩條 link 人手撳入 Google Flights 對到價。

**之後(Phase 1B)概要**:`scouts/reddit_scout.py` 讀 `sources.yaml` 嘅 subreddit `.json` → 原文交 `llm.call_llm("scout", ...)`,system prompt 引用 `sources.yaml` 嘅 `filters` section,只回 JSON(origin/destination/dates/price/currency/source_url/confidence)→ `consolidate.py` 純 code dedup。
