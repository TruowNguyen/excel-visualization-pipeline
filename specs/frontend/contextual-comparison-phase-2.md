# Contextual Comparison — đặc tả Phase 2: Thống kê đa nội dung

- Trạng thái: **Đã triển khai và đạt cổng hồi quy — 2026-09-30**
- Ngày lập kế hoạch: **2026-09-29**
- Điều kiện đầu vào: Phase 1 đã hoàn thành; kiểm tra toàn bộ 6 dự án đã đạt.
- Chế độ sử dụng: vận hành nội bộ trên web.
- Chủ sở hữu phạm vi: popup So sánh mở từ biểu đồ node con trực tiếp trong tab Thống kê.

> Hệ thống hiện đã có Thống kê đa nội dung và Điều tra trong popup. Giới hạn truy vấn lại workspace theo revision lịch sử vẫn giữ nguyên.

## 1. Mục tiêu và kết quả cần đạt

Phase 2 bổ sung một chế độ **Thống kê** vào popup So sánh hiện tại để người dùng trả lời:

- Trong cùng một kỳ, nội dung nào có tổng giá trị cao hơn hoặc thấp hơn?
- Khi chuẩn hóa theo số ngày có dữ liệu, nội dung nào có trung bình mỗi ngày cao hơn hoặc thấp hơn?
- Kết quả được tính từ những ngày nào, có kế thừa ngày quan sát từ nội dung cấp trên hay không?
- Có thể mở bằng chứng tổng hợp của đúng nội dung và đúng điểm biểu đồ hay không?

Kết quả thành công là người dùng có thể chọn 2–3 nội dung cùng cấp, chuyển giữa **Chỉ số gốc** và **Thống kê**, xem một phép tính nhất quán, mở bằng chứng của một điểm và quay lại biểu đồ mà không mất ngữ cảnh.

## 2. Phạm vi tính năng

### 2.1. Giữ nguyên từ Phase 1

- Điểm mở chỉ nằm trên biểu đồ node con trực tiếp trong tab Thống kê.
- Popup lớn, nội dung gốc được khóa, tối đa ba nội dung tính cả nội dung gốc.
- Chỉ so sánh các nội dung cùng dự án, cùng `parent_entity_id` khác rỗng và cùng đơn vị.
- Backend là nguồn quyết định điều kiện hợp lệ.
- Giữ lựa chọn còn hợp lệ khi đổi chế độ, chỉ số, phép tính hoặc phạm vi.
- Dùng `dataVersion.committedImportRef` để ngăn trộn hai phiên bản dữ liệu.
- Phản hồi cũ không được ghi đè phản hồi mới.
- Giữ mục So sánh cũ trong lúc triển khai cho đến khi hoàn thành kiểm tra tương đương.

### 2.2. Năng lực mới của Phase 2

1. Hai chế độ trong cùng popup:
   - **Chỉ số gốc:** `Tổng số`, `Báo sai/Lỗi`, `% báo sai`; đây là Phase 1.
   - **Thống kê:** một phép tính thống kê áp dụng đồng thời cho hai chuỗi kết quả `Tổng số` và `Báo sai/Lỗi`; người dùng không chọn metric trong chế độ này.
2. Chuỗi kết quả của chế độ Thống kê:
   - `Tổng số`, khi entity có giá trị trực tiếp;
   - `Báo sai/Lỗi`, khi có kết quả theo contract missing/zero hiện hành.
3. Phép tính duy nhất người dùng chọn:
   - `Tổng trong kỳ`;
   - `Trung bình mỗi ngày có dữ liệu`.
4. Biểu đồ đa nội dung với tối đa ba entity và hai chuỗi thống kê trên mỗi entity, dùng cùng ngôn ngữ hình ảnh với Chỉ số gốc: màu nhận diện entity; giá trị đếm/tổng dùng cột nhóm; tỷ lệ/trung bình dùng đường liền rộng 3 px và marker 8 px. Trong lens Thống kê, marker/độ trong phân biệt hai chuỗi kết quả.
5. Không hiển thị bảng số liệu hoặc danh sách điểm điều tra bằng bàn phím trong popup. Người dùng nhấn trực tiếp điểm/cột trên biểu đồ để mở Điều tra.
6. Điều tra điểm tổng hợp ngay trong popup, không mở ngăn kéo toàn cục đè lên popup.
7. Điều chỉnh phạm vi bằng các điều khiển đã có của Thống kê; không tạo hệ quy tắc thời gian thứ hai.

