# Phase 1B — RSS Scout 實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 起 Stream B 第一個 buildable chunk — 由 Reddit(`.json`)同錯價網 RSS 收料,交 Haiku scout 腦篩出疑似錯價來回機票(HKG/SZX/CAN 出發),純 code 去重,輸出 `data/candidates_YYYYMMDD.json`。

**Architecture:** 四個細模組,各有單一職責:`feeds.py`(收料+normalize)→ `scout.py`(Haiku 篩 → candidate JSON)→ `consolidate.py`(純 code 去重)→ `run_scout.py`(串起 + 原子寫檔)。全部經現有 `llm.py` 路由(試跑 = `claude_code`/`haiku` = Max plan,$0)。測試跟足 repo 風格:可跑嘅 `test_*.py` script,印 ✅/❌,`uv run python …`(冇 pytest)。

**Tech Stack:** Python 3.13、uv、httpx(HTTP GET)、feedparser(RSS/Atom)、pyyaml、現有 `llm.py`。

**鐵律(每個 task 都遵守):** 對外 request 隨機 delay + retry + 處理 429;唔喺全域 shell set API key;新檔輸出落 `data/`(已 gitignore);壞咗 skip + log,唔當機。

**慣例(抄 `scanner.py`):** `ROOT = Path(__file__).parent`;`log()` = `print(..., flush=True)`;原子寫檔 = 寫 `.json.tmp` 再 `.replace()`;`json.dumps(..., ensure_ascii=False, indent=1)`。

**命令注意:** sandbox Bash 行 `uv` 前要 `export PATH="$HOME/.local/bin:$PATH"`(或用絕對路徑 `~/.local/bin/uv`)。所有 Python 經 `uv run python …`。

---

### Task 1: 同步 CLAUDE.md 到新設計(剔走 M3 / Phase 4.5)

**Files:**
- Modify: `CLAUDE.md`

呢個 task 純文件,令 CLAUDE.md 同 `docs/superpowers/specs/2026-06-13-flight-deal-system-design.md` 一致(user 已決定:scout 用 Haiku、唔用 MiniMax M3、刪走 Phase 4.5 驗證週)。

- [ ] **Step 1: 改 production scout 腦**

喺架構表搵到呢行,將 production 欄由 M3 改做 Haiku:

搵:`| Scout 腦 | `claude_code` provider,model `haiku`(行 user 個 Max plan,$0) | MiniMax M3(`minimax` provider) |`
改:`| Scout 腦 | `claude_code` provider,model `haiku`(行 user 個 Max plan,$0) | Claude Haiku(`anthropic` provider,API) |`

- [ ] **Step 2: 刪走 Phase 4.5 驗證週**

喺【進度】section 搵到並**刪走**成行:
`- [ ] Phase 4.5 — 驗證週(`--compare`:M3 vs Haiku scout 對照 7 日,先決定 production scout 腦)`

- [ ] **Step 3: 更新 Phase 1B 描述 + 加 spec 指標**

將：`- [ ] Phase 1B — Reddit scout(`.json`)+ scout 腦篩選 + consolidate`
改做：`- [ ] **Phase 1B — RSS scout(Reddit `.json` + 錯價網 RSS)+ Haiku 篩 + consolidate** ← 而家做緊(計劃:docs/superpowers/plans/2026-06-13-phase-1b-rss-scout.md;設計:docs/superpowers/specs/2026-06-13-flight-deal-system-design.md)`

- [ ] **Step 4: Commit**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
git add CLAUDE.md
git commit -m "docs(CLAUDE.md): 同步新設計 — scout 用 Haiku、剔走 MiniMax M3 同 Phase 4.5"
```

---

### Task 2: 加 dependencies(httpx、feedparser)

**Files:**
- Modify: `pyproject.toml`(經 `uv add` 自動改)

- [ ] **Step 1: 加兩個 library**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv add httpx feedparser
```

