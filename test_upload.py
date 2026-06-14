"""
test_upload.py — Phase 2.5 upload 純邏輯測試(離線)
跑法:uv run python test_upload.py
"""
import sys

import upload


def main() -> None:
    ok = True

    doc = {"live": [{"source_url": "a"}],
           "unverified": [{"source_url": "b"}, {"source_url": "c"}],
           "dead": [{"source_url": "d"}]}
    deals = upload.deals_from_verified(doc)
    cond = ([d["source_url"] for d in deals] == ["a", "b", "c", "d"])
    print(("✅" if cond else "❌"), "deals_from_verified 合併三 bucket(live→unverified→dead):", len(deals))
    ok = ok and cond

    cond = upload.deals_from_verified({}) == [] and upload.deals_from_verified({"live": None}) == []
    print(("✅" if cond else "❌"), "缺 bucket / None 都唔當機")
    ok = ok and cond

    print()
    print("🎉 upload 純邏輯測試通過" if ok else "⚠️ upload 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
