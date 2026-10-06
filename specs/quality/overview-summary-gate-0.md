# Gate 0 — nguồn dữ liệu cho bốn thẻ Tổng quan

> **Cập nhật sau quyết định nguồn:** người dùng đã duyệt ưu tiên root + nguồn theo dõi riêng có tên/phạm vi. Điểm dừng nguồn dưới đây là lịch sử, đã được giải quyết bằng mapping rõ ràng, không bằng tổng descendants. Calculation/version fixtures bổ sung và kết quả triển khai nằm tại [evidence](overview-summary-metrics-evidence.md); contract hiện hành tại [đặc tả frontend](../frontend/overview-summary-metrics.md).

Ngày kiểm chứng: 05/10/2026. Liên quan: [kế hoạch v1.2](../frontend/overview-summary-metrics-plan.md). Báo cáo giữ bằng chứng ban đầu cho báo sai và bổ sung kiểm chứng sau quyết định đổi sang tổng số.

## Kết luận

**Chưa GO cho triển khai/phát hành đầy đủ bốn thẻ.** Người dùng đã chọn **Tổng số ghi nhận** thay cho báo sai. Numeric cấp dự án theo ngày hiện có ở SmartParking, VOL và VW Vũ Yên, vẫn thiếu ở ANVF, VSO và V-Pet. Cần quyết định cho ba dự án thiếu nguồn; không tự cộng các node con hay đổi phạm vi. Kết quả ban đầu với báo sai (chỉ SmartParking có nguồn) được giữ bên dưới như bằng chứng lịch sử, không phải chỉ số nền đang đề xuất.

Đây là báo cáo kiểm chứng tại điểm dừng nguồn dữ liệu, **không phải tuyên bố đã hoàn tất mọi mục Gate 0**. Chưa có `overviewSummary`, renderer hoặc kiểm thử Playwright của tính năng mới. Các mục version race, hiệu năng range dài và contract integration vẫn phải hoàn tất sau khi chốt nguồn.

## 1. Phương pháp và dữ liệu đã kiểm tra

- Xác nhận cấu hình backend thực tế: database `data/local/analytics.sqlite3`, nguồn `cx_report_master`. Không hiển thị khóa API hay các giá trị bí mật trong `.env`.
- Đọc `v_current_entities` và `v_current_observations` bằng SQLite URI `mode=ro`; inventory chung được đọc trong cùng một transaction. Không gọi import hoặc migration trên database vận hành.
- Current read model tại lần kiểm tra: latest committed run nội bộ **5**, committed at **2026-09-18T08:12:37.883632Z**. Đây là reference kiểm chứng, không phải tham số historical query công khai.
- Kiểm tra toàn bộ **6 dự án / 36 entity**. Không phát hiện ancestry thiếu parent hoặc chu trình trong current entities tại thời điểm kiểm tra.
- Đối chiếu `app/api.py`, `storage/repository.py`, `visualization/charts.py`, `date_ranges.py` và các regression test hiện có.
- Không gọi AI hoặc provider để tính hoặc kiểm chứng số liệu.

## 2. Inventory ban đầu — Tổng báo sai (lỗi)

Số ngày numeric dưới đây đếm đúng metric `Báo sai/Lỗi` tại entity `project`, không tính rate mặc định 0 và không cộng descendants. Khoảng gần đây của cả sáu dự án được `_window(..., mode="recent")` xác định là **07/09/2026–16/09/2026**, bao gồm hai biên.

| Dự án | ID nguồn cấp dự án | Ngày có báo sai numeric toàn current history / khoảng gần đây | Hiện trạng tuần/tháng |
|---|---|---:|---|
| ANVF | `anvf-bb382cac9174` | 0 / 0 | SUM báo sai missing; tổng số cũng không numeric; rate mặc định 0 không tạo số lỗi |
| SmartParking | `smartparking-c67af362b168` | 42 / 8 | Có SUM từ số lỗi nguồn; vẫn có kỳ không hợp lệ theo calculation hiện có |
| V-Pet | `v-pet-46979a8b56f4` | 0 / 0 | Không có observations tại project, không có period summary |
| VOL | `vol-551c256e48f4` | 0 / 0 | Có kỳ suy ra lỗi 0 từ tổng số; không có báo sai nguồn theo ngày |
| VSO | `vso-f7bd47e3a2f8` | 0 / 0 | Không có observations tại project; dữ liệu nằm ở section/item |
| VW Vũ Yên | `vw-vu-yen-77517e69af33` | 0 / 0 | Có kỳ suy ra lỗi 0 từ tổng số; không có báo sai nguồn theo ngày |

