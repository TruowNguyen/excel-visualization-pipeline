# Cấu trúc workbook mẫu

Nguồn khảo sát: `test data for CX report dashboard.xlsx`

## Tổng quan

| Thuộc tính | Giá trị |
|---|---:|
| Sheet | `Sheet1` |
| Số dòng | 43 |
| Số cột | 149 (`A:ES`) |
| Header hierarchy | Dòng 3–4 |
| Dòng dữ liệu chính | 5–40 |
| Project | 6 |
| Section có nhãn rõ ràng | 2 |
| Item | 28 |
| Entity node | 36 |
| Max entity depth | 2 |
| Block `Kết quả triển khai` trong workbook | 44 |
| Block được xử lý từ `01/08/2026` | 41 |
| Công thức | 0 |

## Parent-child entity hierarchy

- Cột A: STT; một giá trị số đánh dấu dòng Project mới.
- Cột B: tên Project, Section hoặc Item.
- Cột C: đơn vị. Giá trị đơn vị được kế thừa xuống các dòng con cho đến khi có đơn vị mới.
- Section được nhận diện bằng rule cấu hình `n.n`, ví dụ `1.1.` và `1.2.`.
- Dòng `-` tạo Item dưới Section gần nhất hoặc Project.
- Dòng `+` tạo node con dưới Item gần nhất.
- Dòng không có marker được giữ bằng `fallback_entity` với confidence trung bình.
- Parser tạo `entity_id`, `parent_entity_id`, `entity_depth` và `entity_path`; schema không giới hạn số cấp.
- Unit được resolve theo nguyên tắc ancestor gần nhất có khai báo unit.
- Workbook có dữ liệu metric ngay trên một số node Project và Section; mọi record trỏ đến `entity_id` tương ứng.

Các Project được phát hiện:

```text
VSO
SmartParking
VW Vũ Yên
ANVF
V-Pet
VOL
```

## Column hierarchy

- Dòng 3 chứa header cấp ngày, ví dụ `Kết quả triển khai 13/09/2026`.
- Dòng 4 chứa metric.
- Một block kết quả thường có ba cột: `Tổng số`, `Báo sai/Lỗi`, `% báo sai`.
- Một số block cũ có thêm `Ghi chú`.
- Tên metric thay đổi theo thời gian, ví dụ `%` và `% báo sai`, hoặc các biến thể của `Báo sai/Lỗi/Nghi ngờ gian lận`; parser giữ tên gốc và map về alias chuẩn.
- Các block `Vấn đề/Phản ánh` nằm xen kẽ từ các ngày cũ. MVP không đưa các block này vào dataset metric vì chúng không thuộc header `Kết quả triển khai`.

## Quy ước giá trị quan sát được

- Tỷ lệ phần trăm chủ yếu được lưu dưới dạng số thập phân, ví dụ `0.08`, với Excel number format `0.00%`.
- Workbook sử dụng ô trống thật, khoảng trắng không ngắt `NBSP` và dấu `-` cho các trạng thái khác nhau.
- `NBSP` chỉ là dữ liệu trình bày và được coi là blank.
- Dấu `-` được giữ thành record `source_marker` để đánh dấu dữ liệu khác bản chất, không đổi thành số 0 hoặc tự diễn giải thành “không có dữ liệu”.
- Ô `% báo sai` trống chỉ được gán `default_zero_rate = 0%` khi `Báo sai/Lỗi` cùng entity/ngày không ghi nhận hoặc bằng 0; `raw_value` vẫn giữ nguyên để phân biệt với số 0 từ Excel.
- Text xuất hiện trong một số ô metric được giữ để audit nhưng không đưa lên chart số.

## Kết quả baseline của pipeline

Với phiên bản parser hiện tại và `minimum_data_date: "2026-08-01"`:

```text
record_count           = 4182
chartable_record_count = 2343
project_count          = 6
section_count          = 2
item_count             = 28
entity_count           = 36
max_entity_depth       = 2
fallback_entity_count  = 1
unknown_unit_count     = 2
unit_count             = 4
default_zero_rate_count = 646
inconsistent_error_metric_count = 89
date_count             = 41
metric_count           = 3
quality_gate_errors    = 0
quality_gate_warnings  = 193
```

Ba metric trong phạm vi hiện tại là `Tổng số`, `Báo sai/Lỗi` và `% báo sai`. Metric `Ghi chú` chỉ xuất hiện trong các block cũ trước mốc lọc nên không được tính vào baseline pipeline, dù parser vẫn hỗ trợ metric này.

Baseline này được xác nhận bằng automated test và smoke test trên workbook thật. Khi workbook hoặc cấu hình thay đổi, manifest mới cần được so sánh với baseline để phát hiện thay đổi cấu trúc ngoài dự kiến.
