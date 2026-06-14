# Phase 2 / Plan 01 — Summary

**Phase:** 02-flexible-trip-length
**Plan:** 01
**Status:** ✅ Complete (human-verify checkpoint approved 2026-06-14)
**Requirements:** FLEX-01, FLEX-02, FLEX-03 — all delivered

## What was built

**`scanner.py`** — 加 `refine_period_lengths()` return-offset 內層:
- 喺每月 fixed-stay grid pass 揾到嘅平價出發日,**只對最平頭 `--refine-days`(預設 10)個日**加掃 `dur−offset … dur+offset`(預設 `--offset 2` = ±2 日,clamp 落 `[MIN_NIGHTS=2, MAX_NIGHTS=14]`)嘅 return,逐日取最平,回寫做嗰日嘅 period(帶自己嘅 `days`)。打和保留原 fixed-stay(唔倒退變貴)。
- 跳過 nights == 原 fixed-stay dur(慳一個無謂 query)。
- 每個 refine query 都經 `on_query` closure 行返 grid pass 同一套 pace/delay/`cool_down`/`rest_or_abort`(鐵律 4)—— 唔係 raw query。
- 新 CLI:`--offset` / `--refine-days` / `--no-refine`。每個 period(refine 同非 refine)都補 `days` 欄。
- `--no-refine` 退回純 fixed-stay 舊行為。

**`web/lib/types.ts`** — `Period` 加 `days?: number | null`。
**`web/components/DestinationCard.tsx`** — `stayDays()` 優先用 `p.days`(fallback 留 return−depart);summary 由單一長度改成 **min–max 範圍**。每月平價日掣本身已逐 period 顯示「N號 M日」+ 價 + 分層,無需改邏輯。

## Verification(human-verify checkpoint,user approved)

- **離線單元** `test_scanner.py`:**9/9 綠**(揀平日 / offset clamp [2,14] / 取最平 / days 欄 / query budget ≤40 / google_flights 用新 pair)。
- **`next build`**:過(0 error),無新 npm dependency。
- **Live 掃描**(真連 Google,`--grid --months 2 --no-browser --offset 2 --refine-days 10`,126 query / 115 ok / 24 min):
  - **HKG-NGO 6月+7月:行程日數 4/5/6/7/8(5 種)** ✅
  - **HKG-KUL 6月:4/5(2 種)** ✅;KUL 7月得 5 日(該月最平 10 日啱啱都係 5 日最抵 — data-dependent,非 bug)。
  - 每 period 帶 depart/return/price/days,`google_flights` deep link 對應自己嗰個 pair(FLEX-03)。
- **已 upload 4 行(KUL+NGO×2 月)入 Supabase**;本機 `next dev` + Playwright 截圖證實展開卡見「N號 M日」多種日數 + 綠/青/黃分層(截圖喺 `~/Downloads/phase2-*.png`)。User 撳 approved。

## Deviations

1. **`on_query` closure 重構**(Rule 1):為咗令 refine query 同 grid query 共用 pacing,將 abort-guard 移入 `on_query`,逐 query 觸發(grid + refine 一致)。外層舊 check 保留但變冗餘(無害)。改善正確性(refine query 而家完整參與 abort guard,滿足 T-02-01)。
2. **KUL 7月單一長度**:非 code 問題 —— 該月最平嗰批日剛好 5 日最抵。加大 `--offset`/`--refine-days` 會出多啲變化但升 query;留 Phase 3 同每日更新一齊調。

## Commits
- `aed3e7a` feat(02): refine_period_lengths + --offset/--refine-days/--no-refine + MIN/MAX_NIGHTS + days field
- `aa02d4a` feat(02): Period.days field + DestinationCard stayDays prefer p.days + trip-length range summary

## Follow-ups(交畀 Phase 3 / 後續)
- **全量重掃 171 條 route 連 refine** → Phase 3(每日更新 / 增量排程);query 預算(每線每月 ~63)要同 6 鐘 job 上限 + IP 風險夾住計。
- plan-checker 2 個非阻塞 warning:Test 5 budget assert 可改成嚴格上限(catch skip-optimisation regression);checkpoint 應分清「Google 封咗」vs「真 bug」。
- 可選:加大 offset/refine-days 令更多線出多種日數(tradeoff:query 量)。
- 可選優化:用 Travelpayouts month-matrix 單程數據做平價日 anchor(token 已喺 .env)。
