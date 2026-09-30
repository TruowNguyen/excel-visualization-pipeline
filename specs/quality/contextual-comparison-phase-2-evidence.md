# Bằng chứng hoàn thành Contextual Comparison Phase 2

- Ngày xác nhận: **2026-09-30**
- Phạm vi: Gate 2.0 và các lát dọc 2.1–2.5
- Kết luận: **GO — Phase 2 đã triển khai; sau kiểm tra tương đương, tab So sánh cũ được ẩn và contract API cũ tiếp tục được giữ**

## 1. Năng lực đã hoàn thành

| Phần | Bằng chứng source | Bằng chứng kiểm thử |
|---|---|---|
| Gate 2.0 — missing/zero | `prepare_period_statistics` nhận dữ liệu kiểm chứng semantic; không suy 0 khi `% báo sai` nguồn dương nhưng thiếu số lỗi | `test_period_statistics_rejects_inferred_zero_when_positive_source_rate_has_no_error_count`; fixture zero, missing, mixed, ký hiệu nguồn và coverage ancestor |
| 2.1 — Tổng đa nội dung | Workspace API nhận lens Thống kê; `build_multi_entity_statistics_chart` áp dụng một cách tính cho cả `Tổng số` và `Báo sai/Lỗi` hiện có | API/chart test + Playwright xác nhận không có bộ chọn chỉ số, đủ hai chuỗi và không render bảng số liệu |
| 2.2 — Trung bình mỗi ngày | API nhận `average_per_day`; frontend vẽ tất cả chuỗi bằng đường nét liền | Chart test + Playwright kiểm tra kiểu đường, đổi phép tính và giữ selection |
| Chuẩn hóa biểu đồ | Chỉ số gốc và Thống kê dùng chung màu entity, cột nhóm cho count/sum, line nét liền 3 px và marker 8 px cho rate/average | Unit test khóa opacity/offset group/line/marker + Playwright kiểm tra trace thực tế |
| 2.3 — Bằng chứng đúng entity | `statistics_comparison` mapper ánh xạ `trace.legendgroup → entity → kỳ` | API resolve từng `aggregateRef` và đối chiếu `context.entity.ref`; fail-closed khi thiếu lineage |
| 2.4 — Điều tra và Audit | Ngăn Điều tra được gắn vào popup; selector thu gọn; phiên popup được giữ khi đi-về Audit | Playwright tại 1366×768 và 1440×900; kiểm tra focus, Escape theo tầng và Audit round-trip |
| 2.5 — tương đương và hồi quy | Builder đa nội dung dùng cùng prepared frame với Statistics | Workbook thật 6 dự án × ngày/tuần/tháng/quý × hai chỉ số × hai phép tính; full backend/frontend regression |

## 2. Contract đã khóa

- `comparison_lens=metric|statistics`, mặc định `metric`.
- `comparison_calculation=sum|average_per_day`, mặc định `sum`.
- Lens Thống kê không có bộ chọn metric; backend trả đồng thời các chuỗi `Tổng số` và `Báo sai/Lỗi` hiện có. `comparison_metric` được bỏ qua trong lens này để tương thích client cũ.
- `comparison`, `comparisonContext`, `comparisonSelection` được giữ; response bổ sung `comparisonTable`.
- `comparisonTable` được giữ để tương thích API nhưng không hiển thị trong popup. Danh sách “Điều tra điểm bằng bàn phím” đã được gỡ; người dùng nhấn trực tiếp điểm/cột trên biểu đồ để mở Điều tra.
- Eligibility do backend quyết định theo same-parent, cùng dự án, cùng đơn vị, phép tính và ít nhất một cặp `(metric, kỳ)` giao nhau.
- Numeric zero là dữ liệu hợp lệ; missing không được biến thành 0 khi tỷ lệ nguồn dương chứng minh có mâu thuẫn.
- `dataVersion.committedImportRef` tiếp tục là public identity; cache key có lens, phép tính và tập ID đã chuẩn hóa.