### 2.3. Không thuộc Phase 2

- Không suy ngược `Báo sai/Lỗi` từ tỷ lệ nguồn đã làm tròn.
- Không thêm công thức thống kê mới ngoài `period_sum` và `average_per_day` hiện có.
- Không so sánh khác dự án, khác cha hoặc khác đơn vị.
- Không hứa truy vết chính xác một ô Excel cho điểm tổng hợp.
- Không xây màn hình phân rã contributor mới; chỉ dùng provenance và danh sách thành phần hiện có.
- Không thêm bảng hoặc migration cơ sở dữ liệu.
- Không tính lại workspace theo `importRef` lịch sử.
- Việc ẩn mục So sánh cũ khỏi điều hướng được thực hiện sau khi Phase 2 hoàn thành kiểm tra tương đương; contract API cũ không bị xóa.
- Không tích hợp AI Insights vào popup trong Phase 2.

### 2.4. Trạng thái source sau triển khai

| Thành phần | Hiện trạng đã xác minh | Quyết định triển khai |
|---|---|---|
| `prepare_period_statistics` | Tổng và Trung bình mỗi ngày dùng đúng missing/zero, ký hiệu nguồn và coverage ancestor | Nhận thêm dữ liệu kiểm chứng semantic; tỷ lệ nguồn dương nhưng thiếu lỗi không còn bị suy thành 0 |
| Builder biểu đồ | Có builder đơn nội dung và `build_multi_entity_statistics_chart` | Một phép tính, đồng thời tối đa hai chuỗi kết quả cho mỗi entity, tối đa ba entity |
| Workspace API | Nhận `comparison_lens=metric|statistics` và `comparison_calculation=sum|average_per_day` | Bổ sung tương thích ngược; mặc định vẫn là Chỉ số gốc |
| Eligibility | Backend đánh giá theo phép tính, các cặp `(metric, kỳ)` chung, đơn vị và same-parent | Entity hợp lệ khi có ít nhất một chuỗi kết quả giao nhau; zero hợp lệ, missing không tạo điểm |
| Aggregate lineage | Mapper đa nội dung dùng `legendgroup → entity → kỳ` | Mỗi điểm có aggregate ref đúng entity; không đổi schema |
| Popup | Có hai chế độ và biểu đồ so sánh; không hiển thị bảng số liệu hoặc danh sách điểm bàn phím | Điều tra được gắn trong popup; selector thu gọn khi mở |
| Audit round-trip | Giữ phiên popup, lựa chọn và Điều tra khi đi-về Audit | Không hứa tái tính revision lịch sử |

Do khoảng trống đầu tiên ảnh hưởng trực tiếp tính đúng, Phase 2 bắt buộc có Gate 2.0 trước khi triển khai giao diện.

## 3. Kiến trúc trải nghiệm cuối

### 3.1. Cấu trúc popup

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ So sánh trong cùng nhóm                                      [Đóng]        │
│ Nội dung gốc · Mức thời gian · Phạm vi · Phiên bản dữ liệu                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Chỉ số gốc] [Thống kê]                                                     │
├──────────────────────┬──────────────────────────────────────────────────────┤
│ Nội dung đã chọn 2/3 │ Phép tính: [Tổng trong kỳ | Trung bình mỗi ngày]    │
│ ☑ Nội dung gốc       │ Kết quả: Tổng số + Báo sai/Lỗi (tự động)           │
│ ☑ Nội dung B         │ Phạm vi: [Theo tab Thống kê ▼]                      │
│ ☐ Nội dung C         ├──────────────────────────────────────────────────────┤
│                      │                                                      │
│ Điều kiện và lý do   │              BIỂU ĐỒ SO SÁNH                        │
│ nếu không hợp lệ     │              tối thiểu 640 × 340                    │
│                      │                                                      │
│                      ├──────────────────────────────────────────────────────┤
├──────────────────────┴──────────────────────────────────────────────────────┤
│ Phiên bản dữ liệu                                           [Xong]        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1.1. Ngôn ngữ biểu đồ thống nhất

- Cùng một entity giữ cùng màu ở cả Chỉ số gốc và Thống kê.
- `Tổng số`, `Báo sai/Lỗi` gốc và `Tổng trong kỳ` dùng cột nhóm; không dùng lại kiểu cột lồng có độ rộng riêng.
- `% báo sai` và `Trung bình mỗi ngày` dùng đường nét liền, rộng 3 px, marker 8 px.
- Chỉ số gốc dùng marker tròn. Thống kê dùng tròn cho `Tổng số`, hình thoi cho `Báo sai/Lỗi` để phân biệt mà không đổi màu entity.
- Legend, unified hover, khoảng cách cột, trục và quy tắc màu dùng chung; khác biệt chỉ phản ánh semantics dữ liệu.

