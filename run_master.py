"""
run_master.py — Phase 2 入口:讀最新 candidates → triage → 核實 → 寫 data/verified_YYYYMMDD.json
跑法:
    uv run python run_master.py                       # 跑最新 data/candidates_*.json
    uv run python run_master.py --file data/xxx.json  # 指定檔
    uv run python run_master.py --no-browser --limit 1   # 淨 HTTP、最多核 1 個(快)
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from pathlib import Path

import master
import scanner

ROOT = Path(__file__).parent


def log(msg: str) -> None:
    print(msg, flush=True)


def _latest_candidates() -> str:
    files = sorted(glob.glob(str(ROOT / "data" / "candidates_*.json")))
    return files[-1] if files else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Stream B master:核實錯價 candidate")
    ap.add_argument("--file", default="", help="指定 candidates JSON(預設攞最新)")
    ap.add_argument("--limit", type=int, default=0, help="最多核幾多個(0=全部)")
    ap.add_argument("--no-browser", action="store_true", help="停用真瀏覽器後備")
    args = ap.parse_args()

    path = args.file or _latest_candidates()
    if not path or not Path(path).exists():
        log("[master] 搵唔到 candidates 檔(data/candidates_*.json)。先跑 run_scout.py。")
        return 1
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    cands = doc.get("candidates", [])
    log(f"[master] 讀 {path}:{len(cands)} 個 candidate")

    high = master.triage(cands)
    if args.limit > 0:
        high = high[:args.limit]
    log(f"[master] triage(confidence≥{master.MIN_CONFIDENCE}):{len(high)} 個要核實")

    browser = None if args.no_browser else scanner.BrowserFetcher()
    results = []
    try:
        for i, c in enumerate(high, 1):
            log(f"[master] 核實 {i}/{len(high)}: "
                f"{c.get('origin')}-{c.get('destination')} {c.get('depart_date')}")
            results.append(master.verify_one(c, browser))
    finally:
        if browser is not None:
            browser.close()

    buckets: dict[str, list] = {"live": [], "unverified": [], "dead": []}
    for r in results:
        buckets.get(r.get("status", "unverified"), buckets["unverified"]).append(r)

    today = dt.date.today()
    out_dir = ROOT / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"verified_{today.strftime('%Y%m%d')}.json"
    out_doc = {
        "verify_date": today.isoformat(),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source_file": path,
        "triaged": len(high),
        "counts": {k: len(v) for k, v in buckets.items()},
        "live": buckets["live"],
        "unverified": buckets["unverified"],
        "dead": buckets["dead"],
    }
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out_doc, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out_path)
    log(f"[master] 寫好 → {out_path}  "
        f"(live {len(buckets['live'])} / unverified {len(buckets['unverified'])} / dead {len(buckets['dead'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
