# Automated Excel Visualization Pipeline

Pipeline tự động trích xuất dữ liệu từ báo cáo Excel bán cấu trúc, chuẩn hóa thành long format có khả năng truy vết, kiểm tra chất lượng dữ liệu và sinh dashboard tương tác bằng Plotly + Streamlit.

Demo được xây dựng và smoke test trực tiếp với file:

```text
D:\task\test data for CX report dashboard.xlsx
```

## 1. Mục tiêu dự án

Workbook nguồn không phải bảng dữ liệu phẳng. Dữ liệu được tổ chức theo hai chiều:

```text
Theo hàng: Project → Entity → Entity → ... (parent-child tree)
Theo cột: Date → Metric
```

Pipeline chuyển đổi cấu trúc này theo luồng:

```text
Excel (.xlsx)
    ↓
Đọc workbook và metadata của ô
    ↓
Phát hiện Project, generic Entity Tree, Unit, Date và Metric
    ↓
Chuẩn hóa thành long format
    ↓
Validation và quality gate
    ↓
Plotly charts + Streamlit dashboard
    ↓
CSV + manifest + validation report
```

Mục tiêu quan trọng nhất là **correctness và traceability**: mỗi record và mỗi điểm trên biểu đồ đều có thể truy ngược về đúng sheet và địa chỉ ô trong Excel.

## 2. Nguyên tắc nghiệp vụ

### 2.1. Không tính lại KPI

File Excel đã được tổng hợp từ nhiều nguồn và không chứa công thức. Pipeline:

- chỉ đọc giá trị đang lưu trong ô;
- không tính lại `% báo sai` từ `Báo sai/Lỗi ÷ Tổng số`;
- không tự cộng hoặc lấy trung bình tỷ lệ phần trăm;
- không suy luận giá trị còn thiếu;
- không chỉnh sửa workbook nguồn.

### 2.2. Giữ nguyên giá trị nguồn

Ví dụ một ô chứa `0.08` với Excel number format là `0.00%`:

```text
raw_value      = 0.08
value_numeric  = 0.08
chart_value    = 8.0
display_value  = 8.00%
number_format  = 0.00%
```

`chart_value` chỉ là phép đổi đơn vị hiển thị sang điểm phần trăm. Giá trị nguồn vẫn được giữ trong `raw_value` và `value_numeric`.

### 2.3. Phân biệt dữ liệu thiếu và số 0

```text
Ô trống/NBSP → không tạo record
0            → số 0 hợp lệ và được vẽ
- / N/A      → missing_marker, không biến thành 0
Text         → giữ để audit, không ép thành số
```

### 2.4. Không tổng hợp sai cấp dữ liệu

Workbook thực tế có metric ở nhiều độ sâu hierarchy. Mỗi record được gắn:

```text
entity_id + parent_entity_id + entity_depth + entity_path
```

Dashboard chỉ so sánh các entity có scope và effective unit tương thích. Không còn biểu đồ `Tổng số` tổng hợp ở đầu trang và dashboard không tự động cộng node con thành node cha. Khi mở dashboard, hệ thống chọn entity nông nhất có dữ liệu trong khoảng hiện tại; các giá trị trong combo chart đều là record thực tế của entity đang hiển thị.

## 3. Kết quả baseline với workbook mẫu

| Chỉ số | Kết quả |
|---|---:|
| Sheet | 1 |
| Project | 6 |
| Section | 2 |
| Item | 28 |
| Tổng entity node | 36 |
| Độ sâu tối đa | 2 |
| Unit chuẩn hóa | 4 |
| Fallback entity | 1 |
| Block ngày | 44 |
| Metric chuẩn hóa | 4 |
| Tổng record | 1.955 |
| Record có thể vẽ | 1.791 |
| Quality gate error | 0 |
| Missing marker warning | 98 |
| Non-numeric metric warning | 53 |

Các metric chuẩn hóa:

```text
Tổng số
Báo sai/Lỗi
% báo sai
Ghi chú
```

Các Project được phát hiện:

```text
VSO
SmartParking
VW Vũ Yên
ANVF
V-Pet
VOL
```

## 4. Cấu trúc dự án

```text
excel_visualization_pipeline/
│
├── app/
│   └── dashboard.py                 # Streamlit dashboard
│
├── config/
│   ├── parser.yaml                  # Rule parser, alias metric, missing marker
│   └── visualization.yaml           # Khai báo cấu hình biểu đồ
│
├── data/
│   └── processed/
│       ├── normalized_data.csv      # Dataset đã chuẩn hóa
│       ├── entities.csv             # Parent-child entity tree
│       ├── manifest.json            # Thống kê và hash file nguồn
│       └── validation_report.json   # Error/warning và địa chỉ ô
│
├── scripts/
│   ├── run_pipeline.py              # Chạy extract + validation + export
│   └── smoke_test.py                # Smoke test end-to-end
│
├── src/excel_visualization_pipeline/
│   ├── ingestion/
│   │   └── excel_reader.py          # Đọc bytes, hash và workbook
│   ├── parser/
│   │   ├── hierarchy.py             # Parent-child state machine
│   │   └── workbook_parser.py       # Ghép entity tree với date/metric block
│   ├── validation/
│   │   └── validator.py             # Quality gate
│   ├── visualization/
│   │   └── charts.py                # Combo chart và các chart builder
│   ├── config.py                    # Dataclass đọc parser.yaml
│   ├── date_ranges.py               # Preset 10 ngày, tuần và tháng
│   ├── entity_selection.py           # Chọn entity mặc định có dữ liệu
│   ├── models.py                    # ParseResult và ValidationReport
│   └── pipeline.py                  # API orchestration và export
│
├── tests/
│   ├── conftest.py                  # Tạo workbook fixture
│   ├── test_parser.py               # Test extract, phần trăm, zero/blank
│   ├── test_validation.py           # Test duplicate và missing marker
│   ├── test_charts.py               # Test ba loại biểu đồ
│   ├── test_date_ranges.py           # Test khoảng ngày, tuần và tháng
│   ├── test_entity_selection.py      # Test fallback entity theo hierarchy
│   └── test_smoke_real_workbook.py  # Test với workbook thực tế
│
├── excel_structure.md               # Kết quả khảo sát workbook thật
├── pyproject.toml                   # Metadata và pytest config
├── requirements.txt                 # Python dependencies
└── README.md
```

## 5. Data model

Mỗi ô metric hợp lệ trở thành một record trong `normalized_data.csv`.

| Trường | Ý nghĩa |
|---|---|
| `source_file` | Tên file Excel nguồn |
| `source_hash` | SHA-256 của file nguồn |
| `sheet_name` | Sheet chứa ô nguồn |
| `cell_address` | Địa chỉ ô, ví dụ `F7` |
| `source_row` | Số dòng Excel |
| `project_id`, `project_label` | ID ổn định và nhãn Project |
| `entity_id` | ID duy nhất của node |
| `parent_entity_id` | ID node cha; null với Project |
| `entity_level` | Nhãn level như `project`, `section`, `item`, `subitem` |
| `entity_depth` | Độ sâu generic, Project bằng 0 |
| `entity_label` | Nhãn dùng để hiển thị |
| `entity_path` | Đường dẫn đầy đủ từ Project đến node |
| `unit_raw`, `unit_original` | Unit khai báo trực tiếp trên node |
| `unit_normalized` | Unit sau alias hoặc effective unit đã normalize |
| `effective_unit` | Unit hiệu lực từ ancestor gần nhất |
| `unit_source_level`, `unit_source_entity_id` | Nguồn kế thừa unit |
| `parser_rule`, `parser_confidence` | Rule và độ tin cậy phân loại node |
| `date` | Ngày của block kết quả |
| `metric_original` | Tên metric nguyên bản trong Excel |
| `metric_normalized` | Tên metric sau alias mapping |
| `raw_value` | Giá trị thật của ô |
| `value_numeric` | Giá trị số nguồn nếu có |
| `chart_value` | Giá trị đã đổi đơn vị để vẽ |
| `display_value` | Giá trị hiển thị thân thiện |
| `number_format` | Excel number format |
| `value_kind` | Kiểu dữ liệu do parser xác định |
| `validation_status` | `valid` hoặc `warning` |

