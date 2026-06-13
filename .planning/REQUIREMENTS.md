# Requirements: Flight Deal System — Amendments Milestone

**Defined:** 2026-06-14
**Core Value:** 畀香港用戶一個可信、每日更新嘅地方,快速搵到值得買嘅平機票同真·錯價票,並一撳對返 Google Flights 實時價。

## v1 Requirements

今個 milestone 嘅 committed 範圍。每個 map 去一個 roadmap phase。

### Flex (彈性行程日數)

- [ ] **FLEX-01**: 用戶喺每張目的地卡,睇到**多種行程日數**(2–14 日範圍)嘅平價出發日,而唔再淨係固定一種日數
- [ ] **FLEX-02**: 每個平價日子清楚標明**行程日數 + 來回價**(似參考網站「11號 6日」),並按價分層顯示最平 / 次平 / 第三平
- [ ] **FLEX-03**: 撳任何一個平價日子,跳去對應日期 + 行程長度嘅 Google Flights 對返實時價

### Daily (每日更新)

- [ ] **DAILY-01**: 平機票數據**每日自動更新一次**(可靠,取代而家 ~3 日一次嘅東拼西湊)
- [ ] **DAILY-02**: 網站每張卡(或全站)顯示**真實「最後更新」**時間,反映實際新鮮度
- [ ] **DAILY-03**: 更新過程**容錯**:就算部分掃描失敗/超時,已完成部分照樣出街(唔會成日 0 更新)

### Misprice (自家錯價偵測 + 社交來源 scout)

- [ ] **MISP-01**: 系統由自己每日掃嘅價,**自動偵測**「某條線異常平」嘅疑似錯價(統計異常,per route×月×艙)
- [ ] **MISP-02**: 偵測到嘅候選**餵入現有 master agent** 核實 live/dead,再經現有 Telegram + 網站錯價區出(零新核實 code)
- [ ] **MISP-03**: 保留並穩固現有 RSS 來源(theflightdeal / fly4free / Reddit `.rss`),與自家偵測並行
- [ ] **MISP-04**: 小紅書(RedNote / Xiaohongshu)scout — crawl 小紅書 收料,篩疑似錯價,餵入現有 master 核實(原 Phase 5;MediaCrawler + cookie/session 登入,session 檔 gitignored)
- [ ] **MISP-05**: Facebook / Instagram scout — 收 FB/IG flight-deal 來源收料,篩疑似錯價,餵入現有 master 核實(原 Phase 6;Apify 或半人手)

### Data (基建)

- [ ] **DATA-01**: 加 append-only `price_history` 表儲每日掃價歷史,並由現有 dated `scan_*.json` backfill,畀 MISP 異常偵測用

## v2 Requirements

承認但暫時唔做,唔入今個 roadmap。

### Sources

- **SRC-01**: `feeds.py` 加 Playwright fallback,解鎖 Secret Flying / FlyerTalk(畀 Cloudflare 擋緊嘅來源)
- **SRC-02**: 商務艙(business/first)錯價專掃 + J/F-vs-Y 比例旗

### Grid

- **GRID-01**: 用付費 API(SearchApi.io / Amadeus)選擇性補掃,做真·硬性完整 2–14 日 grid

## Out of Scope

| Feature | Reason |
|---------|--------|
| 付費 API 做完整 2–14 grid（v1） | user 揀咗免費路線;參考網站本身都唔係真 grid |
| Twitter / X 收料 | 2026 Nitter 死、X API 冇免費 tier,ROI 低 |
| 即時 real-time 入網站先查價 | 沿用 cache / 靜態模型,成本 + 反爬考量 |
| Production LLM(`anthropic` provider)上雲自動跑錯價 scout | 要 API 開支,留到 go-live 後再決定;今個 milestone 聚焦數據 + 偵測能力 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FLEX-01 | Phase 2 | Pending |
| FLEX-02 | Phase 2 | Pending |
| FLEX-03 | Phase 2 | Pending |
| DAILY-01 | Phase 3 | Pending |
| DAILY-02 | Phase 3 | Pending |
| DAILY-03 | Phase 3 | Pending |
| MISP-01 | Phase 4 | Pending |
| MISP-02 | Phase 4 | Pending |
| MISP-03 | Phase 4 | Pending |
| DATA-01 | Phase 4 | Pending |
| MISP-04 | Phase 5 | Pending |
| MISP-05 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12 ✓
- Unmapped: 0 ✓

> Phase 1（Travelpayouts 覆蓋率 Spike)係決策閘,唔直接 map 任何 v1 requirement — 佢交付一個有證據嘅數據源決定,解鎖 FLEX-*(Phase 2)同 DAILY-*(Phase 3)嘅實作路徑。

---
*Requirements defined: 2026-06-14*
*Last updated: 2026-06-14 — 社交來源 scout 由 v2 升做 v1 committed scope(MISP-04 小紅書 / MISP-05 FB·IG),v1 count 10 → 12,新增 Phase 5/6,12/12 mapped*