### 3.2. Khi mở Điều tra

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ So sánh trong cùng nhóm                                      [Đóng]        │
├──────┬──────────────────────────────────────┬───────────────────────────────┤
│ Chọn │ Biểu đồ tối thiểu 600 × 300          │ Điều tra điểm đã chọn         │
│ 2/3  │                                      │ - Kết quả                     │
│      │                                      │ - Quy tắc tính                │
│      │                                      │ - Ngày đủ điều kiện           │
│      │                                      │ - Thành phần dữ liệu hiện có  │
│      │                                      │ - Mở trong Audit              │
├──────┴──────────────────────────────────────┴───────────────────────────────┤
│ [Đóng Điều tra]                                                [Xong]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

- Danh sách sibling được thu gọn thành thanh tóm tắt khi Điều tra mở.
- Điều tra là vùng con của popup, không dùng ngăn kéo toàn cục.
- Tại 1366×768, biểu đồ không thấp hơn 300 px khi Điều tra mở và 340 px khi đóng.
- Tại 1440×900, biểu đồ và Điều tra hiển thị song song.
- Nếu chiều rộng hữu dụng dưới 1200 px, Điều tra chuyển xuống dưới biểu đồ; footer vẫn nằm trong vùng cuộn của popup.

## 4. Quy tắc tính và điều kiện hợp lệ

### 4.1. Công thức được tái sử dụng

| Phép tính | Công thức | Điều kiện |
|---|---|---|
| Tổng trong kỳ | `period_sum = SUM(numeric values)` | Có ít nhất một giá trị số hoặc lỗi trống được suy 0 theo contract hiện tại |
| Trung bình mỗi ngày | `average_per_day = period_sum / eligible_day_count` | `period_sum` tồn tại và `eligible_day_count > 0` |

Không dùng số ngày lịch làm mẫu số. `eligible_day_count` tiếp tục dựa trên ngày có `Tổng số` hợp lệ tại chính nội dung hoặc tổ tiên gần nhất cùng đơn vị, loại ngày có ký hiệu nguồn của chỉ số đang tính.

### 4.2. Quy tắc theo chỉ số

#### `Tổng số`

- `Tổng trong kỳ` chỉ hợp lệ khi nội dung có `Tổng số` trực tiếp.
- `Trung bình mỗi ngày` chỉ hợp lệ khi nội dung có `Tổng số` trực tiếp và có ngày đủ điều kiện.
- Không biến coverage kế thừa thành giá trị `Tổng số` của node con.

#### `Báo sai/Lỗi`

- `Tổng trong kỳ` dùng tổng các giá trị số.
- Lỗi trống chỉ được suy 0 khi có coverage hợp lệ và không có tỷ lệ nguồn dương mâu thuẫn.
- `Trung bình mỗi ngày` dùng cùng `period_sum` chia số ngày đủ điều kiện.
- Ký hiệu nguồn làm kỳ không đủ dữ liệu theo contract hiện hành; không tự đổi thành 0.

### 4.3. Điều kiện của candidate

Một candidate hợp lệ khi đồng thời:

1. là sibling thực của nội dung gốc;
2. thuộc cùng dự án;
3. có cùng đơn vị đã xác định;
4. có ít nhất một cặp `(chỉ số, kỳ)` giao nhau với nội dung gốc cho phép tính đang chọn;
5. không vi phạm quy tắc missing/zero/coverage.

Backend trả mã lý do cụ thể:

- tái sử dụng: `UNIT_UNKNOWN`, `UNIT_MISMATCH`, `NO_OVERLAPPING_PERIOD`, `NOT_SIBLING`, `LIMIT_REACHED`;
- bổ sung dự kiến:
  - `STATISTIC_VALUE_MISSING`: không có kết quả cho chỉ số và phép tính;
  - `NO_ELIGIBLE_DAYS`: có tổng nhưng không có ngày đủ điều kiện cho trung bình;
  - `DIRECT_TOTAL_REQUIRED`: node chỉ có coverage kế thừa, không có `Tổng số` trực tiếp.

`RATE_NUMERATOR_MISSING` chỉ thuộc chế độ Chỉ số gốc với `% báo sai`; không dùng cho chế độ Thống kê.

