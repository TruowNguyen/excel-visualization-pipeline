# Đặc tả hệ thống Excel Visualization Pipeline

## 1. Thông tin tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Hệ thống | Excel Visualization Pipeline |
| Phiên bản package | `0.1.0` |
| Trạng thái | MVP hoàn chỉnh, đang ổn định hóa cho demo nội bộ |
| Ngôn ngữ | Python 3.11+ |
| Giao diện | Streamlit + Plotly |
| Nguồn dữ liệu | Workbook `.xlsx` bán cấu trúc |

Tài liệu này là đặc tả kỹ thuật và nghiệp vụ chính của hệ thống. Khảo sát chi tiết workbook mẫu được lưu riêng tại [`excel_structure.md`](../excel_structure.md).

## 2. Mục tiêu và phạm vi

Hệ thống tự động chuyển báo cáo Excel bán cấu trúc thành dữ liệu long format có khả năng truy vết, kiểm tra chất lượng dữ liệu và trực quan hóa trên dashboard tương tác.

Workbook nguồn có hai chiều phân cấp:

```text
Theo hàng: Project → Entity → Entity → ...
Theo cột: Date → Metric
```

Luồng tổng thể:

```text
Excel .xlsx
    ↓
Đọc bytes, metadata và giá trị ô
    ↓
Phát hiện Project, entity tree, unit, date và metric
    ↓
Chuẩn hóa long format có source lineage
    ↓
Validation và quality gate
    ↓
Plotly charts + Streamlit dashboard
    ↓
CSV + manifest + validation report
```

Phạm vi MVP:

- đọc workbook `.xlsx` không có password;
- xử lý merged header ngày và metric;
- dựng generic parent-child entity tree;
- chuẩn hóa metric và unit theo cấu hình;
- bảo toàn giá trị nguồn và địa chỉ ô;
- phân biệt số, phần trăm, số 0, ô trống, source marker và text;
- validation có error/warning;
- dashboard nội bộ hỗ trợ drill-down, thống kê và so sánh entity;
- export dataset và metadata phục vụ audit.

Ngoài phạm vi hiện tại:

- authentication/authorization;
- database và lịch sử snapshot lâu dài;
- lịch chạy tự động;
- xử lý workbook có password;
- evaluate công thức Excel;
- triển khai nhiều server/replica;
- trực quan hóa block văn bản dài `Vấn đề/Phản ánh`;
- export PNG/PDF hoàn chỉnh.

## 3. Nguyên tắc nghiệp vụ

### 3.1. Không tính lại KPI nguồn

Hệ thống chỉ đọc giá trị đang lưu trong Excel và không:

- tính lại `% báo sai` từ `Báo sai/Lỗi ÷ Tổng số`;
- cộng hoặc lấy trung bình tỷ lệ phần trăm nguồn;
- tự suy luận dữ liệu thiếu, trừ quy tắc `default_zero_rate` được mô tả rõ;
- chỉnh sửa workbook nguồn.

### 3.2. Bảo toàn giá trị và truy vết

Mỗi record giữ `source_file`, SHA-256, sheet, địa chỉ ô, dòng nguồn, `raw_value` và `number_format`.

Ví dụ ô có giá trị `0.08` và format `0.00%`:

```text
raw_value      = 0.08
value_numeric  = 0.08
chart_value    = 8.0
display_value  = 8.00%
number_format  = 0.00%
```

`chart_value` chỉ đổi đơn vị phục vụ biểu đồ. `raw_value` và `value_numeric` vẫn giữ ý nghĩa nguồn.

### 3.3. Phân biệt dữ liệu thiếu và số 0

| Giá trị nguồn | `value_kind` | Xử lý |
|---|---|---|
| `None`, chuỗi rỗng, NBSP `U+00A0` | `not_recorded` | Không vẽ, giữ record để audit |
| `0` | `numeric`/`percentage` | Số hợp lệ và được vẽ |
| `-`, `N/A`, `NA`, `unknown` | `source_marker` | Không ép thành 0, tạo warning |
| Text trong metric số | `text` | Không vẽ, tạo warning |
| Text trong `Ghi chú` | `text` | Hợp lệ, giữ để audit |

