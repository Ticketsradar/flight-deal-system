"""
test_feeds.py — Phase 1B feeds normalize 測試(離線,唔使網絡)
跑法:uv run python test_feeds.py
"""
import sys

from feeds import normalize_rss

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>HKG to Zurich HK$1950</title>
<link>https://www.theflightdeal.com/posts/hkg-zrh/</link>
<description>Possible error fare from Hong Kong</description>
<pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""


def main() -> None:
    ok = True

    # error-fare 網站 RSS:platform 標籤照用
    s = normalize_rss(SAMPLE_RSS, "rss/theflightdeal")
    cond = (len(s) == 1 and s[0]["source_platform"] == "rss/theflightdeal"
            and "Zurich" in s[0]["title"]
            and s[0]["source_url"] == "https://www.theflightdeal.com/posts/hkg-zrh/")
    print(("✅" if cond else "❌"), "rss normalize:", s[0] if s else None)
    ok = ok and cond

    # reddit(走 .rss):同一 parser,platform 標籤係 reddit/r/<sub>
    r = normalize_rss(SAMPLE_RSS, "reddit/r/flightdeals")
    cond = (len(r) == 1 and r[0]["source_platform"] == "reddit/r/flightdeals"
            and r[0]["title"] == "HKG to Zurich HK$1950")
    print(("✅" if cond else "❌"), "reddit-rss normalize:", r[0]["source_platform"] if r else None)
    ok = ok and cond

    print()
    print("🎉 feeds 測試通過" if ok else "⚠️ feeds 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
