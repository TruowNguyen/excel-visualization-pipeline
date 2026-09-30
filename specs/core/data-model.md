# Data model

- Trạng thái: **As-built**
- Contract IDs: `DATA-*`

## Mô hình khái niệm

```text
DataSource
  ├─ SourceArtifact
  ├─ ImportAttempt ── ValidationIssue
  └─ ImportRun
       ├─ ProjectRevision
       ├─ EntityRevision
       ├─ ObservationRevision
       └─ ImportObservationPresence

Project 1 ── * Entity 1 ── * Observation * ── 1 Metric
Observation 1 ── * ObservationRevision
```

## Thực thể chính

| Thực thể/bảng | Trách nhiệm |
|---|---|
| `data_sources` | Định danh nguồn logic ổn định qua nhiều workbook |
| `source_artifacts` | Workbook gốc theo content hash |
| `import_attempts` | Mọi lần thử import, kể cả duplicate/rejected/failed |
| `import_runs` | Chỉ các lần commit thành công và counters |
| `import_scopes` | Phạm vi được khai báo cho snapshot |
| `projects`, `project_revisions` | Identity project và lịch sử nhãn/sheet |
| `entities`, `entity_aliases`, `entity_revisions` | Identity hierarchy, alias và revision |
| `metrics` | Danh mục metric chuẩn hóa |
| `observations` | Logical observation và current pointer |
| `observation_revisions` | Lịch sử business value append-only |
| `import_observation_presence` | Lineage của observation trong từng run |
| `validation_issues` | Error/warning gắn attempt/run và nguồn |
| `aggregate_snapshots` | Kết quả tổng hợp đã dùng cho chart |
| `aggregate_snapshot_members` | Contributor của aggregate |

## Identity và logical key

- `DATA-001`: Source identity là `source_key`, không phải filename.
- `DATA-002`: Project identity là `(source_id, project_key)`.
- `DATA-003`: Entity hiện được resolve bằng exact match trên active alias `(source_id, external_entity_key)`. Nếu không có alias, importer tạo entity mới và alias `initial`.
- `DATA-004`: Observation logical key là:

```text
source_id + entity_id + observed_date + metric_code
```

Unit không nằm trong logical key. Sửa unit hoặc value tạo revision của observation hiện có thay vì observation song song.

- `DATA-009`: Parser tạo external entity key từ `sheet_name + hierarchy path + occurrence`; rename hoặc move làm đổi path thường làm đổi key.
- `DATA-010`: Schema cho phép `alias_reason` là `rename`, `move` hoặc `manual_merge`, nhưng application hiện chỉ tự ghi `initial`; chưa có API/CLI/UI hay test acceptance cho quản trị alias. Nếu key đổi mà không có active alias được chuẩn bị bởi một workflow tương lai, historical observation continuity không được bảo toàn tự động.

## Value contract

| Trường | Ý nghĩa |
|---|---|
| `raw_value` / `raw_value_text` | Giá trị nguồn dùng cho audit |
| `value_numeric` | Giá trị số chuẩn hóa nếu chuyển đổi hợp lệ |
| `chart_value` | Giá trị được phép đưa lên chart; có thể `null` |
| `display_value` | Chuỗi hiển thị bảo toàn ý nghĩa/format |
| `value_kind` | Phân loại number, blank, marker, text, percentage... |
| `validation_status` | Trạng thái validation của record |
| `data_note` | Ghi chú dữ liệu nếu có |

- `DATA-005`: Zero hợp lệ MUST khác missing.
- `DATA-006`: `chart_value = null` MUST không được render như zero.
- `DATA-007`: Dashboard MUST không tính lại KPI nguồn ở cấp record.
- `DATA-008`: Tỷ lệ tổng hợp theo kỳ dùng `SUM(error) / SUM(total) × 100`, không dùng trung bình tỷ lệ ngày.

## Revision và hash

- `semantic_hash`: phát hiện thay đổi business value.
- `lineage_hash`: phát hiện thay đổi vị trí/metadata nguồn.
- Business change tạo `observation_revision` mới.
- Lineage-only change tạo presence mới và không giả thành business revision.
- Current tables giữ pointer tới revision hiện hành; lịch sử là append-only.
- Explicit replay tuân theo `IMP-017`–`IMP-022`: khi semantic value khác, tạo revision mới mang state được replay thay vì trỏ về revision lịch sử cũ.

## Public references

API không công khai primary key số để điều tra lineage. Các ref có prefix:

- `obs_`: observation;
- `lin_`: lineage snapshot;
- `rev_`: observation revision;
- `imp_`: committed import;
- `att_`: import attempt;
- `agg_`: aggregate snapshot.

Ref MUST được kiểm tra theo project/source. Ref sai project trả `404`; cặp observation/lineage không khớp trả `409`.

## Baseline hiện tại

Workbook mẫu được khóa bởi smoke test với 6 project, 36 entity, 41 ngày, 3 metric, 4.182 normalized record và 2.343 chartable record. Baseline là fixture kiểm thử, không phải giới hạn cứng của data model.

ERD và contract database hiện hành xem [database-design.md](database-design.md). Thiết kế nền chi tiết xem [`../../docs/SQLITE_DATABASE_DESIGN_v3.md`](../../docs/SQLITE_DATABASE_DESIGN_v3.md).
