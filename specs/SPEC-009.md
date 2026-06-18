# SPEC-009 MCP server(沉澱可呼叫工具)

## 需求
把已穩定的 supervisor 能力包成 MCP server,讓 Claude/Codex 不只透過 hook 被動
攔截,還能主動呼叫驗證工具(主動回頭查 spec/契約/進度)。

## 完成定義(可驗證)
- [x] 暴露至少 4 個工具:validate_event、validate_diff_paths、contract、status
- [x] 每個工具回傳結構化 dict(GateDecision 或進度),與 CLI 同一套核心邏輯,不重複實作
- [x] 工具邏輯與 MCP 綁定分離:核心函式不依賴 mcp 套件(可單測);只有 server 啟動才需 mcp
- [x] `python -m supervisor.mcp_server` 可啟動(build_server 已驗證註冊 4 工具)
- [x] mcp 未安裝時,核心工具函式仍可 import 與測試(延遲 import)
- [x] 有單元測試:每個工具函式回傳合法結構,不需啟動 MCP runtime(6 測試)

## 對應 ADR
ADR-009
