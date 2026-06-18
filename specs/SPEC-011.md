# SPEC-011 Provenance 產物來源證明

## 需求
為每次變更產生可追溯的來源證明:這個 artifact 對應哪個 commit、哪些檔案、
哪個 spec、哪個 ADR、測試結果如何。讓「誰 merge」之外還能答「對應哪份規格與測試」。

## 完成定義(可驗證)
- [x] `build_attestation(base)`: 蒐集 git HEAD sha+branch、變更檔、分支抽出的
      spec/ADR 參照、tasks 進度快照、時間戳,回 dict
- [x] `supervisor attest --base --out dist/attestation.json` 寫出 JSON
- [x] 證明含必要欄位:commit、changed_files、spec_refs、design_refs、progress、generated_at
- [x] 不依賴外部簽章工具(SLSA/in-toto 加密簽章列為未來);先做可驗證的純記錄
- [x] 有單元測試:attestation 含所有必要欄位、無 git 時優雅降級

## 對應 ADR
ADR-011
