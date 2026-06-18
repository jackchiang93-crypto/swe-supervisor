# 開發狀態:做了什麼 / 沒做什麼

最後更新:2026-06-18

## ✅ 已完成(可跑、有測試守)

| 模組 | 檔案 | 功能 | 測試 |
|---|---|---|---|
| 決策型別 | `supervisor/models.py` | GateDecision/ToolEvent/ErrorCode,confidence 只當 metadata | ✅ |
| 命令分析 | `supervisor/sandbox.py` | shlex tokenize + allowlist,未知程式 fail-closed,偵測管道/串接 | ✅ 6 case |
| 路徑政策 | `supervisor/policy.py` | allowlist-first + HARD_PROTECTED 自保 + 注入篩檢 | ✅ |
| 核心閘門 | `supervisor/core.py` | validate_event,唯讀快路徑,spec 真解析 | ✅ |
| CLI | `supervisor/cli.py` | 4 控制點:plan/validate-event/validate-diff/pre-deploy | smoke |
| Claude hook | `scripts/claude_hook_validate.py` | PreToolUse,從分支名抽 spec ref | — |
| 政策檔 | `policies/default.yaml` | 可調 allowlist/blocked/evidence | — |
| 文件 | README/specs/LICENSE(Apache-2.0) | — | — |

14 單元測試全綠。每個測試對應藍圖一個被修的洞。

## 🔧 已完成整合(這次做的)

- [x] Claude Code hook 端到端實測 — 用原生 PreToolUse JSON:ALLOW 靜默 / REVIEW→ask / BLOCK→deny
- [x] Codex `config.toml` 整合 + `supervisor codex-hook`(exit 2 擋下)
- [x] `supervisor install <專案路徑>` — 一鍵把治理層裝進任何 repo
- [x] hook 友善輸出:擋下時帶 codes + 修正建議,讓 agent 自救
- [x] hook 邏輯收進 CLI(`supervisor claude-hook`),跨專案不必複製腳本

## ❌ 還沒做(藍圖第二階段,自用優先級低)

| 項目 | 為何延後 |
|---|---|
| LLM 審查層(validate-diff 真跑 code review/design drift) | 需接模型 API + 注入防護,規則層先穩 |
| MCP server | hook 先夠用,穩了再沉澱成 MCP 工具 |
| GitHub Actions workflow yaml | 自用本機優先,有 CI 再加 |
| provenance / SLSA / in-toto | 合規導向,單人用不到 |
| TLA+ / Alloy 形式驗證 | 學習成本爆表,只高風險模組才值得 |
| 儀表板 / OTel metrics | 規則跑穩、有數據量再做 |
| 多 agent 併發 policy 鎖 | 單人單 agent 暫無需求 |

## 設計原則(不可退讓)

1. confidence 永不進 gate 邏輯,只進 metrics
2. 安全靠 allowlist + fail-closed,不靠 denylist
3. supervisor 不能改自己的 policy(HARD_PROTECTED 硬編碼)
4. 唯讀操作零延遲,摩擦=採用率殺手
5. 擋下時給 machine-readable codes + required_actions,讓 agent 能自救
