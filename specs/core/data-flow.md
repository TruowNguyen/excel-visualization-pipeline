# Luồng dữ liệu

- Trạng thái: **As-built**
- Contract IDs: `FLOW-*`

## Luồng tổng thể

```text
Workbook .xlsx
  -> Excel reader
  -> Hierarchy + workbook parser
  -> Normalized records + entities + validation report + manifest
  -> Preview quality gate
  -> SQLite import transaction
  -> Current views + append-only history
  -> FastAPI read model
  -> TypeScript dashboard / CSV export / Audit & lineage
```

## Các chặng xử lý

| Chặng | Input | Output | Không được làm |
|---|---|---|---|
| Ingestion | Workbook bytes | Cell values, number format, sheet/cell | Evaluate công thức Excel |
| Parsing | Cell grid + parser config | Entity tree, dates, metrics, normalized rows | Tự thay đổi KPI nguồn |
| Validation | Normalized rows + parser issues | Error/warning có lineage | Biến missing thành zero |
| Preview | Pipeline result | Manifest + issue summary | Ghi database |
| Storage | Valid result + import contract | Current pointers, revisions, presence, audit | Partial commit |
| API | SQLite current views/history | JSON/CSV/Plotly figures | Parse lại workbook trên read path |
| Dashboard | API payload | Charts, tables, filters, investigation | Suy đoán lineage bằng value/date |

## Invariants

- `FLOW-001`: Workbook gốc MUST được định danh bằng SHA-256.
- `FLOW-002`: Mỗi normalized record MUST giữ sheet, cell, source hash và parser metadata khi có nguồn tương ứng.
- `FLOW-003`: `raw_value`, `display_value` và `chart_value` MUST giữ ba mục đích riêng: nguồn, trình bày và vẽ.
- `FLOW-004`: Blank/NBSP/source marker/text MUST không bị tự chuyển thành số 0.
- `FLOW-005`: Dashboard chỉ đọc committed current state; preview không được xuất hiện trên dashboard.
- `FLOW-006`: Sau commit, cache read model MUST được phân biệt bằng latest committed run để dữ liệu mới có thể được đọc.
- `FLOW-007`: Một điểm exact chỉ mở lineage bằng `observationRef + lineageRef`; không fallback join theo ngày/metric/value.
- `FLOW-008`: Aggregate point MUST giữ snapshot và danh sách contributor của đúng lần tính.

## Read path

1. `/api/bootstrap` đọc danh sách project và biên ngày từ current state.
2. `/api/projects/{project}/entities` cung cấp hierarchy.
3. `/api/projects/{project}/workspace` lọc entity/time/view và dựng chart/read model.
4. Frontend render Plotly, statistics, comparison hoặc audit.
5. Khi chọn điểm, frontend dùng opaque refs để mở provenance, revision và import source.

Read path không phụ thuộc file upload trong browser session. Reload trình duyệt không làm mất dữ liệu đã commit.

## Write path

Write path duy nhất của web là preview rồi commit qua `/api/imports`. CLI dùng cùng pipeline và storage core. Chi tiết nằm tại [import-process.md](import-process.md).

## Ranh giới tự động hóa

Hệ thống hiện không có folder watcher, scheduler hoặc connector tới cloud drive. “Cập nhật” hiện có nghĩa là dữ liệu mới xuất hiện sau khi một import được người dùng/operator kích hoạt và commit thành công.

AI-assisted reporting chưa nằm trong flow as-built ở trên. Flow dự kiến MUST đọc committed data qua adapter read-only, khóa snapshot/opaque import ref và không chèn model vào parser/storage write path; xem [AI/Data v2](../ai-data/README.md) và `AI-CON-*`.
