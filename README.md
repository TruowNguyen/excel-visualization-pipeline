# Automated Excel Visualization Pipeline

Pipeline Python chuyển báo cáo Excel bán cấu trúc thành dữ liệu long format có khả năng truy vết, kiểm tra chất lượng và dashboard tương tác bằng Plotly + Streamlit.

```text
Excel → Entity/Date/Metric Parser → Normalized Data
      → Validation → Dashboard → CSV/Manifest/Report
```

## Trạng thái

Dự án đã hoàn thành phạm vi MVP và đang được sử dụng cho demo nội bộ.

Baseline workbook mẫu hiện tại:

| Chỉ số | Giá trị |
|---|---:|
| Project | 6 |
| Entity | 36 |
| Ngày từ `01/08/2026` | 41 |
| Metric | 3 |
| Record | 4.182 |
| Record có thể vẽ | 2.343 |
| Quality-gate error | 0 |
| Warning | 193 |
| Automated test | 35 passed |

## Tính năng chính

- Đọc `.xlsx` và giữ SHA-256, sheet, địa chỉ ô, giá trị/format nguồn.
- Dựng generic parent-child entity tree và kế thừa/override unit.
- Phát hiện block ngày và chuẩn hóa metric bằng cấu hình YAML.
- Phân biệt số 0, ô trống/NBSP, source marker, text và phần trăm.
- Validation có error quality gate và warning truy vết được.
- Combo chart, thống kê SUM/AVG theo kỳ và so sánh nhiều entity.
- Hierarchy Navigator, Audit Table và tải normalized CSV.
- Cache pipeline theo workbook/config để giảm thời gian rerun.
- Khôi phục bộ lọc từ `sessionStorage` sau khi reload mà không đưa trạng thái lên URL.

## Tài liệu

- [Đặc tả đầy đủ hệ thống](docs/SYSTEM_SPECIFICATION.md)
- [Khảo sát cấu trúc workbook mẫu](excel_structure.md)
- [Cấu hình parser](config/parser.yaml)
- [Cấu hình biểu đồ](config/visualization.yaml)

## Yêu cầu

- Python 3.11 trở lên.
- Windows, macOS hoặc Linux.

Thư viện chính: `openpyxl`, `pandas`, `plotly`, `streamlit`, `PyYAML` và `pytest`.

## Cài đặt

```powershell
cd D:\task\excel_visualization_pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Chạy dashboard

```powershell
python -m streamlit run app\dashboard.py
```

Dashboard tự dùng workbook demo tại:

```text
D:\task\test data for CX report dashboard.xlsx
```

Hoặc chọn một file `.xlsx` khác trong sidebar. File upload phải được chọn lại sau khi reload; bộ lọc của workbook mặc định được khôi phục trong cùng tab trình duyệt. Trạng thái tự mất khi đóng tab và không tạo lịch sử lâu dài.

Network URL chỉ nên dùng trong mạng nội bộ tin cậy vì MVP chưa có authentication/authorization.

## Chạy pipeline và export

```powershell
python scripts\run_pipeline.py "..\test data for CX report dashboard.xlsx"
```

Kết quả được ghi vào `data/processed/`:

- `normalized_data.csv`;
- `entities.csv`;
- `manifest.json`;
- `validation_report.json`.

Có thể chọn thư mục khác:

```powershell
python scripts\run_pipeline.py input.xlsx --output D:\output
```

## Kiểm thử

```powershell
python -m pytest
python scripts\smoke_test.py "..\test data for CX report dashboard.xlsx"
```

Kết quả baseline:

```text
35 passed
SMOKE TEST PASSED
```

## Cấu trúc rút gọn

```text
app/dashboard.py                         Streamlit dashboard
config/parser.yaml                       Parser và alias rules
config/visualization.yaml                Đặc tả biểu đồ
docs/SYSTEM_SPECIFICATION.md             Tài liệu kỹ thuật/nghiệp vụ
scripts/run_pipeline.py                  CLI extract/validate/export
scripts/smoke_test.py                    Smoke test workbook thật
src/excel_visualization_pipeline/        Package pipeline
tests/                                   Automated tests
excel_structure.md                       Khảo sát workbook mẫu
```

## Giới hạn hiện tại

- Chỉ hỗ trợ `.xlsx` không có password.
- Không evaluate công thức Excel.
- Chưa có database, lịch sử snapshot hoặc lịch chạy tự động.
- Chưa có authentication/authorization.
- Chưa đóng gói Docker hoặc CI.
- Parser cần thêm rule nếu workbook xuất hiện layout/hierarchy mới.

Chi tiết kiến trúc, data model, business rules, dashboard, baseline, validation và hướng phát triển được duy trì tại [docs/SYSTEM_SPECIFICATION.md](docs/SYSTEM_SPECIFICATION.md).