Khóa logic dùng để phát hiện duplicate:

```text
sheet_name
+ project_id
+ entity_id
+ date
+ metric_normalized
+ unit_normalized
```

## 6. Cách parser hoạt động

### 6.1. Phát hiện header

Parser tìm trong các dòng đầu workbook một hàng có cột `Dự án`. Hàng tiếp theo được coi là hàng metric.

Số dòng tìm kiếm được cấu hình bởi:

```yaml
header_search_rows: 20
```

### 6.2. Phát hiện Project

Một dòng có giá trị số ở cột `STT` được nhận diện là Project mới. Project này trở thành context cho các dòng bên dưới.

### 6.3. Phát hiện generic Entity

Hierarchy không bị giới hạn ở `Project → Section → Item`. Các rule trong `parser.yaml` phân loại marker và chọn parent strategy:

```text
n.n...  → section, parent = project
- ...   → item, parent = section gần nhất hoặc project
+ ...   → subitem, parent = item trước đó
khác    → fallback entity, confidence = medium
```

State machine tạo `entity_id`, `parent_entity_id`, `entity_depth` và `entity_path`. Có thể thêm rule mới trong config mà không thay canonical schema.

### 6.4. Resolve Unit

Unit tuân theo nguyên tắc `nearest defined ancestor wins`. Node có unit riêng sẽ override ancestor; nếu không, nó kế thừa effective unit của parent. V‑Pet là regression case bắt buộc cho cả sub-item và multiple-unit Project.

### 6.5. Phát hiện Date và Metric

Parser chỉ nhận các block có header khớp `Kết quả triển khai` và có ngày `dd/mm/yyyy` hoặc `dd-mm-yyyy`.

Ví dụ:

```text
Kết quả triển khai 13/09/2026
├── Tổng số
├── Báo sai/Lỗi
└── % báo sai
```

Các block `Vấn đề/Phản ánh` nằm xen giữa các block ngày không được đưa vào dataset biểu đồ trong MVP.

### 6.6. Metric alias

Tên metric có thể thay đổi theo thời gian. Ví dụ:

```text
%                 → % báo sai
% báo sai         → % báo sai
Báo sai/Lỗi       → Báo sai/Lỗi
Báo sai/Lỗi/Nghi ngờ gian lận → Báo sai/Lỗi
```

Tên gốc vẫn được giữ trong `metric_original`.

## 7. Validation và quality gate

### 7.1. Lỗi làm dừng dashboard

- Không tìm thấy block ngày.
- Dataset không có record.
- Section không xác định được Project.
- Item không xác định được Project.
- Record thiếu Project, Date hoặc Metric.
- Trùng khóa logic.

Khi có error, dashboard hiển thị validation report và không render biểu đồ.

### 7.2. Cảnh báo không làm dừng dashboard

- Dấu `-`, `N/A`, `unknown` trong ô metric.
- Metric số chứa text.
- Tỷ lệ phần trăm ngoài khoảng 0–100%.
- Sheet không có layout thuộc phạm vi parser.

Warning được giữ trong `validation_report.json` và có `sheet_name`, `cell_address` để kiểm tra lại.

## 8. Dashboard

Dashboard hỗ trợ:

- upload workbook `.xlsx` mới;
- tự động dùng workbook demo nếu chưa upload file;
- mặc định hiển thị 10 ngày có dữ liệu gần nhất của Project đang chọn;
- chọn nhanh theo tuần ISO (Thứ Hai–Chủ Nhật) hoặc theo tháng lịch;
- chế độ `Tùy chỉnh` cho phép chọn `Từ ngày` và `Đến ngày` bằng hai date picker riêng, không dùng thanh kéo;
- chọn một Project trước khi render dashboard;
- toàn bộ KPI, chart, hierarchy và date filter chỉ dùng dữ liệu của Project đã chọn;
- không hiển thị sáu Project chung trên cùng một dashboard;
- không hiển thị biểu đồ `Tổng số` tổng hợp ở đầu dashboard;
- luôn mở trực tiếp phần entity và ưu tiên entity cấp cao nhất có dữ liệu trong khoảng đang chọn;
- nếu entity cấp cao nhất không có dữ liệu, tự động chọn entity cấp kế tiếp có dữ liệu; nếu cần, tiếp tục duyệt xuống các cấp sâu hơn;
- điều hướng bằng Hierarchy Navigator thay cho dropdown Section/Item cố định;
- chọn node hiện tại hoặc các node con trực tiếp;
- `Effective Unit` được cố định theo từng entity từ unit trực tiếp hoặc unit kế thừa từ parent, không có dropdown chọn unit;
- biểu đồ chi tiết kết hợp ba metric: cột `Tổng số` rộng làm nền, cột `Báo sai/Lỗi` hẹp nằm phía trước và đường `% báo sai` trên trục Y phụ;
- mỗi entity/node được render thành một combo chart riêng để không trộn đối tượng hoặc unit;
- khi hiển thị nhiều entity, dashboard xếp tối đa 2 combo chart trên mỗi hàng để tối ưu không gian và khả năng đọc nhãn;
- tự động tạo biểu đồ trung bình cho `Tổng số` và `Báo sai/Lỗi` trong khoảng thời gian đang chọn;
- có khu vực multi-select riêng để so sánh đồng thời tối đa 3 entity tương thích;
- cùng một kiểu combo chart được dùng cho một ngày hoặc cả khoảng `Từ ngày`–`Đến ngày`;
- biểu đồ thời gian chỉ gắn `display_value` tại điểm mới nhất của mỗi series; các điểm còn lại đọc qua unified hover theo ngày;
- toàn bộ ngày hiển thị trên trục và tiêu đề biểu đồ dùng định dạng `DD/MM`;
- bảng dữ liệu chuẩn hóa;
- xem warning chất lượng;
- tải xuống normalized CSV.

Dashboard áp dụng mô hình `Unified Hover + Latest Label + Audit Table`:

- Unified hover được kích hoạt theo vùng ngày trên trục X, không yêu cầu đặt chuột chính xác lên marker hoặc đường line.
- Khoảng bắt hover được giới hạn quanh ngày có dữ liệu, nên vùng trống không tự động hiển thị ngày gần nhất; tooltip không vẽ đường spike dọc xuyên biểu đồ.
- Tooltip dùng tiêu đề ngày `DD/MM/YYYY` và hiển thị đồng thời tất cả metric có dữ liệu tại ngày đó.
- Giá trị dùng `display_value` gốc để giữ đúng định dạng phần trăm; dữ liệu thiếu không được thay bằng `0`.
- Trong biểu đồ multi-select, mỗi entity là một nhóm gồm `Tổng số/Cảnh báo`, `Báo sai/Lỗi` và `% báo sai` của cùng ngày.
- Latest Label chỉ giữ nhãn tại ngày mới nhất của từng series để giảm chồng lấn.
- Biểu đồ tổng hợp ít điểm vẫn hiển thị nhãn trực tiếp trên từng cột.
- `Audit Table — dữ liệu nguồn` cung cấp entity path, metric gốc/chuẩn hóa, raw/display/chart value, sheet, địa chỉ ô, number format, parser rule và validation status.

### 8.1. Quy tắc chọn thời gian

- `10 ngày gần nhất` là chế độ mặc định và lấy 10 ngày phân biệt thực sự có dữ liệu, nên khoảng lịch có thể dài hơn 10 ngày nếu có ngày trống.
- `Theo tuần` liệt kê các tuần có dữ liệu, mới nhất trước; mỗi tuần chạy từ Thứ Hai đến Chủ Nhật theo ISO.
- `Theo tháng` liệt kê các tháng có dữ liệu, mới nhất trước và sử dụng toàn bộ biên tháng lịch.
- Nhãn tuần/tháng hiển thị số ngày thực sự có dữ liệu trong kỳ đã chọn.
- Tất cả biểu đồ và bảng drill-down cùng sử dụng một khoảng thời gian đã chọn.