`raw_value` cố ý giữ kiểu Excel hỗn hợp. Riêng bản dữ liệu đưa vào Audit Table được ép cột `raw_value` sang pandas `string` để tương thích PyArrow; dataset và export không bị thay đổi.

### 3.4. Quy tắc tỷ lệ mặc định

Ô `% báo sai` trống được gán `0%` với `value_kind = default_zero_rate` chỉ khi `Báo sai/Lỗi` cùng entity/ngày không ghi nhận hoặc bằng 0.

- `raw_value` vẫn giữ nguyên;
- dấu `-` không được chuyển thành `0%`;
- nếu số lỗi lớn hơn 0, tỷ lệ trống vẫn là `not_recorded`;
- tỷ lệ dương nhưng số lỗi không ghi nhận tạo warning `INCONSISTENT_ERROR_METRICS`.

### 3.5. Không tổng hợp sai hierarchy

Dashboard không tự cộng node con thành node cha. Mỗi điểm biểu đồ là record thực của đúng `entity_id`. So sánh nhiều entity chỉ được phép trong cùng Project và cùng `effective_unit`.

## 4. Kiến trúc mã nguồn

```text
excel_visualization_pipeline/
├── app/
│   └── dashboard.py
├── config/
│   ├── parser.yaml
│   └── visualization.yaml
├── data/processed/
├── docs/
│   └── SYSTEM_SPECIFICATION.md
├── scripts/
│   ├── run_pipeline.py
│   └── smoke_test.py
├── src/excel_visualization_pipeline/
│   ├── ingestion/excel_reader.py
│   ├── parser/hierarchy.py
│   ├── parser/workbook_parser.py
│   ├── validation/validator.py
│   ├── visualization/charts.py
│   ├── config.py
│   ├── date_ranges.py
│   ├── entity_selection.py
│   ├── models.py
│   └── pipeline.py
└── tests/
```

### 4.1. Ingestion

`ingestion/excel_reader.py`:

- nhận đường dẫn, bytes hoặc binary stream;
- tính SHA-256 của file;
- đọc bằng `openpyxl` với `data_only=True`;
- không evaluate công thức và không ghi ngược vào workbook.

### 4.2. Configuration

`config.py` ánh xạ `parser.yaml` vào `ParserConfig`. Cấu hình chính gồm:

- số dòng tìm header;
- tên cột Project và Unit;
- ngày dữ liệu tối thiểu;
- pattern block kết quả;
- hierarchy rules và parent strategy;
- blank/source markers;
- metric aliases;
- unit aliases.

`visualization.yaml` hiện mô tả ý định cấu hình biểu đồ; chart implementation vẫn nằm chủ yếu trong Python.

### 4.3. Hierarchy parser

`parser/hierarchy.py` là state machine theo từng worksheet.

Quy tắc mặc định:

```text
STT là số → project
n.n...    → section, parent = project
- ...     → item, parent = section gần nhất hoặc project
+ ...     → subitem, parent = item trước đó
khác      → fallback item, confidence = medium
```

Mỗi node có:

- `entity_id`;
- `parent_entity_id`;
- `entity_level`;
- `entity_depth`;
- `entity_path`;
- parser rule/confidence;
- thông tin unit trực tiếp và kế thừa.

Unit tuân theo nguyên tắc ancestor gần nhất có khai báo. Unit trên node con override unit của parent.

### 4.4. Workbook parser

`parser/workbook_parser.py` thực hiện:

1. tìm hàng header có cột `Dự án`;
2. xác định hàng metric ngay bên dưới;
3. phát hiện các block `Kết quả triển khai <ngày>`;
4. áp dụng `minimum_data_date`;
5. dựng entity tree theo dòng;
6. chuẩn hóa metric và giá trị từng ô;
7. tạo record long format;
8. áp dụng `default_zero_rate` và kiểm tra metric không nhất quán;
9. tạo entity table và manifest.

### 4.5. Validation

`validation/validator.py` nhận dataset, entity table và parser issues, sau đó trả `ValidationReport`.

Error làm quality gate thất bại:

