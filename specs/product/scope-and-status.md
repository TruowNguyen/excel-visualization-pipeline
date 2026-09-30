# Phạm vi và trạng thái sản phẩm

- Trạng thái tài liệu: **As-built + scope control**
- Cập nhật: 2026-09-25
- Sản phẩm: **Automated CX Report**
- Repository: **Excel Visualization Pipeline**

## Mục tiêu hiện tại

Chuyển workbook `.xlsx` bán cấu trúc thành dữ liệu chuẩn hóa có validation, lịch sử và lineage; sau đó cung cấp dashboard nội bộ để phân tích theo project, entity, metric và thời gian.

## Phạm vi đã triển khai

| ID | Năng lực | Trạng thái |
|---|---|---|
| SCP-001 | Parse workbook, hierarchy, date block, metric và unit | As-built |
| SCP-002 | Phân biệt zero, blank, marker, text và percentage | As-built |
| SCP-003 | Preview và quality gate trước commit | As-built |
| SCP-004 | Import `incremental` và `full_snapshot` vào SQLite | As-built |
| SCP-005 | Current state, revision history, artifact và import audit | As-built |
| SCP-006 | Dashboard cho 6 project baseline | As-built |
| SCP-007 | Tổng quan, thống kê, so sánh, audit và export CSV | As-built |
| SCP-008 | Truy vết từ điểm biểu đồ về workbook/sheet/cell | As-built |

## Phạm vi đã nêu nhưng chưa triển khai

| ID | Năng lực | Trạng thái | Điều kiện để bắt đầu |
|---|---|---|---|
| SCP-101 | Import/cập nhật tự động theo lịch hằng ngày | Accepted, not built | Chốt nguồn nhận file, lịch chạy, retry và owner vận hành |
| SCP-102 | AI tóm tắt xu hướng tăng/giảm | Accepted, not built | 9Router/model/output draft đã có; còn chốt privacy, retention, cost, evaluation và phê duyệt triển khai |

Import hiện tại chỉ được kích hoạt từ dashboard hoặc CLI. Nút **Làm mới dữ liệu** chỉ đọc lại dữ liệu đã commit; nó không tìm hoặc import workbook mới.

`SCP-102` được quản trị bởi [AI/Data v2](../ai-data/README.md), với trend contract tại [01-ai-trend-analysis.md](../ai-data/01-ai-trend-analysis.md). Việc có `.env.example`, base URL và model mặc định không làm tính năng chuyển thành `As-built`; repository hiện chưa có AI endpoint, adapter hay UI báo cáo AI. Comparison và template-driven report vẫn là proposal, chưa tự động trở thành product scope đã duyệt.

## Hạng mục chờ mentor quyết định

| ID | Năng lực | Trạng thái | Câu hỏi cần chốt |
|---|---|---|---|
| SCP-201 | Nhắc issue sắp/quá due date | Decision needed | Tích hợp trực tiếp, nhận kết quả qua API, hay loại khỏi sản phẩm này? |
| SCP-202 | Phát hiện issue tái phát sau khi fixed | Decision needed | Hệ thống nào sở hữu issue/status và khóa nào dùng để nhận diện tái phát? |
| SCP-203 | Nối identity khi entity/project đổi tên hoặc di chuyển | Decision needed | Quy tắc matching nào được duyệt và ai được quyền tạo/đóng alias? |

Cho tới khi có quyết định, `SCP-201`, `SCP-202` và `SCP-203` MUST NOT được dùng để kết luận bản hiện tại failed acceptance. Nếu đưa issue workflow vào phạm vi, cần bổ sung ít nhất:

- nguồn dữ liệu issue và quyền truy cập;
- định danh issue ổn định;
- trạng thái lifecycle và thời điểm `fixed`;
- due date, timezone và rule sắp/quá hạn;
- kênh, người nhận và chống gửi cảnh báo trùng;
- API/data model/dashboard behavior;
- acceptance fixture và test riêng.

Với `SCP-203`, hành vi hiện tại chỉ resolve đúng một active alias theo external key. Code chưa có workflow quản trị alias cho rename/move/manual merge; đổi path/key không có alias chuẩn bị trước sẽ tạo identity mới. Không chỉnh trực tiếp bảng alias để giả lập một workflow chưa được phê duyệt.

## Ngoài phạm vi bản nội bộ hiện tại

- authentication, authorization và phân quyền theo project;
- public Internet deployment và cam kết SLA;
- nhiều importer writer đồng thời hoặc SQLite trên network share;
- tự evaluate công thức Excel;
- workbook có password;
- tự nhận diện mọi layout mới mà không cần parser rule.

## Quy tắc chốt phạm vi

Một mục `Decision needed` chỉ chuyển trạng thái khi có quyết định ghi rõ: owner, input, output, success metric, deadline và hệ thống chịu trách nhiệm. Quyết định phải cập nhật tài liệu này và các spec bị ảnh hưởng.
