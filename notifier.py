"""
notifier.py — Stream B Telegram 即時推送(Phase 2.2)
====================================================
讀 master 出嘅 verified buckets,依推送政策(spec §7)派 Telegram message:
    live       → owner + 公開 channel(channel 有設先推)
    unverified → owner 一個(帶 ⚠️「請自己快手入原文連結確認」)
    dead       → 唔推(淨係留喺網站歷史區)

每條 message 含:航線 / 價(傳聞+重查)/ 日期 / 狀態 / airline +
                Google Flights / Trip.com / 原文 連結 + 免責聲明。

鐵律:token 只由 .env / 環境變數讀,唔寫死入 code;對外 request 有 retry;
      壞咗就 log 唔當機(收唔到提示好過成個 pipeline 仆)。
"""
from __future__ import annotations

import html
import os
import time

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # 冇 dotenv 都唔好仆,照讀環境變數
    pass

API_BASE = "https://api.telegram.org"
HTTP_TIMEOUT = 20.0
MAX_RETRIES = 3

DISCLAIMER = ("⚠️ 錯價隨時被航空公司更正或取消訂單,價格僅供參考;"
              "務必撳連結自行確認,訂票風險自負。")

STATUS_LABEL = {
    "live": "✅ 已核實 — 仲買到",
    "unverified": "⚠️ 未能自動核實 — 請自己快手入原文連結確認",
    "dead": "❌ 已失效",
}


def log(msg: str) -> None:
    print(f"[notifier] {msg}", flush=True)


def cfg() -> dict:
    """由環境讀 Telegram 設定。owner 支援新舊兩個變數名。"""
    return {
        "token": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        "owner": (os.getenv("TELEGRAM_OWNER_CHAT_ID", "").strip()
                  or os.getenv("TELEGRAM_CHAT_ID", "").strip()),
        "channel": os.getenv("TELEGRAM_CHANNEL_ID", "").strip(),
    }


def _esc(s) -> str:
    """HTML escape 文字內容(&, <, >)。"""
    return html.escape("" if s is None else str(s))


def _price(deal: dict) -> str:
    cur = _esc(deal.get("currency") or "HKD")
    parts = []
    claimed = deal.get("price")
    verified = deal.get("verified_price")
    if claimed not in (None, ""):
        parts.append(f"傳聞 {cur} {_esc(claimed)}")
    if verified not in (None, ""):
        parts.append(f"重查 {cur} {_esc(verified)}")
    return " / ".join(parts) if parts else "價未知"


def _link(label: str, url: str) -> str:
    """Telegram HTML 連結;href 內 &/\"/< 要 escape(quote=True)。"""
    return f'<a href="{html.escape(url, quote=True)}">{label}</a>'


def format_deal(deal: dict) -> str:
    """一個 verified deal → 一段 Telegram HTML message。"""
    status = str(deal.get("status", "unverified")).lower()
    lines = [
        f"✈️ <b>{_esc(deal.get('origin'))} → {_esc(deal.get('destination'))}</b>",
        f"狀態:{STATUS_LABEL.get(status, _esc(status))}",
        f"🗓 {_esc(deal.get('depart_date'))} → {_esc(deal.get('return_date'))}",
        f"💰 {_price(deal)}",
    ]
    if deal.get("airline"):
        lines.append(f"🛫 {_esc(deal.get('airline'))}")
    if deal.get("note"):
        lines.append(f"📝 {_esc(deal.get('note'))}")

    links = []
    if deal.get("gflights_url"):
        links.append(_link("Google Flights", deal["gflights_url"]))
    if deal.get("tripcom_url"):
        links.append(_link("Trip.com", deal["tripcom_url"]))
    if deal.get("source_url"):
        links.append(_link("原文出處", deal["source_url"]))
    if links:
        lines.append("🔗 " + " · ".join(links))

    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def send_message(text: str, chat_id: str, token: str = "",
                 disable_preview: bool = True) -> bool:
    """POST 去 Telegram Bot API sendMessage。成功回 True;壞咗 log + 回 False(retry 過)。"""
    token = token or cfg()["token"]
    if not token or not chat_id:
        log("冇 token 或 chat_id — 跳過呢條")
        return False
    url = f"{API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": disable_preview,
    }
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = httpx.post(url, json=payload, timeout=HTTP_TIMEOUT)
            if resp.status_code == 429:
                wait = 3 * attempt
                log(f"429 rate limit — 等 {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return True
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    log(f"send 失敗(放棄):chat={chat_id} — {last}")
    return False


def notify_verified(buckets: dict, conf: dict | None = None, send=send_message) -> dict:
    """
    依推送政策派 message。send 可注入(測試用 fake,免真 call 網絡)。
    回統計:{"sent","live","unverified","skipped_dead"}。
    """
    conf = conf or cfg()
    token = conf.get("token", "")
    owner = conf.get("owner", "")
    channel = conf.get("channel", "")
    stat = {"sent": 0, "live": 0, "unverified": 0,
            "skipped_dead": len(buckets.get("dead", []) or [])}

    if not token or not owner:
        log("冇 TELEGRAM_BOT_TOKEN 或 owner chat id — 唔推(check .env)")
        return stat

    for deal in buckets.get("live", []) or []:
        text = format_deal(deal)
        if send(text, owner, token=token):
            stat["sent"] += 1
        if channel and send(text, channel, token=token):
            stat["sent"] += 1
        stat["live"] += 1

    for deal in buckets.get("unverified", []) or []:
        if send(format_deal(deal), owner, token=token):
            stat["sent"] += 1
        stat["unverified"] += 1

    log(f"推送完:live {stat['live']} / unverified {stat['unverified']} "
        f"/ dead {stat['skipped_dead']}(唔推);共 send {stat['sent']} 條")
    return stat


if __name__ == "__main__":
    # 直接跑 = send 一個測試 message 畀 owner,證明部電話收到推送。
    c = cfg()
    sample = {
        "origin": "HKG", "destination": "NRT", "status": "unverified",
        "depart_date": "2026-08-30", "return_date": "2026-09-05",
        "price": 600, "verified_price": None, "currency": "HKD",
        "airline": "(測試)Test Air",
        "note": "呢個係 Phase 2.2 測試訊息。你見到佢 = Telegram 推送通咗。",
        "gflights_url": "https://www.google.com/travel/flights",
        "tripcom_url": "https://www.trip.com/flights/",
        "source_url": "https://www.reddit.com/r/flightdeals/",
    }
    ok = send_message(format_deal(sample), c["owner"], token=c["token"])
    print("✅ 測試訊息已 send,請 check 你 Telegram 部電話"
          if ok else "❌ send 失敗,睇上面 [notifier] log")
    raise SystemExit(0 if ok else 1)
