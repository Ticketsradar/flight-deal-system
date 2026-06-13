---
phase: 02-flexible-trip-length
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scanner.py
  - test_scanner.py
  - web/lib/types.ts
  - web/components/DestinationCard.tsx
autonomous: false
requirements: [FLEX-01, FLEX-02, FLEX-03]
must_haves:
  truths:
    - "對驗證 route(HKG-KUL / HKG-NGO)行 grid 掃描後,至少一個月嘅 periods 出現 ≥2 種唔同 trip length(return−depart)"
    - "每個 period 帶自己嘅 depart / return / price / days,google_flights deep link 對應嗰個 depart+return pair"
    - "±offset refine 只施加喺每月最平嗰批出發日,每 route-month query 數約 ~60-70(唔係 28×13 brute force)"
    - "DestinationCard 每個平價日掣顯示行程日數(N號 M日)+ 來回價 + 按價分層,撳跳對應 depart+return 嘅 Google Flights"
    - "web/ next build 過"
  artifacts:
    - path: "scanner.py"
      provides: "refine_period_lengths() 內層 return-offset 掃描 + scan_month 接駁 + --offset/--refine-days/--no-refine CLI flags + period['days'] 欄"
      contains: "def refine_period_lengths"
    - path: "test_scanner.py"
      provides: "refine 揀平日 + clamp [2,14] + days 計算 + query budget 上限 嘅離線單元測試"
      contains: "def test_"
    - path: "web/lib/types.ts"
      provides: "Period.days?: number | null 欄"
      contains: "days"
    - path: "web/components/DestinationCard.tsx"
      provides: "stayDays() 優先用 p.days、summary 行 trip-length 範圍(唔再假設單一長度)"
      contains: "stayDays"
  key_links:
    - from: "scanner.scan_month"
      to: "scanner.refine_period_lengths"
      via: "fixed-stay grid 出 periods → 取最平 N 日 → ±offset 內層取最平 → 回寫 period"
      pattern: "refine_period_lengths"
    - from: "scanner.refine_period_lengths"
      to: "scanner.query_roundtrip"
      via: "每個平日嘅 dur−offset…dur+offset return 各查一次"
      pattern: "query_roundtrip"
    - from: "db.cheap_flight_rows"
      to: "Supabase cheap_flights.periods jsonb"
      via: "mo['periods'] 原樣寫入(已含新 days 欄)"
      pattern: "periods"
    - from: "web/components/DestinationCard.tsx"
      to: "Period.days"
      via: "stayDays(p) 優先 p.days,fallback return−depart"
      pattern: "p\\.days"
---

<objective>
為每條 route × 月,令每個平價出發日帶**自己嘅行程日數(trip length)**,而唔再全部固定一種日數。做法 = Phase 1 拍板嘅 FALLBACK:喺現有 `--grid` 揾到嘅平價出發日上,加一個薄薄嘅 `dur−offset … dur+offset` return-offset 內層(模仿參考網站嘅 dur±2 window),逐個平日取最平嗰個 return,clamp 落 [2,14] 晚,回寫做嗰日嘅 period。query 數受控:±offset **只施加喺每月最平嗰批出發日**(NOT 全部 28 日)。

數據經現有 `upload.py` → Supabase `cheap_flights.periods` (jsonb) → 網站 `DestinationCard.tsx`。UI 已逐 period 計並顯示行程日數,所以只需極少改動。

Purpose: 達成 FLEX-01/02/03 — 用戶喺目的地卡見到多種行程日數嘅平價日(11號 6日 / 13號 4日 …),按價分層,撳跳對應 depart+return 嘅 Google Flights。
Output: scanner.py 變長度 periods、可選 `days` 欄、最小 UI 微調、1–2 條 route 嘅 live 驗證(grid + refine 出 ≥2 種 trip length)。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-flexible-trip-length/02-CONTEXT.md
@.planning/research/REFERENCE-SITE.md
@CLAUDE.md
@scanner.py
@routes.yaml
@db.py
@web/components/DestinationCard.tsx
@web/lib/types.ts
@web/AGENTS.md
</context>

<artifacts_this_phase_produces>
New symbols / flags / fields introduced by this phase (executor MUST create exactly these names; downstream Phase 3 全量重掃會 reuse):

