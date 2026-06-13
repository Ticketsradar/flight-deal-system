"""
feeds.py — Stream B 統一收料器(Phase 1B)
==========================================
讀 sources.yaml 嘅來源,fetch 最近貼文,normalize 成統一 Post dict:
    {"source_platform": str, "source_url": str, "title": str,
     "text": str, "published": str}

支援:
    reddit           — r/<subreddit>/new.json 後門(帶 REDDIT_USER_AGENT,隔 2–3 秒,處理 429)
    error_fare_sites — 各站原生 RSS(feedparser parse)

鐵律:對外 request 隨機 delay + retry + 尊重 rate limit;壞咗 skip + log,唔當機。
"""
from __future__ import annotations

import json
import os
import random
import time

import feedparser
import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

REDDIT_UA = os.getenv("REDDIT_USER_AGENT", "flight-deal-scout/1.0")
GENERIC_UA = "flight-deal-scout/1.0 (+https://github.com/)"
HTTP_TIMEOUT = 20.0
MAX_RETRIES = 3


def log(msg: str) -> None:
    print(f"[feeds] {msg}", flush=True)


def _polite_sleep(lo: float = 2.0, hi: float = 3.0) -> None:
    time.sleep(random.uniform(lo, hi))


def fetch_url(url: str, headers: dict | None = None) -> str | None:
    """GET 一個 URL 回 text。retry(指數退避);429 等耐啲。壞到盡回 None。"""
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = httpx.get(url, headers=headers or {}, timeout=HTTP_TIMEOUT,
                             follow_redirects=True)
            if resp.status_code == 429:
                wait = 10 * attempt
                log(f"429 rate limit:{url} — 等 {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.text
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    log(f"fetch 失敗(放棄):{url} — {last}")
    return None


def normalize_reddit(payload: dict, subreddit: str) -> list[dict]:
    """由 reddit /new.json 嘅 JSON 抽貼文 → Post list。"""
    posts = []
    for child in payload.get("data", {}).get("children", []):
        d = child.get("data", {}) or {}
        posts.append({
            "source_platform": f"reddit/r/{subreddit}",
            "source_url": "https://www.reddit.com" + (d.get("permalink", "") or ""),
            "title": d.get("title", "") or "",
            "text": d.get("selftext", "") or "",
            "published": str(d.get("created_utc", "") or ""),
        })
    return posts


def normalize_rss(xml_text: str, site_name: str) -> list[dict]:
    """用 feedparser parse RSS/Atom 文字 → Post list。"""
    feed = feedparser.parse(xml_text)
    posts = []
    for e in feed.entries:
        posts.append({
            "source_platform": f"rss/{site_name}",
            "source_url": e.get("link", "") or "",
            "title": e.get("title", "") or "",
            "text": e.get("summary", "") or "",
            "published": e.get("published", "") or e.get("updated", "") or "",
        })
    return posts


def fetch_reddit(subreddit: str, limit: int) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    txt = fetch_url(url, headers={"User-Agent": REDDIT_UA})
    if not txt:
        return []
    try:
        payload = json.loads(txt)
    except json.JSONDecodeError:
        log(f"reddit JSON parse 失敗:r/{subreddit}")
        return []
    return normalize_reddit(payload, subreddit)[:limit]


def fetch_rss(site: dict, limit: int) -> list[dict]:
    txt = fetch_url(site["url"], headers={"User-Agent": GENERIC_UA})
    if not txt:
        return []
    return normalize_rss(txt, site.get("name", site["url"]))[:limit]


def fetch_all(sources: dict, limit: int = 25, max_feeds: int = 0) -> list[dict]:
    """讀 sources.yaml dict,fetch 全部來源,合併做一個 Post list。"""
    posts: list[dict] = []
    done = 0

    for entry in sources.get("reddit", []) or []:
        sub = entry.get("subreddit")
        if not sub:
            continue
        got = fetch_reddit(sub, limit)
        log(f"reddit/r/{sub}: {len(got)} 篇")
        posts.extend(got)
        done += 1
        if max_feeds and done >= max_feeds:
            return posts
        _polite_sleep()

    for site in sources.get("error_fare_sites", []) or []:
        if not site.get("url"):
            continue
        got = fetch_rss(site, limit)
        log(f"rss/{site.get('name')}: {len(got)} 篇")
        posts.extend(got)
        done += 1
        if max_feeds and done >= max_feeds:
            return posts
        _polite_sleep()

    return posts
