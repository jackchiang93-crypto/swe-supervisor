# SPEC-010 Spec/Design 總覽(專案檔案夾)

## 需求
一條命令攤開整個專案的軟工狀態:每個 SPEC ↔ 對應 ADR ↔ 進度(做了/沒做),
一目了然又能展開細看,並能拉出單一 SPEC 全文回頭改。落實「規格即事實來源、
進度即證據」的軟工實踐。

## 完成定義(可驗證)
- [x] `discover_specs()`: 蒐集所有 SPEC——含獨立檔(specs/SPEC-NNN.md)與塞在
      specs/current.md 的章節,兩種來源都要抓到
- [x] 每個 SPEC 關聯:對應 ADR(design/adr/ADR-NNN.md)、進度狀態(由 tasks.yaml +
      status 推導)
- [x] `supervisor spec list`: 一行一個 SPEC,顯示 id/標題/有無 ADR/進度勾
- [x] `supervisor spec show SPEC-NNN`: 印出該 SPEC 全文 + 連動的 ADR 全文
- [x] `supervisor overview`: 專案檔案夾——頂部統計(done/total),逐 SPEC 一行狀態;
      `--full` 附上每個 SPEC+ADR 全文
- [x] 有單元測試:散落來源都抓到、ADR 關聯、進度關聯、list/show/overview 輸出(7 測試)

## 對應 ADR
ADR-010
