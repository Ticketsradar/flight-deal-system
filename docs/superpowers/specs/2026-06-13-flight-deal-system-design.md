# Flight Deal System — 增強版設計文件(Design Spec)

> 日期:2026-06-13　|　狀態:設計已經 user 通過,準備入「寫實作計劃」階段
> 對象:非程式員 owner(廣東話溝通,技術名詞保留 English)。本文係 brainstorming 出嚟嘅 single source of truth,實作時對住佢做。

---

## 1. 目標

全自動、每日定時跑、**零人手**嘅平機票 + error fare(錯價票)偵測系統,香港(HKG)/ 深圳(SZX)/ 廣州(CAN)出發,涵蓋未來 12 個月。分兩條獨立 stream:

- **Stream A — 平機票掃描**:掃 57 條航線 × 12 個月,搵每條線每月最平來回價(已建好)。
- **Stream B — 錯價情報**:AI scout 每日由社交平台 / 錯價網收料,篩出疑似錯價;master 核實仲買唔買到,生成 booking 連結。

結果經純 code 合併 → 寫入 Supabase → (a) Telegram 即時推送 owner;(b) Next.js 網站(Vercel)公開顯示。

---

## 2. 決定紀錄(Decision Log)— 本次 brainstorm 鎖定

| # | 議題 | 決定 |
|---|---|---|
| D1 | 系統節奏 | **即時 Telegram 推送 + 每日網站**。錯價靠推送爭取時間;網站做紀錄 + 平機票。 |
| D2 | Trip.com | **只做 deep link**(唔抓價)。冇個人開發者用嘅免費 API,直接爬易壞。價格靠免費 Google Flights。 |
| D3 | Scout 平台範圍 | **全部**(Reddit + 錯價網 RSS + 小紅書 + FB/IG),但**由穩到險分階段上線**。 |
| D4 | 預算 | **盡量 $0**。全行免費 / 公開途徑;唔用付費 Apify / 大額 API。 |
| D5 | FB/IG 收料 | **淨用免費 RSSHub**(出名最唔穩,當「有就賺」)。 |
| D6 | 小紅書收料 | **RSSHub 先試**(免登入、冇封號風險);太少料先後備 MediaCrawler。 |
| D7 | 細 airline / Google Flights 查唔到嘅錯價 | **唔丟棄**,標 `unverified`,連原文連結照樣 **Telegram 通知 owner** 自己快手查。 |
| D8 | 最尾合併 | **純 code,唔用 LLM agent**(智能判斷已喺 scout / master 做晒)。 |
| D9 | Telegram | **私人(owner)+ 公開頻道(訪客)都做**。 |
| D10 | 網站背景 | **全頁風景相背景 + 磨砂玻璃卡 + 自動慢慢淡入淡出**,~15 張免費授權靚景。 |
| D11 | 腦配置 | Scout = **Haiku**,Master = **Sonnet**。**唔用 MiniMax M3**(刪走原 M3 vs Haiku 驗證週)。試跑行 Max plan($0),production 切 Anthropic API。 |

---

## 3. 整體架構 + 數據流

```
                    每日 GitHub Actions cron(全自動,$0)
                                    │
        ┌───────────────────────────┴───────────────────────────┐
  STREAM A — 平機票掃描【已建好】              STREAM B — 錯價情報【要建】
  scanner.py → fast-flights(Google Flights)   一個 RSS scout 讀晒所有 feed:
  57 線 × 12 月 × 每月最平                        Reddit .json / 錯價網 RSS /
  → Google Flights deep link                     小紅書 RSSHub / FB·IG RSSHub
        │                                                   │
        │                                       Scout 腦(Haiku)按 signal 篩 → JSON
        │                                                   │
        │                                       consolidate.py(純 code 去重)
        │                                                   │
        │                                       Master 腦(Sonnet)三層核實(≥70 先核)
        │                                       → live / dead / unverified 三 bucket
        │                                       → Google Flights + Trip.com 連結
        └───────────────────────────┬───────────────────────────┘
                                     │
                    FINAL 合併(純 code,唔用 LLM)
                    → 寫入 Supabase(平機票表 + 錯價表 + 更新時間)
                                     │
                  ┌──────────────────┴──────────────────┐
          Telegram bot(免費)                     Next.js 網站(Vercel,免費)
          live + unverified 即推 owner              全頁風景背景 + 玻璃卡
          + 公開頻道(訪客可加入)                   兩專區 + 篩選 + 熱力圖 + 免責聲明
```

