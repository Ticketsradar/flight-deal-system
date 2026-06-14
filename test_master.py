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
