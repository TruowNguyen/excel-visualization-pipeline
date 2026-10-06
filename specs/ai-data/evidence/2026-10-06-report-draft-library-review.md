# Báo cáo — chủ động chọn bản nháp và xóa bản nháp

Ngày: 06/10/2026. Thay đổi cục bộ luồng UX; giữ nguyên template 1.3, renderer v4, prompt, validator và Analytics Engine.

## Hành vi

- Tab mặc định mở thư viện bản nháp của dự án. Không dùng con trỏ sessionStorage cũ để tự mở báo cáo.
- Reload/quay lại từ tab khác không hiện báo cáo cuối. Chọn tên bản nháp mới tải và hiện nội dung; danh sách thu gọn để ưu tiên đọc báo cáo.
- Tạo báo cáo mới mở thiết lập và ẩn nội dung bản trước. Chuẩn bị bản nháp mới lưu snapshot; không gọi AI. Về danh sách không tự chọn báo cáo nào.
- Tạo từ phạm vi dashboard tiếp tục kế thừa nguồn, tuần/tháng, cách tính và bộ lọc. Đây là chủ ý tạo mới, không tự tạo nội dung.
- Xóa ở mỗi dòng danh sách, có tên đầy đủ cho công nghệ hỗ trợ. Hộp xác nhận ghi rõ tên, tất cả phiên bản và việc PDF/DOCX đã tải không bị xóa. Nút thao tác khóa khi đang xử lý; kết quả xóa được thông báo và focus trở về Tạo báo cáo mới.
- Lỗi/xung đột không xóa nội dung hiện tại. List cập nhật lại; phiên bản mới nhất phải được kiểm tra trước khi xóa. Không tự mở bản tiếp theo.
- Giữ cảnh báo chỉnh sửa chưa lưu. Hủy yêu cầu đọc/ghi khi rời tab, và chặn phản hồi muộn tự mở lại báo cáo.

## Lưu trữ và an toàn

`DELETE /api/projects/{project}/reports/{report_id}` nhận `baseRevision`, kiểm tra project/source và latest revision bằng SQLite transaction, đồng bộ cùng khóa sửa/sinh AI. Migration 008 thêm tombstone riêng; không đổi cấu trúc snapshot hay bảng báo cáo cũ.

Xóa mềm: giữ revisions, checks và cached exports cho khả năng phục hồi quản trị, không có nút khôi phục trong bản này. APIs đọc/sửa/sinh AI/kiểm tra/xuất chặn báo cáo đã xóa; replay request tạo cũ không phục hồi bản xóa. Workbook và dữ liệu KPI không bị xóa. Không xóa bản nháp dữ liệu thực trong quá trình kiểm thử.

## Kiểm chứng

- 48 ca pytest qua: storage, reporting và report story, gồm phân quyền nguồn/dự án, 409 phiên bản cũ, baseRevision không hợp lệ, 404 sau xóa cả cached export, giữ bản nháp khác, giữ dữ liệu phục hồi, chặn replay/append sau xóa.
- 19 ca Playwright qua ở lần chạy cuối: con trỏ cũ không tự mở, tạo mới ẩn bản trước, tab re-entry/reload yêu cầu chọn lại, hủy/xác nhận xóa, xóa thất bại giữ nội dung, xóa dùng revision mới nhất khi đang đọc bản cũ; hồi quy scope dashboard, annotation, editing, export và bố cục 1366/1440/1920/390. 390 là kiểm tra không crop, không cam kết thiết kế mobile.
- TypeScript kiểm tra và production build qua. Cảnh báo kích thước chunk Plotly vẫn còn, ngoài phạm vi thay đổi này.
- Ca xóa lỗi ban đầu thao tác disclosure đang mở như thể đang đóng; thu gọn danh sách khi accept báo cáo đã giải quyết hành vi này. Một lần chạy đang hoạt động bị Vite reload khi sửa file; không dùng kết quả đó làm bằng chứng cuối. Lần cuối toàn bộ 19 ca qua.
- Ảnh thư viện có bản nháp/trống được kiểm tra trực quan: `.impeccable/review/test-artifacts/report-draft-library-final/reports-draft-deletion-can-f6efd-ves-only-after-confirmation/`. Fixture UI là dữ liệu tổng hợp, backend dùng TestClient và kho kiểm thử riêng; không phải kiểm thử production.
- Không gọi LLM mới: thay đổi chỉ liên quan chọn/xóa bản nháp, không chỉnh dữ liệu hay diễn giải. Kết quả kiểm thử API LLM trước đó vẫn ở `2026-10-06-report-clarity-review.md`; không coi đó là cuộc gọi mới cho thay đổi này.

Impeccable harden định hướng xác nhận xóa, xử lý conflict, focus, empty/error state và giữ identity navy/purple hiện có. Không sửa DESIGN.md hoặc sidecar, không sinh raster asset mới. Đánh giá cục bộ: đạt yêu cầu luồng thư viện/xóa, không thay thế đánh giá toàn tính năng hay xác nhận deployment.