**核心原則:兩條 stream 完全獨立,一條壞咗另一條照出嘢。**

---

## 4. Stream A — 平機票掃描(已建好,recap)

- `scanner.py`(v3.1)用 `fast-flights`(免費逆向 Google Flights):HTTP 為主,Playwright 真瀏覽器後備。
- 讀 `routes.yaml`(3 origins × 57 destinations);每月抽樣(`samples_per_month`)減 request;隨機 delay 3–8 秒;`--resume` 接力;原子寫檔 + 低碟保護。
- 輸出 `data/scan_YYYYMMDD.json`(route × 月份 × 最平價 × Google Flights deep link)。
- **餘下收尾**:跑全量 171 routes、人手對 2 條 link。

---

## 5. Stream B — 錯價情報(要建)

### 5.1 收料:統一「RSS feed」做法
一個 scout 程式讀晒 `sources.yaml` 列出嘅所有 feed,normalize 成「最近貼文」清單。**加平台 = 加一行 feed URL,唔使寫新 code。**

| 來源 | 方法 | 穩定度 | 上線階段 |
|---|---|---|---|
| Reddit | 原生 `.json`(自己控制,帶 user-agent + 2–3s delay + 處理 429) | 🟢 高 | Phase 1B |
| 錯價網(Secret Flying / Fly4free 等) | 佢哋原生 RSS | 🟢 高 | Phase 1B |
| 小紅書 | RSSHub(免登入);太少料後備 MediaCrawler | 🟠 中 | Phase 5 |
| FB / IG | 免費 RSSHub(當「有就賺」) | 🔴 低 | Phase 6 |
| Telegram(第時想加) | RSSHub | 🟠 中 | 將來 |

任何 feed 壞咗:靜靜 skip + log,唔影響其他來源。

### 5.2 Scout 腦(Haiku)
- 逐條 feed 貼文原文 → `call_llm("scout", ...)`,system prompt 引用 `sources.yaml` 嘅 `filters`(origins / horizon / error-fare signals)。
- **只回 JSON**:`origin / destination / depart_date / return_date / price / currency / airline / source_platform / source_url / confidence`。
- 平嘢、唔關 HKG/SZX/CAN、純廣告 → 丟。

### 5.3 consolidate.py(純 code)
多條 feed 撞同一張票 → 按(airline + 航線 + 日期)去重,留 confidence 最高嗰條。唔用 LLM。

### 5.4 Master 腦(Sonnet)— 三層核實
只核 `confidence ≥ 70` 嘅候選(成本主閘):

1. **第 1 層|Google Flights 重查(fast-flights)**:cover 到 → 重查實價 → 標 `live`(仲買到 + 實價)或 `dead`(價已返正)。
2. **第 2 層|booking link 死活檢查(可選,後期做)**:貼文有 direct booking URL → Playwright 開頁睇仲 load 到嗎(非 404 / sold out)。弱訊號,core 唔靠。
3. **第 3 層|未能核實 bucket**:細 airline / Google Flights 查唔到 → **唔丟棄**,標 `unverified`,保留原文連結、claimed 價、airline、日期、confidence。

輸出三 bucket:`live` / `unverified` / `dead`,每個都帶 Google Flights deep link(cover 到先有)+ Trip.com 搜尋連結 + 原文連結。

---

## 6. 合併(FINAL,純 code)

讀 Stream A + Stream B 輸出 → 去重、排序、寫入 Supabase。**唔用 LLM**(死規矩嘅嘢,code 又快又穩又 $0)。

---

## 7. 即時推送(Telegram bot)

- **設定(一次過)**:`@BotFather` 開 bot 攞 token → 放 GitHub Secrets(`TELEGRAM_BOT_TOKEN`);owner 私人 chat id(`TELEGRAM_CHAT_ID`)+ 公開頻道 id(`TELEGRAM_CHANNEL_ID`)。
- **推送政策**:
  - `live` 確認錯價 → 即推 owner + 公開頻道 + 網站置頂。
  - `unverified` 疑似錯價(HKG/SZX/CAN,按 confidence 排序)→ 即推 owner,標明「⚠️ 未能自動核實,請自己快手入原文連結確認」。
  - `dead` → 唔推(免洗版),淨係上網站「歷史」區。
