# SPEC-007 Codex 訂閱驗證後端

## 需求
`supervisor review` 的 LLM 顧問層,除了付費 anthropic API,須支援用本機 Codex
訂閱當驗證者(`codex exec`),讓使用者不必另付 per-token API 費用。

## 完成定義(可驗證)
- [x] `supervisor review --backend codex` 走 Codex,`--backend anthropic` 走 API,預設 anthropic
- [x] Codex 後端 shell 呼叫 `codex exec`,把 spec/design/diff 當不可信輸入(先過注入篩檢)
- [x] Codex 後端輸出一樣映射成 GateDecision,判決最多 REVIEW(與 anthropic 後端同規則)— 已真呼叫驗證
- [x] Codex 不在/失敗時優雅降級(ALLOW + 註記),不可硬擋
- [x] 有單元測試:注入短路、Codex 缺席降級、findings→REVIEW 映射(6 測試)

## 對應 ADR
ADR-007
