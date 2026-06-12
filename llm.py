"""
llm.py — LLM 路由器(三個 provider)
=====================================
所有 LLM call 經呢度行。邊個「腦」做邊樣由 .env 決定:

    SCOUT_PROVIDER  / SCOUT_MODEL   — 篩選腦(scout)
    MASTER_PROVIDER / MASTER_MODEL  — 核實腦(master)

Provider 選項:
    claude_code — 行 `claude -p` headless mode(用你個 Claude Max plan,零 API 費)← 試跑階段預設
    anthropic   — Anthropic API(要 ANTHROPIC_API_KEY + Console 有 credit)
    minimax     — MiniMax M3 嘅 Anthropic 兼容接口(要 MINIMAX_API_KEY)

用法:
    from llm import call_llm, extract_json
    reply = call_llm("scout", system="你係機票錯價篩選員...", user="以下係今日嘅貼文...")
    data  = extract_json(reply)

設計決定(背景,改 code 前要知):
    * claude_code provider 用 subprocess call 本機已登入嘅 `claude` CLI,
      認證跟你嘅 Max plan 訂閱;CI 環境用 CLAUDE_CODE_OAUTH_TOKEN 環境變數。
    * minimax provider 行 Anthropic SDK + 自訂 base_url(MiniMax 官方提供 Anthropic 兼容接口);
      M3 係 reasoning model,回應可能含 thinking block — 下面只抽 type=="text" 嘅 block。
    * 所有 provider 共用 retry(指數退避)同 token/cost log。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv 未裝時照行(直接用環境變數)
    pass

DEFAULTS = {
    "scout": {"provider": "claude_code", "model": "haiku"},
    "master": {"provider": "claude_code", "model": "sonnet"},
}

MAX_RETRIES = 3
TIMEOUT_SECONDS = 300


def _log(msg: str) -> None:
    print(f"[llm] {msg}", file=sys.stderr)


# ------------------------------------------------------------------ providers

def _resolve_claude_bin() -> str:
    """搵 claude CLI 執行檔。優先次序:CLAUDE_CLI_PATH(.env 可指定)> PATH > ~/.local/bin。"""
    explicit = os.getenv("CLAUDE_CLI_PATH", "").strip()
    if explicit:
        return explicit
    found = shutil.which("claude")
    if found:
        return found
    fallback = os.path.expanduser("~/.local/bin/claude")
    if os.path.exists(fallback):
        return fallback
    raise RuntimeError(
        "搵唔到 claude CLI。請先安裝(Terminal 行:curl -fsSL https://claude.ai/install.sh | bash),"
        "或者喺 .env 設 CLAUDE_CLI_PATH 指住執行檔位置。"
    )


def _call_claude_code(system: str, user: str, model: str) -> str:
    """經 `claude -p`(print/headless mode)行 — 用你個 Max plan 訂閱額度。

    要求:本機已裝 Claude Code 並已 `claude /login`(或 CI 設咗 CLAUDE_CODE_OAUTH_TOKEN)。
    Prompt 經 stdin 傳入,避開 command line 長度上限。
    """
    cmd = [_resolve_claude_bin(), "-p", "--model", model, "--output-format", "json"]
    if system:
        cmd += ["--append-system-prompt", system]

    # 剔走 API key 類環境變數:.env 入面畀 anthropic provider 用嘅 key 一旦被
    # claude CLI 繼承,佢會轉用 API 計費(扣錢)而唔係 Max plan 訂閱 — 死症,必須隔離。
    env = os.environ.copy()
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        env.pop(var, None)

    proc = subprocess.run(
        cmd,
        input=user,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env=env,
    )
    # CLI 出錯時(例如未登入)會 exit 1,但錯誤詳情放喺 stdout 嘅 JSON 入面、
    # stderr 反而係空 — 所以要先試 parse stdout,先攞到有用嘅錯誤訊息。
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = None

    if payload is not None and payload.get("is_error"):
        detail = str(payload.get("result") or payload)[:800]
        raise RuntimeError(f"claude -p 回報錯誤: {detail}")

    if proc.returncode != 0:
        detail = (proc.stderr.strip() or proc.stdout.strip())[:800]
        raise RuntimeError(f"claude -p 失敗 (exit {proc.returncode}): {detail}")

    if payload is None:
        # CLI 版本差異時可能回純文字 — 直接回傳
        return proc.stdout.strip()

    cost = payload.get("total_cost_usd")
    if cost is not None:
        _log(f"[claude_code/{model}] cost≈${cost:.4f}(計入 Max plan 額度)")
    return str(payload.get("result", "")).strip()


def _call_anthropic_compatible(
    system: str,
    user: str,
    model: str,
    api_key: str,
    base_url: str | None = None,
    tag: str = "anthropic",
) -> str:
    """Anthropic SDK — 同時服務 anthropic(官方)同 minimax(Anthropic 兼容接口)。"""
    import anthropic  # 依賴: uv add anthropic

    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = anthropic.Anthropic(**kwargs)

    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": user}],
    )

    usage = getattr(msg, "usage", None)
    if usage is not None:
        _log(
            f"[{tag}/{model}] in={getattr(usage, 'input_tokens', '?')} "
            f"out={getattr(usage, 'output_tokens', '?')}"
        )

    # 只抽 text block — 自動跳過 MiniMax M3 嘅 thinking block
    parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip()


# --------------------------------------------------------------------- router

def call_llm(role: str, system: str, user: str) -> str:
    """主入口。role 係 "scout" 或 "master";路由由 .env 決定。"""
    role = role.lower()
    if role not in DEFAULTS:
        raise ValueError(f'role 必須係 "scout" 或 "master",收到: {role!r}')

    provider = (
        os.getenv(f"{role.upper()}_PROVIDER", DEFAULTS[role]["provider"]).strip().lower()
    )
    model = os.getenv(f"{role.upper()}_MODEL", DEFAULTS[role]["model"]).strip()

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if provider == "claude_code":
                return _call_claude_code(system, user, model)

            if provider == "anthropic":
                key = os.getenv("ANTHROPIC_API_KEY", "")
                if not key:
                    raise RuntimeError("未設定 ANTHROPIC_API_KEY(填入 .env,唔好 set 落全域 shell)")
                return _call_anthropic_compatible(system, user, model, key, tag="anthropic")

            if provider == "minimax":
                key = os.getenv("MINIMAX_API_KEY", "")
                base = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")
                if not key:
                    raise RuntimeError("未設定 MINIMAX_API_KEY(填入 .env)")
                return _call_anthropic_compatible(
                    system, user, model, key, base_url=base, tag="minimax"
                )

            raise ValueError(f"未知 provider: {provider!r}(可選: claude_code / anthropic / minimax)")

        except Exception as e:  # noqa: BLE001 — 統一 retry
            last_err = e
            if attempt < MAX_RETRIES:
                wait = 2**attempt
                _log(f"[{role}] 第 {attempt} 次失敗: {e} — {wait}s 後重試")
                time.sleep(wait)

    raise RuntimeError(f"[{role}] 重試 {MAX_RETRIES} 次都失敗。最後錯誤: {last_err}")


# -------------------------------------------------------------------- helpers

def extract_json(text: str):
    """由 LLM 回應抽 JSON。

    處理三種情況:(1) 乾淨 JSON;(2) ```json fence 包住;(3) JSON 前後有雜訊文字。
    注意:bracket 配對係簡化版(唔處理 string 入面嘅括號),日常篩選輸出夠用;
    遇到極端 case 出錯時,將原文 print 出嚟人手睇。
    """
    text = text.strip()

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError("回應入面搵唔到有效 JSON。原文頭 500 字:\n" + text[:500])
