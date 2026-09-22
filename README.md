# Automated Excel Visualization Pipeline

Pipeline Python chuyển báo cáo Excel bán cấu trúc thành dữ liệu long format có khả năng truy vết, kiểm tra chất lượng và dashboard tương tác. Giao diện chính hiện dùng TypeScript; FastAPI cung cấp dữ liệu từ SQLite và tái sử dụng logic biểu đồ Python. Streamlit cũ vẫn được giữ để đối chiếu trong giai đoạn chuyển tiếp.

```text
Excel → Entity/Date/Metric Parser → Normalized Data → Validation
      → SQLite history/current views → FastAPI → TypeScript Workspace
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
| Automated test | 48 passed |

## Tính năng chính

- Đọc `.xlsx` và giữ SHA-256, sheet, địa chỉ ô, giá trị/format nguồn.
- Dựng generic parent-child entity tree và kế thừa/override unit.
- Phát hiện block ngày và chuẩn hóa metric bằng cấu hình YAML.
- Phân biệt số 0, ô trống/NBSP, source marker, text và phần trăm.
- Validation có error quality gate và warning truy vết được.
- Combo chart, thống kê SUM/AVG theo kỳ và so sánh nhiều entity.
- Chế độ xem `Theo tuần`/`Theo tháng` so sánh trực tiếp nhiều kỳ lịch trên trục X, thay vì chọn một kỳ rồi hiển thị 7 ngày/những ngày trong tháng. Count được cộng theo kỳ; tỷ lệ kỳ được tính từ tổng lỗi chia tổng cảnh báo.
- Khi thống kê theo tuần, trục X dùng mã tuần ISO như `Tuần 37/2026`; khoảng ngày `07/09–13/09` được giữ trong hover.
- Nếu node con không có `Tổng số` dạng số, AVG của `Báo sai/Lỗi` kế thừa số ngày quan sát từ ancestor gần nhất có `Tổng số`; AVG `Tổng số` của node con vẫn để trống để không biến dữ liệu thiếu thành `0`.
- Interactive legend dạng compact toggle chip, không có label hoặc container lớn: mỗi item tự thể hiện màu/loại series, nhấn để ẩn/hiện và nhấn đúp để chỉ xem một series; series tắt được làm mờ tự động.
- Legend chuẩn hóa chiều cao chip, vùng marker, căn giữa marker/text và khoảng cách giữa các item để bar/line series thẳng hàng.
- Hierarchy Navigator, Audit Table và tải normalized CSV.
- Cache pipeline theo workbook/config để giảm thời gian rerun.
- Khôi phục bộ lọc từ `sessionStorage` sau khi reload mà không đưa trạng thái lên URL.
- SQLite local lưu current state và toàn bộ revision lịch sử của dữ liệu.
- Import idempotent theo workbook hash, parser config và import contract; upload trùng không tạo dữ liệu trùng.
- Phân biệt `full_snapshot` và `incremental`; record vắng mặt trong incremental không bị xóa.
- Audit riêng source artifact, import attempt, committed run, validation issue và sự hiện diện của từng observation.
- Tách business change (`semantic_hash`) khỏi thay đổi vị trí ô/parser metadata (`lineage_hash`).
- Backup bằng SQLite Online Backup API và kiểm tra integrity/foreign key bằng CLI.

## Tài liệu

- [Đặc tả đầy đủ hệ thống](docs/SYSTEM_SPECIFICATION.md)
- [Kiến trúc frontend/backend mới](docs/FRONTEND_BACKEND.md)
- [Thiết kế SQLite v3 đã triển khai](docs/SQLITE_DATABASE_DESIGN_v3.md)
- [Khảo sát cấu trúc workbook mẫu](excel_structure.md)
- [Cấu hình parser](config/parser.yaml)
- [Cấu hình biểu đồ](config/visualization.yaml)

## Yêu cầu

- Python 3.11 trở lên.
- Node.js 20.19+ hoặc 22.12+ để build giao diện TypeScript.
- Windows, macOS hoặc Linux.

Thư viện chính: `openpyxl`, `pandas`, `plotly`, `FastAPI`, `Streamlit` (legacy), `TypeScript`, `Vite` và `pytest`.

## Cài đặt

```powershell
cd D:\task\excel_visualization_pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd frontend
npm ci
cd ..
```

## Chạy giao diện mới (TypeScript + FastAPI)

Mở hai terminal tại thư mục dự án:

```powershell
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
cd frontend
npm run dev
```

Truy cập `http://127.0.0.1:5173`. Vite chuyển tiếp `/api` sang FastAPI. Khi build bản tĩnh, có thể chạy chung một tiến trình:

```powershell
cd frontend
npm run build
cd ..
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Truy cập `http://127.0.0.1:8000`. UI mới gồm sidebar Project/thời gian/hierarchy và workspace Tổng quan, Thống kê, So sánh, Audit, Import, Lịch sử. Dữ liệu bộ lọc lưu trong `sessionStorage` của tab; không nằm trên URL.

Mặc định API chỉ lắng nghe `127.0.0.1`. Chưa có authentication/authorization nên không đưa trực tiếp lên Internet. Trước khi triển khai nhiều người dùng cần thêm auth, phân quyền và đánh giá SQLite single-writer.

## Streamlit cũ (giai đoạn chuyển tiếp)

```powershell
python -m streamlit run app\dashboard.py
```

Khi không chọn file, dashboard chỉ đọc current data đã lưu trong SQLite và không tự import workbook demo hoặc CSV export. Để cập nhật dữ liệu, chọn một file `.xlsx` trong sidebar và chọn rõ chế độ:

- `Toàn bộ snapshot`: file đại diện cho phạm vi đầy đủ; MVP vẫn dùng `missing_policy=ignore`, chưa tự xóa record vắng mặt.
- `Chỉ dữ liệu bổ sung`: chỉ insert/update key có trong file, không suy luận deletion.

File được parse/validate ở chế độ preview trước. Chỉ khi người dùng bấm **Xác nhận import** hệ thống mới commit vào `data/local/analytics.sqlite3`, sau đó đọc lại toàn bộ current data từ SQLite. Vì vậy file incremental vẫn được hiển thị cùng lịch sử đã lưu trước đó. Lịch sử import được xem trực tiếp trong expander **Lịch sử import SQLite**.

Hệ thống chặn việc áp dụng lại cùng một artifact bằng mode khác và chặn replay artifact cũ nếu đã có workbook mới hơn. Quy tắc này tránh workbook demo/cũ ghi đè current state khi giao diện rerun.

File upload phải được chọn lại sau khi reload; bộ lọc dashboard được khôi phục trong cùng tab. Dữ liệu nghiệp vụ không phụ thuộc session trình duyệt vì đã được lưu trong SQLite.

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

## SQLite: khởi tạo và import

Khởi tạo hoặc chạy các migration còn thiếu:

```powershell
python scripts\init_database.py
```

Import full snapshot mặc định:

```powershell
python scripts\import_workbook.py "..\test data for CX report dashboard.xlsx"
```

Import file chỉ chứa dữ liệu bổ sung:

```powershell
python scripts\import_workbook.py input.xlsx --mode incremental
```

Tham số vận hành chính:

```text
--database      Đường dẫn SQLite; mặc định data/local/analytics.sqlite3
--source-key    Định danh nguồn logic; mặc định cx_report_master
--display-name  Tên hiển thị của nguồn
--mode          full_snapshot hoặc incremental
--config        Parser YAML; mặc định config/parser.yaml
--allow-replay  Áp dụng lại artifact cũ có chủ đích để phục hồi/correction
```

Không đổi `source-key` giữa các workbook nối tiếp của cùng một nguồn. Tên file có thể thay đổi vì identity nguồn không dựa vào filename.

`--allow-replay` có thể ghi đè current values bằng revision cũ, vì vậy chỉ dùng sau khi backup và xác nhận rõ workbook cần phục hồi.

### Dữ liệu được tạo

