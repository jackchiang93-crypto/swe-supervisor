# SWE Supervisor 規格

## SPEC-001 事件閘門
validate-event 須對命令、路徑、spec 追溯做判斷,回傳結構化 GateDecision。
唯讀命令走快路徑放行;未知程式預設 review。

## SPEC-002 PR diff 閘門
validate-diff 須檢查變更路徑是否在 allowlist、是否有 spec 追溯、測試是否通過。

## SPEC-003 自我保護
agent 不可修改 policy 檔、.claude/.codex 設定、.github workflow、secrets。
