# Contextual Comparison — shape và contract đã khóa sau Gate 0

- Trạng thái: **Vertical Slice 1 đã triển khai và xác minh**
- Gate 0 hoàn thành: **2026-09-28**
- Vertical Slice 1 rà soát lại: **2026-09-29**
- Phạm vi: Contextual Comparison được mở từ chart node con trong tab Thống kê.
- Phase 2 Thống kê đa nội dung: **đã triển khai và đạt hồi quy** tại [contextual-comparison-phase-2.md](contextual-comparison-phase-2.md).

## 1. Ranh giới

- Entry point chỉ thuộc child chart trực tiếp.
- Large modal, anchor chọn sẵn, tối đa ba entity.
- Candidate phải là true sibling: cùng project và cùng non-null `parent_entity_id` với anchor.
- Chỉ số rõ ràng được kế thừa. Nếu chart có nhiều chuỗi, hệ thống chọn sẵn chỉ số So sánh dùng gần nhất; mặc định an toàn là `Báo sai/Lỗi`. Người dùng vẫn có thể đổi chỉ số mà không phải chọn lại các sibling còn hợp lệ.
- Kế thừa grain, range, include-incomplete và effective unit đã xác định.
- Kiểm tra tương đương đã hoàn tất trong Phase 2; tab So sánh cũ đã được ẩn khỏi điều hướng cấp cao. Contract API cũ vẫn được giữ để tương thích.
- Gate 0 không triển khai CTA, dialog, candidate API hoặc migration tab.

## 2. Contract hierarchy

True sibling được định nghĩa:

```text
candidate.project_id == anchor.project_id
candidate.parent_entity_id == anchor.parent_entity_id
candidate.entity_id != anchor.entity_id
anchor.parent_entity_id IS NOT NULL
```

Equal depth không đủ. `candidate.parent_entity_id == anchor.entity_id` là child của anchor, không phải sibling. Root không có parent không được gom chung chỉ vì cùng `NULL` parent.

## 3. Contract calculation đã khóa

### Statistics

- `SUM`: tổng numeric contributor trong kỳ.
- `Tổng số` toàn missing/source marker: `SUM = missing`, `AVG/ngày = missing`.
- `Báo sai/Lỗi` toàn blank `not_recorded`: chỉ suy ra `SUM = 0` khi có coverage `Tổng số` hợp lệ; metadata `inferred_zero=true` phân biệt với numeric zero.
- `Báo sai/Lỗi` toàn source marker: giữ missing.
- Numeric zero là giá trị hợp lệ, `numeric_value_count > 0`, `inferred_zero=false`.
- `AVG/ngày = period_sum / eligible_day_count` khi SUM tồn tại và `eligible_day_count > 0`.
- Eligible day dựa trên ngày có `Tổng số` numeric tại entity hoặc ancestor coverage; ngày source marker của metric đang tính bị loại.
- Khi coverage của `Tổng số` kế thừa ancestor, `Tổng số · AVG/ngày` vẫn missing.
- Kỳ biên chưa đầy đủ dùng boundary đã clip và số ngày eligible thực tế.

### Original metrics

| Grain | As-built |
|---|---|
| Daily raw | Có; exact observation, missing không tạo point |
| Week | Có; period sum/weighted rate |
| Month | Có; period sum/weighted rate |
| Quarter | Có; dùng cùng period sum/weighted rate như week/month |

`% báo sai` theo kỳ dùng `SUM(Báo sai/Lỗi) / SUM(Tổng số) × 100`; không lấy trung bình tỷ lệ từng ngày và không suy ngược số lỗi từ tỷ lệ nguồn đã làm tròn. Khi node con chỉ có `Báo sai/Lỗi`, mẫu số được lấy từ node gần nhất trong chuỗi tổ tiên có `Tổng số` numeric và cùng đơn vị. Giá trị `Tổng số` của node con vẫn là thiếu; backend chỉ lưu riêng `rate_denominator_sum`, `rate_denominator_source_entity_id` và `inherits_rate_denominator` trong dữ liệu tổng hợp để không biến dữ liệu kế thừa thành quan sát trực tiếp. Nếu một kỳ có `% báo sai > 0` nhưng thiếu `Báo sai/Lỗi`, tỷ lệ theo kỳ là không khả dụng với lý do `RATE_NUMERATOR_MISSING`; dữ liệu tỷ lệ theo ngày vẫn được giữ nguyên. Tooltip tỷ lệ hiển thị mẫu số thực tế đã dùng. Dữ liệu ngày và Thống kê theo ngày có cùng biên ngày nhưng khác quy tắc hợp lệ: Thống kê chỉ có thể suy ra lỗi trống bằng 0 khi không có tỷ lệ nguồn dương mâu thuẫn, còn dữ liệu gốc không biến null thành điểm dữ liệu chính xác.