- 訊息格式:航線、價、日期、狀態、airline、Google Flights / Trip.com / 原文 連結。

---

## 8. 資料庫(Supabase)Schema

- **`cheap_flights`**(Stream A):`id, origin, destination, region, depart_date, return_date, price_hkd, currency, airline, baggage, month, gflights_url, tripcom_url, scanned_at`
- **`error_fares`**(Stream B):`id, origin, destination, airline, depart_date, return_date, claimed_price_hkd, verified_price_hkd(nullable), currency, status(live|dead|unverified), confidence, source_platform, source_url, gflights_url, tripcom_url, found_at, verified_at`
- **`meta`**:`key, value`(例:`last_updated_stream_a`, `last_updated_stream_b`)

鐵律:`sb_secret_` 只放 server-side / Secrets,**唔准入前端或 `NEXT_PUBLIC_`**。

---

## 9. 網站(Next.js + Vercel)

### 9.1 功能(保留參考網站全部 + 升級)
參考網站(flight-deals-web.vercel.app)有嘅照保留:地區 / 月份 / 預算 篩選、手提/寄艙標示、最後更新時間、撳日子去 Google Flights。**升級**:

- 兩專區:**「錯價雷達」置頂(主打)+ 「平機票」**。
- 狀態標籤:`已核實 live` / `未核實 unverified` / `已失效 dead`。
- 出發機場切換:HKG / SZX / CAN。
- **月曆熱力圖**:一眼睇晒邊個月最平(綠=平、黃=中、紅=貴),撳格直接跳該月 Google Flights。
- 折扣 %、即時提示 tie-in、手機友好、**免責聲明置頂**。
- 公開 Telegram 頻道「加入提示」CTA。

### 9.2 風景背景(D10)
- **全頁風景相背景 + 磨砂玻璃(半透明)deal 卡 + 輕微 scrim 暗化**,確保文字喺光相上都讀到。
- **自動慢慢淡入淡出**換相(約每 12 秒)。
- 圖源($0 + 合法):**免費授權圖庫**(Unsplash / Pexels / Wikimedia Commons),curate ~15 張高解析靚景,需 credit 嗰啲擺角落細字。**唔用 Google Images / 有版權圖。** Next.js Image 自動壓縮 + WebP + 手機慳流量。
- 起始景點清單(可改):Petra(約旦)、Rainbow Mountain Vinicunca(秘魯)、K2(巴基斯坦)、Moraine Lake Banff(加拿大)、張掖丹霞、Plitvice(克羅地亞)、Salar de Uyuni(玻利維亞)、Faroe Islands、Torres del Paine(智利)、下龍灣、Cappadocia(土耳其)、Lofoten(挪威)、富士山、Antelope Canyon、Socotra(也門)。

---

## 10. 自動化(GitHub Actions cron)

- **雙 cadence**(慳額度又新鮮):
  - `stream_a`(重型 Google Flights 全掃 + Playwright)→ **一日一次**。
  - `stream_b`(輕量 RSS 讀取 + master 核實 + Telegram 推送)→ **一日幾次**(例如每 3 小時)。
- **Secrets**:`CLAUDE_CODE_OAUTH_TOKEN`(試跑)/ `ANTHROPIC_API_KEY`(production)、`SUPABASE_URL` + `SUPABASE_SERVICE_KEY`、`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` + `TELEGRAM_CHANNEL_ID`、`REDDIT_USER_AGENT`、(可選)`SERPAPI_KEY`。
- **建議 repo 設 public**:GitHub Actions 免費無上限(private 每月 2000 分鐘);所有 key 放 Secrets,唔入 code。

---

## 11. LLM 路由 / 腦配置

