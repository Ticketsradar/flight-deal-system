"""
test_db.py — Phase 2.5 db 純邏輯測試(離線,唔連 Supabase)
跑法:uv run python test_db.py
"""
import sys

import db


def main() -> None:
    ok = True

    # error_fare_row 映射
    d = {"origin": "HKG", "destination": "NRT", "airline": "CX",
         "depart_date": "2026-08-30", "return_date": "2026-09-05",
         "price": 600, "verified_price": 2426, "currency": "HKD",
         "status": "dead", "confidence": 85, "source_platform": "reddit/r/x",
         "source_url": "https://r/x/1", "gflights_url": "https://g", "tripcom_url": "https://t"}
    row = db.error_fare_row(d)
    cond = (row["claimed_price_hkd"] == 600 and row["verified_price_hkd"] == 2426
            and row["status"] == "dead" and row["confidence"] == 85
            and row["source_url"] == "https://r/x/1" and row["destination"] == "NRT")
    print(("✅" if cond else "❌"), "error_fare_row 映射欄位")
    ok = ok and cond

    cond = db.error_fare_row({"origin": "HKG", "destination": "NRT"}) is None
    print(("✅" if cond else "❌"), "冇 source_url → 跳過(回 None)")
    ok = ok and cond

    # cheap_flight_rows 展平 + 跳非 ok + 砌 tripcom
    scan = {"routes": [
        {"origin": "HKG", "dest": "NRT", "region": "東北亞", "months": [
            {"month": "2026-08", "status": "ok", "price": 2426, "currency": "HKD",
             "depart": "2026-08-30", "return": "2026-09-05", "airline": "CX",
             "google_flights": "https://g/nrt"},
            {"month": "2026-09", "status": "failed"},
        ]},
        {"origin": "HKG", "dest": "TPE", "region": "東北亞", "months": [
            {"month": "2026-08", "status": "ok", "price": 900, "currency": "HKD",
             "depart": "2026-08-10", "return": "2026-08-14", "airline": "CI",
             "google_flights": "https://g/tpe"},
        ]},
    ]}
    rows = db.cheap_flight_rows(scan)
    cond = (len(rows) == 2 and rows[0]["origin"] == "HKG" and rows[0]["month"] == "2026-08"
            and rows[0]["price_hkd"] == 2426 and rows[0]["gflights_url"] == "https://g/nrt"
            and "trip.com" in (rows[0]["tripcom_url"] or ""))
    print(("✅" if cond else "❌"), "cheap_flight_rows 展平+跳failed+砌tripcom:", len(rows))
    ok = ok and cond

    # upsert:注入 fake client,砌啱 URL/headers,回行數
    seen: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, json=json)

        class R:
            def raise_for_status(self):
                pass
        return R()

    conf = {"url": "https://x.supabase.co", "key": "sb_secret_K"}
    n = db.upsert("error_fares", [row], "source_url", c=conf, client=fake_post)
    cond = (n == 1 and "/rest/v1/error_fares?on_conflict=source_url" in seen["url"]
            and seen["headers"]["apikey"] == "sb_secret_K"
            and "merge-duplicates" in seen["headers"]["Prefer"])
    print(("✅" if cond else "❌"), "upsert 砌 URL/headers + 回行數")
    ok = ok and cond

    # URL 容錯:貼咗 /rest/v1 都剝返基底
    import os
    os.environ["SUPABASE_URL"] = "https://abc.supabase.co/rest/v1/"
    os.environ["SUPABASE_SECRET_KEY"] = "sb_secret_x"
    c2 = db.cfg()
    cond = c2["url"] == "https://abc.supabase.co" and c2["key"] == "sb_secret_x"
    print(("✅" if cond else "❌"), "cfg URL 容錯(剝 /rest/v1):", c2["url"])
    ok = ok and cond
    del os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"]

    # 未配置 → no-op 回 0
    n0 = db.upsert("error_fares", [row], "source_url", c={"url": "", "key": ""}, client=fake_post)
    cond = n0 == 0
    print(("✅" if cond else "❌"), "未配置 → 0(no-op,唔當機)")
    ok = ok and cond

    print()
    print("🎉 db 純邏輯測試通過" if ok else "⚠️ db 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
