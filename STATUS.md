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

## ✅ 「code 有沒有照 spec/design」— 已實作(分兩層)

核心認知:**確定性檢查可信→硬擋;LLM 不可信→最多 REVIEW。**

| 層 | 檔案 | 性質 | 可否硬擋 |
|---|---|---|---|
| 設計漂移(架構 import 規則) | `design_rules.py` | AST 靜態檢查,ground truth | ✅ BLOCK |
| LLM 顧問審查 | `review.py` | 機率性,opus-4-8 structured output | ❌ 最多 REVIEW |
| CLI `review` | 合併兩層,確定性優先 | — | — |

- LLM 輸入(spec/design/diff)先過 `screen_injection`,疑似注入→不餵模型,改 REVIEW
- LLM 判決永不單獨 ALLOW/BLOCK;confidence 設 0(不當訊號)
- 無 API 金鑰/未裝 anthropic → 跳過 LLM,確定性閘門照跑

## ❌ 還沒做(藍圖第二階段,自用優先級低)

| 項目 | 為何延後 |
|---|---|
| MCP server | hook 先夠用,穩了再沉澱成 MCP 工具 |
| GitHub Actions workflow yaml | 自用本機優先,有 CI 再加 |
| provenance / SLSA / in-toto | 合規導向,單人用不到 |
| TLA+ / Alloy 形式驗證 | 學習成本爆表,只高風險模組才值得 |
| 儀表板 / OTel metrics | 規則跑穩、有數據量再做 |
| 多 agent 併發 policy 鎖 | 單人單 agent 暫無需求 |

## ✅ 治理閉環(這次補齊)

| 功能 | 檔案 | 作用 |
|---|---|---|
| 進度打勾板 | `progress.py` + `supervisor status` | 證據推導,每次重驗,勾不會騙人;省 token |
| spec+design 腳手架 | `supervisor new SPEC-NNN` | 一鍵生 spec+ADR stub+進度項,逼 spec-first |
| design 強制 | `policy.needs_design_ref` + `core.verify_design_refs` | 碰架構面路徑→必須帶可解析 ADR,否則擋 |

進度狀態四態:`[x]` 已驗證 / `[ ]` 未做 / `[?]` 無驗證方式 / `[!]` 宣稱已做但測試掛。

## 設計原則(不可退讓)

1. confidence 永不進 gate 邏輯,只進 metrics
2. 安全靠 allowlist + fail-closed,不靠 denylist
3. supervisor 不能改自己的 policy(HARD_PROTECTED 硬編碼)
4. 唯讀操作零延遲,摩擦=採用率殺手
5. 擋下時給 machine-readable codes + required_actions,讓 agent 能自救
