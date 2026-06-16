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

    # delete 砌 URL + 守門
    seen2: dict = {}

    def fake_del(url, headers=None, timeout=None):
        seen2["url"] = url

        class R:
            def raise_for_status(self):
                pass
        return R()

    okd = db.delete("error_fares", "source_url=eq.x", c=conf, client=fake_del)
    cond = okd and "/rest/v1/error_fares?source_url=eq.x" in seen2["url"]
    print(("✅" if cond else "❌"), "delete 砌 URL")
    ok = ok and cond
    cond = db.delete("x", "key=eq.1", c={"url": "", "key": ""}) is False
    print(("✅" if cond else "❌"), "delete 未配置 → False")
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

    # ── Task 1: scanned_at threaded into cheap_flight_rows ──────────────────
    # Positive: generated_at in scan_doc → every row carries it as scanned_at
    scan_with_ts = {
        "generated_at": "2026-06-14T09:00:00",
        "routes": [
            {"origin": "HKG", "dest": "NRT", "region": "東北亞", "months": [
                {"month": "2026-08", "status": "ok", "price": 2426, "currency": "HKD",
                 "depart": "2026-08-30", "return": "2026-09-05", "airline": "CX",
                 "google_flights": "https://g/nrt"},
            ]},
            {"origin": "HKG", "dest": "TPE", "region": "東北亞", "months": [
                {"month": "2026-08", "status": "ok", "price": 900, "currency": "HKD",
                 "depart": "2026-08-10", "return": "2026-08-14", "airline": "CI",
                 "google_flights": "https://g/tpe"},
            ]},
        ],
    }
    rows_ts = db.cheap_flight_rows(scan_with_ts)
    cond = (len(rows_ts) == 2
            and all(r.get("scanned_at") == "2026-06-14T09:00:00" for r in rows_ts))
    print(("✅" if cond else "❌"), "scanned_at == generated_at on every row:", [r.get("scanned_at") for r in rows_ts])
    ok = ok and cond

    # Fallback: no generated_at → scanned_at is a non-empty ISO string (not None)
    scan_no_ts = {
        "routes": [
            {"origin": "HKG", "dest": "BKK", "region": "東南亞", "months": [
                {"month": "2026-08", "status": "ok", "price": 500, "currency": "HKD",
                 "depart": "2026-08-01", "return": "2026-08-07", "airline": "HX",
                 "google_flights": "https://g/bkk"},
            ]},
        ],
    }
    rows_no_ts = db.cheap_flight_rows(scan_no_ts)
    fallback_val = rows_no_ts[0].get("scanned_at") if rows_no_ts else None
    cond = (len(rows_no_ts) == 1
            and fallback_val is not None
            and isinstance(fallback_val, str)
            and len(fallback_val) >= 10)
    print(("✅" if cond else "❌"), "scanned_at fallback(no generated_at) → non-empty ISO str:", fallback_val)
    ok = ok and cond

    # Existing assertions remain: cheap_flight_rows still produces correct rows
    # (already covered by the earlier flat test)

    # ── Task 2: _order_stale + stale_routes no-op ───────────────────────────
    # Pure ordering: null/never-scanned FIRST, then oldest → newest
    raw_rows = [
        {"origin": "HKG", "destination": "NRT", "scanned_at": "2026-06-13T10:00:00"},
        {"origin": "HKG", "destination": "BKK", "scanned_at": None},
        {"origin": "HKG", "destination": "TPE", "scanned_at": "2026-06-10T08:00:00"},
    ]
    ordered = db._order_stale(raw_rows)
    names = [r["destination"] for r in ordered]
    cond = (names == ["BKK", "TPE", "NRT"])
    print(("✅" if cond else "❌"), "_order_stale: null first, then oldest→newest:", names)
    ok = ok and cond

    # Each entry in _order_stale result has "origin", "destination", "last"
    cond = all("last" in r and "origin" in r and "destination" in r for r in ordered)
    print(("✅" if cond else "❌"), "_order_stale keys: origin/destination/last present")
    ok = ok and cond

    # stale_routes() returns [] when unconfigured (no network, no crash)
    result = db.stale_routes(c={"url": "", "key": ""})
    cond = result == []
    print(("✅" if cond else "❌"), "stale_routes() unconfigured → []:", result)
    ok = ok and cond

    # ── Batch B: _order_sparse + sparse_routes(補掃選擇器)──────────────
    import datetime as _dt
    NOW = _dt.datetime(2026, 6, 15, tzinfo=_dt.timezone.utc)
    sparse_rows = [
        {"origin": "HKG", "destination": "NRT", "scanned_at": "2026-06-10T00:00:00+00:00", "periods": []},
        {"origin": "HKG", "destination": "NRT", "scanned_at": "2026-06-10T00:00:00+00:00", "periods": []},
        {"origin": "HKG", "destination": "FUK", "scanned_at": "2026-06-15T00:00:00+00:00", "periods": list(range(10))},
        {"origin": "HKG", "destination": "FUK", "scanned_at": "2026-06-15T00:00:00+00:00", "periods": list(range(10))},
        {"origin": "HKG", "destination": "SIN", "scanned_at": "2026-06-15T00:00:00+00:00", "periods": [1, 2, 3, 4]},
    ]
    sp = db._order_sparse(sparse_rows, min_periods=5, stale_days=3, now=NOW)
    keys = [r["destination"] for r in sp]
    # FUK(20 periods, 今日)唔 sparse;NRT(0, 太舊)+ SIN(4)係 sparse;NRT 比 SIN 排前(periods 少)
    cond = (keys == ["NRT", "SIN"])
    print(("✅" if cond else "❌"), "_order_sparse: sparse(少 periods/太舊)先,sparsest 排頭:", keys)
    ok = ok and cond

    cond = all(("origin" in r and "destination" in r and "periods" in r) for r in sp)
    print(("✅" if cond else "❌"), "_order_sparse keys: origin/destination/periods present")
    ok = ok and cond

    # sparse_routes() 未配置 → [](no-op 安全)
    result = db.sparse_routes(c={"url": "", "key": ""})
    cond = result == []
    print(("✅" if cond else "❌"), "sparse_routes() unconfigured → []:", result)
    ok = ok and cond

    # filter_non_degrading(防退步):新 periods < 現有 → 丟;>= 或 現有冇 → 留
    new_rows = [
        {"origin": "HKG", "destination": "NRT", "month": "2026-07", "periods": [1, 2, 3]},        # 3 < 10 → 丟
        {"origin": "HKG", "destination": "NRT", "month": "2026-08", "periods": list(range(11))},  # 11 >= 5 → 留
        {"origin": "HKG", "destination": "SIN", "month": "2026-06", "periods": [1, 2]},           # 現有冇 → 留
    ]
    existing = {("HKG", "NRT", "2026-07"): 10, ("HKG", "NRT", "2026-08"): 5}
    kept_keys = [(r["destination"], r["month"]) for r in db.filter_non_degrading(new_rows, existing)]
    cond = (kept_keys == [("NRT", "2026-08"), ("SIN", "2026-06")])
    print(("✅" if cond else "❌"), "filter_non_degrading: 丟退步月份、留改善/新月份:", kept_keys)
    ok = ok and cond

    # _order_sparse:同 periods 同 last 時用 (origin,destination) 穩定排序(多 shard 一致)
    tie_rows = [
        {"origin": "HKG", "destination": "BBB", "scanned_at": None, "periods": []},
        {"origin": "HKG", "destination": "AAA", "scanned_at": None, "periods": []},
    ]
    tie = [r["destination"] for r in db._order_sparse(tie_rows, min_periods=5, stale_days=3, now=NOW)]
    cond = (tie == ["AAA", "BBB"])
    print(("✅" if cond else "❌"), "_order_sparse: tie 穩定排序 (origin,destination):", tie)
    ok = ok and cond

    # delete_stale_cheap_flights:cutoff 格式(Z 結尾、無 '+')+ 未配置 no-op + DELETE filter 正確
    cutoff = db.stale_cutoff_iso(3, now=NOW)  # NOW=2026-06-15 → 3 日前 = 2026-06-12
    cond = (cutoff == "2026-06-12T00:00:00Z")
    print(("✅" if cond else "❌"), "stale_cutoff_iso(3):", cutoff)
    ok = ok and cond

    cond = (db.delete_stale_cheap_flights(c={"url": "", "key": ""}) is False)
    print(("✅" if cond else "❌"), "delete_stale_cheap_flights 未配置 → False(no-op)")
    ok = ok and cond

    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

    def _fake_del(url, headers=None, timeout=None):
        captured["url"] = url
        return _Resp()

    db.delete_stale_cheap_flights(stale_days=3, c={"url": "https://x.supabase.co", "key": "k"},
                                  client=_fake_del, now=NOW)
    cond = ("cheap_flights?scanned_at=lt.2026-06-12T00:00:00Z" in captured.get("url", ""))
    print(("✅" if cond else "❌"), "delete_stale_cheap_flights DELETE filter:", captured.get("url", "")[-55:])
    ok = ok and cond

    print()
    print("🎉 db 純邏輯測試通過" if ok else "⚠️ db 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