### 4.4. Hành vi theo dữ liệu thực tế

- **SmartParking:** Thống kê `Báo sai/Lỗi` của các node con dùng ngày coverage kế thừa từ node cha.
- **VSO:** các vấn đề con có thể so sánh Tổng và Trung bình mỗi ngày của `Báo sai/Lỗi`; không được coi là có `Tổng số` trực tiếp.
- **V-Pet:** candidate khác đơn vị hoặc chưa có đơn vị tiếp tục bị loại có giải thích.
- **ANVF, VOL, VW Vũ Yên:** các phép tính thiếu chỉ số phải hiển thị trạng thái không đủ dữ liệu; không suy đoán để tạo biểu đồ.

## 5. Hợp đồng API dự kiến

### 5.1. Yêu cầu bổ sung, tương thích ngược

Endpoint vẫn là:

```text
GET /api/projects/{project}/workspace
```

Tham số hiện có được giữ nguyên. Phase 2 mở rộng:

```text
view=comparison
comparison_anchor=<entity_id>
comparison_entities=<anchor,sibling...>
comparison_lens=statistics
comparison_calculation=<sum|average_per_day>
statistics_group=<day|week|month|quarter>
statistics_count=<n>
statistics_from=<date>
statistics_to=<date>
include_incomplete=<true|false>
```

- `comparison_lens` mặc định `metric` để client Phase 1 không đổi hành vi.
- `comparison_calculation` chỉ được dùng khi `comparison_lens=statistics`.
- `comparison_metric` tiếp tục được chấp nhận để tương thích client cũ nhưng bị bỏ qua khi `comparison_lens=statistics`; ở chế độ này backend luôn tính hai chuỗi đếm hiện có.
- ID được chuẩn hóa và giới hạn ba nội dung trước khi dựng cache key.

### 5.2. Phản hồi bổ sung

```json
{
  "comparisonContext": {
    "lens": "statistics",
    "anchor": {
      "entityId": "opaque",
      "parentEntityId": "opaque",
      "effectiveUnit": "Cảnh báo"
    },
    "metric": null,
    "metrics": ["Tổng số", "Báo sai/Lỗi"],
    "calculation": "average_per_day",
    "grain": "week",
    "range": {"start": "2026-08-01", "end": "2026-09-16"},
    "coveragePolicy": "nearest_ancestor_total"
  },
  "comparisonSelection": {
    "accepted": ["anchor", "sibling"],
    "removed": [],
    "limit": 3
  },
  "comparisonCandidates": [],
  "comparison": {"data": [], "layout": {}},
  "comparisonTable": {
    "columns": ["period", "entity", "metric", "value", "eligibleDays"],
    "rows": []
  },
  "dataVersion": {
    "committedImportRef": "imp_opaque",
    "committedAt": "ISO-8601"
  }
}
```

- Giữ trường `comparison` làm figure chung cho cả hai chế độ.
- `comparisonTable` tiếp tục được backend trả để tương thích API, nhưng frontend không hiển thị bảng trong popup. Khả năng tiếp cận dùng danh sách điểm lấy từ figure và aggregate refs.
- Không trả `run_id` nội bộ.
- Không trả dữ liệu của revision lịch sử.

### 5.3. Cache và phản hồi cũ

Cache key tối thiểu phải gồm:

```text
source revision
project
anchor
accepted entity IDs đã sắp xếp
lens
calculation
grain
range
include_incomplete
```

Frontend tiếp tục dùng `AbortController` riêng và kiểm tra danh tính yêu cầu. Phản hồi chỉ được nhận nếu đồng thời khớp phiên popup, lens, phép tính, phạm vi và phiên bản dữ liệu; với chế độ Chỉ số gốc, danh tính vẫn gồm chỉ số.

## 6. Bằng chứng tổng hợp

### 6.1. Phần tái sử dụng

- Bảng `aggregate_snapshots` và `aggregate_snapshot_members`.
- API provenance và contributors hiện có.
- Quy tắc `inferred_zero`, coverage source và eligible day hiện có.
- Exact observation vẫn dùng cho điểm dữ liệu ngày thuộc chế độ Chỉ số gốc.

### 6.2. Phần phải bổ sung

Mapper Thống kê đa nội dung phải ánh xạ độc lập:

```text
trace → entity_id → metric → calculation → period → aggregate snapshot
```

Không được lấy entity đầu tiên của toàn bộ DataFrame như mapper Thống kê đơn nội dung hiện tại. Mỗi điểm phải tạo hoặc tái sử dụng aggregate ref của đúng entity.