```text
data/
├── local/analytics.sqlite3      Database chính
├── raw/<sha256>.xlsx            Workbook gốc theo content hash
└── backups/*.sqlite3            Bản backup
```

Toàn bộ `data/` đã được gitignore.

### Kiểm tra lịch sử và integrity

```powershell
python scripts\inspect_import_history.py
python scripts\verify_database.py
```

`verify_database.py` phải trả:

```text
integrity_check = ok
foreign_key_issues = []
is_valid = true
```

### Backup

```powershell
python scripts\backup_database.py
```

Chọn đường dẫn cụ thể:

```powershell
python scripts\backup_database.py --output D:\backup\analytics.sqlite3
```

Script dùng SQLite Online Backup API, không copy thẳng database khi WAL đang hoạt động.

## Mô hình lịch sử

- `import_attempts`: mọi lần upload/chạy CLI, bao gồm duplicate, rejected và failed.
- `import_runs`: chỉ lần import commit thành công.
- `source_artifacts`: file gốc và SHA-256.
- `import_scopes`: phạm vi khai báo của full snapshot.
- `projects`, `entities`, `observations`: identity/current pointer.
- `*_revisions`: lịch sử append-only.
- `import_observation_presence`: record xuất hiện trong từng committed run, kể cả unchanged.
- `validation_issues`: warning/error theo attempt/run.
- `v_current_entities`, `v_current_observations`: read model cho dashboard.

Một observation dùng logical key:

```text
source_id + entity_id + observed_date + metric_code
```

Unit không nằm trong key; sửa unit tạo revision thay vì observation song song.

## Kiểm thử

```powershell
python -m pytest
python scripts\smoke_test.py "..\test data for CX report dashboard.xlsx"
python scripts\smoke_test_storage.py "..\test data for CX report dashboard.xlsx"
```

Kết quả baseline:

```text
48 passed
SMOKE TEST PASSED
STORAGE SMOKE TEST PASSED
```

## Cấu trúc rút gọn

```text
app/api.py                               FastAPI backend cho TypeScript workspace
frontend/                                TypeScript/Vite UI mới
app/dashboard.py                         Streamlit legacy để đối chiếu
config/parser.yaml                       Parser và alias rules
config/visualization.yaml                Đặc tả biểu đồ
docs/SYSTEM_SPECIFICATION.md             Tài liệu kỹ thuật/nghiệp vụ
scripts/run_pipeline.py                  CLI extract/validate/export
scripts/import_workbook.py               CLI import idempotent vào SQLite
scripts/init_database.py                 Khởi tạo/migrate database
scripts/inspect_import_history.py        Xem attempt/run/counters
scripts/backup_database.py               Online backup
scripts/verify_database.py               Integrity và foreign-key check
scripts/smoke_test.py                    Smoke test workbook thật
scripts/smoke_test_storage.py            Smoke Excel → SQLite → chart
src/excel_visualization_pipeline/        Package pipeline
src/excel_visualization_pipeline/storage/ SQLite storage/repository/importer
tests/                                   Automated tests
excel_structure.md                       Khảo sát workbook mẫu
```

## Giới hạn hiện tại

- Chỉ hỗ trợ `.xlsx` không có password.
- Không evaluate công thức Excel.
- SQLite phù hợp local/single writer; chưa hỗ trợ nhiều importer writer đồng thời hoặc network share.
- Auto-tombstone đang tắt trong dashboard/CLI mặc định; chỉ bật bằng declared scope đã được kiểm thử.
- Entity rename/move chưa tự động merge; cần alias mapping thủ công để nối identity cũ.
- Chưa có lịch import tự động; hiện kích hoạt từ dashboard hoặc CLI.
- Chưa có authentication/authorization.
- Chưa đóng gói Docker hoặc CI.
- Parser cần thêm rule nếu workbook xuất hiện layout/hierarchy mới.

Chi tiết kiến trúc, data model, business rules, dashboard, baseline, validation và hướng phát triển được duy trì tại [docs/SYSTEM_SPECIFICATION.md](docs/SYSTEM_SPECIFICATION.md).