VSO có hai nhóm trực tiếp `Chất lượng cảnh báo - ghi nhận trên hệ thống` và `Test thực địa`. Cùng đơn vị không chứng minh hai tập nghiệp vụ độc lập. V-Pet có đơn vị khác nhau như `Lượt (ngày)` và `Lượt (lũy kế)`; không được cộng thành một chuỗi tổng.

**Không kết luận năm dự án thiếu lỗi numeric là không có lỗi trong thực tế.** Không coi zero suy ra ở grain tuần/tháng là zero nguồn tại grain ngày. Một project có nguồn numeric cũng không bảo đảm mọi range/grain đều có kết quả.

Ví dụ SmartParking: summary tháng 08/2026 có error SUM **1460**. Tháng 09/2026 trả missing theo calculation hiện tại khi có tỷ lệ nguồn dương tại ngày thiếu error count; không thay đổi calculation này để ép các thẻ có số.

### 2.1. Kiểm tra lại sau quyết định dùng Tổng số ghi nhận

Đã đọc lại database cấu hình thực tế ở chế độ chỉ đọc. Query lấy đúng `metric_code='total'` tại `entity_level='project'`, group theo source/entity ID; không lấy chart đang chọn hoặc cộng cha/con. Khoảng gần đây vẫn là 07–16/09/2026.

| Dự án | Ngày có tổng số numeric toàn current history / khoảng gần đây | Đơn vị nguồn project | Giới hạn |
|---|---:|---|---|
| ANVF | 0 / 0 | Lượt | Project toàn missing/text; ba item có tổng số numeric nhưng chưa được duyệt cộng thành tổng |
| SmartParking | 43 / 9 | Lượt | Có nguồn tổng; không yêu cầu số báo sai để dùng tổng số |
| V-Pet | 0 / 0 | Chưa xác định | Không có observations project; các item gồm Lượt (ngày), Lượt (lũy kế) và đơn vị chưa xác định |
| VOL | 28 / 9 | Lượt | Có tổng số numeric dù không có số báo sai numeric tại project |
| VSO | 0 / 0 | Cảnh báo | Tổng số ở section; không tự chọn nhóm 1.1 làm tổng VSO hoặc cộng hai nhóm |
| VW Vũ Yên | 29 / 9 | Cảnh báo | Có tổng số numeric dù không có số báo sai numeric tại project |

Độ phủ nguồn project tăng **1/6 → 3/6** khi đổi từ báo sai sang tổng số. Việc đổi metric không giải quyết việc project thiếu quan sát hoặc thiếu hợp đồng tổng hợp. Không cộng số lũy kế và số phát sinh; không tự tính hiệu snapshot lũy kế để tạo series mới.

Các thẻ đề xuất đổi thành **Vấn đề có dữ liệu / Ghi nhận cao nhất / Ghi nhận thấp nhất / Thay đổi lớn nhất**, có ngữ cảnh chung **Tổng số ghi nhận**. Source metric key vẫn là `Tổng số`, không rename dữ liệu/database. Issue count giữ định nghĩa riêng trên ba metric nguồn hợp lệ.

Chưa thêm source resolver hoặc phép tính thẻ; chưa chạy bộ test tính năng tổng số mới vì nó chưa được cài đặt. Kết quả 56 tests tại mục 6 thuộc lần kiểm chứng calculation hiện có trước quyết định đổi metric, không phải nghiệm thu cho thay đổi mới.

## 3. Nguồn đếm vấn đề khả thi

Audit thử quy tắc đếm distinct item trong kế hoạch: chỉ finite numeric/percentage/percentage_text của ba metric chính; bỏ `default_zero_rate`, marker/text/missing. Quan sát subitem ánh xạ về item sở hữu bằng parent ID; project/section không được tính. Không đếm `None`/NaN của mapping như một vấn đề.

Current read model chỉ có validation status `valid` và `warning`; không có rejected/error để kết luận toàn bộ quality eligibility cho dữ liệu tương lai. Production contract vẫn cần khóa cách loại các trạng thái quality không hợp lệ và fixture riêng.

| Dự án | Vấn đề có dữ liệu toàn current history | Trong 07–16/09/2026 |
|---|---:|---:|
| ANVF | 3 | 3 |
| SmartParking | 5 | 5 |
| V-Pet | 3 | 3 |
| VOL | 2 | 2 |
| VSO | 9 | 7 |
| VW Vũ Yên | 4 | 4 |