### 8.2. Quy tắc chọn entity ban đầu

- Entity được xét theo `entity_depth` từ nhỏ đến lớn, sau đó theo thứ tự dòng nguồn `source_row`.
- Chỉ dữ liệu dạng số thuộc ba metric combo và nằm trong khoảng thời gian hiện tại được xem là dữ liệu có thể trình bày.
- Node cha có dữ liệu luôn được ưu tiên; node con chỉ được chọn tự động khi các node cấp trên không có dữ liệu.
- Nếu toàn bộ cây không có dữ liệu trong khoảng đã chọn, dashboard vẫn chọn node gốc và hiển thị trạng thái không có dữ liệu.

Unit không phải là bộ lọc tùy chọn trên giao diện. Khi render, mỗi biểu đồ tự lấy đúng `effective_unit` của entity tương ứng. Nếu file Excel không khai báo unit và entity cũng không kế thừa được từ parent, dashboard ghi rõ `Chưa xác định từ Excel` thay vì tự đoán đơn vị.

### 8.3. Quy tắc combo chart

- Hai cột dùng chung trục Y trái vì đều là số lượng và phải có cùng `effective_unit`.
- `Tổng số` là cột nền rộng và `Báo sai/Lỗi` là cột hẹp nằm phía trước (`barmode=overlay`); hai giá trị không bị cộng chồng.
- `% báo sai` là đường trên trục Y phải vì khác đơn vị với số lượng.
- Combo chart chi tiết từ chối đầu vào chứa nhiều `entity_id` hoặc nhiều `effective_unit`. Dashboard chịu trách nhiệm tách thành từng biểu đồ riêng và tự gắn unit cố định của entity.
- Nếu một node thiếu một trong ba metric, dashboard vẫn vẽ phần dữ liệu có sẵn và ghi rõ metric bị thiếu bên dưới biểu đồ.

### 8.4. Biểu đồ trung bình

- Khu vực tự động dùng chính khoảng thời gian đang chọn ở sidebar: 10 ngày gần nhất, một tuần, một tháng hoặc khoảng tùy chỉnh.
- Chỉ tính hai metric số lượng `Tổng số` và `Báo sai/Lỗi`; `% báo sai` không tham gia tính năng này.
- Mỗi metric được lấy trung bình trên số ngày thực sự có record của metric đó.
- Giá trị `0` là dữ liệu hợp lệ và được tính; ô trống hoặc missing marker bị loại khỏi mẫu số.
- Biểu đồ dùng grouped bar chart để so sánh trực tiếp giá trị trung bình của hai metric.
- Nếu phạm vi chứa nhiều Effective Unit, các biểu đồ tách thành panel riêng theo unit.

### 8.5. So sánh nhiều entity

- Khu vực `So sánh nhiều entity` có multi-select riêng, không thay đổi Hierarchy Navigator của biểu đồ chi tiết.
- Người dùng chọn ít nhất 2 và tối đa 3 entity.
- Các entity phải thuộc cùng Project và có cùng `effective_unit`; có thể chọn lẫn Project, Section, Item hoặc Sub-item.
- `Metric so sánh` cho phép chọn một trong `Tổng số`, `Báo sai/Lỗi` hoặc `% báo sai`; mặc định là `Báo sai/Lỗi`.
- Với `Tổng số` và `Báo sai/Lỗi`, mỗi entity là một series cột có màu riêng.
- Với `% báo sai`, mỗi entity là một đường có màu riêng.
- Mỗi series chỉ hiển thị trực tiếp `display_value` mới nhất; mọi ngày vẫn đọc được qua unified hover.
- Legend luôn thêm cấp hierarchy, ví dụ `[Project] VSO` hoặc `[Item] Camera`, để tránh nhầm dữ liệu cha và con.
- Biểu đồ chỉ hiển thị metric đang chọn: số lượng dùng trục Y theo Effective Unit chung, phần trăm dùng trục Y có hậu tố `%`; không tính thêm tỷ lệ dẫn xuất.
- Nếu lựa chọn không tương thích, dashboard không render chart và hiển thị điều kiện cần sửa.

