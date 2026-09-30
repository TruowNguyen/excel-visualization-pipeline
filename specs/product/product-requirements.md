# Product Requirements Document — Automated CX Report

- Tên ngắn: **PRD**
- Phiên bản: 1.0
- Cập nhật: 2026-09-25
- Trạng thái: **Baseline hiện tại + backlog đã biết**
- Product owner/mentor: **TBD**
- Người dùng chính: Nhân sự CX nội bộ

## 1. Tóm tắt sản phẩm

Automated CX Report chuyển báo cáo Excel bán cấu trúc thành một không gian phân tích có validation, lịch sử và truy vết. Người dùng có thể import workbook, xem KPI theo project/entity/thời gian, so sánh các entity cùng đơn vị và quay từ một điểm biểu đồ về đúng ô Excel nguồn.

Sản phẩm hiện là công cụ nội bộ chạy với FastAPI, TypeScript/Vite và SQLite. Nó chưa phải hệ thống SaaS/public Internet và chưa có authentication hoặc phân quyền.

## 2. Vấn đề cần giải quyết

Quy trình báo cáo CX dựa trên Excel hiện có các rủi ro:

- cấu trúc phân cấp, metric và ngày nằm trong workbook bán cấu trúc;
- đối chiếu thủ công mất thời gian và dễ làm mất ngữ nghĩa zero/missing;
- khó biết một số trên dashboard đến từ sheet, ô và workbook nào;
- file cập nhật có thể tạo dữ liệu trùng hoặc ghi đè lịch sử;
- việc so sánh giữa project/entity/kỳ chưa có contract thống nhất.

## 3. Mục tiêu sản phẩm

| ID | Mục tiêu |
|---|---|
| PRD-G01 | Chuẩn hóa workbook mà vẫn bảo toàn giá trị và lineage nguồn |
| PRD-G02 | Ngăn dữ liệu lỗi đi vào current dashboard bằng preview và quality gate |
| PRD-G03 | Cho phép phân tích 6 project baseline theo hierarchy, metric và thời gian |
| PRD-G04 | Lưu current state và lịch sử revision/import có thể audit |
| PRD-G05 | Đối chiếu một giá trị/tổng hợp trên chart với nguồn hình thành |
| PRD-G06 | Giảm thao tác tổng hợp và so sánh thủ công của nhân sự CX |

## 4. Ngoài mục tiêu hiện tại

- thay thế hệ thống quản lý issue/ticket;
- tự tính lại KPI nguồn ngoài rule tổng hợp đã khai báo;
- hỗ trợ mọi layout Excel mà không cần cấu hình;
- public deployment, multi-tenant hoặc phân quyền chi tiết;
- nhiều tiến trình ghi đồng thời vào SQLite;
- tự động đồng bộ hằng ngày khi chưa chốt nguồn file và owner vận hành.

## 5. Người dùng và nhu cầu

### CX Analyst

Cần xem xu hướng, thống kê, so sánh entity và điều tra số liệu bất thường mà không đọc lại từng ô Excel.

### Data Operator

Cần preview workbook, biết lỗi trước khi ghi, chọn đúng mode import và kiểm tra kết quả/lịch sử.

### Maintainer

Cần thay đổi parser rule có kiểm soát, chạy migration/test, backup/restore và chẩn đoán lineage.

### Mentor/Product Owner

Cần xác nhận phạm vi, tiêu chí hoàn thành và quyết định các tích hợp như AI hoặc issue management.

## 6. Hành trình chính

1. Operator nhận workbook và mở tab Import.
2. Hệ thống parse/validate rồi hiển thị project, date range, hash và issues.
3. Operator chọn `incremental` hoặc `full_snapshot` và xác nhận.
4. Hệ thống commit atomically và cập nhật lịch sử.
5. Analyst chọn project, entity, thời gian và workspace.
6. Analyst chọn một điểm để xem workbook/sheet/cell/revision nguồn.
7. Analyst tải CSV hoặc ghi nhận kết quả đối chiếu khi cần.

Use case chi tiết nằm tại [use-cases.md](use-cases.md).

## 7. Yêu cầu chức năng

### Ingestion và validation

- `PRD-F01`: Hệ thống MUST nhận workbook `.xlsx` hợp lệ.
- `PRD-F02`: Hệ thống MUST nhận diện project/entity hierarchy, date block, metric và unit theo config.
- `PRD-F03`: Hệ thống MUST bảo toàn zero, blank, source marker, text, percentage và Excel number format.
- `PRD-F04`: Hệ thống MUST preview và hiển thị error/warning trước commit.
- `PRD-F05`: Validation error MUST chặn commit; warning MUST được audit.

### Storage và lịch sử

- `PRD-F06`: Hệ thống MUST hỗ trợ `incremental` và `full_snapshot`.
- `PRD-F07`: Import cùng artifact/config/contract MUST idempotent.
- `PRD-F08`: Hệ thống MUST lưu current state, revision, artifact, attempt, run và presence.
- `PRD-F09`: Hệ thống MUST không xóa record vắng mặt trong incremental.
- `PRD-F10`: Commit MUST atomic và có counters kiểm tra được.

### Dashboard và phân tích

