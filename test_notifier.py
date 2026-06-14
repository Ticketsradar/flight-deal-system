"""
test_notifier.py — Phase 2.2 notifier 純邏輯測試(離線,唔 send 真 message)
跑法:uv run python test_notifier.py
"""
import sys

from notifier import format_deal, notify_verified, DISCLAIMER


def make(status: str, **kw) -> dict:
    d = {"origin": "HKG", "destination": "NRT", "status": status,
         "depart_date": "2026-08-30", "return_date": "2026-09-05",
         "price": 600, "currency": "HKD", "airline": "Test Air",
         "gflights_url": "https://g.co/?a=1&b=2",
         "tripcom_url": "https://trip.com/?x=1&y=2",
         "source_url": "https://reddit.com/r/x"}
    d.update(kw)
    return d


def main() -> None:
    ok = True

    msg = format_deal(make("live", verified_price=580, note="仲買到"))
    cond = ("HKG → NRT" in msg and "2026-08-30" in msg and "HKD 600" in msg
            and "HKD 580" in msg and "Test Air" in msg and DISCLAIMER in msg
            and "google" in msg.lower() and "trip.com" in msg.lower())
    print(("✅" if cond else "❌"), "format_deal 含航線/價/連結/免責")
    ok = ok and cond

    cond = "&amp;" in msg and "<a href=" in msg
    print(("✅" if cond else "❌"), "format_deal 連結 HTML escape(& → &amp;)")
    ok = ok and cond

    # 路由:fake send 記低每 call 嘅 (chat, token)
    calls: list = []
    fake = lambda text, chat, token="": (calls.append((chat, token)) or True)
    buckets = {"live": [make("live")],
               "unverified": [make("unverified"), make("unverified")],
               "dead": [make("dead"), make("dead"), make("dead")]}
    conf = {"token": "T", "owner": "OWNER", "channel": "CHAN"}
    stat = notify_verified(buckets, conf=conf, send=fake)
    cond = (stat["sent"] == 4 and stat["live"] == 1 and stat["unverified"] == 2
            and stat["skipped_dead"] == 3)
    print(("✅" if cond else "❌"), "notify_verified 計數:", stat)
    ok = ok and cond

    chats = [c for c, _ in calls]
    cond = chats.count("CHAN") == 1 and chats.count("OWNER") == 3  # live owner + unverified×2
    print(("✅" if cond else "❌"), "路由:channel 只收 live,owner 收齊 live+unverified")
    ok = ok and cond

    # 冇 channel:live 淨推 owner
    calls2: list = []
    fake2 = lambda text, chat, token="": (calls2.append(chat) or True)
    stat2 = notify_verified({"live": [make("live")], "unverified": [], "dead": []},
                            conf={"token": "T", "owner": "OWNER", "channel": ""}, send=fake2)
    cond = stat2["sent"] == 1 and calls2 == ["OWNER"]
    print(("✅" if cond else "❌"), "冇 channel:live 淨推 owner")
    ok = ok and cond

    # 冇 token/owner:0 send,唔當機,dead 照計
    stat3 = notify_verified(buckets, conf={"token": "", "owner": "", "channel": ""}, send=fake)
    cond = stat3["sent"] == 0 and stat3["skipped_dead"] == 3
    print(("✅" if cond else "❌"), "冇 token:0 send 唔當機")
    ok = ok and cond

    print()
    print("🎉 notifier 純邏輯測試通過" if ok else "⚠️ notifier 測試有失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
