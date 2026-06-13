# Phase 1 Spike — Travelpayouts 覆蓋率(決策閘結果)

**Date:** 2026-06-14
**Verdict:** ✅ **FALLBACK** — 行 fast-flights 自己掃 **±2 日 return-offset**(唔用 Travelpayouts 做主力)。

## 測咗乜(真 token,無審批阻攔)
| Endpoint | calls | 來回? | 密度 | 結論 |
|---|---|---|---|---|
| `v2/prices/month-matrix` | 84(12 線×7 月) | ❌ 單程(`return_date` 係空字串) | **高**:1017 筆、`found_at` 中位 **1 日前**、HKG 線每月 20+ 筆、連 SZX/CAN 都有數據 | 數據多但**單程**,計唔到行程日數 |
| `v2/prices/latest` `one_way=false` | 84 | ✅ | **極疏**:84 call 總共得 6 筆,且多數 `return_date==depart_date`(0 晚) | 唔夠用 |
| `v1/prices/cheap` | 4 | ✅(`departure_at`/`return_at`) | 每線 ~1 筆(淨係最平嗰張) | 太少,做唔到分層 |
| `v2/prices/week-matrix` | 4 | ✅(`depart_date`×`return_date`) | 每 call ~1 格(HKG-NRT 0) | 唔係真 grid,太疏 |

**核心發現**:token 完全正常、數據新鮮(1–4 日前),但 **Travelpayouts 嘅 round-trip(來回)cache 太疏**,畀唔到我哋要嘅「每月多個、唔同行程日數嘅平價選擇 + 分層」。佢只有**單程** month-matrix 夠密。研究報告 `DATA-SOURCES.md` 假設咗 month-matrix 有 `return_date` —— 實測證實係**空**,假設唔成立。

## 拍板理由
- 變行程長度需要**密集嘅來回**數據;Travelpayouts 畀唔到。
- FALLBACK 路徑(`REFERENCE-SITE.md` 已證實 = 參考網站本身做法)**保證做到**:fast-flights 喺每月揾到嘅平價出發日,加一層 `dur−2 … dur+2`(~5 個)return-offset 取最平 → 每個平價日帶自己嘅行程日數 + 來回價。$0、live、唔使任何外部 API。
- Spike 用 ~10 分鐘 + 一個免費 token,就喺**未寫 pipeline 之前**否決咗一條會撞牆嘅路 —— 正正係 spike 嘅價值。

## Bonus — Phase 2/3 可選優化(month-matrix 唔好嘥)
month-matrix 嘅**單程**數據雖然唔直接用得做來回顯示,但佢**又平、又密、又新鮮(1 call/route-month、免費、含 China origins)**,可以做「**平價出發日 anchor finder**」:先用佢揾出每月邊幾日最平,再叫 fast-flights **淨係喺嗰幾日**掃 ±2 return → 大幅減 query(順手紓緩 Phase 3 每日更新嗰個 6 鐘樽頸)。`TRAVELPAYOUTS_TOKEN` 留喺 `.env` 備用,唔急住用。

## Evidence(raw)
- `TRAVELPAYOUTS-SPIKE.json`(month-matrix)、`TRAVELPAYOUTS-SPIKE-latest.json`、`TRAVELPAYOUTS-SPIKE-v3.json`
- month-matrix 樣本:`{"depart_date":"2026-07-19","return_date":"","value":894,...}` ← 單程
- week-matrix 樣本:`{"depart_date":"2026-08-08","return_date":"2026-08-19","value":1688,...}` ← 11 晚,但每 call 得 1 格
- 注意:Travelpayouts 用**城市碼**(SEL=首爾 / TYO=東京),Phase 2 如要用 anchor 優化要做 IATA↔城市碼對應。
