"""
db.py — Supabase 寫入 / 讀取(Phase 2.5)
=========================================
經 PostgREST(httpx)upsert 兩條 stream 嘅結果入 Supabase:
    cheap_flights — Stream A(scanner scan_*.json,每 route 每月最平)
    error_fares   — Stream B(master verified_*.json 嘅 live/unverified/dead)
    meta          — last_updated 時間戳

鐵律:SUPABASE_URL + SUPABASE_SECRET_KEY 只由 .env / 環境變數讀,唔寫死;
      未配置就 no-op(log + 回 0),唔當機;對外 request 有 retry。
"""
from __future__ import annotations

import datetime as dt
import os
import time

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import master  # reuse tripcom_link(純 URL builder)

HTTP_TIMEOUT = 30.0
MAX_RETRIES = 3


def log(msg: str) -> None:
    print(f"[db] {msg}", flush=True)


def cfg() -> dict:
    """由環境讀 Supabase 設定。URL 容錯:就算貼咗 /rest/v1 都剝返做基底。"""
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    key = (os.getenv("SUPABASE_SECRET_KEY", "").strip()
           or os.getenv("SUPABASE_SERVICE_KEY", "").strip())
    return {"url": url, "key": key}


def configured(c: dict | None = None) -> bool:
    c = c or cfg()
    return bool(c.get("url") and c.get("key"))


def _headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v):
    n = _num(v)
    return int(n) if n is not None else None


# ---------- 行映射 ----------

def error_fare_row(d: dict) -> dict | None:
    """master verified deal → error_fares 行。冇 source_url(upsert key)就跳過。"""
    if not d.get("source_url"):
        return None
    return {
        "origin": d.get("origin"),
        "destination": d.get("destination"),
        "airline": d.get("airline"),
        "depart_date": d.get("depart_date") or None,
        "return_date": d.get("return_date") or None,
        "claimed_price_hkd": _num(d.get("price")),
        "verified_price_hkd": _num(d.get("verified_price")),
        "currency": d.get("currency") or "HKD",
        "status": d.get("status") or "unverified",
        "confidence": _int(d.get("confidence")),
        "source_platform": d.get("source_platform"),
        "source_url": d.get("source_url"),
        "gflights_url": d.get("gflights_url"),
        "tripcom_url": d.get("tripcom_url"),
    }


def cheap_flight_rows(scan_doc: dict) -> list[dict]:
    """scanner scan_*.json → cheap_flights 行(展平 routes × status==ok 月份)。
    每行帶 scanned_at = scan_doc["generated_at"](若有)或當前時間(ISO),
    確保 upsert UPDATE 時 scanned_at 真正更新,唔會凍咗喺第一次 INSERT 嘅 default now()。
    """
    scanned_at = (scan_doc.get("generated_at")
                  or dt.datetime.now().isoformat(timespec="seconds"))
    rows = []
    for rt in scan_doc.get("routes", []) or []:
        origin, dest, region = rt.get("origin"), rt.get("dest"), rt.get("region")
        for mo in rt.get("months", []) or []:
            if mo.get("status") != "ok":
                continue
            depart, ret = mo.get("depart"), mo.get("return")
            cur = mo.get("currency") or "HKD"
            tripcom = (master.tripcom_link(origin, dest, depart, ret, currency=cur)
                       if (origin and dest and depart and ret) else None)
            rows.append({
                "origin": origin, "destination": dest, "region": region,
                "depart_date": depart or None, "return_date": ret or None,
                "price_hkd": _num(mo.get("price")), "currency": cur,
                "airline": mo.get("airline"), "baggage": None,
                "month": mo.get("month"),
                "gflights_url": mo.get("google_flights"),
                "tripcom_url": tripcom,
                "periods": mo.get("periods"),  # top-3 平價時段(jsonb)
                "scanned_at": scanned_at,       # 明確覆寫,UPDATE 時時間戳真正推進
            })
    return rows


# ---------- 寫入 / 讀取 ----------