Expected:uv 顯示 `+ feedparser` (httpx 可能已存在,只會寫入 pyproject)。

- [ ] **Step 2: 確認 import 得到**

```bash
uv run python -c "import httpx, feedparser; print('httpx', httpx.__version__, '| feedparser', feedparser.__version__)"
```

Expected:印出兩個版本號,冇 error。

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: 加 httpx + feedparser(Phase 1B RSS scout 用)"
```

---

### Task 3: 擴充 sources.yaml — 加錯價網 RSS

**Files:**
- Modify: `sources.yaml`

- [ ] **Step 1: 喺 `reddit:` section 之後、`xiaohongshu:` 之前,加 `error_fare_sites:` section**

```yaml
# ── 錯價網 RSS(原生 feed,公開合法、最穩)──────────────────────
# 規矩:用原生 RSS;每個 feed 之間隨機 delay。URL 起步用以下,Task 8 smoke 會實測,
# 拎唔到嘢(0 篇)嘅 feed 喺度刪走或換 URL。
error_fare_sites:
  - name: secretflying           # secretflying.com — 國際 error fare 大台
    url: https://www.secretflying.com/feed/
    lang: en
    priority: high
  - name: fly4free               # fly4free.com — 國際平機票/錯價
    url: https://www.fly4free.com/feed/
    lang: en
    priority: medium
```

- [ ] **Step 2: 確認 YAML 仍然 parse 得到**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python -c "import yaml; s=yaml.safe_load(open('sources.yaml',encoding='utf-8').read()); print('error_fare_sites:', [x['name'] for x in s.get('error_fare_sites',[])]); print('reddit:', [x['subreddit'] for x in s.get('reddit',[])][:3])"
```

Expected:`error_fare_sites: ['secretflying', 'fly4free']` + reddit 頭三個 subreddit。

- [ ] **Step 3: Commit**

```bash
git add sources.yaml
git commit -m "config(sources.yaml): 加錯價網 RSS feeds(secretflying, fly4free)"
```

---

### Task 4: feeds.py — 統一收料 + normalize(TDD,離線測試先行)

**Files:**
- Create: `feeds.py`
- Create: `test_feeds.py`

- [ ] **Step 1: 寫住會失敗嘅測試 `test_feeds.py`**

```python
"""
test_feeds.py — Phase 1B feeds normalize 測試(離線,唔使網絡)
跑法:uv run python test_feeds.py
"""
import sys

from feeds import normalize_reddit, normalize_rss

SAMPLE_REDDIT = {
    "data": {"children": [
        {"data": {"title": "Error fare? HKG-LON RT cheap",
                  "selftext": "Cathay business mispriced",
                  "permalink": "/r/flightdeals/comments/abc/hkg_lon/",
                  "created_utc": 1750000000}},
    ]}
}

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>HKG to Zurich HK$1950</title>
<link>https://secretflying.com/posts/hkg-zrh/</link>
<description>Possible error fare from Hong Kong</description>
<pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""


def main() -> None:
    ok = True

    r = normalize_reddit(SAMPLE_REDDIT, "flightdeals")
    cond = (len(r) == 1 and r[0]["source_url"].endswith("/hkg_lon/")
            and r[0]["source_platform"] == "reddit/r/flightdeals"
            and "HKG-LON" in r[0]["title"])
    print(("✅" if cond else "❌"), "reddit normalize:", r[0] if r else None)
    ok = ok and cond

    s = normalize_rss(SAMPLE_RSS, "secretflying")
    cond = (len(s) == 1 and s[0]["source_platform"] == "rss/secretflying"
            and "Zurich" in s[0]["title"]
            and s[0]["source_url"] == "https://secretflying.com/posts/hkg-zrh/")
    print(("✅" if cond else "❌"), "rss normalize:", s[0] if s else None)
    ok = ok and cond

    print()
    print("🎉 feeds 測試通過" if ok else "⚠️ feeds 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 跑佢確認失敗**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python test_feeds.py
```

