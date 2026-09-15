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
| Block `Kết quả triển khai` | 44 |
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
- Dấu `-` được giữ thành record `missing_marker`, không đổi thành số 0.
- Text xuất hiện trong một số ô metric được giữ để audit nhưng không đưa lên chart số.

## Kết quả baseline

Với phiên bản parser demo hiện tại:

```text
record_count           = 1955
chartable_record_count = 1791
project_count          = 6
section_count          = 2
item_count             = 28
entity_count           = 36
max_entity_depth       = 2
date_count             = 44
metric_count           = 4
quality_gate_errors    = 0
```

Baseline này được kiểm tra trong smoke test. Khi workbook thay đổi, manifest mới cần được so sánh với baseline để phát hiện thay đổi cấu trúc ngoài dự kiến.