| Symbol | File | Kind | Notes |
|--------|------|------|-------|
| `refine_period_lengths(...)` | scanner.py | function | 內層 return-offset 掃描;入參見 Task 1 |
| `--offset` | scanner.py | CLI flag (int, default 2) | return-offset 闊度(dur−offset…dur+offset);±2 = 5 個 return |
| `--refine-days` | scanner.py | CLI flag (int, default 10) | 每月對最平頭 N 個出發日施加 refine |
| `--no-refine` | scanner.py | CLI flag (bool) | 停用 refine,退回純 fixed-stay grid(舊行為) |
| `period["days"]` | scanner.py / db jsonb | field (int) | = (return − depart) 日數;同步落 Period type |
| `MIN_NIGHTS` / `MAX_NIGHTS` | scanner.py | const (2 / 14) | clamp 範圍 |
| `Period.days?` | web/lib/types.ts | optional field (`number \| null`) | 顯式 trip length;前端 stayDays fallback 照留 |
| `test_scanner.py` | repo root | test file | 離線單元測試(uv run python test_scanner.py) |

不改 db.py / upload.py / schema.sql:`periods` jsonb 原樣寫入,新 `days` key 自動跟住入庫(jsonb 無 schema 限制)。
</artifacts_this_phase_produces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: scanner.py 加 refine_period_lengths return-offset 內層 + days 欄 + CLI flags + 單元測試</name>
  <files>scanner.py, test_scanner.py</files>
  <read_first>
    - scanner.py L460-529 `scan_month()` — fixed-stay grid pass 點砌 `oks` / `periods`(每 depart 一筆,price 升序),`best` 點揀。
    - scanner.py L234-285 `query_roundtrip()` — 查一對 depart/return,回 `{status, price, airline, stops, tfs, via, ...}`;reuse 佢(已有 seat 參數)。
    - scanner.py L306-307 `deep_link()` — 由 tfs 砌 GF URL;refine 後嘅 period 要用新 depart+return 嘅 tfs。
    - scanner.py L443-458 `cool_down()` / `rest_or_abort()` — 既有 pacing;refine 嘅每個 query 都要行返同一套 delay/cool_down(鐵律 4)。
    - scanner.py L51-57 module const(SAMPLE_DAYS / COOL_EVERY 等)— 喺呢度加 `MIN_NIGHTS=2` / `MAX_NIGHTS=14`。
    - scanner.py L344-381 `main()` argparse — 喺呢度加 `--offset` / `--refine-days` / `--no-refine`。
    - test_db.py L1-30 — 既有離線測試風格(plain asserts + `uv run python test_X.py`,sys.exit 退碼);test_scanner.py 跟同一風格。
  </read_first>
  <behavior>
    refine_period_lengths(origin, dest, periods, dur, refine_days, offset, currency, browser, query_fn, ...) 行為:
    - Test 1 (揀平日): periods 已 price 升序;refine 只施加喺頭 `refine_days` 個 period(其餘原樣保留)。傳入 15 個 period、refine_days=10 → 只有頭 10 個會被 query_fn 觸碰。
    - Test 2 (offset 範圍 + clamp): 對一個平日,生成嘅 candidate return offsets = dur−offset … dur+offset(offset=2 → 5 個 nights 值),但 clamp 落 [MIN_NIGHTS, MAX_NIGHTS];e.g. dur=3, offset=2 → nights 應為 {2,3,4,5}(1 被 clamp 走,去重),NOT 含 1 或 0。dur=13, offset=2 → {11,12,13,14}(15 被 clamp)。
    - Test 3 (取最平): 用 fake query_fn 回唔同價,refine 後嗰日 period 嘅 price/return/days 對應**最平**嗰個 offset(若所有 offset 都貴過原本 fixed-stay 價,保留原本 period — 唔好倒退變貴)。
    - Test 4 (days 欄): 每個輸出 period 帶 `days` = (date(return) − date(depart)).days,整數;且 fixed-stay 原始 period(未 refine 嗰啲)都要補返 `days` 欄。
    - Test 5 (query budget): refine_days=10、offset=2(每日 5 個 return,當中 1 個 = 原本 fixed-stay 已知無謂重查 → 跳過,實際每日 ~4 個新 query)→ 每 route-month refine 新增 query ≤ refine_days × (2×offset) = 40;連原本 grid ~28 → 總 ~60-70。寫一個 assert 守住「refine 新增 query 數 ≤ refine_days × 2 × offset」。
    - Test 6 (google_flights): refine 換咗 return 嘅 period,其 `google_flights` 用新 depart+return pair 嘅 tfs(透過 query_fn 回嘅 tfs → deep_link),NOT 舊 fixed-stay 嗰條。
  </behavior>
  <action>
    喺 scanner.py 加 module const `MIN_NIGHTS = 2` 同 `MAX_NIGHTS = 14`(放喺現有 const block L51-57 附近)。

    新增函數 `refine_period_lengths(origin, dest, periods, dur, refine_days, offset, currency, browser, query_fn=query_roundtrip, on_query=None)`:
    - `periods` 係 scan_month 已砌好、price 升序嘅 list(每筆有 depart/return/price/airline/google_flights/tfs)。
    - 對頭 `refine_days` 個 period:解析 depart 做 date;對每個 nights ∈ unique(clamp(dur−offset … dur+offset, MIN_NIGHTS, MAX_NIGHTS)),計 candidate return = depart + nights。
    - 跳過 nights == 原本 fixed-stay dur 嗰個(嗰價已知,慳一個 query)。對其餘每個 candidate 叫 `query_fn(origin, dest, depart, ret, currency, browser)`。每 query 後叫 `on_query`(由 scan_month 注入,行 pace/stats/delay/cool_down/guard,同 grid pass 一致 — 鐵律 4)。
    - 收集成功(status==ok)candidate,連同原本 fixed-stay period,揀最平嗰個做呢日嘅新 period(price 越低越好;打和保留原 fixed-stay)。新 period 帶 depart / return(用最平 candidate 嘅)/ price / airline / `days` = (return−depart).days / `google_flights` = deep_link(該 candidate tfs, currency)。
    - 其餘冇 refine 嘅 period:原樣保留,但補 `days` 欄。
    - 回新 periods list(仍 price 升序 — refine 後重新 sort by price)。
    - **唔好**喺 action 入面用 raw query;一律經 query_fn + on_query,等 pacing/stats 同 grid pass 共用。

    喺 `scan_month()`:fixed-stay grid pass 砌好 `oks`/`top`/`periods` 之後(L496-508 之後),若 `not no_refine` 且 `args.grid`,將 `top`(或 periods)交畀 `refine_period_lengths(...)`,用 route 嘅 stay_nights 做 dur、`refine_days`/`offset` 由 args 傳入。注意 scan_month 而家係 main() 內嵌 closure,可以直接讀 args / pace / guard / cool_down / rest_or_abort;`on_query` callback 包住「pace['q']+=1; stats['queries']+=1; tier2 計數; delay; cool_down(); guard.consec 更新」嗰套(同 L472-495 一致),refine 嘅 fail 都要 feed 入 guard.consec → rest_or_abort 機制。`best`/月層 summary 用 refine 後 periods[0]。確保 month-level `depart`/`return`/`price`/`google_flights` 跟 refine 後最平。

    喺 main() argparse 加:`--offset`(int default 2)、`--refine-days`(int default 10)、`--no-refine`(store_true)。傳落 scan_month。**注意**:offset/refine_days 係 Claude's discretion 嘅預設值 — ±2(5 個 return,跳過已知 1 個 = ~4 新 query/日)× 最平 10 日 ≈ 每 route-month +40 query,連 grid ~28 = ~60-70,合 CONTEXT 目標。喺 scanner.py module docstring 補一段講 refine 策略 + query budget。

    建立 `test_scanner.py`(離線、無網絡):用 monkeypatch / 注入嘅 fake `query_fn`(回造數 dict,含 tfs/price/airline/status)測 Test 1-6。跑法 `uv run python test_scanner.py`,全 pass exit 0 / 任一 fail exit 1(跟 test_db.py 風格)。fake query_fn 唔好真連 Google。
  </action>
  <verify>
    <automated>cd /Users/alvinlai/Downloads/flight-deal-system && export PATH="$HOME/.local/bin:$PATH" && uv run python test_scanner.py</automated>
  </verify>
  <acceptance_criteria>
    - `test_scanner.py` 全綠(Test 1-6 通過):refine 只碰頭 refine_days 個平日、offset clamp 落 [2,14]、取最平、days 欄正確、query budget assert 守住、google_flights 用新 pair。
    - `refine_period_lengths` / `--offset` / `--refine-days` / `--no-refine` / `MIN_NIGHTS` / `MAX_NIGHTS` / `period["days"]` 全部存在於 scanner.py。
    - `python -c "import ast; ast.parse(open('scanner.py').read())"` 過(語法無破)。
    - refine 嘅每個 query 都經 on_query(pace/delay/cool_down/guard)— grep scan_month 內 refine 接駁見到 on_query 注入,無 raw query_roundtrip 繞過 pacing。
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: web Period.days 欄 + DestinationCard 微調 + next build</name>
  <files>web/lib/types.ts, web/components/DestinationCard.tsx</files>
  <read_first>
    - web/AGENTS.md — ⚠️ 改 web/ 前**必讀** `node_modules/next/dist/docs/`(呢個唔係你記憶中嗰個 Next.js;有 breaking changes)。改任何 web/ code 前先 `ls web/node_modules/next/dist/docs/` 搵相關 guide 讀。
    - web/lib/types.ts L5-11 `Period` interface — 加 `days?: number | null`。
    - web/components/DestinationCard.tsx L10-13 `stayDays(p)` — 而家純靠 return−depart 計;改成優先用 `p.days`,fallback 照計。
    - web/components/DestinationCard.tsx L62 + L89 — summary 嗰句 `· {stay}日` 假設**單一** trip length(用 all[0]);Phase 2 之後一個目的地會有多種長度,要改成範圍(min–max 日)或攞走。
    - web/components/DestinationCard.tsx L113-136 — 每個平價日掣已渲染 `stayDays(p) 日` + 價 + 分層 + GF link;呢部分基本唔使改,確認 days 顯示行得通。
  </read_first>
  <action>
    1. `web/lib/types.ts`:`Period` interface 加 `days?: number | null`(optional — 舊 row 冇都唔會炸)。

    2. `web/components/DestinationCard.tsx`:
       - `stayDays(p)` 改成:若 `p.days != null` 直接回 `p.days`,否則 fallback 現有 `(return−depart)` 計法(保留 null-guard)。
       - summary 嗰句(L62 `const stay = …` + L89 顯示)而家假設單一長度。改成計**範圍**:由全部 period 嘅 stayDays 取 min/max,顯示「{min}–{max}日」(min==max 就顯示「{min}日」),冇有效日數就唔顯示。NOT 再淨係用 all[0]。
       - 每月平價日掣(L113-136)維持逐 period 顯示「N號 M日」+ 價 + 分層,唔使改邏輯,只確認 `stayDays(p)` 而家會優先攞 `p.days`。
       - 唔好引入新 dependency、唔好改其他 component。改動範圍只限呢兩個檔。

    3. **改之前**先讀 `web/node_modules/next/dist/docs/` 入面同 client/server component / build 相關 guide(AGENTS.md 鐵律),確認冇用到已 deprecated 嘅 API。本檔係純展示 component,理應只係 TSX 邏輯改動。
  </action>
  <verify>
    <automated>cd /Users/alvinlai/Downloads/flight-deal-system/web && export PATH="$HOME/.local/bin:$PATH" && npx next build 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `web/lib/types.ts` 嘅 `Period` 有 `days?: number | null`。
    - `DestinationCard.tsx` `stayDays` 優先用 `p.days`、summary 顯示 trip-length 範圍(min–max,單一長度時顯示單值)、平價日掣照逐 period 顯示日數+價。
    - `npx next build` 過(0 type / build error)。
    - 無新 npm dependency 加入(`git diff web/package.json` 無變)。
  </acceptance_criteria>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    scanner.py 多咗 return-offset refine 內層(平價日帶可變 trip length),web Period 多咗 days 欄、DestinationCard 顯示行程日數範圍。executor 已對 **1–2 條驗證 route**(HKG-KUL、HKG-NGO — 即參考網站張相嗰兩條)行咗:

    ```
    uv run python scanner.py --only HKG-KUL --grid --months 2 --no-browser --offset 2 --refine-days 10
    uv run python scanner.py --only HKG-NGO --grid --months 2 --no-browser --offset 2 --refine-days 10
    ```

    並 inspect `data/scan_*.json`:確認該 route 至少一個月嘅 `periods` 出現 **≥2 種唔同 `days`**(trip length),每筆帶 depart/return/price/days/google_flights。executor 亦本機跑 `cd web && npx next dev -p 3000` + Playwright 截圖,證實展開卡見到「N號 M日」多種日數 + 分層 + 撳跳對應 GF。

    ⚠️ 注意:Google Flights 重度反爬,grid+refine query 量大,真 live 跑可能部分 query 被擋或 beyond_data — 只要驗證 route 有一個月出到 ≥2 種 trip length 嘅 periods 就算達標(Phase 2 唔需要全量,全量重掃係 Phase 3)。
  </what-built>
  <how-to-verify>
    1. 睇 executor 貼出嘅 `data/scan_*.json` 摘錄 — 確認 HKG-KUL 或 HKG-NGO 某月 `periods` 有 ≥2 種 `days` 值(例如 4 日同 6 日),且每筆 `google_flights` link 嘅 tfs 對應自己嗰個 depart+return。
    2. 睇 executor 貼出嘅本機截圖 — 確認展開目的地卡見到唔同出發日帶唔同行程日數(似參考網站「11號 6日 / 13號 4日」),按價分層(綠/青/黃),summary 顯示日數範圍。
    3. (可選)自己撳一個平價日掣,確認跳去對應 depart+return 嘅 Google Flights 對返實時價(FLEX-03)。
    4. 確認 `next build` 過(Task 2 verify log)。
  </how-to-verify>
  <resume-signal>打 "approved" 或者講邊度唔啱(例如想 offset ±3、想 refine 多啲日、UI 想點改)</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| scanner → Google Flights | 出站爬蟲(HTTP + Playwright);refine 內層**增加** query 量,可能觸發 rate-limit / block |
