"""
test_consolidate.py — Phase 1B 去重測試(離線)
跑法:uv run python test_consolidate.py
"""
import sys

from consolidate import consolidate


def main() -> None:
    ok = True
    cands = [
        {"airline": "Cathay", "origin": "HKG", "destination": "LHR",
         "depart_date": "2026-09-12", "return_date": "2026-09-20", "confidence": 60},
        {"airline": "cathay ", "origin": "hkg", "destination": "lhr",
         "depart_date": "2026-09-12", "return_date": "2026-09-20", "confidence": 85},
        {"airline": "Edelweiss", "origin": "SZX", "destination": "ZRH",
         "depart_date": "2026-11-03", "return_date": "2026-11-12", "confidence": 70},
    ]
    out = consolidate(cands)

    cond1 = len(out) == 2
    print(("✅" if cond1 else "❌"), "去重後 3→2 條:", len(out))
    ok = ok and cond1

    cond2 = bool(out) and out[0]["confidence"] == 85
    print(("✅" if cond2 else "❌"), "保留高 confidence + 排頭:", out[0]["confidence"] if out else None)
    ok = ok and cond2

    print()
    print("🎉 consolidate 測試通過" if ok else "⚠️ consolidate 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
