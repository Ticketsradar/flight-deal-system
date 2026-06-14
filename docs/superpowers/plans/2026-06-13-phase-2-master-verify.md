# Phase 2 — Master 核實 Agent 實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 執行喺一條 feature branch(`phase-2-master-verify`),完成後 merge 返 main。

**Goal:** 起 Stream B 嘅 master 核實腦 — 讀 scout 出嘅 candidate,triage(confidence≥70),重查實價,Sonnet 判 `live`/`dead`/`unverified`,生成 Google Flights + Trip.com 連結,輸出 `data/verified_YYYYMMDD.json` 三 bucket。

**Architecture:** 兩個新檔 + 一個細改。`master.py` 係邏輯(triage / 重查 / Sonnet 判斷 / 砌連結);`run_master.py` 係入口(讀最新 candidates → 核實 → 寫檔)。重查**直接 reuse `scanner.query_roundtrip`**(加一個 backward-compatible 嘅 `seat` 參數);live/dead/unverified 由 Sonnet 對住「candidate + 重查現價」判斷。

**Tech Stack:** Python 3.13、uv、現有 `scanner.py`(fast-flights 查價)、`llm.py`(Sonnet via claude_code = Max plan $0)。測試跟 repo 風格:可跑嘅 `test_*.py` 印 ✅/❌,`uv run python`,冇 pytest。

**鐵律:** 對外 request 隨機 delay + retry + 尊重 rate limit(由 scanner 處理);唔喺全域 shell set API key;sandbox Bash 行 `uv` 前 `export PATH="$HOME/.local/bin:$PATH"`。

**慣例:** `ROOT = Path(__file__).parent`;`log()` = `print(flush=True)`;原子寫檔 `.json.tmp` → `.replace()`;`json.dumps(..., ensure_ascii=False, indent=1)`。

---

### Task 1: 畀 scanner.query_roundtrip 加 `seat` 參數(backward-compatible)

**Files:**
- Modify: `scanner.py`(query_roundtrip 簽名 + TFSData seat)

- [ ] **Step 1: 改函數簽名(加 `seat` 預設 economy)**

搵:
```python
def query_roundtrip(origin: str, dest: str, depart: dt.date, ret: dt.date,
                    currency: str, browser) -> dict:
```
改:
```python
def query_roundtrip(origin: str, dest: str, depart: dt.date, ret: dt.date,
                    currency: str, browser, seat: str = "economy") -> dict:
```

- [ ] **Step 2: 用個參數(唔再寫死 economy)**

搵:`        seat="economy",`
改:`        seat=seat,`

- [ ] **Step 3: 確認 backward-compatible(舊 call 唔帶 seat 都得 + 接受 business)**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python -c "import inspect, scanner; p=inspect.signature(scanner.query_roundtrip).parameters; print('有 seat 參數:', 'seat' in p); print('預設:', p['seat'].default)"
```
Expected:`有 seat 參數: True` + `預設: economy`。

- [ ] **Step 4: 確認 scanner 仍可正常 import(冇打爛嘢)**

```bash
uv run python -c "import scanner; print('scanner import ok;', hasattr(scanner,'query_roundtrip'), hasattr(scanner,'deep_link'))"
```
Expected:`scanner import ok; True True`。

- [ ] **Step 5: Commit**

```bash
git add scanner.py
git commit -m "feat(scanner): query_roundtrip 加 backward-compatible seat 參數(畀 master 查 business 艙)"
```

---

### Task 2: master.py + test_master.py(核實邏輯,TDD)

**Files:**
- Create: `master.py`
- Create: `test_master.py`

- [ ] **Step 1: 寫住會失敗嘅測試 `test_master.py`**

```python
"""
test_master.py — Phase 2 master 純邏輯測試(離線,唔 call LLM / 唔查網)
跑法:uv run python test_master.py
"""
import sys

from master import (triage, infer_seat, tripcom_link, build_master_system,
                    parse_verdict, build_links)


