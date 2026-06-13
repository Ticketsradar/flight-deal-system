"""
test_scanner.py — 離線單元測試:refine_period_lengths

跑法: uv run python test_scanner.py
全 pass → exit 0 / 任一 fail → exit 1

Tests:
  1. 揀平日:只有頭 refine_days 個 period 被 query_fn 觸碰
  2. offset 範圍 + clamp:[MIN_NIGHTS, MAX_NIGHTS];跳過 dur 本身
  3. 取最平:refine 後用最平 candidate,若所有都貴保留原 period
  4. days 欄:所有 output period 帶正確 days
  5. query budget:refine 新增 query ≤ refine_days × 2 × offset
  6. google_flights:refine 換 return 後用新 depart+return 嘅 tfs(deep_link)
"""
from __future__ import annotations

import datetime as dt
import sys
from scanner import refine_period_lengths, MIN_NIGHTS, MAX_NIGHTS, deep_link

PASS_COUNT = 0
FAIL_COUNT = 0

def ok(name: str) -> None:
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  PASS  {name}")

def fail(name: str, msg: str) -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"  FAIL  {name}: {msg}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────
# Helpers — fake query_fn 回造數 dict
# ─────────────────────────────────────────────────────────────────

def make_period(depart: str, ret: str, price: int) -> dict:
    """建一個最簡 period dict(模擬 scan_month 砌好嘅)"""
    tfs = f"fake_tfs_{depart}_{ret}"
    return {
        "depart": depart,
        "return": ret,
        "price": price,
        "airline": "TestAir",
        "google_flights": f"https://gf.example/?tfs={tfs}",
        "tfs": tfs,
    }


def make_periods(n: int, base_date: str = "2026-09-10", stay: int = 7,
                 base_price: int = 1000) -> list:
    """建 n 個 period,各相差 1 天出發,price 遞增"""
    result = []
    d0 = dt.date.fromisoformat(base_date)
    for i in range(n):
        dep = (d0 + dt.timedelta(days=i)).isoformat()
        ret = (d0 + dt.timedelta(days=i + stay)).isoformat()
        result.append(make_period(dep, ret, base_price + i * 10))
    return result


# ─────────────────────────────────────────────────────────────────
# Test 1 — 揀平日:只有頭 refine_days 個 period 被 query_fn 觸碰
# ─────────────────────────────────────────────────────────────────
def test_1_only_top_n_refined():
    touched_deps = set()

    def fake_query(origin, dest, depart, ret, currency, browser):
        touched_deps.add(depart.isoformat())
        return {"status": "ok", "price": 9999, "airline": "FakeAir",
                "tfs": f"t_{depart}_{ret}"}

    periods = make_periods(15, stay=7, base_price=1000)
    refine_days = 10
    refine_period_lengths(
        origin="HKG", dest="KUL",
        periods=periods,
        dur=7, refine_days=refine_days, offset=2,
        currency="HKD", browser=None,
        query_fn=fake_query,
    )
    # 只有頭 10 個 period 的出發日應該被 query_fn 接觸
    top_deps = {p["depart"] for p in periods[:refine_days]}
    untouched_deps = {p["depart"] for p in periods[refine_days:]}
    if not touched_deps.issubset(top_deps):
        outside = touched_deps - top_deps
        fail("test_1_only_top_n_refined",
             f"query_fn 觸碰咗唔應該觸碰嘅出發日: {outside}")
    elif touched_deps & untouched_deps:
        fail("test_1_only_top_n_refined",
             "query_fn 觸碰咗頭 refine_days 以外嘅 period")
    else:
        ok("test_1_only_top_n_refined")


