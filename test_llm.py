"""
test_llm.py — Phase 1.0 通關測試
================================
驗證 scout 同 master 兩個腦都 call 通 + 識出 JSON。

跑法:
    uv run python test_llm.py

全綠 = Phase 1.0 完成。有紅 = copy 個 error 畀 Claude Code 整。
"""
import os
import sys

from llm import call_llm, extract_json


def main() -> None:
    all_ok = True

    for role in ("scout", "master"):
        provider = os.getenv(f"{role.upper()}_PROVIDER", "claude_code")
        model = os.getenv(f"{role.upper()}_MODEL", "(預設)")
        print(f"\n=== 測試 {role}(provider={provider}, model={model})===")

        # 測試 1:基本回應
        try:
            reply = call_llm(
                role,
                system="You are a test assistant. Follow instructions exactly.",
                user=f"Reply with exactly this text and nothing else: OK-{role}",
            )
            passed = f"OK-{role}" in reply
            print(("✅" if passed else "❌"), "基本回應:", reply.strip()[:120])
            all_ok = all_ok and passed
        except Exception as e:  # noqa: BLE001
            print("❌ 基本回應出錯:", e)
            all_ok = False
            continue  # 基本都唔通,跳過 JSON 測試

        # 測試 2:JSON 輸出(scout / master 日常工作格式)
        try:
            reply = call_llm(
                role,
                system="You output only valid JSON. No markdown fences, no explanation.",
                user=(
                    'Return exactly this JSON object: '
                    '{"status": "ready", "role": "%s"}' % role
                ),
            )
            data = extract_json(reply)
            passed = isinstance(data, dict) and data.get("status") == "ready"
            print(("✅" if passed else "❌"), "JSON 輸出:", data)
            all_ok = all_ok and passed
        except Exception as e:  # noqa: BLE001
            print("❌ JSON 測試出錯:", e)
            all_ok = False

    print()
    if all_ok:
        print("🎉 全部通過 — Phase 1.0 完成!可以開始 Phase 1A(fast-flights 掃描器)。")
    else:
        print("⚠️ 有測試失敗 — 將上面成段 output copy 畀 Claude Code,叫佢 debug 到全綠。")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