| scan_*.json → Supabase → web | 自家產出嘅 jsonb(`periods`,含新 `days`);無第三方輸入跨界 |

無新 auth / secret / 第三方輸入引入(Phase 2 全部係自家爬蟲 + 自家數據形狀)。鐵律 1(key 只喺 .env / Secrets)、鐵律 4(delay/retry/rate-limit)維持不變。

## STRIDE Threat Register (ASVS L1; block_on=high)

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-01 | Denial of Service (自招被封) | scanner refine 內層 query 量上升 | mitigate | refine **只施加最平 refine_days(10) 個出發日**,offset 預設 ±2(跳過已知 fixed-stay 那一個 → 每日 ~4 新 query),每 route-month 封頂 ~60-70;refine 嘅每個 query 一律經既有 `on_query`/`cool_down`/`rest_or_abort` pacing(鐵律 4),NOT raw query。test_scanner Test 5 用 assert 守住 query budget 上限。 |
| T-02-02 | Tampering (爬到嘅價/日期錯配) | period 嘅 days / google_flights 對唔上 depart+return | mitigate | `days` = (return−depart) 由**儲低嘅 date pair** 計(同參考網站一致,0 mismatch 模型);`google_flights` 用最平 candidate 自己嘅 tfs(deep_link);test Test 4/6 驗證 days 正確 + link 用新 pair;前端 stayDays fallback 再計一次做雙保險。 |
| T-02-03 | Information Disclosure | .env key / Supabase secret | accept | Phase 2 唔掂 secret;沿用既有鐵律(SUPABASE_SECRET_KEY 只喺 .env / Secrets,唔入前端 NEXT_PUBLIC)。無新暴露面。 |
| T-02-04 | Tampering | npm/pip/cargo installs | accept | Phase 2 **唔加任何新 package**(scanner 用現有 fast-flights/playwright;web 無新 dependency — Task 2 acceptance 已守 package.json 無變)。無新供應鏈面 → 無 legitimacy gate 需要。 |
</threat_model>

