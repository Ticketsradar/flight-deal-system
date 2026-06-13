"""
upload.py — Phase 2.5 最終合併器(純 code,無 LLM)
===================================================
讀最新嘅本地 JSON,一次過倒入 Supabase:
    data/scan_*.json      → cheap_flights(Stream A)
    data/verified_*.json  → error_fares(Stream B,live+unverified+dead 全入,status 分辨)
再寫 meta 嘅 last_updated_stream_a / _b 時間戳。

呢個就係 cron 每日跑完兩條 stream 之後嘅收尾。Supabase 未配置 → db 層自動 no-op,唔當機。
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import db

ROOT = Path(__file__).parent


def log(msg: str) -> None:
    print(f"[upload] {msg}", flush=True)


def _latest(pattern: str) -> str:
    files = sorted(glob.glob(str(ROOT / "data" / pattern)))
    return files[-1] if files else ""


def deals_from_verified(doc: dict) -> list[dict]:
    """verified_*.json 三 bucket 合併做一條 deals list(全部入 error_fares)。"""
    return [d for k in ("live", "unverified", "dead") for d in (doc.get(k) or [])]


def main() -> int:
    n_cheap = n_err = 0

    scan_path = _latest("scan_*.json")
    if scan_path:
        scan = json.loads(Path(scan_path).read_text(encoding="utf-8"))
        n_cheap = db.push_cheap_flights(scan)
        db.set_meta("last_updated_stream_a", scan.get("scan_date", ""))
        log(f"Stream A {Path(scan_path).name}: cheap_flights {n_cheap} 行")
    else:
        log("冇 scan_*.json — 跳過 Stream A")

    ver_path = _latest("verified_*.json")
    if ver_path:
        doc = json.loads(Path(ver_path).read_text(encoding="utf-8"))
        deals = deals_from_verified(doc)
        n_err = db.push_error_fares(deals)
        db.set_meta("last_updated_stream_b", doc.get("verify_date", ""))
        log(f"Stream B {Path(ver_path).name}: error_fares {n_err} 行(由 {len(deals)} deals)")
    else:
        log("冇 verified_*.json — 跳過 Stream B")

    log(f"完:cheap_flights {n_cheap} / error_fares {n_err} 寫入 Supabase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
