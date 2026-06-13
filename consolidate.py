"""
consolidate.py — Phase 1B 純 code 去重
====================================
多個來源嘅 candidate 合併:同一(airline+origin+destination+depart+return)
留 confidence 最高嗰個,再按 confidence 由高到低排序。唔用 LLM。
"""
from __future__ import annotations


def _key(c: dict) -> tuple:
    def norm(field: str) -> str:
        return str(c.get(field, "") or "").strip().lower()
    return (norm("airline"), norm("origin"), norm("destination"),
            norm("depart_date"), norm("return_date"))


def _conf(c: dict) -> float:
    try:
        return float(c.get("confidence", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def consolidate(candidates: list[dict]) -> list[dict]:
    best: dict[tuple, dict] = {}
    for c in candidates:
        k = _key(c)
        if k not in best or _conf(c) > _conf(best[k]):
            best[k] = c
    return sorted(best.values(), key=_conf, reverse=True)