def upsert(table: str, rows: list[dict], on_conflict: str,
           c: dict | None = None, client=None) -> int:
    """PostgREST upsert(merge-duplicates)。client 可注入(測試用 fake)。回成功寫入行數。"""
    c = c or cfg()
    rows = [r for r in rows if r]
    if not rows:
        return 0
    if not configured(c):
        log(f"未配置 SUPABASE_URL/SECRET_KEY — 跳過 {table}({len(rows)} 行未寫)")
        return 0
    url = f"{c['url']}/rest/v1/{table}?on_conflict={on_conflict}"
    headers = _headers(c["key"])
    post = client or httpx.post
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = post(url, headers=headers, json=rows, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            return len(rows)
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    log(f"upsert {table} 失敗(放棄):{last}")
    return 0


def select(table: str, params: str = "select=*&limit=5", c: dict | None = None) -> list:
    """GET 讀返(主要畀 live test / debug 用)。"""
    c = c or cfg()
    if not configured(c):
        return []
    url = f"{c['url']}/rest/v1/{table}?{params}"
    try:
        resp = httpx.get(url, headers={"apikey": c["key"],
                                       "Authorization": f"Bearer {c['key']}"},
                         timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:  # noqa: BLE001
        log(f"select {table} 失敗:{e}")
        return []


def _order_stale(rows: list[dict]) -> list[dict]:
    """純本地排序:把 origin/destination/scanned_at 行列摺疊成一行/route pair,
    取最舊 scanned_at(null = 從未掃 = 最舊),由舊到新排列。
    回 [{"origin","destination","last"},...] 排好序。
    """
    seen: dict[tuple, str | None] = {}
    for r in rows:
        key = (r.get("origin"), r.get("destination"))
        val = r.get("scanned_at")
        if key not in seen:
            seen[key] = val
        else:
            # keep the minimum (oldest) — None beats any timestamp
            prev = seen[key]
            if prev is None:
                pass  # None already = stalest, keep it
            elif val is None:
                seen[key] = None
            else:
                seen[key] = val if val < prev else prev

    def _sort_key(item):
        last = item["last"]
        # None → stalest → sort first by returning a tuple that sorts before any real ts
        return (0, "") if last is None else (1, last)

    result = [{"origin": k[0], "destination": k[1], "last": v} for k, v in seen.items()]
    result.sort(key=_sort_key)
    return result


def stale_routes(limit: int | None = None, c: dict | None = None) -> list[dict]:
    """讀 cheap_flights,回 [{"origin","destination","last"}] 由最舊 scanned_at 到最新。
    null/從未掃嘅路線排最前。未配置 Supabase → [] (no-op 安全)。
    limit: 限制回幾多條(None = 全部)。
    """
    c = c or cfg()
    if not configured(c):
        return []
    params = "select=origin,destination,scanned_at&order=scanned_at.asc.nullsfirst"
    if limit:
        params += f"&limit={limit * 10}"  # 取多啲,本地 dedupe 之後再截
    rows = select("cheap_flights", params, c=c)
    ordered = _order_stale(rows)
    if limit is not None:
        ordered = ordered[:limit]
    return ordered


def delete(table: str, params: str, c: dict | None = None, client=None) -> bool:
    """DELETE 符合 PostgREST filter 嘅行(例:source_url=eq.xxx)。主要畀自測清手尾用。"""
    c = c or cfg()
    if not configured(c):
        return False
    url = f"{c['url']}/rest/v1/{table}?{params}"
    fn = client or httpx.delete
    try:
        resp = fn(url, headers=_headers(c["key"]), timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001
        log(f"delete {table} 失敗:{e}")
        return False


def push_error_fares(deals: list[dict], c: dict | None = None, client=None) -> int:
    n = upsert("error_fares", [error_fare_row(d) for d in deals], "source_url",
               c=c, client=client)
    if n:
        log(f"error_fares upsert {n} 行")
    return n


def push_cheap_flights(scan_doc: dict, c: dict | None = None, client=None) -> int:
    n = upsert("cheap_flights", cheap_flight_rows(scan_doc), "origin,destination,month",
               c=c, client=client)
    if n:
        log(f"cheap_flights upsert {n} 行")
    return n


def set_meta(key: str, value, c: dict | None = None, client=None) -> int:
    return upsert("meta", [{"key": key, "value": str(value)}], "key", c=c, client=client)


if __name__ == "__main__":
    # 直接跑 = 寫一筆測試 error_fare 入 Supabase,再讀返出嚟證明接通。
    c = cfg()
    if not configured(c):
        log("未配置 SUPABASE_URL / SUPABASE_SECRET_KEY(.env)。")
        raise SystemExit(1)
    log(f"連 {c['url']}")
    sample = {
        "origin": "HKG", "destination": "TPE", "airline": "(測試)DB Test Air",
        "depart_date": "2026-09-10", "return_date": "2026-09-14",
        "price": 888, "verified_price": None, "currency": "HKD",
        "status": "unverified", "confidence": 75,
        "source_platform": "selftest", "source_url": "https://example.com/db-selftest",
        "gflights_url": "https://www.google.com/travel/flights",
        "tripcom_url": "https://www.trip.com/flights/",
    }
    n = push_error_fares([sample], c=c)
    rows = select("error_fares",
                  "select=source_url,origin,destination,status&order=found_at.desc&limit=10")
    hit = any(r.get("source_url") == "https://example.com/db-selftest" for r in rows)
    delete("error_fares", "source_url=eq.https%3A%2F%2Fexample.com%2Fdb-selftest", c=c)  # 清返測試行
    log(f"寫入 {n} 行;讀返搵到測試行:{hit};已清走測試行")
    print("✅ Supabase 接通(寫到 + 讀到 + 自己清手尾)" if (n == 1 and hit)
          else "❌ 接唔通,睇上面 [db] log")
    raise SystemExit(0 if (n == 1 and hit) else 1)