## 9. Yêu cầu môi trường

- Windows, macOS hoặc Linux.
- Python 3.11 trở lên.
- File đầu vào định dạng `.xlsx`.
- Không yêu cầu Microsoft Excel được cài trên máy.

Các thư viện chính:

```text
openpyxl
pandas
plotly
streamlit
PyYAML
pytest
```

## 10. Cài đặt

### 10.1. Mở PowerShell và vào thư mục dự án

```powershell
cd D:\task\excel_visualization_pipeline
```

### 10.2. Khuyến nghị tạo virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell chặn activation script, có thể chạy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Thay đổi trên chỉ áp dụng cho cửa sổ PowerShell hiện tại.

### 10.3. Cài dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 11. Chạy pipeline và xuất dữ liệu

Từ thư mục `D:\task\excel_visualization_pipeline`:

```powershell
python scripts\run_pipeline.py "..\test data for CX report dashboard.xlsx"
```

Mặc định kết quả được ghi vào:

```text
data/processed/normalized_data.csv
data/processed/entities.csv
data/processed/manifest.json
data/processed/validation_report.json
```

Chỉ định output khác:

```powershell
python scripts\run_pipeline.py "D:\data\report.xlsx" --output "D:\data\processed"
```

Exit code:

```text
0 → quality gate hợp lệ
1 → có validation error
```

## 12. Chạy dashboard

```powershell
cd D:\task\excel_visualization_pipeline
python -m streamlit run app\dashboard.py
```

Sau khi server khởi động, mở địa chỉ Streamlit in ra terminal, thường là:

```text
http://localhost:8501
```

Nếu cổng 8501 đang được sử dụng:

```powershell
python -m streamlit run app\dashboard.py --server.port 8502
```

Dashboard mặc định đọc file demo ở thư mục cha. Có thể dùng nút upload trong sidebar để kiểm tra một workbook khác.

## 13. Chạy test

### 13.1. Chạy toàn bộ automated tests

```powershell
cd D:\task\excel_visualization_pipeline
python -m pytest
```

Kết quả baseline:

```text
6 passed
```

### 13.2. Chạy riêng parser tests

```powershell
python -m pytest tests\test_parser.py
```

### 13.3. Chạy validation tests

```powershell
python -m pytest tests\test_validation.py
```

### 13.4. Chạy chart tests

```powershell
python -m pytest tests\test_charts.py
```

### 13.5. Chạy smoke test với workbook thật

```powershell
python scripts\smoke_test.py "..\test data for CX report dashboard.xlsx"
```

Smoke test kiểm tra:

- workbook được parse thành công;
- quality gate không có error;
- phát hiện được Project và Date;
- có record dạng số;
- line chart render được;
- bar chart render được;
- combo chart ba metric render được cho đúng một entity;
- biểu đồ trung bình chỉ tính `Tổng số` và `Báo sai/Lỗi`;
- biểu đồ multi-select render metric được chọn cho 2–3 entity tương thích;

Kết quả thành công:

```text
SMOKE TEST PASSED
```

## 14. Cấu hình parser

File cấu hình: `config/parser.yaml`.