<verification>
## Phase-level checks (tie to ROADMAP Phase 2 success criteria)

1. **FLEX-01**(多種行程日數):驗證 route 某月 `periods` 有 ≥2 種 `days` → Task 1 test + checkpoint inspect scan_*.json。
2. **FLEX-02**(每日標明日數+價+分層):DestinationCard 逐 period 顯示「N號 M日」+ 價 + priceTier 分層 → Task 2 + checkpoint 截圖。
3. **FLEX-03**(撳跳對應 GF):每 period `google_flights` 用自己 depart+return 嘅 tfs → Task 1 Test 6 + checkpoint 點掣驗證。
4. **build/数據形狀**:`next build` 過(Task 2),`periods` jsonb 帶 days 寫得入 Supabase(db.cheap_flight_rows 原樣帶 mo['periods'],無需改 db.py — jsonb 無 schema 限制)。

## Commands
- `uv run python test_scanner.py`(離線單元,Task 1)
- `cd web && npx next build`(Task 2)
- `uv run python scanner.py --only HKG-KUL --grid --months 2 --no-browser --offset 2 --refine-days 10`(checkpoint live 驗證 — 真連 Google)
</verification>

<success_criteria>
- [ ] `refine_period_lengths` 喺平價出發日加 `dur±offset`(clamp [2,14])return-offset 內層,取最平,回寫 period(帶 `days`)。
- [ ] query 受控:每 route-month refine 新增 ≤ refine_days × 2 × offset(預設 ≤40),總 ~60-70,經既有 pacing(鐵律 4)。
- [ ] `period["days"]` + `Period.days?` 落 scanner + types.ts;DestinationCard `stayDays` 優先用之、summary 顯示日數範圍。
- [ ] 驗證 route(HKG-KUL / HKG-NGO)某月 `periods` 出 ≥2 種 trip length(checkpoint 確認)。
- [ ] `test_scanner.py` 全綠;`next build` 過;無新 npm/pip package。
- [ ] FLEX-01 / FLEX-02 / FLEX-03 全部 demonstrable。
</success_criteria>

<output>
Create `.planning/phases/02-flexible-trip-length/02-01-SUMMARY.md` when done.
</output>