## 4. Public data version

Workspace response có additive field:

```json
{
  "dataVersion": {
    "committedImportRef": "imp_opaque",
    "committedAt": "ISO-8601"
  }
}
```

- Internal current revision/cache identity là `run_id`.
- Public chart data version là opaque `committedImportRef`.
- Popup snapshot là payload đã nhận cùng `committedImportRef`.
- Import commit mới tạo `committedImportRef` mới.

Backend hiện chỉ dựng workspace từ current view. Không có query `as_of`, `revision` hoặc `importRef` cho chart calculation. Vì vậy “Tiếp tục xem snapshot này” chỉ được giữ payload đã tải trong memory và không được đổi metric/range/recalculate. Reload, mất session payload hoặc yêu cầu calculation khác phải chuyển sang current revision. Exact lineage ref cũ và aggregate snapshot ref cũ vẫn resolve được bất biến.

## 5. Lineage boundary

- Daily original count point có thể dùng exact `observationRef + lineageRef`.
- Grouped và Statistics point là aggregate.
- Aggregate registry/provenance hiện tại được tái sử dụng.
- Mapper `attach_aggregate_lineage(kind="statistics")` tiếp tục chỉ nhận một entity và fail closed với multi-entity input.
- Phase 2 đã bổ sung mapper `kind="statistics_comparison"`, ánh xạ trace → entity bằng `legendgroup` và có regression chống gắn nhầm nguồn.
- Không thêm storage schema và không hứa exact Excel-cell lineage cho aggregate.
- Phase 2 chỉ tái sử dụng contributor hiện có, không thêm drilldown hoặc storage mới.

## 6. Điều chỉnh so với shape ban đầu

1. “Tiếp tục xem snapshot này” không phải historical calculation mode; nó chỉ giữ chart payload đã tải.
2. Statistics zero suy ra phải mang `inferred_zero`, không được đồng nhất với numeric zero.
3. Original quarter đã được bổ sung trong Slice 1 bằng đúng period-sum/weighted-rate semantics hiện có, không thêm công thức mới.
4. Aggregate lineage cho Statistics đa entity chỉ dùng mapper riêng của Phase 2; không nới mapper đơn nội dung.

## 7. Gate cho Vertical Slice 1

**COMPLETED**, với phạm vi Vertical Slice 1:

- dùng helper same-parent đã khóa;
- dùng `dataVersion.committedImportRef` làm public snapshot identity;
- không quảng bá historical recalculation;
- quarter support dùng cùng period-sum/weighted-rate semantics hiện có;
- giữ contract API So sánh cũ tương thích ngược trong giai đoạn chuyển tiếp.

## 8. As-built Vertical Slice 1

- CTA **So sánh** chỉ xuất hiện trên chart Statistics của `scope=children`; nút gọn, không thay đổi card Overview.
- Large modal dùng anchor cố định và tối đa ba entity tổng cộng.
- Khi chart có nhiều chỉ số/chuỗi, popup chọn sẵn chỉ số So sánh dùng gần nhất hoặc `Báo sai/Lỗi`; mức thời gian, phạm vi, quy tắc kỳ chưa đầy đủ và đơn vị không bị hỏi lại.
- Backend trả điều kiện hợp lệ theo chỉ số và phép tính, phân biệt số 0 với dữ liệu thiếu, và loại lựa chọn không hợp lệ kèm mã lý do. Khi đổi chỉ số, các lựa chọn vẫn hợp lệ được giữ nguyên.
- `% báo sai` của node con theo tuần/tháng/quý dùng mẫu số `Tổng số` từ tổ tiên gần nhất cùng đơn vị khi node con không có mẫu số riêng; provenance tổng hợp ghi cả tử số node con và mẫu số tổ tiên.
- Request contextual có `AbortController` riêng; response cũ không thể ghi đè request mới.
- `dataVersion` khác snapshot chart nguồn chuyển modal sang trạng thái stale; không cho tính tiếp trên revision cũ. Người dùng chỉ có thể cập nhật current workspace hoặc đóng popup.
- Popup không mở Investigation và không triển khai multi-entity Statistics lineage trong Slice 1.
- Tab So sánh cũ không còn xuất hiện trong điều hướng và không còn lối mở từ popup; contract backend khi không có `comparison_anchor` vẫn được giữ để tương thích.

Bằng chứng triển khai và lệnh kiểm thử nằm tại [contextual-comparison-vs1-evidence.md](../quality/contextual-comparison-vs1-evidence.md).