```yaml
header_search_rows: 20
project_column: "Dự án"
unit_column: "Đơn vị"
minimum_data_date: "2026-08-01"
result_header_patterns:
  - "kết quả triển khai"
hierarchy_rules:
  - name: numbered_section
    pattern: '^\s*\d+\.\d+[\.\s]'
    entity_level: section
    parent_strategy: project
  - name: plus_subitem
    pattern: '^\s*\+\s*'
    entity_level: subitem
    parent_strategy: previous_item_or_project
    strip_marker: true
  - name: dash_item
    pattern: '^\s*-\s*'
    entity_level: item
    parent_strategy: section_or_project
    strip_marker: true
fallback_entity_level: item
fallback_parent_strategy: project
blank_markers:
  - ""
  - "\u00a0"
missing_markers:
  - "-"
  - "n/a"
  - "na"
  - "unknown"
unit_aliases:
  "cảnh báo": "alert_count"
  "lượt": "event_count"
  "lượt (ngày)": "daily_event_count"
  "lượt (lũy kế)": "cumulative_event_count"
```

`minimum_data_date` là mốc chất lượng dữ liệu toàn cục. Pipeline bỏ hoàn toàn các block ngày trước mốc này khỏi normalized data, validation, dashboard, Audit Table và CSV xuất ra. Cấu hình hiện tại bắt đầu từ `01/08/2026` vì dữ liệu cũ hơn chưa được chuẩn hóa.

Khi workbook đổi tên metric, thêm alias tại `metric_aliases`:

```yaml
metric_aliases:
  "tỷ lệ lỗi": "% báo sai"
  "số cảnh báo lỗi": "Báo sai/Lỗi"
```

Khi tên header block thay đổi, thêm pattern:

```yaml
result_header_patterns:
  - "kết quả triển khai"
  - "kết quả vận hành"
```

## 15. Sử dụng pipeline trong Python

```python
from pathlib import Path

from excel_visualization_pipeline.pipeline import export_result, run_pipeline

result = run_pipeline(
    Path("report.xlsx"),
    config_path=Path("config/parser.yaml"),
)

if result.report.is_valid:
    export_result(result, Path("data/processed"))
else:
    for issue in result.report.errors:
        print(issue)
```

Nếu package chưa được cài editable, thêm `src` vào `PYTHONPATH` hoặc cài:

```powershell
python -m pip install -e .
```

Sau đó có thể import package từ bất kỳ script nào trong virtual environment.

## 16. Kiểm tra kết quả extract

Khi cần xác nhận một điểm trên biểu đồ:

1. Xem tooltip hoặc bảng dữ liệu dưới dashboard.
2. Lấy `source_file`, `sheet_name` và `cell_address`.
3. Mở workbook nguồn.
4. Tới đúng sheet và ô.
5. So sánh `raw_value`, `display_value` và `number_format`.

`source_hash` giúp xác nhận record được sinh từ đúng phiên bản file. Nếu nội dung workbook thay đổi, hash sẽ thay đổi.

## 17. Quy trình sử dụng file Excel mới

1. Sao lưu file nguồn.
2. Chạy `run_pipeline.py` với file mới.
3. Kiểm tra exit code và `validation_report.json`.
4. So sánh `manifest.json` với lần chạy trước, đặc biệt các trường:
   - `project_count`;
   - `section_count`;
   - `item_count`;
   - `date_count`;
   - `metric_count`;
   - `record_count`.
5. Nếu quality gate hợp lệ, mở dashboard và kiểm tra một số ô ngẫu nhiên bằng `cell_address`.
6. Chỉ phát hành dashboard/report sau khi đối soát hoàn tất.

## 18. Troubleshooting

### Không nhận lệnh `streamlit`

Luôn chạy thông qua Python module:

```powershell
python -m streamlit run app\dashboard.py
```

### `ModuleNotFoundError`

Đảm bảo virtual environment đang active và chạy:

```powershell
python -m pip install -r requirements.txt
```

### Không tìm thấy block ngày

Kiểm tra:

- header ngày có nằm trong 20 dòng đầu không;
- header có chứa `Kết quả triển khai` không;
- ngày có dạng `dd/mm/yyyy` hoặc `dd-mm-yyyy` không;
- nếu tên header mới, cập nhật `result_header_patterns`.

### Entity bị nhận sai level hoặc sai parent

Cập nhật `hierarchy_rules` trong `config/parser.yaml`: `pattern`, `entity_level`, `parent_strategy`, `strip_marker` và `confidence`. Không cần thêm cột Section/Item mới vào schema.