Khi mở Điều tra:

- kết quả và công thức phải khớp điểm đã chọn;
- `coverage_source_entity_id` phải được hiển thị khi kế thừa;
- số ngày đủ điều kiện và số ngày lịch phải tách biệt;
- contributor dùng phân trang hiện có;
- không gọi contributor drilldown mới hoặc tuyên bố mỗi điểm tương ứng một ô Excel.

## 7. Vòng đời trạng thái

| Sự kiện | Hành vi bắt buộc |
|---|---|
| Mở popup | Mở ở chế độ dùng gần nhất; lần đầu dùng `Chỉ số gốc`; anchor được chọn và request điều kiện chạy ngay |
| Chuyển sang Thống kê | Giữ anchor và sibling; ẩn lựa chọn chỉ số; trả đồng thời các chuỗi `Tổng số` và `Báo sai/Lỗi` hiện có; mặc định phép tính `Tổng trong kỳ` |
| Đổi chỉ số | Chỉ áp dụng ở chế độ Chỉ số gốc; tính lại eligibility, giữ candidate còn hợp lệ và giải thích candidate bị loại |
| Đổi phép tính | Tính lại eligibility và chart; không xóa lựa chọn trước khi backend xác nhận |
| Chọn/bỏ sibling | Anchor không thể bỏ; tối đa ba nội dung; request mới hủy request cũ |
| Đổi phạm vi | Dùng điều khiển Thống kê hiện có; tính lại eligibility, chart và aggregate refs |
| Mở Điều tra | Khóa định danh điểm; thu gọn selector; giữ chart nhìn thấy được |
| Đóng Điều tra | Giữ popup và biểu đồ tại ngữ cảnh hiện tại; xóa trạng thái chọn khi đóng trực tiếp |
| Mở Audit | Lưu phiên popup, điểm, cuộn và focus; điều hướng tới đúng observation/aggregate context hiện hỗ trợ |
| Quay lại từ Audit | Khôi phục popup nếu `dataVersion` còn khớp; nếu không, chuyển trạng thái dữ liệu mới |
| Import commit khi popup mở | Khóa điều khiển, không trộn payload; cho cập nhật dữ liệu hiện hành hoặc đóng popup |
| Đóng popup | Hủy request, giải phóng Plotly, trả focus và vị trí cuộn về nút nguồn |

## 8. Trạng thái giao diện bắt buộc

- Đang tải điều kiện.
- Đang cập nhật biểu đồ nhưng vẫn giữ khung và kích thước cũ.
- Chưa đủ hai nội dung.
- Không có sibling.
- Khác đơn vị.
- Thiếu giá trị thống kê.
- Không có ngày đủ điều kiện.
- Chỉ có coverage kế thừa nhưng phép tính yêu cầu `Tổng số` trực tiếp.
- Lỗi mạng có nút Thử lại.
- Dữ liệu mới đã commit.
- Không có provenance cho điểm tổng hợp: fail closed, chart vẫn xem được nhưng nút Điều tra bị vô hiệu kèm giải thích.
- Không render danh sách điểm bàn phím; phần biểu đồ nhận lại không gian dọc và footer luôn nhìn thấy.

## 9. Khả năng tiếp cận và ngôn ngữ

- Hai chế độ dùng `tablist`, `tab`, `tabpanel` đúng ngữ nghĩa.
- Phép tính dùng nhóm radio hoặc segmented control có nhãn rõ; không chỉ phân biệt bằng màu.
- Mỗi trace có màu, tên và ký hiệu; không dựa riêng vào màu. Với Trung bình mỗi ngày, tất cả đường là nét liền.
- Danh sách điểm thu gọn là nguồn thay thế tiếp cận được cho thao tác chọn điểm trên biểu đồ.
- Thông báo loại candidate dùng `aria-live=polite`; lỗi request dùng `role=alert`.
- Escape đóng tầng trên cùng trước: Điều tra → popup.
- Tất cả nội dung hiển thị dùng tiếng Việt: “Tổng trong kỳ”, “Trung bình mỗi ngày”, “Ngày có dữ liệu”, “Nội dung cùng nhóm”.
- Không hiển thị mã `RATE_NUMERATOR_MISSING`, `NO_ELIGIBLE_DAYS` hoặc tên trường API cho người dùng.

## 10. Module dự kiến thay đổi khi triển khai

### Backend

