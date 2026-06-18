# SPEC-008 OpenAPI 契約閘門

## 需求
把 OpenAPI 當 HTTP API 單一事實來源。supervisor 須能確定性檢查:
契約本身有效、且每個文件化端點都有對應契約測試。這是「照不照 spec」的
可信硬擋之一(不問 LLM)。

## 完成定義(可驗證)
- [x] `validate_openapi(path)`: 載入 yaml,缺 openapi/info/paths 或結構壞 → BLOCK
- [x] `check_contract_coverage(spec, test_dir)`: openapi 每個 operationId 都須在
      契約測試檔出現,缺一個 → BLOCK(文件化端點卻無契約測試)
- [x] 契約有效且覆蓋齊全 → ALLOW
- [x] CLI `supervisor contract --spec contracts/openapi.yaml --tests tests/contract`
- [x] 有單元測試:無效契約擋、缺覆蓋擋、齊全放行(7 測試)

## 對應 ADR
ADR-008
