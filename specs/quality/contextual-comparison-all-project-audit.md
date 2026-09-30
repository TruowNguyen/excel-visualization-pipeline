# Đối chiếu So sánh theo ngữ cảnh trên toàn bộ dự án

- Ngày đối chiếu: **2026-09-29**
- Nguồn: cơ sở dữ liệu hiện hành `data/local/analytics.sqlite3`
- Phạm vi: **6 dự án, 36 nội dung, 7 nhóm cùng cấp, 360 tổ hợp nội dung gốc/chỉ số/mức thời gian**
- Mức thời gian: ngày, tuần, tháng, quý
- Chỉ số: `Tổng số`, `Báo sai/Lỗi`, `% báo sai`

## 1. Kết quả tổng quát

- Không phát hiện phép tính nào sai công thức `SUM(Báo sai/Lỗi) / SUM(Tổng số) × 100` trong các kỳ có đủ tử số và mẫu số.
- Không phát hiện trường hợp node con kế thừa mẫu số nhưng bị gán giả `Tổng số` trực tiếp.
- Mọi tổ hợp được backend đánh dấu hợp lệ đều dựng được biểu đồ; không có trường hợp “hợp lệ nhưng chart rỗng”.
- Phát hiện và sửa một lỗi dùng chung: kỳ có tỷ lệ nguồn dương nhưng thiếu `Báo sai/Lỗi` từng bị suy thành `0%`. Sau sửa, kỳ đó không khả dụng và trả lý do `RATE_NUMERATOR_MISSING`.
- Không suy ngược số lỗi từ tỷ lệ nguồn vì tỷ lệ đã được làm tròn; dữ liệu ngày vẫn giữ nguyên và xem được.

## 2. Kết quả theo dự án

| Dự án | Kết quả có thể so sánh | Giới hạn do dữ liệu nguồn |
|---|---|---|
| ANVF | `Tổng số` đủ ngày/tuần/tháng/quý; `% báo sai` theo ngày đủ; hai nội dung cùng cấp có tỷ lệ tổng hợp hợp lệ | `Điểm danh xe ghép` có tỷ lệ dương nhưng thiếu `Báo sai/Lỗi`, nên tỷ lệ tuần/tháng/quý bị loại có giải thích |
| SmartParking | Năm node con so sánh được `Báo sai/Lỗi` và `% báo sai` ở cả bốn mức thời gian; mẫu số kế thừa đúng từ node cha | Node con không có `Tổng số` trực tiếp nên không so sánh chỉ số này |
| V-Pet | Dữ liệu từng nội dung vẫn hiển thị theo hợp đồng đã khóa | Các nội dung cùng cấp khác đơn vị (`Lượt (ngày)`, `Lượt (lũy kế)`) và một nội dung chưa có đơn vị; hiện không có cặp hợp lệ để tạo biểu đồ so sánh |
| VOL | `Tổng số` đủ bốn mức; `% báo sai` xem được theo ngày/tuần/tháng | Quý hiện không có đủ hai sibling cùng có tử số hợp lệ; không tạo biểu đồ thay vì suy đoán |
| VSO | 11 nội dung gốc có `Báo sai/Lỗi` và `% báo sai` hợp lệ ở ngày/tuần/tháng/quý; 9 node con kế thừa mẫu số đúng | `Tổng số` chủ yếu nằm ở node cấp trên nên các vấn đề con không được coi là có Tổng số trực tiếp |
| VW Vũ Yên | `Tổng số` đủ bốn mức; `% báo sai` theo ngày đủ | Ba node có tỷ lệ nguồn dương nhưng thiếu `Báo sai/Lỗi`; tỷ lệ tuần/tháng/quý bị loại với `RATE_NUMERATOR_MISSING` |

## 3. Quyết định dữ liệu

1. Ưu tiên `Báo sai/Lỗi` numeric làm tử số chính xác.
2. Có thể kế thừa `Tổng số` từ tổ tiên gần nhất cùng đơn vị làm mẫu số.
3. Chỉ suy lỗi trống bằng 0 khi không có tỷ lệ nguồn dương mâu thuẫn.
4. Không dùng tỷ lệ nguồn đã làm tròn để dựng lại số lỗi.
5. Nếu thiếu tử số nhưng tỷ lệ nguồn dương, dữ liệu ngày vẫn dùng được; tổng hợp tuần/tháng/quý trả không khả dụng.

## 4. Bằng chứng tự động

- `tests/test_charts.py::test_grouped_error_rate_inherits_nearest_parent_total_without_filling_child_total`
- `tests/test_charts.py::test_grouped_rate_does_not_infer_zero_when_positive_source_rate_has_no_error_count`
- `tests/test_charts.py::test_grouped_rate_still_infers_zero_when_source_rate_is_explicit_zero`
- `tests/test_api.py::test_contextual_comparison_contract_filters_siblings_and_keeps_legacy_api`
- `frontend/e2e/contextual-comparison.spec.ts::grouped percentage explains when the source rate has no exact numerator`

## 5. Kết luận

Logic dùng chung đã được kiểm tra trên toàn bộ dữ liệu hiện hành, không gắn riêng với VSO. Những trường hợp chưa dựng được biểu đồ là giới hạn có thể giải thích từ dữ liệu nguồn hoặc đơn vị, không phải lỗi rơi dữ liệu hay lỗi chọn nội dung cùng cấp.