## 3. Kết quả kiểm thử

| Cổng | Kết quả |
|---|---|
| Backend `pytest -q` | **92/92 đạt** |
| Workbook thật 6 dự án | **Đạt**, không có trường hợp có dữ liệu đủ để dựng chart nhưng chart rỗng; giá trị trace khớp prepared Statistics |
| Contextual Playwright | **14/14 đạt**, gồm hai trạng thái cũ trong phiên không được khôi phục thành tab cấp cao |
| Toàn bộ Playwright | **50/50 đạt** |
| Kiểm tra lại ba luồng Phase 2 sau hardening lifecycle | **3/3 đạt** |
| TypeScript + Vite production build | **Đạt** |
| `git diff --check` | **Đạt**, không có lỗi whitespace |

Các cảnh báo còn lại không phát sinh từ Phase 2: cảnh báo deprecation của `httpx` qua FastAPI TestClient và một cảnh báo pandas trong canonical storage cũ.

## 4. Giới hạn còn giữ nguyên

- Không truy vấn hoặc tính lại workspace theo revision/import lịch sử.
- Điểm tổng hợp không được mô tả là một ô Excel chính xác; người dùng mở contributor rồi mới xem observation cụ thể.
- Không thêm công thức ngoài Tổng trong kỳ và Trung bình mỗi ngày hiện có.
- Không thay storage schema, không migration database, không thêm contributor drilldown mới.
- Tab So sánh cũ đã được ẩn khỏi điều hướng và không còn lối mở từ popup. Contract API cũ vẫn tồn tại để tương thích; không có migration cơ sở dữ liệu.

## 5. Ảnh hưởng tới Thống kê hiện tại

Thay đổi calculation duy nhất là sửa semantics đã xác nhận: nếu một ngày có `% báo sai > 0` nhưng `Báo sai/Lỗi` chưa ghi nhận, kỳ đó không còn được suy thành lỗi bằng 0. Trường hợp `% báo sai = 0` với lỗi trống vẫn được suy 0 khi có ngày coverage hợp lệ; ký hiệu nguồn tiếp tục bị loại khỏi mẫu số ngày. Không có công thức mới được thêm âm thầm.

## 6. Hotfix ánh xạ nhiều kỳ

- Lỗi thực tế: khi một trace Thống kê có từ hai kỳ, Plotly cung cấp `trace.x` dưới dạng mảng NumPy. Biểu thức boolean `trace.x or []` làm API phát sinh `ValueError` và trả lỗi 500.
- Cách sửa: kiểm tra `trace.x is not None` rồi chuyển rõ ràng sang `list`; không thay đổi dữ liệu, công thức hoặc aggregate ref.
- Regression: API fixture dùng hai kỳ ngày trong `test_contextual_comparison_contract_filters_siblings_and_keeps_legacy_api`, vì vậy phiên bản cũ sẽ lỗi ngay tại bước ánh xạ aggregate lineage.
- Kiểm chứng dữ liệu hiện hành: 14 tổ hợp same-parent trên 6 dự án, với cả `sum` và `average_per_day`, đều trả HTTP 200; trường hợp không đủ sibling hợp lệ trả selection/chart rỗng theo contract thay vì lỗi máy chủ.

## 7. Tinh gọn Điều tra điểm

- Đã gỡ hoàn toàn giao diện “Điều tra điểm bằng bàn phím”, module sinh danh sách điểm, registry sự kiện, kiểu dữ liệu và CSS liên quan theo quyết định sản phẩm.
- Điều tra và Đối chiếu vẫn mở từ thao tác nhấn trực tiếp điểm/cột Plotly; popup So sánh vẫn giữ Điều tra nội tuyến và vòng đi-về Đối chiếu.
- Production build đạt; toàn bộ Playwright **50/50 đạt**, gồm assertion giao diện bàn phím không còn được render.