- `PRD-F11`: Người dùng MUST chọn được project, entity, scope và khoảng thời gian.
- `PRD-F12`: Hệ thống MUST cung cấp Tổng quan, Thống kê, So sánh và Audit.
- `PRD-F13`: Hệ thống MUST hỗ trợ ngày/tuần/tháng/quý theo rule tương ứng.
- `PRD-F14`: So sánh MUST giới hạn 2–3 entity cùng project và effective unit.
- `PRD-F15`: Missing MUST không được hiển thị như zero.
- `PRD-F16`: Người dùng MUST tải được normalized CSV theo project.

### Lineage và investigation

- `PRD-F17`: Exact chart point MUST truy về đúng observation, revision, import và cell nguồn.
- `PRD-F18`: Aggregate point MUST giải thích rule, result và contributor.
- `PRD-F19`: Ref cũ MUST tiếp tục resolve đúng snapshot cũ sau import mới.
- `PRD-F20`: Khi không có safe ref, hệ thống MUST từ chối suy đoán nguồn.

### Chức năng chưa triển khai

- `PRD-F101`: Scheduled daily import — **Accepted, not built**.
- `PRD-F102`: AI trend summary — **Accepted, not built**. Contract canonical nằm tại [AI/Data v2](../ai-data/README.md) và [trend analysis](../ai-data/01-ai-trend-analysis.md); comparison/reporting vẫn là proposal riêng.
- `PRD-F201`: Due-date reminder — **Decision needed**.
- `PRD-F202`: Recurrence detection — **Decision needed**.

Chi tiết trạng thái và điều kiện đưa vào scope xem [scope-and-status.md](scope-and-status.md).

## 8. Yêu cầu phi chức năng

| ID | Yêu cầu |
|---|---|
| PRD-N01 | Correctness: baseline và business rule phải được khóa bằng automated test |
| PRD-N02 | Traceability: số liệu chartable phải có lineage an toàn khi contract hỗ trợ |
| PRD-N03 | Recoverability: database phải backup bằng SQLite Online Backup API |
| PRD-N04 | Integrity: migration/import không để lỗi foreign key hoặc partial commit |
| PRD-N05 | Accessibility: điều khiển ứng dụng dùng được bằng bàn phím và chữ chính đạt WCAG AA; chọn điểm Plotly để Điều tra là tương tác con trỏ, không có danh sách điểm bàn phím song song |
| PRD-N06 | Performance: thay filter không dựng lại DOM/chart không cần thiết; request cũ không ghi đè request mới |
| PRD-N07 | Security boundary: mặc định bind localhost và không public khi chưa có auth/HTTPS |
| PRD-N08 | Compatibility: hỗ trợ Python 3.11+ và Node 20.19+/22.12+ theo tài liệu vận hành |

## 9. Business rules trọng yếu

- Không tự cộng node con thành node cha.
- Zero khác missing; ô trống/marker không biến thành zero.
- `% báo sai` theo kỳ là `SUM(Báo sai/Lỗi) / SUM(Tổng số) × 100`.
- Observation key không chứa unit; đổi unit tạo revision.
- Dashboard chỉ đọc committed current state.
- Preview không ghi database.
- Incremental không suy luận deletion.
- Entity hiện chỉ giữ continuity khi external key resolve tới active alias. Workflow xác nhận/tạo alias cho rename/move/manual merge chưa được triển khai và là `SCP-203` Decision needed.

## 10. Chỉ số thành công và baseline

### Baseline có bằng chứng

- 6 project;
- 36 entity;
- 41 ngày từ `2026-08-01`;
- 3 metric;
- 4.182 normalized record;
- 2.343 chartable record;
- 0 quality-gate error trên workbook mẫu.

### Chỉ số vận hành cần owner chốt target

| Chỉ số | Cách đo | Target |
|---|---|---|
| Import success rate | committed / valid attempts | TBD |
| Time-to-dashboard | từ nhận file tới committed dashboard | TBD |
| Manual reconciliation variance | chênh lệch so với báo cáo được duyệt | 0 cho fixture đã chốt |
| Lineage resolution rate | chart points có safe provenance / chart points | TBD |
| User task completion | analyst hoàn tất import/phân tích/audit không cần can thiệp kỹ thuật | TBD |

Không tự đặt target production khi chưa có dữ liệu vận hành hoặc xác nhận của mentor.

## 11. Dependencies và giả định

- Workbook nguồn tuân theo layout/rule đã cấu hình.
- Máy chạy có quyền đọc workbook và ghi `data/`.
- SQLite dùng local filesystem với một writer tại một thời điểm.
- Người vận hành hiểu sự khác nhau giữa incremental và full snapshot.
- Source key được giữ ổn định qua các lần import cùng nguồn.

## 12. Rủi ro

| Rủi ro | Giảm thiểu hiện tại |
|---|---|
| Layout workbook thay đổi | Config-driven parser, validation, smoke fixture |
| Ghi đè bởi workbook cũ | Hash/contract identity và replay protection |
| Số liệu thiếu bị hiểu là zero | Value-kind contract và chart null |
| Không biết nguồn của số | Exact/aggregate lineage và audit lookup |
| SQLite dùng sai môi trường | Localhost/single-writer boundary và backup/integrity scripts |
| Scope issue workflow không rõ | `Decision needed`, không đưa vào acceptance gate |

## 13. Release và nghiệm thu

Một release chỉ được xác nhận khi:

- yêu cầu trong phạm vi có spec và test;
- quality gate tại [acceptance-criteria.md](../quality/acceptance-criteria.md) pass;
- known limitations được ghi nhận;
- workbook/config version và manifest được lưu;
- các mục `Decision needed` không bị quảng bá là đã triển khai.
