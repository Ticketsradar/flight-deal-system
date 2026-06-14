"""spike_travelpayouts.py — Phase 1 spike v3:試 cheap + week-matrix
=================================================================================
v1 month-matrix → 單程(return_date 空)。v2 latest one_way=false → 幾乎冇數據。
v3(本檔)試:
  A) v1/prices/cheap          — 最平來回票(應有 depart+return)
  B) v2/prices/week-matrix    — 出發×回程格(真·變行程長度)
只測 4 條代表線,dump 樣本 + 密度,睇 Travelpayouts 到底有冇可用嘅來回變長度數據。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
TOKEN = (os.environ.get("TRAVELPAYOUTS_TOKEN") or "").strip()
ROOT = Path(__file__).parent
CHEAP = "https://api.travelpayouts.com/v1/prices/cheap"
WEEKM = "https://api.travelpayouts.com/v2/prices/week-matrix"
HEAD = {"X-Access-Token": TOKEN, "Accept-Encoding": "gzip, deflate"}

ROUTES = [("HKG", "BKK"), ("HKG", "NRT"), ("HKG", "KUL"), ("SZX", "BKK")]
DEP = "2026-08-10"
RET = "2026-08-15"


def nights_of(dep, ret):
    try:
        return (dt.date.fromisoformat(ret) - dt.date.fromisoformat(dep)).days
    except Exception:
        return None


def probe_cheap(o, d):
    p = {"origin": o, "destination": d, "depart_date": "2026-08",
         "return_date": "2026-08", "currency": "hkd", "show_to_affiliates": "false"}
    r = httpx.get(CHEAP, params=p, headers=HEAD, timeout=30)
    if r.status_code != 200:
        return {"http": r.status_code, "body": r.text[:200]}
    j = r.json()
    data = j.get("data") or {}
    recs = []
    for dest, byidx in data.items():
        for _, rec in (byidx or {}).items():
            recs.append(rec)
    nn = [nights_of(x.get("depart_date"), x.get("return_date")) for x in recs]
    nn = [x for x in nn if x and x > 0]
    return {"records": len(recs), "with_return": sum(1 for x in recs if x.get("return_date")),
            "nights": sorted(set(nn)), "usable_2_14": sum(1 for x in nn if 2 <= x <= 14),
            "sample": recs[0] if recs else None}


def probe_week(o, d):
    p = {"origin": o, "destination": d, "depart_date": DEP, "return_date": RET,
         "currency": "hkd", "show_to_affiliates": "false"}
    r = httpx.get(WEEKM, params=p, headers=HEAD, timeout=30)
    if r.status_code != 200:
        return {"http": r.status_code, "body": r.text[:200]}
    j = r.json()
    data = j.get("data") or []
    nn = [nights_of(x.get("depart_date"), x.get("return_date")) for x in data]
    nn = [x for x in nn if x and x > 0]
    return {"records": len(data), "with_return": sum(1 for x in data if x.get("return_date")),
            "nights": sorted(set(nn)), "usable_2_14": sum(1 for x in nn if 2 <= x <= 14),
            "sample": data[0] if data else None}


def main():
    if not TOKEN:
        print("✗ 冇 TRAVELPAYOUTS_TOKEN")
        return 1
    result = {}
    for (o, d) in ROUTES:
        route = f"{o}-{d}"
        c = probe_cheap(o, d)
        time.sleep(0.7)
        w = probe_week(o, d)
        time.sleep(0.7)
        result[route] = {"cheap": c, "week_matrix": w}
        print(f"\n=== {route} ===")
        print(f"  cheap      : {c.get('records','?')} 筆 / 有return {c.get('with_return','?')} "
              f"/ nights {c.get('nights','?')} / 2-14 {c.get('usable_2_14','?')}"
              + (f"  [HTTP {c['http']}]" if 'http' in c else ""))
        print(f"  week-matrix: {w.get('records','?')} 筆 / 有return {w.get('with_return','?')} "
              f"/ nights {w.get('nights','?')} / 2-14 {w.get('usable_2_14','?')}"
              + (f"  [HTTP {w['http']}]" if 'http' in w else ""))

    # 樣本
    for route, v in result.items():
        for ep in ("cheap", "week_matrix"):
            s = v[ep].get("sample")
            if s:
                print(f"\n[{route} {ep}] 樣本:{json.dumps(s, ensure_ascii=False)}")
                break
        else:
            continue
        break
    for route, v in result.items():
        s = v["week_matrix"].get("sample")
        if s:
            print(f"\n[{route} week_matrix] 樣本:{json.dumps(s, ensure_ascii=False)}")
            break

    out = ROOT / ".planning" / "research" / "TRAVELPAYOUTS-SPIKE-v3.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n寫咗 {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