def main() -> None:
    ok = True

    t = triage([{"confidence": 85}, {"confidence": 70}, {"confidence": 69}, {"confidence": "x"}])
    cond = len(t) == 2
    print(("✅" if cond else "❌"), "triage 留 ≥70:", len(t))
    ok = ok and cond

    cond = (infer_seat({"reason": "business class mispriced"}) == "business"
            and infer_seat({"title": "great economy deal"}) == "economy"
            and infer_seat({"reason": "頭等 first class"}) == "first")
    print(("✅" if cond else "❌"), "infer_seat 認到艙位")
    ok = ok and cond

    link = tripcom_link("HKG", "LHR", "2026-09-12", "2026-09-20", seat="business")
    cond = ("dcity=hkg" in link and "acity=lhr" in link and "ddate=2026-09-12" in link
            and "class=c" in link and link.startswith("https://www.trip.com/flights/"))
    print(("✅" if cond else "❌"), "tripcom_link:", link[:64], "…")
    ok = ok and cond

    s = build_master_system()
    cond = "live" in s and "dead" in s and "unverified" in s and "JSON" in s
    print(("✅" if cond else "❌"), "master system prompt 含三個 status")
    ok = ok and cond

    v = parse_verdict('{"status":"live","verified_price":2180,"note":"仲買到"}')
    cond = v["status"] == "live" and v["verified_price"] == 2180
    print(("✅" if cond else "❌"), "parse_verdict 正常:", v["status"])
    ok = ok and cond
    cond = parse_verdict("唔係 JSON 嘅垃圾")["status"] == "unverified"
    print(("✅" if cond else "❌"), "parse_verdict 壞回應 → unverified")
    ok = ok and cond

    links = build_links({"origin": "HKG", "destination": "LHR",
                         "depart_date": "2026-09-12", "return_date": "2026-09-20"},
                        {"tfs": "ABC123", "status": "ok"})
    cond = "tfs=ABC123" in links["gflights_url"] and "trip.com" in links["tripcom_url"]
    print(("✅" if cond else "❌"), "build_links 出兩條 link")
    ok = ok and cond

    print()
    print("🎉 master 純邏輯測試通過" if ok else "⚠️ master 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 跑佢確認失敗**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python test_master.py
```
Expected:FAIL —`ModuleNotFoundError: No module named 'master'`。

- [ ] **Step 3: 寫 `master.py`**

```python
"""
master.py — Phase 2 Master 核實腦(Sonnet)
==========================================
讀 scout candidate → triage(confidence≥70)→ 重查實價(reuse scanner)→
Sonnet 判 live/dead/unverified → 生成 Google Flights + Trip.com 連結。
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.parse

from llm import call_llm, extract_json
import scanner

MIN_CONFIDENCE = 70
SEAT_CLASS = {"economy": "y", "premium-economy": "w", "business": "c", "first": "f"}


def triage(candidates: list[dict], min_conf: int = MIN_CONFIDENCE) -> list[dict]:
    """只留 confidence ≥ 門檻(控制 LLM 成本主閘)。"""
    def conf(c: dict) -> float:
        try:
            return float(c.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            return 0.0
    return [c for c in candidates if conf(c) >= min_conf]


def infer_seat(cand: dict) -> str:
    """由 candidate 文字估艙位(好多錯價係 business/first)。"""
    blob = " ".join(str(cand.get(k, "")) for k in ("title", "reason", "airline", "text")).lower()
    if "first class" in blob or "頭等" in blob:
        return "first"
    if "business" in blob or "商務" in blob or "商务" in blob:
        return "business"
    if "premium econom" in blob or "特選經濟" in blob:
        return "premium-economy"
    return "economy"


def tripcom_link(origin: str, dest: str, depart: str, ret: str,
                 seat: str = "economy", currency: str = "HKD") -> str:
    """Trip.com 來回搜尋 deep link(唔抓價,純畀用戶撳去比價/訂票)。"""
    params = {
        "dcity": origin.lower(), "acity": dest.lower(),
        "ddate": depart, "rdate": ret,
        "triptype": "rt", "class": SEAT_CLASS.get(seat, "y"), "quantity": 1,
        "locale": "zh-HK", "curr": currency,
    }
    return "https://www.trip.com/flights/showfarefirst?" + urllib.parse.urlencode(params)


def build_master_system() -> str:
    return (
        "你係機票錯價核實員。會畀你一個疑似錯價 candidate(scout 抽出)、佢嘅原文,"
        "同埋我哋啱啱用 Google Flights 重查同一條線 / 日期嘅結果。\n"
        "你要判斷張錯價而家係咩狀態,只回一個 JSON object:\n"
        '{"status": "live|dead|unverified", "verified_price": number 或 null, "note": "一句中文解釋"}\n\n'
        "判斷準則:\n"
        "- live:重查到嘅現價仍然異常平(同 claimed 錯價差唔多咁離譜),即仲買到。\n"
        "- dead:重查到嘅現價已經返返正常(明顯貴過 claimed),即錯價已被改正。\n"
        "- unverified:重查 status 唔係 ok(Google Flights 查唔到,例如細 airline / 冇收錄),"
        "無法確認 → 照樣保留畀人手快手查。\n"
        "- 艙位注意:如果 candidate 講緊 business / first 但重查係 economy 價,"
        "唔好當 dead,應該 unverified(艙位對唔上)。\n"
        "verified_price 填重查到嘅現價(冇就 null)。唔好回 JSON 以外嘅文字。"
    )


def parse_verdict(reply: str) -> dict:
    """由 Sonnet 回應抽 verdict;抽唔到 / 格式錯 → 當 unverified。"""
    try:
        data = extract_json(reply)
    except Exception:  # noqa: BLE001
        return {"status": "unverified", "verified_price": None, "note": "核實回應解析失敗"}
    if not isinstance(data, dict):
        return {"status": "unverified", "verified_price": None, "note": "核實回應格式不符"}
    status = str(data.get("status", "unverified")).lower()
    if status not in ("live", "dead", "unverified"):
        status = "unverified"
    return {"status": status, "verified_price": data.get("verified_price"),
            "note": str(data.get("note", ""))}


def _parse_date(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s).strip())
    except (ValueError, AttributeError):
        return None


def requery(cand: dict, browser, currency: str = "HKD") -> dict:
    """reuse scanner.query_roundtrip 重查 candidate 嘅線/日期。路由/日期壞 → failed。"""
    depart = _parse_date(cand.get("depart_date", ""))
    ret = _parse_date(cand.get("return_date", ""))
    origin = str(cand.get("origin", "")).strip().upper()
    dest = str(cand.get("destination", "")).strip().upper()
    if not (depart and ret and len(origin) == 3 and len(dest) == 3):
        return {"status": "failed", "error": "bad_route_or_date", "tfs": ""}
    return scanner.query_roundtrip(origin, dest, depart, ret, currency, browser,
                                   seat=infer_seat(cand))


def build_links(cand: dict, rq: dict, currency: str = "HKD") -> dict:
    """Google Flights deep link(由重查 tfs)+ Trip.com 搜尋 link。"""
    tfs = rq.get("tfs", "")
    gf = scanner.deep_link(tfs, currency) if tfs else ""
    tc = tripcom_link(str(cand.get("origin", "")), str(cand.get("destination", "")),
                      str(cand.get("depart_date", "")), str(cand.get("return_date", "")),
                      seat=infer_seat(cand), currency=currency)
    return {"gflights_url": gf, "tripcom_url": tc}


def verify_one(cand: dict, browser, currency: str = "HKD") -> dict:
    """重查 → Sonnet 判斷 → 砌連結 → 併返落 candidate。"""
    rq = requery(cand, browser, currency)
    user = json.dumps({"candidate": cand, "requery": rq}, ensure_ascii=False)
    try:
        verdict = parse_verdict(call_llm("master", system=build_master_system(), user=user))
    except Exception as e:  # noqa: BLE001
        verdict = {"status": "unverified", "verified_price": None, "note": f"核實出錯:{e}"}
    links = build_links(cand, rq, currency)
    out = dict(cand)
    out.update(status=verdict["status"], verified_price=verdict["verified_price"],
               note=verdict["note"], requery_status=rq.get("status"),
               gflights_url=links["gflights_url"], tripcom_url=links["tripcom_url"])
    return out
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run python test_master.py
```
Expected:7 個 ✅ + `🎉 master 純邏輯測試通過`,exit 0。

- [ ] **Step 5: Commit**

```bash
git add master.py test_master.py
git commit -m "feat(master): triage + 重查 + Sonnet 判 live/dead/unverified + 連結"
```

---

### Task 3: run_master.py — 入口 + 三 bucket 寫檔

**Files:**
- Create: `run_master.py`

- [ ] **Step 1: 寫 `run_master.py`**

```python
"""
run_master.py — Phase 2 入口:讀最新 candidates → triage → 核實 → 寫 data/verified_YYYYMMDD.json
跑法:
    uv run python run_master.py                       # 跑最新 data/candidates_*.json
    uv run python run_master.py --file data/xxx.json  # 指定檔
    uv run python run_master.py --no-browser --limit 1   # 淨 HTTP、最多核 1 個(快)
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from pathlib import Path

import master
import scanner

ROOT = Path(__file__).parent


def log(msg: str) -> None:
    print(msg, flush=True)


def _latest_candidates() -> str:
    files = sorted(glob.glob(str(ROOT / "data" / "candidates_*.json")))
    return files[-1] if files else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Stream B master:核實錯價 candidate")
    ap.add_argument("--file", default="", help="指定 candidates JSON(預設攞最新)")
    ap.add_argument("--limit", type=int, default=0, help="最多核幾多個(0=全部)")
    ap.add_argument("--no-browser", action="store_true", help="停用真瀏覽器後備")
    args = ap.parse_args()

    path = args.file or _latest_candidates()
    if not path or not Path(path).exists():
        log("[master] 搵唔到 candidates 檔(data/candidates_*.json)。先跑 run_scout.py。")
        return 1
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    cands = doc.get("candidates", [])
    log(f"[master] 讀 {path}:{len(cands)} 個 candidate")

    high = master.triage(cands)
    if args.limit > 0:
        high = high[:args.limit]
    log(f"[master] triage(confidence≥{master.MIN_CONFIDENCE}):{len(high)} 個要核實")

    browser = None if args.no_browser else scanner.BrowserFetcher()
    results = []
    try:
        for i, c in enumerate(high, 1):
            log(f"[master] 核實 {i}/{len(high)}: "
                f"{c.get('origin')}-{c.get('destination')} {c.get('depart_date')}")
            results.append(master.verify_one(c, browser))
    finally:
        if browser is not None:
            browser.close()

    buckets: dict[str, list] = {"live": [], "unverified": [], "dead": []}
    for r in results:
        buckets.get(r.get("status", "unverified"), buckets["unverified"]).append(r)

    today = dt.date.today()
    out_dir = ROOT / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"verified_{today.strftime('%Y%m%d')}.json"
    out_doc = {
        "verify_date": today.isoformat(),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source_file": path,
        "triaged": len(high),
        "counts": {k: len(v) for k, v in buckets.items()},
        "live": buckets["live"],
        "unverified": buckets["unverified"],
        "dead": buckets["dead"],
    }
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out_doc, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out_path)
    log(f"[master] 寫好 → {out_path}  "
        f"(live {len(buckets['live'])} / unverified {len(buckets['unverified'])} / dead {len(buckets['dead'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 確認 import 得到(冇查網)**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python -c "import run_master; print('run_master import ok')"
```
Expected:`run_master import ok`(冇 error)。

- [ ] **Step 3: Commit**

```bash
git add run_master.py
git commit -m "feat(run_master): 入口 — 讀 candidates → triage → 核實 → 寫 verified_*.json 三 bucket"
```

---

### Task 4: 全鏈路 live smoke(完成標準)

**Files:**(冇新檔;造一個 fixture + 跑)

- [ ] **Step 1: 造一個已知 candidate fixture(HKG 出發、未來日期、Google Flights cover 到嘅線)**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python - <<'PY'
import json, datetime as dt
from pathlib import Path
d1 = (dt.date.today().replace(day=1) + dt.timedelta(days=90))
d2 = d1 + dt.timedelta(days=6)
doc = {"scan_date": dt.date.today().isoformat(), "posts_fetched": 1, "candidate_count": 1,
       "candidates": [{
           "origin": "HKG", "destination": "NRT",
           "depart_date": d1.isoformat(), "return_date": d2.isoformat(),
           "price": 600, "currency": "HKD", "airline": "ANA",
           "source_platform": "rss/test", "source_url": "https://example.com/hkg-nrt-test",
           "confidence": 90, "reason": "Suspiciously low economy round trip"}]}
Path("data").mkdir(exist_ok=True)
Path("data/candidates_testfixture.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
print("造好 fixture:", d1, "→", d2)
PY
```
Expected:`造好 fixture: <未來日期> → <未來日期>`。

- [ ] **Step 2: 跑 master 核實個 fixture(淨 HTTP、核 1 個)**

```bash
uv run python run_master.py --file data/candidates_testfixture.json --no-browser --limit 1
```
Expected:見到 `讀 …testfixture…: 1 個` → `triage…: 1 個` → `核實 1/1: HKG-NRT …` → `寫好 → …/data/verified_YYYYMMDD.json (live x / unverified y / dead z)`,exit 0。
(係邊個 bucket 都 OK — 重點係跑得通、分到 bucket、寫到檔。HKG-NRT economy $600 多數會 `dead`,因為實價貴過 $600。)

- [ ] **Step 3: 確認輸出檔結構 + 連結**

```bash
uv run python -c "import json; d=json.load(open('data/verified_$(date +%Y%m%d).json',encoding='utf-8')); print('keys:',list(d.keys())); print('counts:',d['counts']); items=d['live']+d['unverified']+d['dead']; r=items[0]; print('status:',r['status'],'| requery:',r['requery_status'],'| note:',r['note'][:50]); print('GF:',r['gflights_url'][:55]); print('Trip:',r['tripcom_url'][:55])"
```
Expected:印出 `keys`(含 live/unverified/dead/counts)、第一個結果嘅 status / requery_status / note、兩條連結(`google.com/travel/flights…` + `trip.com/flights…`)。

- [ ] **Step 4: 離線回歸測試**

```bash
uv run python test_master.py >/dev/null && echo "master ✅" \
 && uv run python test_feeds.py >/dev/null && echo "feeds ✅" \
 && uv run python test_consolidate.py >/dev/null && echo "consolidate ✅" \
 && uv run python test_scout.py >/dev/null && echo "scout ✅"
```
Expected:四個 ✅。

- [ ] **Step 5: 清走 fixture(唔好留低污染真資料)+ Commit**

```bash
rm -f data/candidates_testfixture.json
git add -A
git commit -m "test(phase-2): master 全鏈路 live smoke 通過" --allow-empty
```

---

### Task 5: 更新 CLAUDE.md 進度 + 收尾

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 剔 Phase 2 完成**

搵:`- [ ] Phase 2 — master 核實 agent(triage → fast-flights 重query → deep links)`
改:`- [x] **Phase 2 — master 核實 agent** ✅ 2026-06-13(master.py + run_master.py;triage≥70 → reuse scanner.query_roundtrip 重查(加 seat 參數)→ Sonnet 判 live/dead/unverified → Google Flights + Trip.com 連結 → data/verified_*.json;計劃 docs/superpowers/plans/2026-06-13-phase-2-master-verify.md)`

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE.md): 剔 Phase 2 完成 ✅(master 核實 agent)"
```

---

## Self-Review

**1. Spec coverage(spec Section 5.4 / 7):**
- 讀最新 candidates → run_master `_latest_candidates` ✅
- triage confidence≥70(成本主閘)→ `master.triage` ✅
- 第 1 層 Google Flights 重查(reuse scanner)→ `master.requery` + Task 1 seat 參數 ✅
- live/dead/unverified 判斷 → `build_master_system` + Sonnet + `parse_verdict` ✅
- 細 airline 查唔到 → unverified:`requery` 回 failed → Sonnet 判 unverified ✅
- Google Flights + Trip.com 連結 → `build_links` / `tripcom_link` ✅
- 三 bucket 輸出 → `run_master` buckets + `data/verified_*.json` ✅
- 第 2 層 Playwright link 死活檢查:spec 講明「可選、後期做」,Phase 2 唔做 — 一致 ✅

**2. Placeholder scan:** 冇 TBD / 冇「自己加 error handling」/ 每個 code step 都有完整碼。Trip.com link 用 `showfarefirst` 格式,Task 4 Step 3 會印出嚟肉眼睇到實際 URL(可撳去確認落正確搜尋頁)。

**3. Type consistency:**
- `query_roundtrip(..., seat="economy")` — Task 1 改、`master.requery` 用 `seat=infer_seat(cand)`,一致 ✅
- requery 回傳 dict 一定有 `tfs`(scanner 所有 return path 都有)→ `build_links` 安全用 `rq.get("tfs")` ✅
- candidate 欄位(origin/destination/depart_date/return_date/price/currency/airline/confidence/reason)同 Phase 1B scout 輸出一致 ✅
- verdict dict 形狀 `{status, verified_price, note}` — `parse_verdict` 產出、`verify_one` 用,一致 ✅
- bucket key `live/unverified/dead` — `build_master_system` 要求、`parse_verdict` 校驗、`run_master` 分桶,一致 ✅

冇發現問題。
