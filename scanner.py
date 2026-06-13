"""
scanner.py — 引擎A:fast-flights 掃描器(Phase 1A,v3 雙層版)
==============================================================
讀 routes.yaml(origins × destinations),每條 route × 未來 12 個月,
每月抽幾個代表出發日問 Google Flights,攞最平來回價,
輸出 data/scan_YYYYMMDD.json,每條結果連 Google Flights deep link。

用法:
    uv run python scanner.py --smoke              # 冒煙測試:3 條代表 route、每月 1 個樣本
    uv run python scanner.py                      # 全量掃描(routes.yaml 全部組合)
    uv run python scanner.py --samples 1 --resume # 接力:沿用今日已掃,只補失敗+未掃
    uv run python scanner.py --max-routes 5       # 只掃頭 5 條 route
    uv run python scanner.py --no-browser         # 唔用真瀏覽器後備(CI 未裝 playwright 時)

雙層查價策略(2026-06-13 實測得出):
    Tier 1 — HTTP 直撈(快、平):Google 對熱門 route 近中期日子會 server-render,
             但對冷門 route / 遠期日子好多時只回「未載入」空殼頁,點 retry 都廢。
    Tier 2 — 真瀏覽器(playwright headless Chrome,慢但渣都撈埋):行 JavaScript
             攞到幾乎所有 Google 有嘅數據;遇「Oops」會撳 Reload 兩次。
             連真瀏覽器都「No results returned」= 航空公司未放票(約 10.5 個月後),
             標 beyond_data;同一 route 連續 2 個月 beyond_data 就跳過剩低月份。

防 block(鐵律 4):
    * 每月只抽 1–4 個代表日;query 之間隨機等 3–8 秒;每 30 個 query 唞 20–40 秒。
    * 連續 10 個 query 真失敗 → 自動唞 10–15 分鐘再戰(最多 3 次),先至放棄。
    * 每完成一條 route 即刻寫檔;--resume 可以接力,唔會由頭嚟過。
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import random
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import yaml
from fast_flights import FlightData, Passengers, TFSData
from fast_flights.core import parse_response
from fast_flights.primp import Client

ROOT = Path(__file__).parent
GF_URL = "https://www.google.com/travel/flights"

# 每月抽樣出發日(spread 開,避開月頭月尾極端日子)
SAMPLE_DAYS = {1: [12], 2: [10, 24], 3: [8, 18, 28], 4: [5, 13, 21, 28]}
ABORT_AFTER = 10       # 連續咁多個 query 真失敗 → 唞長覺/收工
MAX_LONG_RESTS = 3     # 自動唞長覺次數上限
COOL_EVERY = 30        # 每 N 個 query 唞 20–40 秒
MIN_FREE_BYTES = 1_200_000_000  # 硬碟剩低過 1.2GB 就安全暫停(部機個碟好逼,爆碟教訓)
BEYOND_SKIP_AFTER = 2  # 同一 route 連續 N 個月「Google 未有數據」→ 跳過剩低月份


class ShellPage(Exception):
    """Google 回咗未載入結果嘅空殼頁(HTTP 層先會有)"""


class Blocked(Exception):
    """HTTP 非 200 / 驗證頁 — 疑似被 rate limit"""


class AbortScan(Exception):
    """連環失敗到盡,優雅收工"""


def log(msg: str) -> None:
    print(msg, flush=True)


def gf_params(tfs: str, currency: str) -> dict:
    # 注意:tfu 參數係必需 — 冇咗佢連真瀏覽器都會「Oops」(實測)
    return {"tfs": tfs, "hl": "en", "tfu": "EgQIABABIgA", "curr": currency}


# ------------------------------------------------------------ Tier 1:HTTP

def fetch_http(tfs: str, currency: str):
    """HTTP 直撈一次。每次開新 Client = 新隨機瀏覽器偽裝。"""
    client = Client(impersonate="random", verify=False)
    res = client.get(GF_URL, params=gf_params(tfs, currency))
    if res.status_code != 200:
        raise Blocked(f"HTTP {res.status_code}")
    try:
        return parse_response(res)
    except RuntimeError as e:
        msg = str(e)
        if "Loading results" in msg:
            raise ShellPage() from None
        if "unusual traffic" in msg.lower() or "captcha" in msg.lower():
            raise Blocked("Google 驗證頁") from None
        return None  # 頁面正常但冇航班


# ------------------------------------------------------ Tier 2:真瀏覽器

class BrowserFetcher:
    """長開一個 headless Chrome 重用(慳卻每次 3-4 秒嘅開機時間)。"""

    UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    RECYCLE_EVERY = 60  # 每 N 次 fetch 換新 context(清 cookies,防指紋累積)

    def __init__(self):
        self._pw = None
        self._browser = None
        self._ctx = None
        self._page = None
        self._fetches = 0

    def _ensure(self) -> None:
        if self._pw is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
        if self._browser is None or not self._browser.is_connected():
            self._browser = self._pw.chromium.launch(
                args=["--disable-blink-features=AutomationControlled",
                      "--disk-cache-size=104857600"])  # cache 上限 100MB,咪食晒個碟
            self._ctx = None
        if self._ctx is None or self._fetches >= self.RECYCLE_EVERY:
            if self._ctx is not None:
                try:
                    self._ctx.close()
                except Exception:
                    pass
            self._ctx = self._browser.new_context(
                user_agent=self.UA, viewport={"width": 1366, "height": 900},
                locale="en-US")
            self._page = self._ctx.new_page()
            self._fetches = 0

    @staticmethod
    def _outcome(page, timeout_s: float = 14.0) -> str:
        """等到 結果出現/明確冇數據/超時 為止。"""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                if page.locator("ul.Rk10dc li").count() > 0:
                    return "results"
                txt = page.evaluate("() => document.body.innerText") or ""
            except Exception:
                return "error"
            if "No results returned" in txt or "something went wrong" in txt:
                return "oops"
            if "No flights" in txt:
                return "no_flights"
            page.wait_for_timeout(700)
        return "stuck"

    def fetch(self, url: str):
        """回 ("ok", html) / ("no_flights", None) / ("beyond", None) / ("fail", reason)。"""
        for round_ in (1, 2):  # 瀏覽器出事就重啟一次再試
            try:
                self._ensure()
                self._fetches += 1
                page = self._page
                page.goto(url, timeout=35000)
                if page.url.startswith("https://consent.google.com"):
                    page.click('text="Accept all"')
                    page.wait_for_timeout(2000)
                outcome = self._outcome(page)
                reloads = 0
                while outcome == "oops" and reloads < 2:
                    reloads += 1
                    try:
                        page.get_by_text("Reload", exact=False).first.click(timeout=3000)
                    except Exception:
                        page.reload(timeout=35000)
                    outcome = self._outcome(page)
                if outcome == "results":
                    html = page.evaluate(
                        "() => document.querySelector('[role=\"main\"]').innerHTML")
                    return ("ok", html)
                if outcome == "no_flights":
                    return ("no_flights", None)
                if outcome == "oops":
                    return ("beyond", None)  # 撳極 Reload 都冇 = Google 真係未有數據
                return ("fail", f"browser_{outcome}")
            except Exception as e:
                # 瀏覽器死咗 — 掉咗佢,下一圈會重啟
                try:
                    if self._browser is not None:
                        self._browser.close()
                except Exception:
                    pass
                self._browser = None
                self._ctx = None
                if round_ == 2:
                    return ("fail", f"browser_{type(e).__name__}")
        return ("fail", "browser_unreachable")

    def close(self) -> None:
        for closer in (lambda: self._ctx.close(), lambda: self._browser.close(),
                       lambda: self._pw.stop()):
            try:
                closer()
            except Exception:
                pass


# ------------------------------------------------------------ 查價(合體)

def parse_price(raw: str):
    """'HK$2312' → 2312;'Price unavailable' → None。"""
    digits = re.sub(r"[^0-9]", "", raw or "")
    return int(digits) if digits else None


def _result_to_dict(result, tfs: str, via: str) -> dict:
    if result is None:
        return {"status": "no_flights", "tfs": tfs, "via": via}
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
        return {"status": "no_flights", "tfs": tfs, "via": via}
    best.update(status="ok", tfs=tfs, via=via,
                price_trend=result.current_price or "")
    return best


def query_roundtrip(origin: str, dest: str, depart: dt.date, ret: dt.date,
                    currency: str, browser, seat: str = "economy") -> dict:
    """查一對來回日期:先 HTTP(最多 3 次,純空殼 2 次就算),唔得就真瀏覽器。"""
    flt = TFSData.from_interface(
        flight_data=[
            FlightData(date=depart.isoformat(), from_airport=origin, to_airport=dest),
            FlightData(date=ret.isoformat(), from_airport=dest, to_airport=origin),
        ],
        trip="round-trip",
        passengers=Passengers(adults=1),
        seat=seat,
    )
    tfs = flt.as_b64().decode()
    last_err = ""
    shells = 0
    for _ in range(3):
        try:
            return _result_to_dict(fetch_http(tfs, currency), tfs, via="http")
        except ShellPage:
            shells += 1
            last_err = f"空殼頁×{shells}"
            if shells >= 2:
                break  # HTTP 冇得救 — 升級真瀏覽器
            time.sleep(random.uniform(3, 6))
        except Blocked as e:
            last_err = str(e)
            time.sleep(random.uniform(8, 15))
            break  # 被擋就唔好再嘥 HTTP,直接升級
        except Exception as e:
            last_err = type(e).__name__
            time.sleep(random.uniform(4, 8))

    if browser is not None:
        url = GF_URL + "?" + urllib.parse.urlencode(gf_params(tfs, currency))
        status, payload = browser.fetch(url)
        time.sleep(random.uniform(1, 3))  # 瀏覽器嗰下都要抖
        if status == "ok":
            class _Resp:
                status_code = 200
                text = payload
                text_markdown = payload
            try:
                return _result_to_dict(parse_response(_Resp), tfs, via="browser")
            except RuntimeError:
                return {"status": "no_flights", "tfs": tfs, "via": "browser"}
        if status == "no_flights":
            return {"status": "no_flights", "tfs": tfs, "via": "browser"}
        if status == "beyond":
            return {"status": "beyond_data", "tfs": tfs}
        last_err = payload or "browser_fail"

    return {"status": "failed", "error": last_err, "tfs": tfs}


# ------------------------------------------------------------ 掃描編排

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


KEEP_STATUSES = {"ok", "no_flights", "no_data", "beyond_data"}  # resume 時呢啲月份直接沿用


def main() -> int:
    ap = argparse.ArgumentParser(description="引擎A:Google Flights 掃描器(fast-flights,雙層)")
    ap.add_argument("--smoke", action="store_true", help="冒煙測試:3 條代表 route、每月 1 個樣本")
    ap.add_argument("--max-routes", type=int, default=0, help="只掃頭 N 條 route(0=全部)")
    ap.add_argument("--months", type=int, default=12, help="掃未來幾多個月(預設 12)")
    ap.add_argument("--samples", type=int, default=0, help="每月抽樣日數 1–4(預設用 routes.yaml)")
    ap.add_argument("--resume", action="store_true", help="沿用今日已掃結果,只補失敗月份+未掃 route")
    ap.add_argument("--no-browser", action="store_true", help="停用真瀏覽器後備(淨 HTTP)")
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

    out_dir = ROOT / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"scan_{today.strftime('%Y%m%d')}.json"

    # 清走上次瀏覽器可能留低嘅 temp profile(防膨脹)
    for leftover in Path(tempfile.gettempdir()).glob("*playwright*"):
        shutil.rmtree(leftover, ignore_errors=True)

    # ---- resume:讀返今日已有結果 ----
    old_recs: dict = {}
    if args.resume and out_path.exists():
        try:
            old = json.loads(out_path.read_text(encoding="utf-8"))
            old_recs = {f'{r["origin"]}-{r["dest"]}': r for r in old.get("routes", [])}
            log(f"[scan] resume:讀到今日已有 {len(old_recs)} 條 route 紀錄,會沿用得嘅月份")
        except Exception as e:
            log(f"[scan] resume 讀檔失敗({type(e).__name__})— 由頭掃過")

    total_q = len(routes) * len(months) * samples
    est_min = total_q * (((delay_lo + delay_hi) / 2) + 3) / 60
    log(f"[scan] {len(routes)} 條 route × {len(months)} 個月 × 每月 {samples} 樣本"
        f" ≈ {total_q} queries,淨 HTTP 預計 ~{est_min:.0f} 分鐘(瀏覽器後備另計)")

    browser = None if args.no_browser else BrowserFetcher()

    scan = {
        "scan_date": today.isoformat(),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source": "fast-flights(Google Flights)+ playwright 後備",
        "currency": currency,
        "status": "running",
        "params": {"smoke": args.smoke, "months": len(months),
                   "samples_per_month": samples, "routes": len(routes),
                   "resumed": bool(old_recs)},
        "stats": {"queries": 0, "ok": 0, "no_flights": 0, "failed": 0,
                  "beyond_data": 0, "tier2_used": 0, "tier2_saved": 0,
                  "resumed_months": 0},
        "routes": [],
    }
    # resume:先 seed 晒舊紀錄,處理到嗰條 route 就原位更新(唔會跌數據)
    rec_index: dict = {}
    for key, old_rec in old_recs.items():
        scan["routes"].append(old_rec)
        rec_index[key] = len(scan["routes"]) - 1

    pace = {"q": 0}
    guard = {"consec": 0, "rests": 0}
    t0 = time.time()

    def save(status: str) -> None:
        scan["status"] = status
        scan["stats"]["elapsed_s"] = round(time.time() - t0)
        ms = [mr for rt in scan["routes"] for mr in rt["months"]]
        scan["stats"]["months_ok"] = sum(1 for x in ms if x["status"] == "ok")
        scan["stats"]["months_failed"] = sum(1 for x in ms if x["status"] == "failed")
        scan["stats"]["months_beyond"] = sum(1 for x in ms if x["status"] == "beyond_data")
        tmp_path = out_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(scan, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp_path.replace(out_path)  # 原子替換 — 寫到一半爆碟都唔會整爛舊檔

    def cool_down() -> None:
        if pace["q"] and pace["q"] % COOL_EVERY == 0:
            zzz = random.uniform(20, 40)
            log(f"[scan] …唞 {zzz:.0f} 秒(每 {COOL_EVERY} 個 query 抖一抖)")
            time.sleep(zzz)

    def rest_or_abort() -> None:
        """連環真失敗:唞長覺(最多 3 次),唞完唔掂先至收工。"""
        if guard["rests"] >= MAX_LONG_RESTS:
            raise AbortScan()
        guard["rests"] += 1
        zzz = random.uniform(600, 900)
        log(f"[scan] ⚠ 連續 {ABORT_AFTER} 個 query 失敗 — 自動唞 {zzz/60:.0f} 分鐘等 Google 消氣"
            f"(第 {guard['rests']}/{MAX_LONG_RESTS} 次)")
        time.sleep(zzz)
        guard["consec"] = 0

    def scan_month(origin: str, dest: str, stay: int, y: int, m: int) -> dict:
        mlabel = f"{y}-{m:02d}"
        oks: list = []
        tried = failed = beyond = 0
        last_err = ""
        for day in sample_days:
            depart = dt.date(y, m, min(day, calendar.monthrange(y, m)[1]))
            if depart < today + dt.timedelta(days=3):
                continue  # 太近/已過嘅日子唔查
            ret = depart + dt.timedelta(days=stay)
            r = query_roundtrip(origin, dest, depart, ret, currency, browser)
            tried += 1
            pace["q"] += 1
            scan["stats"]["queries"] += 1
            if r.get("via") == "browser":
                scan["stats"]["tier2_used"] += 1
            if r["status"] == "ok":
                scan["stats"]["ok"] += 1
                guard["consec"] = 0
                if r.get("via") == "browser":
                    scan["stats"]["tier2_saved"] += 1
                oks.append({**r, "depart": depart.isoformat(), "return": ret.isoformat()})
            elif r["status"] == "no_flights":
                scan["stats"]["no_flights"] += 1
                guard["consec"] = 0
            elif r["status"] == "beyond_data":
                scan["stats"]["beyond_data"] += 1
                beyond += 1
                guard["consec"] = 0  # Google 有答覆,只係未有數據 — 唔算被擋
            else:
                scan["stats"]["failed"] += 1
                failed += 1
                last_err = r.get("error", "")
                guard["consec"] += 1
            time.sleep(random.uniform(float(delay_lo), float(delay_hi)))
            cool_down()
        if oks:
            oks.sort(key=lambda o: o["price"])
            top: list = []
            seen_dep: set = set()
            for o in oks:  # 揀 top-3 唔同出發日(避免同一日重複)
                if o["depart"] in seen_dep:
                    continue
                seen_dep.add(o["depart"])
                top.append(o)
                if len(top) >= 3:
                    break
            best = top[0]
            periods = [{"depart": o["depart"], "return": o["return"], "price": o["price"],
                        "airline": o["airline"], "google_flights": deep_link(o["tfs"], currency)}
                       for o in top]
            via = "🌐" if best.get("via") == "browser" else ""
            return {
                "month": mlabel, "status": "ok",
                "price": best["price"], "currency": currency,
                "depart": best["depart"], "return": best["return"],
                "airline": best["airline"], "stops": best["stops"],
                "duration": best["duration"], "price_trend": best["price_trend"],
                "google_flights": deep_link(best["tfs"], currency),
                "periods": periods,
                "samples_tried": tried, "samples_failed": failed,
                "via": best.get("via", "http"), "_via_mark": via,
            }
        if beyond and failed == 0:
            return {"month": mlabel, "status": "beyond_data",
                    "samples_tried": tried}
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
            mark = mrec.pop("_via_mark", "") or ("🌐" if mrec.get("via") == "browser" else "")
            log(f"{prefix} {origin}→{dest} {mrec['month']}"
                f"  {currency} {mrec['price']:,}({name},{stops_txt}){mark}")
        elif mrec["status"] == "beyond_data":
            log(f"{prefix} {origin}→{dest} {mrec['month']}  − Google 未有數據"
                +("(跳過)" if mrec.get("skipped") else ""))
        else:
            log(f"{prefix} {origin}→{dest} {mrec['month']}"
                f"  ✗ {mrec['status']}({mrec.get('error', '')})")

    exit_code = 0
    try:
        for ri, route in enumerate(routes, 1):
            free = shutil.disk_usage(str(ROOT)).free
            if free < MIN_FREE_BYTES:
                log(f"[scan] ⚠ 硬碟得返 {free / 1e9:.1f}GB — 安全暫停,執完位用 --resume 接力")
                save("paused_low_disk")
                return 3
            key = f'{route["origin"]}-{route["dest"]}'
            old_rec = old_recs.get(key)
            old_months = {m["month"]: m for m in old_rec["months"]} if old_rec else {}

            rec = {k: route[k] for k in
                   ("origin", "origin_name", "dest", "dest_name", "region", "stay_nights")}
            rec["months"] = []
            consec_beyond = 0
            skipping = False
            for (y, m) in months:
                mlabel = f"{y}-{m:02d}"
                kept = old_months.get(mlabel)
                if kept is not None and kept["status"] in KEEP_STATUSES:
                    rec["months"].append(kept)
                    scan["stats"]["resumed_months"] += 1
                    consec_beyond = consec_beyond + 1 if kept["status"] == "beyond_data" else 0
                    continue
                if skipping or consec_beyond >= BEYOND_SKIP_AFTER:
                    if not skipping:
                        skipping = True
                        log(f"[{ri:>3}/{len(routes)}] {route['origin']}→{route['dest']}"
                            f"  ↷ 連續 {consec_beyond} 個月 Google 未有數據,之後月份照標跳過")
                    rec["months"].append({"month": mlabel, "status": "beyond_data",
                                          "skipped": True})
                    scan["stats"]["beyond_data"] += 1
                    continue
                mrec = scan_month(route["origin"], route["dest"],
                                  route["stay_nights"], y, m)
                consec_beyond = consec_beyond + 1 if mrec["status"] == "beyond_data" else 0
                rec["months"].append(mrec)
                log_month(f"[{ri:>3}/{len(routes)}]", route["origin"], route["dest"], mrec)
                if guard["consec"] >= ABORT_AFTER:
                    rest_or_abort()
            # 原位更新(resume)或者加新
            if key in rec_index:
                scan["routes"][rec_index[key]] = rec
            else:
                scan["routes"].append(rec)
                rec_index[key] = len(scan["routes"]) - 1
            save("running")  # 每條 route 完即寫檔,斷咗都有得剩
    except AbortScan:
        save("aborted_blocked")
        log(f"[scan] ⚠ 唞極都係連環失敗 — 收工。已掃部分保留喺 {out_path.name},"
            f"遲啲用 --resume 接力")
        exit_code = 2
    except KeyboardInterrupt:
        save("interrupted")
        log(f"[scan] 手動中斷,已掃部分保留喺 {out_path.name}(--resume 可接力)")
        exit_code = 1
    except OSError as e:
        # 多數係爆碟 — save 用原子寫法,舊檔無事;呢度唔好再試寫嘢
        try:
            log(f"[scan] ⚠ 系統 I/O 錯誤({e})— 收工,執完位用 --resume 接力")
        except Exception:
            pass
        exit_code = 3
    finally:
        if browser is not None:
            browser.close()

    if exit_code:
        return exit_code

    save("completed")
    s = scan["stats"]
    log("")
    log(f"[scan] ✅ 完成:{s['queries']} queries(成功 {s['ok']} / 冇航班 {s['no_flights']}"
        f" / Google未有數據 {s['beyond_data']} / 失敗 {s['failed']});"
        f"真瀏覽器出動 {s['tier2_used']} 次救返 {s['tier2_saved']} 個;"
        f"沿用舊結果 {s['resumed_months']} 個月份;用咗 {s['elapsed_s'] // 60} 分鐘")
    log(f"[scan] 月份總計:{s['months_ok']} 有價 / {s['months_beyond']} 未有數據"
        f" / {s['months_failed']} 失敗 → {out_path}")

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
