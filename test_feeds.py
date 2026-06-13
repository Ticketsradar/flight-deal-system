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