- không tìm thấy block ngày;
- dataset rỗng;
- entity không xác định được Project;
- record thiếu Project, Date hoặc Metric;
- trùng logical key;
- parent entity không tồn tại;
- cycle trong entity tree.

Warning không chặn dashboard:

- source marker;
- text trong metric số;
- phần trăm ngoài 0–100%;
- fallback entity classification;
- chưa xác định được unit;
- metric lỗi và tỷ lệ không nhất quán;
- worksheet không thuộc layout parser hỗ trợ.

### 4.6. Orchestration và export

`pipeline.py` điều phối:

```text
load_excel → parse_workbook → validate_dataset → PipelineResult
```

`export_result` tạo:

- `normalized_data.csv`;
- `entities.csv`;
- `manifest.json`;
- `validation_report.json`.

## 5. Mô hình dữ liệu

### 5.1. Normalized record

Mỗi ô metric thuộc phạm vi trở thành một record.

| Nhóm | Trường |
|---|---|
| Nguồn | `source_file`, `source_hash`, `sheet_name`, `cell_address`, `source_row` |
| Project | `project_id`, `project_label` |
| Hierarchy | `entity_id`, `parent_entity_id`, `entity_level`, `entity_depth`, `entity_label`, `entity_path`, `entity_key` |
| Unit | `unit_raw`, `unit_original`, `unit_normalized`, `effective_unit`, `unit_source_level`, `unit_source_entity_id` |
| Parser | `parser_rule`, `parser_confidence` |
| Legacy projection | `project`, `section`, `item`, `unit` |
| Observation | `date`, `metric_original`, `metric_normalized` |
| Value | `raw_value`, `value_numeric`, `chart_value`, `display_value`, `number_format`, `value_kind`, `data_note` |
| Quality | `validation_status` |

Logical key dùng phát hiện duplicate:

```text
sheet_name
+ project_id
+ entity_id
+ date
+ metric_normalized
+ unit_normalized
```

### 5.2. Entity table

`entities.csv` lưu một record cho mỗi node hierarchy, gồm định danh, parent, depth/path, unit resolution và parser metadata. Dataset metric tham chiếu entity bằng `entity_id`.

### 5.3. Manifest

Manifest cung cấp fingerprint và thống kê của một lần parse:

- source file/hash và số sheet;
- số record/chartable record;
- số Project/Section/Item/Entity;
- độ sâu tối đa;
- số fallback entity và unknown unit;
- số unit, ngày và metric;
- số default-zero và inconsistent metric;
- danh sách Project/metric;
- mốc ngày tối thiểu.

## 6. Phát hiện date và metric

Parser chỉ nhận header khớp pattern cấu hình và chứa ngày dạng `dd/mm/yyyy` hoặc `dd-mm-yyyy`.

```text
Kết quả triển khai 13/09/2026
├── Tổng số
├── Báo sai/Lỗi
└── % báo sai
```

Metric alias mặc định:

```text
%                                  → % báo sai
% báo sai                          → % báo sai
Báo sai/Lỗi                        → Báo sai/Lỗi
Báo sai/Lỗi/Nghi ngờ gian lận     → Báo sai/Lỗi
```

Tên nguồn luôn được giữ trong `metric_original`.

## 7. Dashboard

### 7.1. Nguồn dữ liệu và quality gate

- người dùng có thể upload `.xlsx`;
- nếu không upload, dashboard dùng workbook demo ở thư mục cha;
- nếu report có error, dashboard hiển thị lỗi và không render chart;
- warning vẫn được hiển thị trong khu vực cảnh báo.

### 7.2. Cache

Dashboard dùng `st.cache_data` cho `PipelineResult`. Cache key gồm:

- bytes của workbook;
- tên file;
- đường dẫn parser config;
- `mtime_ns` của parser config.

Cache được dùng chung giữa các session nhưng mỗi caller nhận một bản sao an toàn. Khi workbook hoặc cấu hình thay đổi, cache key thay đổi và pipeline chạy lại.

### 7.3. Trạng thái và reload

Dashboard dùng một Streamlit component v2 ẩn để ghi trạng thái hiện tại vào `window.sessionStorage` của trình duyệt:

- Project;
- chế độ và khoảng thời gian;
- entity và phạm vi hierarchy;
- nhóm/phạm vi/mode thống kê;
- tùy chọn kỳ chưa đầy đủ;
- metric và entity so sánh.

Reload tạo session Streamlit mới; component đọc JSON từ `sessionStorage`, gửi về Python và dashboard khôi phục widget. URL không chứa Project, entity hoặc bộ lọc. Trạng thái được tách theo browser tab/origin và tự mất khi đóng tab, nên không tạo lịch sử lâu dài phía server.

State có `source_hash`; nếu workbook hiện tại khác workbook đã lưu, dashboard bỏ state cũ và dùng mặc định an toàn. Query parameters từ phiên bản cũ được tự xóa khỏi URL.

File upload không thể tự khôi phục sau reload theo cơ chế bảo mật trình duyệt. Người dùng phải chọn lại file; state chỉ được áp dụng nếu hash nguồn còn phù hợp.

### 7.4. Chọn thời gian

- `10 ngày gần nhất`: 10 ngày phân biệt có dữ liệu gần nhất;
- `Theo tuần`: tuần ISO, Thứ Hai–Chủ Nhật;
- `Theo tháng`: tháng lịch;
- `Tùy chỉnh`: ngày bắt đầu/kết thúc trong phạm vi dữ liệu.

Khoảng sidebar áp dụng cho combo chart, Audit Table và so sánh entity. Thống kê SUM/AVG có phạm vi độc lập.

### 7.5. Entity navigation

- chọn Project trước;
- tự động chọn entity nông nhất có dữ liệu số trong khoảng hiện tại;
- nếu node cấp cao không có dữ liệu, tiếp tục tìm xuống cấp dưới;
- cho phép xem node hiện tại hoặc các node con trực tiếp;
- effective unit được cố định theo entity, không có unit dropdown.

### 7.6. Combo chart

- `Tổng số`: cột nền;
- `Báo sai/Lỗi`: cột cùng độ rộng nằm phía trước;
- `% báo sai`: đường trên trục Y phụ;
- mỗi entity có chart riêng;
- tối đa hai chart trên một hàng;
- không nhận dữ liệu của nhiều entity hoặc nhiều unit trong cùng chart.

### 7.7. Thống kê theo kỳ

Hỗ trợ nhóm theo ngày, tuần, tháng và quý.

- `SUM`: cột;
- `AVG/ngày = SUM / số ngày hợp lệ`: đường;
- chỉ áp dụng cho `Tổng số` và `Báo sai/Lỗi`;
- ngày `Tổng số` trống/source marker không vào mẫu số;
- `Báo sai/Lỗi` trống đóng góp 0 nếu `Tổng số` cùng ngày là số hợp lệ;
- có thể bao gồm hoặc loại kỳ biên chưa đầy đủ;
- hỗ trợ các kỳ gần nhất, toàn bộ dữ liệu hoặc khoảng kỳ tùy chọn.

### 7.8. So sánh nhiều entity

- chọn 2–3 entity;
- cùng Project và cùng effective unit;
- có thể khác cấp hierarchy;
- metric số lượng dùng grouped bar;
- phần trăm dùng line;
- không tạo tỷ lệ dẫn xuất.

### 7.9. Hover, label và audit

- unified hover theo ngày;
- chỉ gắn nhãn trực tiếp tại điểm mới nhất của series;
- tooltip dùng `display_value` để bảo toàn định dạng;
- Audit Table hiển thị nguồn, hierarchy, raw/display/chart value, sheet/cell, number format và parser metadata;
- cột `raw_value` chỉ được cast sang string trên slice hiển thị để tương thích Arrow và tiết kiệm bộ nhớ.

## 8. Baseline workbook mẫu

Nguồn: `D:\task\test data for CX report dashboard.xlsx`.

Với `minimum_data_date: "2026-08-01"`:

| Chỉ số | Giá trị |
|---|---:|
| Sheet | 1 |
| Project | 6 |
| Section | 2 |
| Item/Sub-item | 28 |
| Entity | 36 |
| Max depth | 2 |
| Unit chuẩn hóa | 4 |
| Fallback entity | 1 |
| Unknown unit | 2 |
| Date | 41 |
| Metric | 3 |
| Record | 4.182 |
| Chartable record | 2.343 |
| Default zero rate | 646 |
| Inconsistent error metric | 89 |
| Quality-gate error | 0 |
| Warning | 193 |

