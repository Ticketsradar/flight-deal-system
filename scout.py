"""
scout.py — Phase 1B Scout 腦(Haiku)篩貼文
==========================================
讀 sources.yaml 嘅 filters 砌 system prompt,將貼文批次交 scout 腦,回 candidate JSON。
經現有 llm.py 路由(試跑 = claude_code/haiku = Max plan $0)。
"""
from __future__ import annotations

import json

from llm import call_llm, extract_json

REQUIRED = ("origin", "destination", "depart_date", "return_date", "price",
            "currency", "airline", "source_platform", "source_url", "confidence")


def build_scout_system(filters: dict) -> str:
    origins = ", ".join(filters.get("origins", []) or [])
    horizon = filters.get("horizon_months", 12)
    signals = "\n".join(f"- {s}" for s in (filters.get("signals", []) or []))
    return (
        "你係機票錯價(error fare)篩選員。以下會畀你一批社交平台 / RSS 貼文(JSON array)。\n"
        f"任務:揀出**由 {origins} 出發、未來 {horizon} 個月**嘅疑似錯價 / 超平來回機票。\n\n"
        "錯價加權訊號:\n" + signals + "\n\n"
        "規則:\n"
        f"- 出發地一定要係 {origins} 其中一個(機場代碼);唔係就唔好出。\n"
        "- 唔關事、純廣告、資料不足 → 跳過,唔好作。\n"
        "- 日期用 YYYY-MM-DD;唔肯定就留空字串。\n"
        "- price 係 number 或 null;confidence 係 0–100,越似真錯價越高。\n"
        "- source_platform / source_url 直接照抄返畀你嗰篇貼文嘅值。\n\n"
        "**只回一個 JSON array**,每個 object 欄位:\n"
        "origin, destination, depart_date, return_date, price, currency, airline, "
        "source_platform, source_url, confidence, reason。\n"
        "冇 candidate 就回 []。唔好有 JSON 以外嘅任何文字。"
    )


def chunked(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _valid(c: dict) -> bool:
    return isinstance(c, dict) and all(k in c for k in REQUIRED)


def screen_posts(posts: list[dict], filters: dict, batch: int = 12) -> list[dict]:
    """逐批交 scout 腦篩;回合格 candidate list。一批壞咗 skip,唔當機。"""
    system = build_scout_system(filters)
    out: list[dict] = []
    for group in chunked(posts, batch):
        user = json.dumps(group, ensure_ascii=False)
        try:
            reply = call_llm("scout", system=system, user=user)
            data = extract_json(reply)
        except Exception as e:  # noqa: BLE001
            print(f"[scout] 一批失敗,跳過:{e}", flush=True)
            continue
        if isinstance(data, list):
            out.extend([c for c in data if _valid(c)])
    return out