Đây là **kết quả audit chỉ đọc**, chưa phải response hoặc tính năng đã cài đặt. VSO giảm từ 9 xuống 7 cho thấy số trong khoảng không phải metadata toàn bộ project đổi nhãn. Không thay bốn thẻ bằng một thẻ hoàn thành và ba placeholder khi chưa có quyết định phát hành.

## 4. Calculation đã kiểm chứng

Fixture mới: [`test_overview_summary_gate_0.py`](../../tests/test_overview_summary_gate_0.py), 14 trường hợp tham số hóa cho week/month. Chúng kiểm chứng hàm hiện có `prepare_period_metric_summary`, không tạo công thức mới:

- Toàn missing + rate mặc định 0: error SUM vẫn missing.
- Numeric error 0: giữ 0 nguồn; `rate_calculation_source` không phải inferred zero.
- Blank error + numeric total + rate 0: grouped error có thể suy ra 0; raw daily error vẫn missing.
- Source marker: không suy ra 0.
- Tỷ lệ nguồn dương nhưng thiếu số lỗi: grouped error không hợp lệ.
- Root không có quan sát: số của child không tự tạo project summary, kể cả truyền coverage data.
- Mixed numeric và missing: SUM giữ giá trị numeric; không biến missing thành quan sát 0.

Đây là khác biệt grain có chủ đích trong implementation hiện tại, không xác nhận lỗi semantics cần sửa. Không sửa SUM, AVG/ngày, weighted rate, AI hoặc parser trong lượt này. Chính sách cặp lịch liền nhau và boundary completeness của thẻ thay đổi lớn nhất chưa được cài đặt/kiểm thử.

## 5. Version và cache — điểm chưa đóng

`_load_source_snapshot` dùng committed run làm cache key nhưng đọc current views; bỏ tham số revision trong thân hàm. `load_current_data` và `load_current_entities` mở các lần đọc riêng; route workspace đọc committed version trước `_project`, trong khi `_source` lại đọc version riêng.

Đây là **rủi ro read/version race xác định từ source**, chưa được tái hiện bằng concurrent fixture ở lượt này. Không được tuyên bố version coherence đã qua gate. Sau khi chọn nguồn cần transaction snapshot nhất quán hoặc bounded recheck/retry và regression chứng minh dữ liệu/chart/thẻ không bị gắn nhầm version. Backend hiện không cung cấp historical workspace calculation qua tham số public revision.

Không đổi public `dataVersion`; đề xuất dùng chung `workspace.dataVersion` và field summary additive vẫn giữ trong bản plan, chưa phải API đã triển khai.

## 6. Kiểm thử và thay đổi thực hiện

Đã chạy:

```text
python -m pytest tests/test_overview_summary_gate_0.py tests/test_charts.py tests/test_date_ranges.py tests/test_api.py
56 passed, 19 warnings in 13.73s
```

Warnings là deprecation FastAPI/asyncio hiện có. Phạm vi kết quả này là fixture Gate 0 và hồi quy backend liên quan, không phải toàn bộ project hoặc nghiệm thu giao diện mới.

Thay đổi trong lượt này:

- Thêm file fixture kiểm chứng Gate 0; không thay expected của test hiện có.
- Thêm báo cáo này, cập nhật trạng thái plan/index để không báo đã triển khai.
- Không sửa source ứng dụng, API, frontend, database, storage schema hoặc cấu hình AI trong lượt này. Các thay đổi đã tồn tại trong worktree từ trước được giữ nguyên.

## 7. Quyết định cần người dùng

1. **Giữ toàn dự án:** dùng Tổng số ghi nhận, chấp nhận ba thẻ thiếu dữ liệu ở ANVF/VSO/V-Pet và các range không có nguồn. Tổng số missing không được suy ra zero theo quy tắc của báo sai. Đây là quyết định chấp nhận giá trị sử dụng hạn chế, cần duyệt rõ.
2. **Đổi phạm vi ba thẻ diễn biến:** đếm vấn đề vẫn toàn dự án, đỉnh/đáy/thay đổi dựa trên nội dung đang chọn, ghi rõ phạm vi và nguồn. Cần cập nhật plan/contract vì không còn là ba chỉ số tổng của toàn dự án.
3. **Cung cấp nguồn tổng hợp nghiệp vụ:** người dùng xác nhận mapping nguồn/các tập không trùng và đơn vị tương thích. Không tự cộng mọi node hoặc mọi sheet.

Sau quyết định: hoàn tất Gate 0 còn lại rồi tiếp tục các lát backend → validation → frontend → testing theo thứ tự. **Chưa GO cho Phase 2–4; Phase 1 có nguồn đếm khả thi nhưng chưa triển khai hay nghiệm thu.**
