# 開發狀態 / Development Status

> ⚠️ **進度不在這裡手寫——手寫的會過時、會騙人(這份檔案自己就犯過)。**
> Live progress is NOT hand-maintained here. Run the evidence-based board:
>
> ```bash
> supervisor overview        # 全專案:每個 SPEC ↔ ADR ↔ 進度(當場重驗)
> supervisor status          # 打勾進度板
> supervisor spec list       # 所有規格
> ```
>
> 這些命令每次重跑驗證,`[x]` = 機器當場驗過,`[!]` = 宣稱已做但測試掛。
> 不像手寫清單會說謊。

## 真正還沒做 / Genuinely not done (board 不會顯示的)

這些是刻意的範圍邊界,不是漏做。各 ADR 有寫明取捨。

| 項目 | 狀態 | 原因 |
|---|---|---|
| Provenance 加密簽章(SLSA/in-toto) | 部分 | `attest` 產純 JSON 記錄,未簽章。防竄改需 CI+OIDC(ADR-011) |
| OpenAPI runtime 一致性(schemathesis) | 部分 | `contract` 做到 traceability 級(有測試),非跑 server 比對(ADR-008) |
| TLC 實跑驗證 | 條件式 | `formal` 有 `TLA_TOOLS`+java 才跑,否則誠實降級(ADR-012) |
| 多 agent 併發 policy 鎖 | 未做 | 單人單 agent 暫無需求 |
| OTel metrics / 即時儀表板 | 未做 | `dashboard` 是靜態快照;即時遙測待數據量需求 |

## 設計原則(不可退讓)/ Non-negotiable principles

1. confidence 永不進 gate 邏輯,只進 metrics / confidence never feeds gate logic
2. 安全靠 allowlist + fail-closed,不靠 denylist / allowlist + fail-closed, never denylist
3. supervisor 不能改自己的 policy(HARD_PROTECTED 硬編碼)/ can't disarm itself
4. 唯讀操作零延遲,摩擦=採用率殺手 / read-only ops zero-latency
5. 擋下時給 machine-readable codes + required_actions,讓 agent 自救 / actionable block reasons
6. **進度從證據推導,絕不手寫** / progress is evidence-derived, never hand-written