- `app/api.py`
  - mở rộng `comparison_lens`;
  - thêm `comparison_calculation`;
  - điều kiện hợp lệ cho Thống kê;
  - dựng `comparisonTable`;
  - cache key đầy đủ.
- `src/excel_visualization_pipeline/visualization/charts.py`
  - thêm builder Thống kê đa nội dung;
  - tái sử dụng `prepare_period_statistics`, không sao chép công thức.
- `app/aggregate_lineage.py`
  - mapper trace → entity cho Thống kê đa nội dung;
  - bỏ fail-closed chỉ trong đường gọi mới sau khi mapper có test.

### Frontend

- `frontend/src/main.ts`
  - lens state, calculation state, range state;
  - biểu đồ và thao tác nhấn trực tiếp điểm/cột để Điều tra;
  - Điều tra cục bộ trong popup;
  - khôi phục state khi đi Audit và quay lại.
- `frontend/src/style.css`
  - layout hai chế độ;
  - selector thu gọn;
  - panel Điều tra không chồng lấp;
  - responsive tại các viewport khóa.
- `frontend/src/terminology.ts`
  - thông báo eligibility và tên phép tính bằng tiếng Việt.

### Kiểm thử và tài liệu

- `tests/test_charts.py`
- `tests/test_aggregate_lineage.py`
- `tests/test_api.py`
- `frontend/e2e/contextual-comparison-phase-2.spec.ts`
- `specs/quality/acceptance-criteria.md`
- `specs/quality/traceability-matrix.md`

Không dự kiến thay đổi schema SQLite.

## 11. Kế hoạch triển khai theo lát dọc

Mỗi lát dọc phải hoàn tất backend → phép tính → điều kiện hợp lệ → frontend → kiểm thử trước khi chuyển lát tiếp theo.

### Gate 2.0 — Parity phép tính và missing/zero

**Phụ thuộc:** Phase 1 và báo cáo đối chiếu 6 dự án.

- Đối chiếu `prepare_period_statistics` với quy tắc đã khóa của `prepare_period_metric_summary`.
- Bổ sung dữ liệu kiểm tra để phát hiện ngày có `% báo sai > 0` nhưng thiếu `Báo sai/Lỗi`.
- Không suy 0 trong trường hợp mâu thuẫn; không suy ngược tử số từ tỷ lệ đã làm tròn.
- Ghi báo cáo tác động tới chart Thống kê đơn nội dung hiện tại.
- Thêm regression cho ba hình dạng dữ liệu:
  - node con có lỗi, node cha có Tổng số;
  - Tổng số + tỷ lệ dương nhưng thiếu lỗi;
  - Tổng số + tỷ lệ 0 và lỗi trống hợp lệ.
- Chưa thêm tab, component hoặc API Phase 2 trong Gate này.

**Cổng ra:** cùng entity/kỳ không được cho kết quả missing/zero mâu thuẫn giữa Thống kê và So sánh chỉ số gốc.

### Lát 2.1 — Tổng trong kỳ đa nội dung

**Phụ thuộc:** Gate 2.0.

- Backend nhận `comparison_lens=statistics` và `comparison_calculation=sum`.
- Dùng `prepare_period_statistics` cho từng entity.
- Eligibility theo `period_sum`.
- Frontend có tab Thống kê, chỉ chọn `Tổng trong kỳ` hoặc `Trung bình mỗi ngày`; cả `Tổng số` và `Báo sai/Lỗi` được trả tự động khi có dữ liệu.
- Chart hiển thị kết quả; bảng số liệu không được render trong popup.
- Chưa bật Điều tra nếu aggregate mapper chưa hoàn tất; nút phải ẩn hoặc vô hiệu có giải thích.

**Cổng ra:** sum đa nội dung hoạt động trên VSO và SmartParking; V-Pet loại đúng do đơn vị.

### Lát 2.2 — Trung bình mỗi ngày và coverage

**Phụ thuộc:** 2.1.

- Thêm `average_per_day`.
- Giữ `eligibleDayCount`, `calendarDayCount`, `coverageSourceEntityId` trong API để giải thích provenance; không render bảng số liệu.
- Phân biệt node có Tổng số trực tiếp và node chỉ kế thừa ngày coverage.
- Giữ selection khi đổi Tổng ↔ Trung bình.

**Cổng ra:** kết quả Statistics đơn nội dung và Comparison đa nội dung khớp tuyệt đối cho cùng entity/kỳ.

### Lát 2.3 — Bằng chứng đúng entity

