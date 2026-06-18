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

## 核心零 API,LLM 是選配

督促 coding AI 回頭看 spec、做好 QA、不偏離架構——**這套核心完全不需要任何 LLM API**。
coding AI(Claude Code/Codex)本身就是 LLM;supervisor 只當「給它判決的煞車+裁判」,
透過 hook 把機器可讀的理由塞回去,AI 自己讀懂、自己回頭改。

| 督促 | 機制 | 要 API? |
|---|---|---|
| 你沒對到 spec | spec ref 須在 specs/ 解析 | ❌ |
| 你改架構沒更新 design | ADR ref 須在 design/adr/ 解析 | ❌ |
| 你偏離分層 | AST import 規則 | ❌ |
| QA 沒做 | validate-diff 跑測試,沒過就擋 | ❌ |
| 危險命令/動禁區 | tokenize + allowlist | ❌ |
| 散文 spec 的語意漂移 | LLM 顧問(REVIEW-only) | ✅ 選配 |

最後一項的「顧問腦」可三選一:
- `supervisor review --backend codex` — 用本機 Codex 訂閱,**不付 API 錢**
- `supervisor review --backend anthropic` — 付費 API(`[llm]` 選用依賴)
- 都不裝 → 顧問跳過,確定性閘門照常硬擋

核心督促(spec追溯/design強制/QA/命令/路徑)零 API。

## 工作流程(治理閉環)

```
1. 要加/改功能  → supervisor new SPEC-006   # 一鍵生 spec+ADR stub+進度項
                  填好 spec/ADR 再動工
2. coding       → gate 攔截:沒 SPEC 參照→擋;碰架構沒 ADR→擋
3. 做完         → 在 tasks.yaml 綁 verify(test/file)
                  supervisor status 自動打勾(勾=當場驗證,不會騙人)
4. 回頭看進度    → supervisor status  # 5 行打勾板,不用重讀對話、不燒 token
```

## 四個控制點

| 命令 | 時機 | 作用 |
|---|---|---|
| `plan` | 開工前 | 篩 spec/issue 注入,再交 LLM |
| `validate-event` | 工具使用前 | 命令風險 + 路徑 allowlist + spec 追溯 |
| `validate-diff` | PR 合併前 | 路徑政策 + 追溯 + 跑測試 |
| `pre-deploy` | 部署前 | rollback/測試證據,production 強制人工批准 |
| `review` | code review | 設計漂移硬擋 + LLM 顧問(REVIEW-only) |
| `new` | 開工前 | 生 spec+ADR stub + 進度項(spec-first 一鍵) |
| `status` | 任何時候 | 證據推導的打勾進度板 |
| `spec list` | 任何時候 | 列出所有 SPEC(含埋在 current.md 的),含 ADR+進度 |
| `spec show SPEC-NNN` | 改功能前 | 拉出單一 SPEC 全文 + 連動 ADR |
| `overview [--full]` | 任何時候 | 專案軟工總覽:做到哪、剩多少,--full 附全文 |

## 整合

- **Claude Code**: `.claude/settings.json` 已設 PreToolUse → `scripts/claude_hook_validate.py`
- **GitHub**: `.github/workflows/ai-governor.yml` 做 PR gate
- exit code 2 = block/review,Claude 會擋下並把 stderr 顯示給 agent

## 還沒做(藍圖列為第二階段)

MCP server、provenance/SLSA attestation、TLA+/Alloy、儀表板。自用前提下優先級低,規則跑穩再加。

## License

Apache-2.0
