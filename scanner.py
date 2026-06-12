"""
scanner.py — 引擎A:fast-flights 掃描器(Phase 1A)
====================================================
讀 routes.yaml(origins × destinations),每條 route × 未來 12 個月,
每月抽幾個代表出發日問 Google Flights,攞最平來回價,
輸出 data/scan_YYYYMMDD.json,每條結果連 Google Flights deep link。

用法:
    uv run python scanner.py --smoke          # 冒煙測試:3 條代表 route、每月 1 個樣本
    uv run python scanner.py                  # 全量掃描(routes.yaml 全部組合)
    uv run python scanner.py --max-routes 5   # 只掃頭 5 條 route
    uv run python scanner.py --months 3       # 只掃未來 3 個月
    uv run python scanner.py --samples 1      # 每月只抽 1 個出發日(快一倍)

設計(對應 CLAUDE.md 鐵律 4 + 實測經驗):
    * 每月只抽 1–4 個代表出發日,唔逐日掃 365 日。
    * 每個 query 之間隨機等 3–8 秒;每 30 個 query 加唞 20–40 秒。
    * Google 有時回「未載入結果」空殼頁:
        - 近/中期日子 — 換新瀏覽器偽裝 retry 通常第 2 次就得(實測)。
        - 遠期日子(約 9 個月後)— 點試都係殼,所以連續 2 次純空殼就提早放棄,
          留返俾第二輪;第二輪都唔得就標 failed(=攞唔到價,唔代表冇航班)。
    * 主掃完成後有第二輪補掃:唞 60 秒俾 Google 消氣,再救返暫時性失敗嘅月份。
    * 連續 10 個 query 失敗 → 當被 block,優雅收工,已掃部分照樣寫檔。
    * 每完成一條 route 即刻寫一次檔 — 中途斷咗都唔會冇晒。
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import random
import re
import sys
import time
from pathlib import Path

import yaml
from fast_flights import FlightData, Passengers, TFSData
from fast_flights.core import parse_response
from fast_flights.primp import Client

ROOT = Path(__file__).parent
GF_URL = "https://www.google.com/travel/flights"

# 每月抽樣出發日(spread 開,避開月頭月尾極端日子)
SAMPLE_DAYS = {1: [12], 2: [10, 24], 3: [8, 18, 28], 4: [5, 13, 21, 28]}
MAX_ATTEMPTS = 4        # 每個 query 最多試幾次(混合錯誤時)
SHELL_ONLY_CAP = 2      # 全部 attempt 都係純空殼 → 試夠咁多次就收手(遠期日子常態)
ABORT_AFTER = 10        # 連續咁多個 query 失敗 → 當被 Google 擋,成個 scan 收工
COOL_EVERY = 30         # 每 N 個 query 唞長啲


class ShellPage(Exception):
    """Google 回咗未載入結果嘅空殼頁"""


class Blocked(Exception):
    """HTTP 非 200 / 驗證頁 — 疑似被 rate limit"""


class AbortScan(Exception):
    """連續失敗太多,優雅收工"""


def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------ 查價核心

def fetch_once(tfs_b64: str, currency: str):
    """問一次 Google Flights。每次開新 Client = 新隨機瀏覽器偽裝。

    回 fast-flights Result;頁面正常但真係冇航班就回 None;空殼頁/被擋就 raise。
    """
    client = Client(impersonate="random", verify=False)
    res = client.get(GF_URL, params={
        "tfs": tfs_b64, "hl": "en", "tfu": "EgQIABABIgA", "curr": currency,
    })
    if res.status_code != 200:
        raise Blocked(f"HTTP {res.status_code}")
    try:
        return parse_response(res)
    except RuntimeError as e:
        msg = str(e)
        if "Loading results" in msg:
            raise ShellPage() from None
        if "unusual traffic" in msg.lower() or "captcha" in msg.lower():
            raise Blocked("Google 驗證頁(疑似被擋)") from None
        return None


def parse_price(raw: str):
    """'HK$2312' → 2312;'Price unavailable' → None。"""
    digits = re.sub(r"[^0-9]", "", raw or "")
    return int(digits) if digits else None


def query_roundtrip(origin: str, dest: str, depart: dt.date, ret: dt.date,
                    currency: str, patience: float = 1.0) -> dict:
    """查一對來回日期,回最平嗰班(連 tfs,deep link 用)。

    patience >1 = 等耐啲先 retry(第二輪補掃用)。
    """
    flt = TFSData.from_interface(
        flight_data=[
            FlightData(date=depart.isoformat(), from_airport=origin, to_airport=dest),
            FlightData(date=ret.isoformat(), from_airport=dest, to_airport=origin),
        ],
        trip="round-trip",
        passengers=Passengers(adults=1),
        seat="economy",
    )
    tfs = flt.as_b64().decode()
    last_err = ""
    shells = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = fetch_once(tfs, currency)
            if result is None:
                return {"status": "no_flights", "tfs": tfs}
            best = None
            for fl in result.flights:
                p = parse_price(fl.price)
                if p and (best is None or p < best["price"]):
                    best = {
                        "price": p,
                        "airline": fl.name,
                        "stops": fl.stops if isinstance(fl.stops, int) else None,
                        "duration": fl.duration,
                    }
            if best is None:
                return {"status": "no_flights", "tfs": tfs}
            best.update(status="ok", tfs=tfs, price_trend=result.current_price or "")
            return best
        except ShellPage:
            shells += 1
            last_err = f"空殼頁×{shells}"
            if shells == attempt and attempt >= SHELL_ONLY_CAP:
                break  # 次次都純空殼 — 多數係遠期日子,試落去嘥時間
            time.sleep(random.uniform(3, 6) * attempt * patience)
        except Blocked as e:
            last_err = str(e)
            time.sleep(random.uniform(10, 20) * attempt * patience)
        except Exception as e:  # 網絡錯誤等
            last_err = type(e).__name__
            time.sleep(random.uniform(5, 10) * patience)
    return {"status": "failed", "error": last_err, "tfs": tfs}


# ------------------------------------------------------------------ 掃描編排

def upcoming_months(n: int, sample_days: list, today: dt.date) -> list:
    """未來 n 個月;今個月仲有可用抽樣日(3 日後)就計埋今個月。"""
    y, m = today.year, today.month
    usable = any(
        dt.date(y, m, min(d, calendar.monthrange(y, m)[1])) >= today + dt.timedelta(days=3)
        for d in sample_days
    )
    if not usable:
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    out = []
    for _ in range(n):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def deep_link(tfs: str, currency: str) -> str:
    return f"{GF_URL}?tfs={tfs}&hl=zh-HK&curr={currency}"


def build_routes(cfg: dict) -> list:
    """origins × destinations 全組合,跳過 exclude 名單。"""
    exclude = {str(x).strip().upper() for x in (cfg.get("exclude") or [])}
    routes = []
    for o in cfg["origins"]:
        for d in cfg["destinations"]:
            if f'{o["code"]}-{d["code"]}'.upper() in exclude:
                continue
            routes.append({
                "origin": o["code"], "origin_name": o["name"],
                "dest": d["code"], "dest_name": d["name"],
                "region": d["region"], "stay_nights": int(d["stay_nights"]),
            })
    return routes


def pick_smoke(routes: list) -> list:
    """揀 3 條有代表性:HKG 短途、HKG 長途、非 HKG 出發。"""
    conds = [
        lambda r: r["origin"] == "HKG" and r["stay_nights"] <= 6,
        lambda r: r["origin"] == "HKG" and r["stay_nights"] >= 9,
        lambda r: r["origin"] != "HKG",
    ]
    picks = []
    for cond in conds:
        hit = next((r for r in routes if cond(r) and r not in picks), None)
        if hit:
            picks.append(hit)
    return picks or routes[:3]


def main() -> int:
    ap = argparse.ArgumentParser(description="引擎A:Google Flights 掃描器(fast-flights)")
    ap.add_argument("--smoke", action="store_true", help="冒煙測試:3 條代表 route、每月 1 個樣本")
    ap.add_argument("--max-routes", type=int, default=0, help="只掃頭 N 條 route(0=全部)")
    ap.add_argument("--months", type=int, default=12, help="掃未來幾多個月(預設 12)")
    ap.add_argument("--samples", type=int, default=0, help="每月抽樣日數 1–4(預設用 routes.yaml)")
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "routes.yaml").read_text(encoding="utf-8"))
    dfl = cfg.get("defaults") or {}
    currency = str(dfl.get("currency", "HKD"))
    delay_lo, delay_hi = (dfl.get("delay_seconds") or [3, 8])[:2]
    samples = args.samples or int(dfl.get("samples_per_month", 2))
    samples = max(1, min(4, samples))

    routes = build_routes(cfg)
    if args.smoke:
        routes = pick_smoke(routes)
        samples = 1
    if args.max_routes > 0:
        routes = routes[: args.max_routes]

    today = dt.date.today()
    sample_days = SAMPLE_DAYS[samples]
    months = upcoming_months(args.months, sample_days, today)

    total_q = len(routes) * len(months) * samples
    est_min = total_q * (((delay_lo + delay_hi) / 2) + 3) / 60
    log(f"[scan] {len(routes)} 條 route × {len(months)} 個月 × 每月 {samples} 樣本"
        f" ≈ {total_q} queries,預計 ~{est_min:.0f} 分鐘(未計 retry)")

    out_dir = ROOT / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"scan_{today.strftime('%Y%m%d')}.json"

    scan = {
        "scan_date": today.isoformat(),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source": "fast-flights(Google Flights)",
        "currency": currency,
        "status": "running",
        "params": {"smoke": args.smoke, "months": len(months),
                   "samples_per_month": samples, "routes": len(routes)},
        "stats": {"queries": 0, "ok": 0, "no_flights": 0, "failed": 0},
        "routes": [],
    }
    pace = {"q": 0}        # 行咗幾多個 query(計唞嘅時機)
    guard = {"consec": 0}  # 連續失敗 query 數(判斷被 block)
    t0 = time.time()

    def save(status: str) -> None:
        scan["status"] = status
        scan["stats"]["elapsed_s"] = round(time.time() - t0)
        ms = [mr for rt in scan["routes"] for mr in rt["months"]]
        scan["stats"]["months_ok"] = sum(1 for x in ms if x["status"] == "ok")
        scan["stats"]["months_failed"] = sum(1 for x in ms if x["status"] == "failed")
        out_path.write_text(json.dumps(scan, ensure_ascii=False, indent=1), encoding="utf-8")

    def cool_down() -> None:
        if pace["q"] and pace["q"] % COOL_EVERY == 0:
            zzz = random.uniform(20, 40)
            log(f"[scan] …唞 {zzz:.0f} 秒(每 {COOL_EVERY} 個 query 抖一抖,防 block)")
            time.sleep(zzz)

    def scan_month(origin: str, dest: str, stay: int, y: int, m: int,
                   patience: float = 1.0, abort_on_streak: bool = True) -> dict:
        mlabel = f"{y}-{m:02d}"
        best = None
        tried = failed = 0
        last_err = ""
        for day in sample_days:
            depart = dt.date(y, m, min(day, calendar.monthrange(y, m)[1]))
            if depart < today + dt.timedelta(days=3):
                continue  # 太近/已過嘅日子唔查
            ret = depart + dt.timedelta(days=stay)
            r = query_roundtrip(origin, dest, depart, ret, currency, patience=patience)
            tried += 1
            pace["q"] += 1
            scan["stats"]["queries"] += 1
            if r["status"] == "ok":
                scan["stats"]["ok"] += 1
                guard["consec"] = 0
                if best is None or r["price"] < best["price"]:
                    best = {**r, "depart": depart.isoformat(), "return": ret.isoformat()}
            elif r["status"] == "no_flights":
                scan["stats"]["no_flights"] += 1
                guard["consec"] = 0  # Google 有答,只係冇貨 — 唔算被擋
            else:
                scan["stats"]["failed"] += 1
                failed += 1
                last_err = r.get("error", "")
                guard["consec"] += 1
                if abort_on_streak and guard["consec"] >= ABORT_AFTER:
                    raise AbortScan()
            time.sleep(random.uniform(float(delay_lo), float(delay_hi)) * patience)
            cool_down()
        if best:
            return {
                "month": mlabel, "status": "ok",
                "price": best["price"], "currency": currency,
                "depart": best["depart"], "return": best["return"],
                "airline": best["airline"], "stops": best["stops"],
                "duration": best["duration"], "price_trend": best["price_trend"],
                "google_flights": deep_link(best["tfs"], currency),
                "samples_tried": tried, "samples_failed": failed,
            }
        status = "failed" if (tried and failed == tried) else "no_data"
        mrec = {"month": mlabel, "status": status,
                "samples_tried": tried, "samples_failed": failed}
        if last_err:
            mrec["error"] = last_err
        return mrec

    def log_month(prefix: str, origin: str, dest: str, mrec: dict) -> None:
        if mrec["status"] == "ok":
            st = mrec["stops"]
            stops_txt = "直航" if st == 0 else (f"{st}轉" if st else "?")
            name = mrec["airline"] or "?"
            log(f"{prefix} {origin}→{dest} {mrec['month']}"
                f"  {currency} {mrec['price']:,}({name},{stops_txt})")
        else:
            log(f"{prefix} {origin}→{dest} {mrec['month']}"
                f"  ✗ {mrec['status']}({mrec.get('error', '')})")

    try:
        for ri, route in enumerate(routes, 1):
            rec = {k: route[k] for k in
                   ("origin", "origin_name", "dest", "dest_name", "region", "stay_nights")}
            rec["months"] = []
            try:
                for (y, m) in months:
                    mrec = scan_month(route["origin"], route["dest"],
                                      route["stay_nights"], y, m)
                    rec["months"].append(mrec)
                    log_month(f"[{ri:>3}/{len(routes)}]", route["origin"], route["dest"], mrec)
            except AbortScan:
                scan["routes"].append(rec)  # 半路嗰條 route 都保留
                raise
            scan["routes"].append(rec)
            save("running")  # 每條 route 完即寫檔,斷咗都有得剩

        # ---- 第二輪:補掃失敗月份(暫時性 block 通常隔陣就好返)----
        fails = [(rec, i) for rec in scan["routes"]
                 for i, mr in enumerate(rec["months"]) if mr["status"] == "failed"]
        recovered = 0
        if fails:
            log(f"[scan] 第二輪:補掃 {len(fails)} 個失敗月份(先唞 60 秒俾 Google 消氣)")
            time.sleep(60)
            guard["consec"] = 0
            for rec, i in fails:
                if guard["consec"] >= 6:
                    log("[scan] 第二輪都連環失敗 — 放棄補掃淨低嘅,慳返啲請求")
                    break
                y, m = (int(x) for x in rec["months"][i]["month"].split("-"))
                mrec = scan_month(rec["origin"], rec["dest"], rec["stay_nights"],
                                  y, m, patience=1.6, abort_on_streak=False)
                if mrec["status"] == "ok":
                    recovered += 1
                rec["months"][i] = mrec
                log_month("[補掃]", rec["origin"], rec["dest"], mrec)
                save("running")
            log(f"[scan] 第二輪救返 {recovered}/{len(fails)} 個月份")
        scan["stats"]["recovered_2nd_pass"] = recovered

    except AbortScan:
        save("aborted_blocked")
        log(f"[scan] ⚠ 連續 {ABORT_AFTER} 個 query 失敗 — 疑似被 Google 暫時擋住,"
            f"優雅收工。已掃部分保留喺 {out_path.name}")
        return 2
    except KeyboardInterrupt:
        save("interrupted")
        log(f"[scan] 手動中斷,已掃部分保留喺 {out_path.name}")
        return 1

    save("completed")
    s = scan["stats"]
    log("")
    log(f"[scan] ✅ 完成:{s['queries']} queries(成功 {s['ok']} / 冇航班 {s['no_flights']}"
        f" / 失敗 {s['failed']});月份計 {s['months_ok']} OK / {s['months_failed']} 攞唔到,"
        f"用咗 {s['elapsed_s'] // 60} 分鐘")
    log(f"[scan] 結果:{out_path}")

    oks = [(rt, mr) for rt in scan["routes"] for mr in rt["months"] if mr["status"] == "ok"]
    if oks:
        log("")
        log("[scan] 人手抽查(撳入去 Google Flights 對吓價):")
        for rt, mr in random.sample(oks, min(2, len(oks))):
            log(f"  {rt['origin']}→{rt['dest']} {rt['dest_name']} {mr['month']}"
                f"  {mr['currency']} {mr['price']:,}  {mr['depart']} 去 {mr['return']} 返")
            log(f"  {mr['google_flights']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
