"""
scripts/verify_workflows.py — 驗證 scan.yml + scan-weekly.yml 結構正確

跑法: uv run python scripts/verify_workflows.py
全 pass → exit 0;任一 fail → exit 1 + stderr 描述

Checks:
  1. scan.yml YAML 格式合法(scan-weekly.yml 已刪走,跳過)
  2. 每個存在嘅 workflow 都有 concurrency guard(防 cron-delay double-fire,DAILY-03)
  3. 每個存在嘅 workflow 都有 if: always() upload step(獨立於 scan step,DAILY-03)
  4. scan.yml(daily)有 active cron schedule(Phase 4 已 uncomment)
  5. scan-weekly.yml 若存在則有 active Sunday cron(0 2 * * 0)
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML 唔見咗 — uv sync 先", file=sys.stderr)
    sys.exit(1)

PASS_COUNT = 0
FAIL_COUNT = 0

ROOT = Path(__file__).parent.parent
DAILY = ROOT / ".github" / "workflows" / "scan.yml"
WEEKLY = ROOT / ".github" / "workflows" / "scan-weekly.yml"


def ok(msg: str) -> None:
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  PASS  {msg}")


def fail(msg: str) -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"  FAIL  {msg}", file=sys.stderr)


def load_yaml(path: Path) -> dict | None:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"{path.name}: yaml.safe_load 失敗 — {e}")
        return None


def raw_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def get_on(doc: dict) -> dict:
    """yaml.safe_load 喺 YAML 1.1 會將 'on' 解析做 True(boolean)。
    呢個 helper 兩個 key 都試。"""
    return doc.get("on") or doc.get(True) or {}


def check_concurrency(doc: dict, label: str) -> None:
    """Workflow-level concurrency block 存在且有 group。"""
    c = doc.get("concurrency")
    if isinstance(c, dict) and c.get("group"):
        ok(f"{label}: concurrency.group = {c['group']!r}")
    else:
        fail(f"{label}: 缺少 concurrency.group(防 double-fire 必須有)")


def find_steps(doc: dict) -> list[dict]:
    """Extract all steps from all jobs."""
    steps = []
    for job in (doc.get("jobs") or {}).values():
        steps.extend(job.get("steps") or [])
    return steps


def check_upload_step_always(doc: dict, label: str) -> None:
    """有一個 step 係 upload.py 且帶 if: always()。"""
    steps = find_steps(doc)
    upload_steps = [s for s in steps
                    if isinstance(s.get("run"), str) and "upload.py" in s["run"]]
    if not upload_steps:
        fail(f"{label}: 搵唔到 upload.py step")
        return
    always_steps = [s for s in upload_steps
                    if s.get("if", "").strip() == "always()"]
    if always_steps:
        ok(f"{label}: upload.py step 帶 if: always()(DAILY-03)")
    else:
        fail(f"{label}: upload.py step 存在但缺 if: always()")


def check_scan_step_separate(doc: dict, label: str) -> None:
    """scanner.py 同 upload.py 唔能喺同一個 step 裏(DAILY-03 bug 修)。"""
    steps = find_steps(doc)
    combined = [s for s in steps
                if isinstance(s.get("run"), str)
                and "scanner.py" in s["run"]
                and "upload.py" in s["run"]]
    if combined:
        fail(f"{label}: scanner.py 同 upload.py 喺同一個 run block"
             " — 必須拆做兩個獨立 step")
    else:
        ok(f"{label}: scanner.py 同 upload.py 係獨立 step")


def check_daily_cron_active(raw: str, label: str) -> None:
    """Daily scan.yml 必須有 active schedule/cron(Phase 4 production 狀態)。"""
    doc_check = yaml.safe_load(raw)
    on_block = get_on(doc_check)
    has_active_schedule = "schedule" in on_block
    if has_active_schedule:
        ok(f"{label}: has active cron schedule (production state)")
    else:
        fail(f"{label}: 缺少 active cron schedule — daily scan 唔會自動跑")


def check_weekly_cron_active(doc: dict, label: str) -> None:
    """scan-weekly.yml 必須有 active Sunday cron = '0 2 * * 0'。"""
    on_block = get_on(doc)
    schedules = on_block.get("schedule") or []
    crons = [s.get("cron", "") for s in schedules if isinstance(s, dict)]
    if "0 2 * * 0" in crons:
        ok(f"{label}: 有 active cron '0 2 * * 0'(週日 02:00 UTC)")
    else:
        fail(f"{label}: 搵唔到 active cron '0 2 * * 0';實際: {crons}")


# ─────────────────────────────────────────────────────────────────
print("=== verify_workflows.py ===")

# 1. Parse
daily_doc = load_yaml(DAILY)

if daily_doc:
    ok(f"scan.yml: yaml.safe_load 成功")

if not WEEKLY.exists():
    ok("scan-weekly.yml: 已刪走(daily 全量已取代,唔需要)")
    weekly_doc = None
else:
    weekly_doc = load_yaml(WEEKLY)
    if weekly_doc:
        ok(f"scan-weekly.yml: yaml.safe_load 成功")

# 2. Concurrency guard
if daily_doc:
    check_concurrency(daily_doc, "scan.yml")
if weekly_doc:
    check_concurrency(weekly_doc, "scan-weekly.yml")

# 3. Upload step with if: always()
if daily_doc:
    check_upload_step_always(daily_doc, "scan.yml")
if weekly_doc:
    check_upload_step_always(weekly_doc, "scan-weekly.yml")

# 4. Scan + upload are separate steps
if daily_doc:
    check_scan_step_separate(daily_doc, "scan.yml")
if weekly_doc:
    check_scan_step_separate(weekly_doc, "scan-weekly.yml")

# 5. Daily cron active (Phase 4 production state)
check_daily_cron_active(DAILY.read_text(encoding="utf-8"), "scan.yml")

# 6. Weekly cron active (only if file exists)
if weekly_doc:
    check_weekly_cron_active(weekly_doc, "scan-weekly.yml")

print()
print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
sys.exit(0 if FAIL_COUNT == 0 else 1)