Warning breakdown:

| Code | Số lượng |
|---|---:|
| `INCONSISTENT_ERROR_METRICS` | 89 |
| `SOURCE_MARKER` | 54 |
| `NON_NUMERIC_METRIC` | 48 |
| `FALLBACK_ENTITY_CLASSIFICATION` | 1 |
| `UNKNOWN_UNIT` | 1 |

Metric trong phạm vi hiện tại:

- `Tổng số`;
- `Báo sai/Lỗi`;
- `% báo sai`.

Parser vẫn hỗ trợ `Ghi chú`, nhưng metric này chỉ xuất hiện ở block cũ trước mốc lọc.

## 9. Kiểm thử

Bộ test hiện có 35 test:

| Nhóm | Số lượng |
|---|---:|
| Charts | 16 |
| Date ranges | 7 |
| Entity selection | 4 |
| Parser | 4 |
| Validation | 2 |
| Hierarchy | 1 |
| Real workbook smoke | 1 |

Smoke test kiểm tra pipeline, quality gate và khả năng dựng line/bar/combo/statistics/comparison chart trên workbook thật.

Baseline chính được khóa bằng assertion trong `tests/test_smoke_real_workbook.py`; thay đổi workbook hoặc semantics parser ngoài dự kiến sẽ làm test thất bại.

## 10. Vận hành nội bộ

### Cài đặt

```powershell
cd D:\task\excel_visualization_pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Chạy dashboard

```powershell
python -m streamlit run app\dashboard.py
```

- Local URL phục vụ người dùng trên máy chạy server.
- Network URL phục vụ thiết bị khác cùng mạng có thể truy cập máy/port.
- Mỗi tab là một session riêng; widget state giữa người dùng không bị trộn.
- Các session dùng chung CPU, RAM, cache và tiến trình Streamlit.
- Không public Network URL ra Internet vì hệ thống chưa có authentication.

### Chạy pipeline và export

```powershell
python scripts\run_pipeline.py "..\test data for CX report dashboard.xlsx"
```

### Chạy test

```powershell
python -m pytest
python scripts\smoke_test.py "..\test data for CX report dashboard.xlsx"
```

## 11. Cấu hình parser

File: `config/parser.yaml`.

Khi workbook thay đổi:

1. kiểm tra header Project/Unit;
2. cập nhật `result_header_patterns` nếu tên block đổi;
3. thêm metric alias thay vì sửa tên trong code;
4. thêm hierarchy rule nếu xuất hiện marker/parent strategy mới;
5. thêm unit alias nếu có cách viết unit mới;
6. chạy test và smoke test;
7. so sánh manifest với baseline;
8. cập nhật tài liệu nếu thay đổi là chủ đích.

## 12. Hướng phát triển sau MVP

- parser riêng cho `Vấn đề/Phản ánh`;
- schema-drift comparison giữa các manifest;
- giao diện mapping metric alias;
- đối soát số ô nguồn với số record normalized;
- export HTML/PDF/PNG;
- Docker và CI;
- logging/monitoring;
- folder watcher và refresh tự động;
- authentication/authorization;
- database và snapshot history khi chuyển từ demo sang vận hành lâu dài;
- tách service/API khi cần tích hợp hoặc scale nhiều instance.

## 13. Tiêu chí MVP đã hoàn thành

- [x] Đọc workbook thật và merged header.
- [x] Dựng generic entity tree và unit inheritance/override.
- [x] Phát hiện date block và metric alias.
- [x] Bảo toàn source lineage và Excel number format.
- [x] Phân biệt zero/blank/source marker/text/percentage.
- [x] Validation report và quality gate.
- [x] Hierarchy Navigator và entity fallback.
- [x] Combo chart, statistics và multi-entity comparison.
- [x] Audit Table và CSV download.
- [x] Cache theo workbook/config.
- [x] Khôi phục bộ lọc qua browser `sessionStorage` sau reload, không làm lộ state trên URL.
- [x] Automated tests và smoke test workbook thật.