### Metric mới không được gom đúng nhóm

Thêm alias vào `metric_aliases`. Không xóa hoặc sửa `metric_original`, vì trường này phục vụ truy vết dữ liệu nguồn.

### Dashboard dừng ở quality gate

Mở `validation_report.json` hoặc bảng lỗi trên dashboard. Dùng `sheet_name` và `cell_address` để kiểm tra từng ô gây lỗi. Không nên bỏ quality gate chỉ để biểu đồ chạy.

### Giá trị phần trăm hiển thị sai

Kiểm tra `raw_value` và `number_format`:

- `raw_value = 0.08`, `number_format = 0.00%` → 8%;
- `raw_value = 8`, format thường → 8;
- text `8%` → parser lưu `value_numeric = 0.08`, `chart_value = 8`.

## 19. Giới hạn hiện tại

- Chỉ hỗ trợ `.xlsx`.
- Chưa xử lý file có password.
- Không evaluate công thức Excel.
- Chưa trực quan hóa nội dung dài trong các block `Vấn đề/Phản ánh`.
- Chưa có database hoặc lịch chạy tự động.
- Chưa có authentication/authorization cho dashboard.
- Parser vẫn cần cập nhật hierarchy rule nếu workbook xuất hiện marker hoặc parent strategy mới.
- Export PNG/PDF cần bổ sung engine như Kaleido; MVP hiện hỗ trợ dashboard và CSV.

## 20. Hướng phát triển tiếp theo

- Tạo parser riêng cho `Vấn đề/Phản ánh`.
- So sánh manifest giữa hai phiên bản workbook và cảnh báo schema drift.
- Thêm giao diện mapping metric alias.
- Thêm kiểm tra đối soát số ô nguồn với số record normalized.
- Thêm export dashboard sang HTML/PDF.
- Đóng gói Docker.
- Thêm CI để tự chạy unit test và smoke test.
- Thêm chế độ theo dõi thư mục và tự refresh khi có file mới.

## 21. Tiêu chí bàn giao MVP

- [x] Đọc workbook `.xlsx` thực tế.
- [x] Xử lý merged header theo ngày.
- [x] Phát hiện Project và dựng generic parent-child entity tree.
- [x] Có `entity_id`, `parent_entity_id`, `entity_depth` và `entity_path`.
- [x] Hỗ trợ Item → Sub-item và unit inheritance/override.
- [x] Có Hierarchy Navigator trên dashboard.
- [x] Phát hiện 44 block ngày tự động.
- [x] Chuẩn hóa metric alias.
- [x] Giữ nguyên giá trị nguồn và Excel number format.
- [x] Phân biệt phần trăm, số 0, blank, missing marker và text.
- [x] Ghi thông tin truy vết sheet/cell cho từng record.
- [x] Có validation report và quality gate.
- [x] Mở trực tiếp entity nông nhất có dữ liệu và tự động fallback xuống cấp dưới.
- [x] Có line/bar cơ bản và combo chart ba metric.
- [x] Combo chart tách riêng theo entity/unit với Tooltip, Latest Label và Audit Table.
- [x] Có biểu đồ trung bình tự động theo khoảng thời gian đang chọn.
- [x] Effective Unit cố định theo entity, không yêu cầu người dùng chọn.
- [x] Multi-select so sánh tối đa 3 entity cùng Project và unit, cho phép khác cấp hierarchy.
- [x] Có dashboard filter và upload file.
- [x] Có normalized CSV, entities CSV và manifest.
- [x] Có unit test và smoke test với workbook thật.

## 22. Lệnh chạy nhanh

```powershell
cd D:\task\excel_visualization_pipeline
python -m pip install -r requirements.txt
python -m pytest
python scripts\smoke_test.py "..\test data for CX report dashboard.xlsx"
python scripts\run_pipeline.py "..\test data for CX report dashboard.xlsx"
python -m streamlit run app\dashboard.py
```
