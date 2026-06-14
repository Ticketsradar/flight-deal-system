"""
test_scout.py — Phase 1B scout 純邏輯測試(離線,唔 call LLM)
跑法:uv run python test_scout.py
"""
import sys

from scout import build_scout_system, chunked, _valid

FILTERS = {"origins": ["HKG", "SZX", "CAN"], "horizon_months": 12,
           "signals": ["商務艙價錢接近經濟艙", "非美籍航空長途異常平"]}

REQUIRED = ("origin", "destination", "depart_date", "return_date", "price",
            "currency", "airline", "source_platform", "source_url", "confidence")


def main() -> None:
    ok = True

    sysmsg = build_scout_system(FILTERS)
    cond = "HKG" in sysmsg and "商務艙" in sysmsg and "JSON array" in sysmsg
    print(("✅" if cond else "❌"), "system prompt 含 origins + signals + 格式要求")
    ok = ok and cond

    groups = list(chunked([1, 2, 3, 4, 5], 2))
    cond = groups == [[1, 2], [3, 4], [5]]
    print(("✅" if cond else "❌"), "chunked:", groups)
    ok = ok and cond

    good = {k: "x" for k in REQUIRED}
    cond = _valid(good) and not _valid({"origin": "HKG"})
    print(("✅" if cond else "❌"), "_valid 篩走缺欄位嘅 candidate")
    ok = ok and cond

    print()
    print("🎉 scout 純邏輯測試通過" if ok else "⚠️ scout 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