**Phụ thuộc:** 2.1 và 2.2.

- Thêm mapper đa nội dung.
- Aggregate ref của từng trace/điểm resolve đúng entity, chỉ số, phép tính và kỳ.
- Reuse registry/contributors; không thêm storage.
- Fail closed nếu thiếu lineage.

**Cổng ra:** không có aggregate ref nào gắn nhầm entity; regression mapper đơn nội dung vẫn xanh.

### Lát 2.4 — Điều tra trong popup và vòng đi Audit

**Phụ thuộc:** 2.3.

- Panel Điều tra cục bộ.
- Thu gọn selector, giữ kích thước biểu đồ.
- Mở Audit và quay lại giữ đúng điểm, cuộn, focus và phiên dữ liệu.
- Data version mới chặn khôi phục payload cũ.

**Cổng ra:** kiểm thử nhấn điểm biểu đồ, Escape, stale data và hai viewport chuẩn đạt.

### Lát 2.5 — Kiểm tra tương đương và khóa Phase 2

**Phụ thuộc:** 2.1–2.4.

- Đối chiếu cả 6 dự án.
- So sánh kết quả đơn nội dung với đa nội dung.
- Chạy toàn bộ backend, build và Playwright.
- Lập báo cáo chênh lệch với mục So sánh cũ.
- Khóa bằng chứng tương đương trước khi quyết định ẩn lối vào cũ; không xóa contract backend trong lát này.

**Cổng ra:** không còn lỗi nghiêm trọng, không có công thức mới ngoài contract, tài liệu bằng chứng được cập nhật.

## 12. Tiêu chí nghiệm thu và ca kiểm thử dự kiến

### Lát 2.1

- `CMP2-ACC-001`: mở tab Thống kê giữ anchor và sibling đã chọn.
- `CMP2-ACC-002`: Tổng trong kỳ của mỗi entity khớp `prepare_period_statistics.period_sum`.
- `CMP2-ACC-002A`: tab Thống kê không có bộ chọn chỉ số; cùng một cách tính trả cả `Tổng số` và `Báo sai/Lỗi` hiện có, đồng thời giữ chỉ số gốc khi quay lại tab trước.
- `CMP2-ACC-003`: khác đơn vị, khác cha và khác dự án bị loại bởi backend.
- Playwright: chuyển Chỉ số gốc → Thống kê không đóng popup hoặc mất focus.
- Playwright: popup không có bảng số liệu hoặc danh sách điểm bàn phím và vẫn mở được Điều tra khi nhấn điểm biểu đồ.

### Lát 2.2

- `CMP2-ACC-004`: Trung bình mỗi ngày bằng tổng chia ngày đủ điều kiện.
- `CMP2-ACC-005`: ngày thiếu, ngày có ký hiệu nguồn và kỳ chưa đầy đủ theo đúng contract hiện có.
- `CMP2-ACC-006`: coverage kế thừa dùng đúng ancestor gần nhất nhưng không tạo Tổng số giả.
- Playwright: đổi phép tính giữ candidate hợp lệ và giải thích candidate bị loại.

### Lát 2.3

- `CMP2-ACC-007`: mỗi điểm có aggregate ref đúng entity.
- `CMP2-ACC-008`: contributor của AVG gồm value và coverage đúng vai trò.
- `CMP2-ACC-009`: lineage thiếu làm Điều tra không khả dụng, không đoán ref.
- Backend: hai entity cùng kỳ không được dùng chung ref nếu context khác entity.

### Lát 2.4

- `CMP2-ACC-010`: Điều tra không che chart tại 1366×768 và 1440×900.
- `CMP2-ACC-011`: đóng Điều tra giữ popup/biểu đồ ổn định; vòng đi-về Đối chiếu giữ đúng điểm và viewport.
- `CMP2-ACC-012`: Audit round-trip khôi phục popup khi cùng phiên bản.
- `CMP2-ACC-013`: import mới khóa payload cũ; phản hồi cũ không ghi đè.
- Playwright: nhấn điểm biểu đồ, Escape theo tầng, không tràn ngang, footer luôn tiếp cận được.

### Lát 2.5

- `CMP2-ACC-014`: ma trận 6 dự án không có trường hợp backend báo hợp lệ nhưng chart rỗng.
- `CMP2-ACC-015`: kết quả entity trong chart đa nội dung bằng chart Thống kê đơn nội dung.
- `CMP2-ACC-016`: Phase 1, AI Insights, Audit và import freshness không regression.
- `CMP2-ACC-017`: sau khi đạt kiểm tra tương đương, tab So sánh cũ và lối mở từ popup được ẩn; contract API cũ vẫn tương thích.