# ─────────────────────────────────────────────────────────────────
# Test 2 — offset 範圍 + clamp
# ─────────────────────────────────────────────────────────────────
def test_2_offset_clamp():
    test_cases = [
        # (dur, offset, expected_nights_queried)
        # offset=2 → dur-2..dur+2 但跳過 dur 本身,再 clamp [2,14]
        (3, 2, {2, 4, 5}),       # raw: 1,2,3,4,5 → clamp→1→2; skip 3; → {2,4,5}
        (13, 2, {11, 12, 14}),   # raw: 11,12,13,14,15 → clamp→15→14; skip 13; → {11,12,14}
        (7, 2, {5, 6, 8, 9}),    # raw: 5,6,7,8,9 → skip 7; clamp 全 ok; → {5,6,8,9}
    ]

    for dur, offset, expected in test_cases:
        nights_queried = set()

        def fake_query(origin, dest, depart, ret, currency, browser,
                       _dep=None):
            nights = (ret - depart).days
            nights_queried.add(nights)
            return {"status": "ok", "price": 5000, "airline": "A",
                    "tfs": f"t_{depart}_{ret}"}

        periods = make_periods(1, stay=dur)
        refine_period_lengths(
            origin="HKG", dest="KUL",
            periods=periods,
            dur=dur, refine_days=5, offset=offset,
            currency="HKD", browser=None,
            query_fn=fake_query,
        )
        if nights_queried != expected:
            fail(f"test_2_offset_clamp dur={dur} offset={offset}",
                 f"期望 nights {expected},實際 {nights_queried}")
        elif dur in nights_queried:
            fail(f"test_2_offset_clamp dur={dur}",
                 f"dur={dur} 本身不應被 query(已知)")
        else:
            ok(f"test_2_offset_clamp dur={dur} offset={offset}")


# ─────────────────────────────────────────────────────────────────
# Test 3 — 取最平:用最平 candidate;若所有都貴保留原 period
# ─────────────────────────────────────────────────────────────────
def test_3_pick_cheapest():
    # Case A:candidate 有更平 → 換
    dep = "2026-09-10"
    ret_fixed = "2026-09-17"  # dur=7
    orig_price = 2000
    best_nights = 5          # 呢個 candidate 最平
    best_price = 1500

    prices_by_nights = {5: 1500, 6: 1800, 8: 1900, 9: 2100}

    def fake_query_a(origin, dest, depart, ret, currency, browser):
        nights = (ret - depart).days
        p = prices_by_nights.get(nights, 3000)
        return {"status": "ok", "price": p, "airline": "A",
                "tfs": f"t_{depart}_{ret}"}

    periods_a = [make_period(dep, ret_fixed, orig_price)]
    result_a = refine_period_lengths(
        origin="HKG", dest="KUL",
        periods=periods_a,
        dur=7, refine_days=5, offset=2,
        currency="HKD", browser=None,
        query_fn=fake_query_a,
    )
    if not result_a:
        fail("test_3_pick_cheapest case A", "result 為空")
    elif result_a[0]["price"] != best_price:
        fail("test_3_pick_cheapest case A",
             f"期望 price={best_price},得到 {result_a[0]['price']}")
    elif result_a[0].get("days") != best_nights:
        fail("test_3_pick_cheapest case A",
             f"期望 days={best_nights},得到 {result_a[0].get('days')}")
    else:
        ok("test_3_pick_cheapest case A (換最平)")

    # Case B:所有 candidate 都貴 → 保留原 period(唔退步)
    def fake_query_b(origin, dest, depart, ret, currency, browser):
        return {"status": "ok", "price": 9999, "airline": "B",
                "tfs": f"t_{depart}_{ret}"}

    periods_b = [make_period(dep, ret_fixed, orig_price)]
    result_b = refine_period_lengths(
        origin="HKG", dest="KUL",
        periods=periods_b,
        dur=7, refine_days=5, offset=2,
        currency="HKD", browser=None,
        query_fn=fake_query_b,
    )
    if not result_b:
        fail("test_3_pick_cheapest case B", "result 為空")
    elif result_b[0]["price"] != orig_price:
        fail("test_3_pick_cheapest case B",
             f"期望保留原 price={orig_price},得到 {result_b[0]['price']}")
    else:
        ok("test_3_pick_cheapest case B (保留原 period)")