Expected:FAIL —`ModuleNotFoundError: No module named 'feeds'` 或 ImportError。

- [ ] **Step 3: 寫 `feeds.py`**

```python
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run python test_feeds.py
```

Expected:兩個 ✅ + `🎉 feeds 測試通過`,exit 0。

- [ ] **Step 5: Commit**

```bash
git add feeds.py test_feeds.py
git commit -m "feat(feeds): 統一收料器 — reddit .json + RSS normalize"
```

---

### Task 5: consolidate.py — 純 code 去重(TDD)

**Files:**
- Create: `consolidate.py`
- Create: `test_consolidate.py`

- [ ] **Step 1: 寫住會失敗嘅測試 `test_consolidate.py`**

```python
"""
test_consolidate.py — Phase 1B 去重測試(離線)
跑法:uv run python test_consolidate.py
"""
import sys

from consolidate import consolidate


def main() -> None:
    ok = True
    cands = [
        {"airline": "Cathay", "origin": "HKG", "destination": "LHR",
         "depart_date": "2026-09-12", "return_date": "2026-09-20", "confidence": 60},
        {"airline": "cathay ", "origin": "hkg", "destination": "lhr",
         "depart_date": "2026-09-12", "return_date": "2026-09-20", "confidence": 85},
        {"airline": "Edelweiss", "origin": "SZX", "destination": "ZRH",
         "depart_date": "2026-11-03", "return_date": "2026-11-12", "confidence": 70},
    ]
    out = consolidate(cands)

    cond1 = len(out) == 2
    print(("✅" if cond1 else "❌"), "去重後 3→2 條:", len(out))
    ok = ok and cond1

    cond2 = bool(out) and out[0]["confidence"] == 85
    print(("✅" if cond2 else "❌"), "保留高 confidence + 排頭:", out[0]["confidence"] if out else None)
    ok = ok and cond2

    print()
    print("🎉 consolidate 測試通過" if ok else "⚠️ consolidate 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 跑佢確認失敗**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python test_consolidate.py
```

Expected:FAIL —`ModuleNotFoundError: No module named 'consolidate'`。

- [ ] **Step 3: 寫 `consolidate.py`**

```python
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run python test_consolidate.py
```

Expected:兩個 ✅ + `🎉 consolidate 測試通過`,exit 0。

- [ ] **Step 5: Commit**

```bash
git add consolidate.py test_consolidate.py
git commit -m "feat(consolidate): 純 code 去重(留最高 confidence)"
```

---

### Task 6: scout.py — Haiku 篩貼文(TDD 純邏輯部分)

**Files:**
- Create: `scout.py`
- Create: `test_scout.py`

- [ ] **Step 1: 寫住會失敗嘅測試 `test_scout.py`**

```python
"""
test_scout.py — Phase 1B scout 純邏輯測試(離線,唔 call LLM)
跑法:uv run python test_scout.py
"""
import sys

from scout import build_scout_system, chunked, _valid

FILTERS = {"origins": ["HKG", "SZX", "CAN"], "horizon_months": 12,
           "signals": ["商務艙價錢接近經濟艙", "非美籍航空長途異常平"]}

REQUIRED = ("origin", "destination", "depart_date", "return_date", "price",
            "currency", "airline", "source_platform", "source_url", "confidence")


def main() -> None:
    ok = True

    sysmsg = build_scout_system(FILTERS)
    cond = "HKG" in sysmsg and "商務艙" in sysmsg and "JSON array" in sysmsg
    print(("✅" if cond else "❌"), "system prompt 含 origins + signals + 格式要求")
    ok = ok and cond

    groups = list(chunked([1, 2, 3, 4, 5], 2))
    cond = groups == [[1, 2], [3, 4], [5]]
    print(("✅" if cond else "❌"), "chunked:", groups)
    ok = ok and cond

    good = {k: "x" for k in REQUIRED}
    cond = _valid(good) and not _valid({"origin": "HKG"})
    print(("✅" if cond else "❌"), "_valid 篩走缺欄位嘅 candidate")
    ok = ok and cond

    print()
    print("🎉 scout 純邏輯測試通過" if ok else "⚠️ scout 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 跑佢確認失敗**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python test_scout.py
```