Các tiêu chí `CMP2-ACC-001` đến `CMP2-ACC-017` đã có source và test evidence; chi tiết ở mục 17.

## 13. Thứ tự phụ thuộc

```text
Phase 1 đã hoàn thành
        │
        ▼
Gate 2.0 parity missing/zero
        │
        ▼
2.1 Tổng trong kỳ
        │
        ▼
2.2 Trung bình/ngày + coverage
        │
        ▼
2.3 Mapper bằng chứng đa nội dung
        │
        ▼
2.4 Điều tra + Audit round-trip
        │
        ▼
2.5 Đối chiếu 6 dự án + cổng regression
```

Không triển khai 2.1 trước khi Gate 2.0 đạt. Không triển khai song song 2.3 với 2.1 nếu contract figure chưa ổn định; mapper bằng chứng phải bám đúng cấu trúc trace cuối cùng.

## 14. Quyết định đã khóa

1. Phase 2 mở rộng popup hiện tại, không tạo màn hình mới.
2. Chế độ Thống kê tự động hiển thị `Tổng số` và `Báo sai/Lỗi` hiện có; không có bộ chọn chỉ số.
3. Mỗi lần chỉ chọn một phép tính; tối đa ba entity và tối đa sáu chuỗi kết quả.
4. Công thức tái sử dụng từ `prepare_period_statistics`.
5. Backend quyết định eligibility và coverage source.
6. Popup chỉ hiển thị chart; `comparisonTable` chỉ được giữ ở backend để tương thích API.
7. Điều tra nằm trong popup, không chồng ngăn kéo toàn cục.
8. Aggregate lineage phải ánh xạ theo entity; không nới fail-closed trước khi có test.
9. Không thay schema, không historical recalculation; sau kiểm tra tương đương chỉ ẩn lối vào So sánh cũ, không xóa contract backend.
10. Kiểm tra toàn bộ 6 dự án là cổng bắt buộc trước khi kết thúc Phase 2.

## 15. Kết quả xác minh từ source

1. `comparisonTable` vẫn tồn tại trong response để tương thích nhưng không được render trong popup.
2. Figure tiếp tục dùng trường `comparison` cho cả hai chế độ.
3. API vẫn trả `eligibleDays` và `calendarDays` để giải thích coverage trong provenance.
4. Chart giữ kích thước tối thiểu; không render danh sách điểm bàn phím bên dưới.
5. Audit mở đúng observation từ contributor; backend chưa hỗ trợ dựng lại workspace lịch sử.
6. Gate 2.0 đã harden `prepare_period_statistics` trước khi builder đa nội dung sử dụng.

## 16. Điều kiện triển khai đã đáp ứng

Phase 2 đã giữ nguyên ba quyết định chính:

- chế độ Thống kê dùng một phép tính tại một thời điểm;
- `Tổng số` yêu cầu dữ liệu trực tiếp, không lấy giá trị ancestor;
- Điều tra dùng provenance hiện có, không mở rộng contributor drilldown hoặc historical workspace.

## 17. Bằng chứng hoàn thành

- Gate 2.0: `test_period_statistics_rejects_inferred_zero_when_positive_source_rate_has_no_error_count` khóa trường hợp tỷ lệ nguồn dương nhưng thiếu số lỗi.
- Lát 2.1–2.3: `test_contextual_comparison_contract_filters_siblings_and_keeps_legacy_api` và `test_multi_entity_statistics_uses_calculation_as_the_only_selection_axis` xác minh contract Thống kê, hai chuỗi kết quả, đường trung bình nét liền và aggregate ref đúng entity.
- Lát 2.4: `frontend/e2e/contextual-comparison.spec.ts` xác minh chuyển chế độ, giữ sibling, không render bảng số liệu/danh sách điểm bàn phím, nhấn biểu đồ mở Điều tra trong popup, vòng đi-về Audit, dữ liệu mới và phản hồi cũ.
- Lát 2.5: `test_contextual_statistics_real_workbook_matrix_has_no_eligible_empty_chart` chạy workbook thật của 6 dự án trên ngày/tuần/tháng/quý, hai chỉ số và hai phép tính.
- Điều hướng cấp cao không còn tab So sánh cũ và popup không còn nút mở mục cũ; contract API legacy vẫn có regression test, không có migration cơ sở dữ liệu.
