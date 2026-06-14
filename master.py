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