Expected:FAIL —`ModuleNotFoundError: No module named 'scout'`。

- [ ] **Step 3: 寫 `scout.py`**

```python
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
uv run python test_scout.py
```

Expected:三個 ✅ + `🎉 scout 純邏輯測試通過`,exit 0。

- [ ] **Step 5: Commit**

```bash
git add scout.py test_scout.py
git commit -m "feat(scout): Haiku 篩貼文 → candidate JSON(system prompt 引用 sources.yaml filters)"
```

---

### Task 7: run_scout.py — 串起 + 原子寫檔

**Files:**
- Create: `run_scout.py`

- [ ] **Step 1: 寫 `run_scout.py`**

```python
"""
run_scout.py — Phase 1B 入口:收料 → scout 篩 → 去重 → 寫 data/candidates_YYYYMMDD.json
跑法:
    uv run python run_scout.py                  # 正常跑
    uv run python run_scout.py --limit 5        # 每個來源最多 5 篇(快速)
    uv run python run_scout.py --dry-run --limit 3   # 淨係 fetch + 印,唔 call LLM
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import yaml

import feeds
from consolidate import consolidate
from scout import screen_posts

ROOT = Path(__file__).parent


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Stream B:RSS scout(收料 → 篩 → 去重)")
    ap.add_argument("--limit", type=int, default=25, help="每個來源最多攞幾多篇")
    ap.add_argument("--max-feeds", type=int, default=0, help="只跑頭 N 個來源(0=全部)")
    ap.add_argument("--dry-run", action="store_true", help="唔 call LLM,淨係 fetch + 印")
    args = ap.parse_args()

    sources = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    filters = sources.get("filters", {}) or {}

    log("[scout] 開始收料…")
    posts = feeds.fetch_all(sources, limit=args.limit, max_feeds=args.max_feeds)
    log(f"[scout] 收到 {len(posts)} 篇貼文")

    if args.dry_run:
        for p in posts[:12]:
            log(f"  - [{p['source_platform']}] {p['title'][:70]}")
        log("[scout] --dry-run:唔 call LLM,完。")
        return 0

    candidates = screen_posts(posts, filters)
    log(f"[scout] scout 腦篩出 {len(candidates)} 個 candidate")

    final = consolidate(candidates)
    log(f"[scout] 去重後 {len(final)} 個")

    today = dt.date.today()
    out_dir = ROOT / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"candidates_{today.strftime('%Y%m%d')}.json"
    doc = {
        "scan_date": today.isoformat(),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source": "Stream B RSS scout(reddit .json + error-fare RSS)",
        "posts_fetched": len(posts),
        "candidate_count": len(final),
        "candidates": final,
    }
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out_path)
    log(f"[scout] 寫好 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Dry-run 驗證收料(唔使 LLM,順便實測 RSS feed 生死)**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python run_scout.py --dry-run --limit 3
```

Expected:見到逐個來源嘅篇數,例如 `reddit/r/flightdeals: 3 篇`、`rss/secretflying: 3 篇`,最後印頭幾條標題。
**若有 feed 顯示 `0 篇`** → 嗰個 RSS URL 失效,返 `sources.yaml` 換 URL 或刪走嗰行,再跑一次直到至少 reddit + 一個 RSS 有嘢。

- [ ] **Step 3: Commit**

```bash
git add run_scout.py
git commit -m "feat(run_scout): 串起 收料→篩→去重 + 原子寫 data/candidates_*.json"
```

---

### Task 8: 全鏈路 live smoke(完成標準)

**Files:**(冇新檔;呢個 task 係跑 + 驗證)

