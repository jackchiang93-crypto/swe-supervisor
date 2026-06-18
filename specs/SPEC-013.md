# SPEC-013 Dashboard 靜態儀表板

## 需求
產生自包含 HTML 儀表板,把專案軟工狀態(進度、SPEC↔ADR、未完成清單)視覺化,
免跑 server、直接開檔即看。給人一眼掌握全貌。

## 完成定義(可驗證)
- [x] `render_dashboard()`: 從 dossier 聚合資料產生單一 HTML 字串(內嵌 CSS,無外部依賴)
- [x] 顯示:總進度(done/total)、每個 SPEC 一列(狀態色塊/標題/ADR/進度)、未完成清單
- [x] `supervisor dashboard --out dashboard.html` 寫出檔案
- [x] HTML 自包含(無 CDN/外連),可離線開
- [x] 有單元測試:HTML 含所有 SPEC id、進度數字、為合法 HTML 骨架

## 對應 ADR
ADR-013