- 全部 call 經 `llm.py`,provider 由 `.env` 決定。
- **Scout = Haiku;Master = Sonnet。唔用 MiniMax M3。**
- 試跑:`SCOUT_PROVIDER=claude_code`(model `haiku`)、`MASTER_PROVIDER=claude_code`(model `sonnet`)→ 行 Max plan,$0。
- Production:切 `anthropic` provider(`ANTHROPIC_API_KEY`),scout 仍用 `haiku`、master 用 `sonnet`。
- 成本控制:master 只核 `confidence ≥ 70`;Sonnet 係 production 主要成本。

---

## 12. 建造次序(Roadmap)

| # | 階段 | 完成標準 |
|---|---|---|
| ① | **1A 收尾**(Stream A) | 全量 171 routes 跑完 + 人手對 2 條 link |
| ② | **1B｜RSS scout** 🟢 | Reddit + 錯價網 RSS → Haiku 篩 → consolidate 去重 → 本地 JSON;跑一日出到合理 candidate |
| ③ | **2｜master 三層核實** 🟢 | 三 bucket 分得啱、連結撳到 |
| ④ | **2.2｜Telegram 推送** 🟢 | 手機收到真提示(live + unverified) |
| ⑤ | **2.5｜Supabase** 🟢 | 兩條 stream 寫入 DB、網站讀到 |
| ⑥ | **3｜Next.js 網站 + Vercel** 🔵 | deploy 到、手機靚、風景背景 + 玻璃卡、對 2 deal |
| ⑦ | **4｜GitHub Actions 全自動** 🟢 | 雙 cadence + Secrets,連跑 2–3 日零人手 |
| ⑧ | **5｜小紅書 scout** 🟠 | RSSHub 接到,壞唔到核心 |
| ⑨ | **6｜FB/IG scout** 🔴 | 免費 RSSHub,加 feed 即得,有就賺 |

> 做到 ⑦,owner 已有一個「完全自動、每日跑、會 Telegram 通知」嘅網。⑧⑨ 係純加料。

---

## 13. 風險紅旗

1. **錯價 vs 每日跑**:即時推 + B 一日幾次已緩解,但社交 / RSS 本身有延遲 — **真‧搶到 live 錯價會係少數,`unverified` 提示居多**,要管理預期。
2. **fast-flights 隨時俾 Google 改壞**(最大長期技術風險)→ Playwright + SerpApi 後備 + 降級唔當機,但間中可能要修。
3. **RSSHub(尤其 IG/FB)唔穩** → 當「有就賺」,核心唔靠。
4. **ToS / 法律**:各平台 scraping 多數違反佢哋 ToS(民事層面);**買錯價票本身係消費者合法行為**;靠免責聲明 + 免費授權圖 + 個人非商業用途控制風險;若將來商業化 / 大流量要再評估。
5. **成本**:production Sonnet master 係主成本 → confidence≥70 閘控制;試跑 Max plan $0。

---

## 14. 鐵律(security / 負責任做法)

1. 所有 key 只存 `.env`(本機)+ GitHub Secrets(CI);`.gitignore` 包 `.env`、`data/`、cookie/session 檔。
2. **唔准喺全域 shell set 任何 API key**(會搶 Claude Code 訂閱認證)。
3. Supabase `sb_secret_` 唔准入前端 / `NEXT_PUBLIC_`。
4. 對外 request(Google / Reddit / RSSHub / 參考網站)一律隨機 delay、retry、尊重 rate limit。
5. 網站圖只用**免費授權**來源,需要 credit 就放 credit;唔用有版權圖。
6. 網站 + 推送必須有**免責聲明**(錯價隨時失效、航空公司可能取消錯價訂單、須自行確認)。

---

## 15. 成功標準(Acceptance)

- [ ] Stream B 跑一日,出到合理錯價 candidate 清單(本地 JSON)。
- [ ] Master 正確分 live / dead / unverified;Google Flights + Trip.com 連結撳到。
- [ ] 細 airline / 查唔到嘅錯價,owner 喺 Telegram 收到帶原文連結嘅提示。
- [ ] 網站 deploy 到 Vercel,手機顯示靚(風景背景 + 玻璃卡 + 兩專區 + 篩選 + 熱力圖 + 免責聲明)。
- [ ] GitHub Actions 雙 cadence 連跑 2–3 日零人手。
- [ ] 全程 $0(試跑行 Max plan;免費 tier)。