- [ ] **Step 1: 跑一次真‧全鏈路(會經 Max plan call Haiku,$0)**

```bash
cd /Users/alvinlai/Downloads/flight-deal-system
export PATH="$HOME/.local/bin:$PATH"
uv run python run_scout.py --limit 8
```

Expected:依次印出 收料篇數 → `scout 腦篩出 N 個 candidate` → `去重後 M 個` → `寫好 → …/data/candidates_YYYYMMDD.json`,exit 0。
(N、M 可以細甚至 0 — 視乎當日有冇錯價貼文;**重點係成條鏈路行得通、有寫檔**。)

- [ ] **Step 2: 確認輸出檔結構正確**

```bash
uv run python -c "import json,glob; f=sorted(glob.glob('data/candidates_*.json'))[-1]; d=json.load(open(f,encoding='utf-8')); print('檔:', f); print('keys:', list(d.keys())); print('posts_fetched:', d['posts_fetched'], '| candidate_count:', d['candidate_count']); print('第一個 candidate:', (d['candidates'][0] if d['candidates'] else '（今日冇 candidate，但鏈路 OK）'))"
```

Expected:印出檔名、top-level keys(含 `candidates`)、篇數、第一個 candidate(或「今日冇 candidate」訊息)。

- [ ] **Step 3: 全部離線測試再跑一次(回歸)**

```bash
uv run python test_feeds.py && uv run python test_consolidate.py && uv run python test_scout.py
```

Expected:三個 script 全 ✅,exit 0。

- [ ] **Step 4: 人手抽查(owner 驗證點)**

如果 `candidate_count > 0`:打開最新 `data/candidates_*.json`,隨機揀一個 candidate,撳佢個 `source_url` 入去原文,confirm 真係講緊一張 HKG/SZX/CAN 出發嘅平/錯價票(唔係亂作)。**呢步係 owner 嘅 validation checkpoint。**

- [ ] **Step 5: Commit(收尾)**

```bash
git add -A
git commit -m "test(phase-1b): 全鏈路 live smoke 通過 — Stream B RSS scout 完成" --allow-empty
```

---

## Self-Review(寫計劃後自查)

**1. Spec coverage(對 Phase 1B 範圍):**
- 統一 RSS 收料(Reddit `.json` + 錯價網 RSS)→ Task 3、4 ✅
- Haiku scout 經 `call_llm("scout")` 按 `sources.yaml` filters 篩 → Task 6 ✅
- 只回指定欄位 JSON → `build_scout_system` + `_valid` ✅
- 純 code 去重(airline+航線+日期 留最高 confidence)→ Task 5 ✅
- 輸出本地 `data/*.json` → Task 7 ✅
- 完成標準(跑一日,data/ 有合理 candidate JSON)→ Task 8 ✅
- 鐵律(delay/retry/429;唔 set 全域 key)→ `feeds.fetch_url` + `_polite_sleep`;LLM key 由 `llm.py` 隔離 ✅

**2. Placeholder scan:** 冇 TBD / 「自己加 error handling」/ 冇碼空步;每個 code step 都有完整可貼嘅碼。RSS feed URL 係起步值,Task 7 Step 2 有實測 + 換走死 feed 嘅明確指示(唔係 placeholder,係有驗證嘅起點)。

**3. Type consistency:**
- Post dict 欄位(`source_platform/source_url/title/text/published`)— `normalize_*` 產出、`fetch_*` 傳遞、`run_scout` 印 `title`,一致 ✅
- candidate 欄位 `REQUIRED` — `scout._valid` 同 `test_scout.REQUIRED` 同 `consolidate._key` 用嘅(airline/origin/destination/depart_date/return_date)一致 ✅
- 函數簽名:`feeds.fetch_all(sources, limit, max_feeds)`、`scout.screen_posts(posts, filters, batch)`、`consolidate.consolidate(candidates)`、`run_scout` 全部 call 法對得上 ✅

冇發現問題。
