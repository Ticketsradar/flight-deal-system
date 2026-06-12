# Flight Deal System — Phase 1.0 Starter Kit

> 呢個 kit 將我哋成段對話嘅設計決定寫死咗入 code,等你本機個 Claude Code(佢冇我哋嘅對話 context)唔使重新發明。你只需要交收 + 跑通測試。

## 入面有乜

| 檔案 | 係乜 |
|---|---|
| `llm.py` | **可換腦路由器**:三個 provider — `claude_code`(行你 Max plan,試跑用)/ `anthropic`(production master)/ `minimax`(production scout)。由 `.env` 兩行決定邊個腦做邊樣 |
| `test_llm.py` | Phase 1.0 通關測試:兩個腦各做「基本回應」+「JSON 輸出」兩個測試 |
| `sources.yaml` | Scout 收料來源 config:已 verify 嘅 Telegram handle、7 個 Reddit sub、XHS 關鍵字(Phase 5)、錯價篩選 signal |
| `env.example` | 環境變數範本 — copy 做 `.env` 用,預設 `claude_code` provider(零 API 成本) |

## 點開始(三步)

1. **開一個 project folder**(例如 `flight-deal-system`),將呢四個檔擺入去。
2. **喺嗰個 folder 開 Claude Code**(terminal 打 `claude`,或者 Claude Desktop 開嗰個 folder)。
3. **貼以下 prompt 畀 Claude Code**(成段 copy):

> 我係非程式員。呢個 folder 已經有四個 starter file:`llm.py`(LLM 路由器,支持 claude_code / anthropic / minimax 三個 provider,claude_code 係經 `claude -p` 行我個 Max plan)、`test_llm.py`、`sources.yaml`、`env.example`。請幫我:
> (1) 用 `uv` init 一個 Python project,加依賴:`anthropic`、`python-dotenv`、`pyyaml`;
> (2) copy `env.example` 做 `.env`,整 `.gitignore` 確保 `.env` 同 `compare_log/` 唔會 commit;
> (3) 讀一次 `llm.py`,對照我部機 `claude` CLI 嘅實際版本(`claude --version` / `claude -p --help`),如果 flag 名或者 JSON output 格式有出入就修正 `_call_claude_code`;
> (4) 跑 `uv run python test_llm.py`,有錯就 debug 到全綠;
> (5) `git init` + 第一個 commit,然後教我喺 GitHub 開新 repo 並 push 上去。
> 每一步用中文解釋你做緊乜。注意:唔好喺全域 shell set 任何 API key。

## 通關標準

`uv run python test_llm.py` 出 **🎉 全部通過** — 即係 scout(haiku)同 master(sonnet)都經你個 Max plan call 通,**一蚊 API 費都未使**。

## 之後點切去 production

試跑滿意後,開 `.env` 改路由(乜 code 都唔使掂):

```dotenv
SCOUT_PROVIDER=minimax          # + 填 MINIMAX_API_KEY
SCOUT_MODEL=MiniMax-M3
MASTER_PROVIDER=anthropic       # + 填 ANTHROPIC_API_KEY
MASTER_MODEL=claude-sonnet-4-6
```

再跑一次 `test_llm.py` 驗證新路由。

## 常見伏

- **`claude: command not found`** → Claude Code 未裝或未入 PATH。裝法:Mac/Linux `curl -fsSL https://claude.ai/install.sh | bash`;Windows PowerShell `irm https://claude.ai/install.ps1 | iex`。
- **claude_code provider 認證錯** → terminal 打 `claude` 互動登入一次(用 Max plan 帳號);CI/GitHub Actions 環境就要 `claude setup-token` 生成 `CLAUDE_CODE_OAUTH_TOKEN` 做 secret。
- **行得好慢** → `claude -p` 正常比直接 API 慢(成架 agent 起動緊),試跑階段冇所謂;production 換 API 就快。
- **撞 Max plan 額度上限** → 你 vibe coding 同呢啲 call 食同一個 5 小時 window;等個 window reset,或者照住上面切 production。
- **`test_llm.py` JSON 測試肥佬** → 多數係 model 包咗 markdown fence;`extract_json` 已處理大部分情況,仍然肥就 copy error 畀 Claude Code。

## 一個誠實聲明

呢套 code 喺我(對話入面嘅 Claude)嘅環境寫好但**冇網絡實跑過** — `claude` CLI 嘅 flag 同 output 格式會隨版本微調。所以 handoff prompt 嘅第 (3)(4) 步就係叫你本機 Claude Code 對照實際版本修正再跑到全綠:呢個唔係補鑊,係設計嘅一部分。
