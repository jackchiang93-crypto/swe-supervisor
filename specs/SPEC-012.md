# SPEC-012 Formal 形式驗證閘門(TLA+/Alloy)

## 需求
高風險模組(狀態機、併發、一致性)可補形式規格。supervisor 提供閘門:確認高風險
模組有對應 formal 模型,且在工具鏈具備時跑 model checking。

## 完成定義(可驗證)
- [x] `formal_gate(formal_dir)`: 掃 formal/*.tla、*.als;無模型 → ALLOW(附註,不硬擋)
- [x] 偵測 TLC 工具鏈(java + tla2tools.jar 路徑由 env TLA_TOOLS 提供):
      有 → 跑 TLC 並回 pass/fail;無 → 降級(列出模型但標「工具鏈缺,略過檢查」)
- [x] TLC 回 fail → BLOCK;pass → ALLOW
- [x] `supervisor formal --dir formal`
- [x] 有單元測試:無模型降級、有模型偵測、工具鏈缺降級(不需真跑 TLC)

## 對應 ADR
ADR-012
