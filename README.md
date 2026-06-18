# SWE Supervisor

監督 AI coding agent 的治理層。不是另一個寫 code 的 agent,是用來**擋它跑歪**的閘門。
整合 Claude Code / Codex hooks 與 GitHub CI。

## 與原藍圖的差異(刻意修掉的洞)

| 藍圖原作 | 問題 | 本實作 |
|---|---|---|
| `"rm -rf" in cmd` 字串黑名單 | 雙空格/拆旗標/路徑前綴/管道秒繞 | shlex tokenize + allowlist,未知程式 fail-closed (`sandbox.py`) |
| spec_refs 寫死 `["SPEC-001"]` | traceability 變蓋章 | 從分支名抽 ref,且須在 `specs/` 真解析 (`core.verify_spec_refs`) |
| confidence 同時當「別信」又當 gate 輸入 | 自相矛盾 | confidence 只進 metrics,絕不進 gate 邏輯 |
| blocked_paths 沒含 policy 自己 | agent 可改 policy 自我解除武裝 | `HARD_PROTECTED` 硬編碼,policy 檔不可被改 |
| 每個 event 都過重檢查 | 摩擦=採用率殺手 | 唯讀命令走零延遲快路徑 |
| 未篩注入就餵 LLM | 間接 prompt injection | `screen_injection` 先擋 |

## 快速開始

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q

# 單次事件
supervisor validate-event --tool Bash --command "rm -rf build"   # → review
supervisor validate-event --tool Write --file src/a.py --spec-ref SPEC-001  # → allow

# PR diff gate
supervisor validate-diff --base origin/main --spec-ref SPEC-001 --test-cmd "pytest -q"
```

## 四個控制點

| 命令 | 時機 | 作用 |
|---|---|---|
| `plan` | 開工前 | 篩 spec/issue 注入,再交 LLM |
| `validate-event` | 工具使用前 | 命令風險 + 路徑 allowlist + spec 追溯 |
| `validate-diff` | PR 合併前 | 路徑政策 + 追溯 + 跑測試 |
| `pre-deploy` | 部署前 | rollback/測試證據,production 強制人工批准 |

## 整合

- **Claude Code**: `.claude/settings.json` 已設 PreToolUse → `scripts/claude_hook_validate.py`
- **GitHub**: `.github/workflows/ai-governor.yml` 做 PR gate
- exit code 2 = block/review,Claude 會擋下並把 stderr 顯示給 agent

## 還沒做(藍圖列為第二階段)

MCP server、provenance/SLSA attestation、TLA+/Alloy、儀表板。自用前提下優先級低,規則跑穩再加。

## License

Apache-2.0