# ─────────────────────────────────────────────────────────────────
# Test 4 — days 欄:所有 output period 都有正確 days
# ─────────────────────────────────────────────────────────────────
def test_4_days_field():
    def fake_query(origin, dest, depart, ret, currency, browser):
        nights = (ret - depart).days
        return {"status": "ok", "price": 1000 + nights * 100, "airline": "A",
                "tfs": f"t_{depart}_{ret}"}

    # 15 period,只 refine 頭 5 個;其餘 10 個直接補 days
    periods = make_periods(15, stay=7)
    result = refine_period_lengths(
        origin="HKG", dest="KUL",
        periods=periods,
        dur=7, refine_days=5, offset=2,
        currency="HKD", browser=None,
        query_fn=fake_query,
    )
    errors = []
    for p in result:
        if "days" not in p:
            errors.append(f"depart={p.get('depart')} 冇 days 欄")
        else:
            # 驗算:days 應等於 (return - depart)
            dep_d = dt.date.fromisoformat(p["depart"])
            ret_d = dt.date.fromisoformat(p["return"])
            expected_days = (ret_d - dep_d).days
            if p["days"] != expected_days:
                errors.append(
                    f"depart={p['depart']} days={p['days']} 期望={expected_days}")
    if errors:
        fail("test_4_days_field", "; ".join(errors[:3]))
    else:
        ok("test_4_days_field")


# ─────────────────────────────────────────────────────────────────
# Test 5 — query budget:refine 新增 query ≤ refine_days × 2 × offset
# ─────────────────────────────────────────────────────────────────
def test_5_query_budget():
    query_count = [0]

    def fake_query(origin, dest, depart, ret, currency, browser):
        query_count[0] += 1
        return {"status": "ok", "price": 9999, "airline": "A",
                "tfs": f"t_{depart}_{ret}"}

    refine_days = 10
    offset = 2

    periods = make_periods(15, stay=7)
    refine_period_lengths(
        origin="HKG", dest="KUL",
        periods=periods,
        dur=7, refine_days=refine_days, offset=offset,
        currency="HKD", browser=None,
        query_fn=fake_query,
    )
    max_allowed = refine_days * 2 * offset  # = 40
    if query_count[0] > max_allowed:
        fail("test_5_query_budget",
             f"refine 新增 {query_count[0]} queries > 上限 {max_allowed}")
    else:
        ok(f"test_5_query_budget ({query_count[0]} queries ≤ {max_allowed})")


# ─────────────────────────────────────────────────────────────────
# Test 6 — google_flights:refine 換 return 後用新 pair 嘅 tfs(deep_link)
# ─────────────────────────────────────────────────────────────────
def test_6_google_flights_new_tfs():
    dep = "2026-09-10"
    ret_fixed = "2026-09-17"   # dur=7, orig_price=2000
    orig_price = 2000
    cheap_nights = 5           # candidate 最平
    cheap_price = 1500
    cheap_ret = dt.date.fromisoformat(dep) + dt.timedelta(days=cheap_nights)

    captured_tfs = {}

    def fake_query(origin, dest, depart, ret, currency, browser):
        nights = (ret - depart).days
        tfs_val = f"NEW_TFS_{depart.isoformat()}_{ret.isoformat()}"
        # 記低每個 nights 用嘅 tfs
        captured_tfs[nights] = tfs_val
        p = cheap_price if nights == cheap_nights else 9999
        return {"status": "ok", "price": p, "airline": "A", "tfs": tfs_val}

    periods = [make_period(dep, ret_fixed, orig_price)]
    result = refine_period_lengths(
        origin="HKG", dest="KUL",
        periods=periods,
        dur=7, refine_days=5, offset=2,
        currency="HKD", browser=None,
        query_fn=fake_query,
    )

    if not result:
        fail("test_6_google_flights_new_tfs", "result 為空")
        return

    best = result[0]
    expected_tfs = captured_tfs.get(cheap_nights)
    expected_link = deep_link(expected_tfs, "HKD") if expected_tfs else None

    if best["price"] != cheap_price:
        fail("test_6_google_flights_new_tfs",
             f"期望 price={cheap_price},得到 {best['price']}")
    elif best.get("google_flights") != expected_link:
        fail("test_6_google_flights_new_tfs",
             f"google_flights 唔係新 pair 嘅 deep_link\n"
             f"  期望: {expected_link}\n"
             f"  實際: {best.get('google_flights')}")
    else:
        ok("test_6_google_flights_new_tfs")


# ─────────────────────────────────────────────────────────────────
# Run all tests
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== test_scanner.py ===")
    test_1_only_top_n_refined()
    test_2_offset_clamp()
    test_3_pick_cheapest()
    test_4_days_field()
    test_5_query_budget()
    test_6_google_flights_new_tfs()
    print()
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    sys.exit(0 if FAIL_COUNT == 0 else 1)
