"""
feeds.py — Stream B 統一收料器(Phase 1B)
==========================================
讀 sources.yaml 嘅來源,fetch 最近貼文,normalize 成統一 Post dict:
    {"source_platform": str, "source_url": str, "title": str,
     "text": str, "published": str}

全部來源都係 RSS/Atom(用 feedparser parse):
    reddit           — r/<subreddit>/new/.rss(reddit 官方 RSS;.json API 已被 403,.rss 仍可用)
    error_fare_sites — 各站原生 RSS(theflightdeal / fly4free 等)

鐵律:對外 request 隨機 delay + retry + 尊重 rate limit;壞咗 skip + log,唔當機。
"""
from __future__ import annotations

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

# reddit .rss 要似瀏覽器嘅 UA 先唔會 403(.rss 係 reddit 官方公開 feed)
BROWSER_UA = os.getenv(
    "FEEDS_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
)
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
                wait = 6 * attempt
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


def normalize_rss(xml_text: str, platform: str) -> list[dict]:
    """用 feedparser parse RSS/Atom 文字 → Post list。platform 係完整 source_platform 標籤。"""
    feed = feedparser.parse(xml_text)
    posts = []
    for e in feed.entries:
        posts.append({
            "source_platform": platform,
            "source_url": e.get("link", "") or "",
            "title": e.get("title", "") or "",
            "text": e.get("summary", "") or "",
            "published": e.get("published", "") or e.get("updated", "") or "",
        })
    return posts


def fetch_reddit(subreddit: str, limit: int) -> list[dict]:
    """reddit 官方 RSS(/new/.rss)— .json API 已被 403。"""
    url = f"https://www.reddit.com/r/{subreddit}/new/.rss?limit={limit}"
    txt = fetch_url(url, headers={"User-Agent": BROWSER_UA})
    if not txt:
        return []
    return normalize_rss(txt, f"reddit/r/{subreddit}")[:limit]


def fetch_rss(site: dict, limit: int) -> list[dict]:
    txt = fetch_url(site["url"], headers={"User-Agent": BROWSER_UA})
    if not txt:
        return []
    return normalize_rss(txt, f"rss/{site.get('name', site['url'])}")[:limit]


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
        _polite_sleep(5, 9)  # reddit 對 .rss 都會 429 — 隔耐啲先溫純

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
