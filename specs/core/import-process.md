# Quy trình import workbook

- Trạng thái: **As-built**
- Contract IDs: `IMP-*`

## Mục tiêu

Import phải đưa dữ liệu hợp lệ vào SQLite mà không làm thay đổi current state khi preview thất bại, file bị thay đổi, quality gate lỗi hoặc commit không hoàn tất.

## Tác nhân và đầu vào

- Người dùng dashboard hoặc operator CLI.
- File `.xlsx` không có password, tối đa 50 MB khi đi qua API.
- Parser config tại `config/parser.yaml`.
- `source_key` ổn định cho các workbook thuộc cùng một nguồn logic.
- Chế độ `incremental` hoặc `full_snapshot`.

## Luồng chuẩn

```text
Chọn workbook
  -> đọc bytes + tính SHA-256
  -> parse hierarchy/date/metric/value
  -> normalize + validation
  -> trả preview, manifest và issues (chưa ghi dữ liệu)
  -> người dùng xác nhận mode và hash preview
  -> tạo import attempt
  -> exact duplicate -> replay protection -> quality/key validation
  -> transaction upsert project/entity/observation/revision/presence
  -> commit run + counters
  -> dashboard đọc lại current views từ SQLite
```

## Quy tắc bắt buộc

### Preview

- `IMP-001`: Preview MUST không tạo `import_attempt`, `import_run` hoặc thay đổi current state.
- `IMP-002`: Preview MUST trả manifest, tổng error/warning và tối đa 100 issue chi tiết qua API.
- `IMP-003`: Error làm preview không hợp lệ; warning không tự chặn commit.
- `IMP-004`: UI MUST vô hiệu hóa commit khi preview không hợp lệ.

### Xác nhận và chống file thay đổi

- `IMP-005`: Commit MUST nhận lại chính file đã preview và `expected_hash`.
- `IMP-006`: Nếu SHA-256 mới khác `expected_hash`, API MUST trả `409` và không commit.
- `IMP-007`: `full_snapshot` trên UI MUST yêu cầu xác nhận bổ sung.

### Chế độ import

- `IMP-008`: `incremental` chỉ insert/update các logical key có mặt; không suy luận record vắng mặt là deletion.
- `IMP-009`: `full_snapshot` MUST có ít nhất một scope. Khi caller không truyền scope, core tự tạo một scope cho mỗi sheet từ ngày nhỏ nhất đến lớn nhất, `is_complete=true` và `missing_policy=ignore`.
- `IMP-010`: Cùng artifact/config/contract đã commit MUST cho kết quả duplicate, không tạo observation trùng.
- `IMP-011`: Áp lại artifact cũ sau run mới hơn MUST bị chặn, trừ thao tác phục hồi có chủ đích bằng CLI `allow_replay`.
- `IMP-016`: Tombstone chỉ được áp dụng khi mode là `full_snapshot`, scope resolve được, `is_complete=true`, `missing_policy=tombstone`, observation nằm trong selector và không xuất hiện trong run. Web API và CLI hiện không nhận declared scope/tombstone option; đường này chỉ có ở storage core cho caller lập trình.

Vì auto scope dùng `missing_policy=ignore`, full snapshot qua dashboard/CLI mặc định không xóa record vắng mặt và giữ current state ngoài các key có trong workbook. Không được mô tả `full_snapshot` hiện tại như một thao tác tự đồng bộ deletion.

### Explicit replay

- `IMP-017`: Explicit replay là **forward recovery**, không phải rollback current pointer. `allow_replay=True` tạo attempt mới, replay contract mới và committed run mới rồi áp dụng artifact qua pipeline bình thường.
- `IMP-018`: Replay contract MUST chứa `base_contract_hash`, `base_contract_json` và `explicit_replay_attempt_id`. Vì attempt ID mới ở mỗi lần chạy, explicit replay cố ý non-idempotent ở cấp run; artifact và logical observation vẫn được dùng lại.
- `IMP-019`: Replay có business value khác current tạo revision `update`; observation đang deleted tạo `restore`; value không đổi giữ current business revision; logical key mới tạo `insert`. Replay không tái sử dụng revision lịch sử cũ làm current khi có business change.
- `IMP-020`: Mọi observation có mặt trong replay MUST có presence và lineage snapshot mới; `latest_presence_id` chuyển sang presence mới ngay cả khi business revision không đổi. Mọi revision cũ vẫn append-only.
- `IMP-021`: Thứ tự canonical trong `_process_result` là exact duplicate → stale/artifact replay protection → quality gate → duplicate logical-key validation → transactional commit → duplicate recheck tại commit boundary. Entry point `import_workbook` có thể từ chối parse/quality lỗi trước khi gọi `_process_result`.
- `IMP-022`: Explicit replay chỉ bỏ qua stale/artifact-already-applied rejection. Nó MUST không bỏ qua parse/quality validation, logical-key validation hoặc transaction integrity. Replay hiện chỉ được expose qua CLI `--allow-replay`, không qua public API/dashboard.

Unique constraint của run vẫn là `(source_id, source_hash, parser_config_hash, import_contract_hash)`. Replay contract có attempt ID riêng nên mỗi explicit replay hợp lệ có identity khác; revision/presence uniqueness không xung đột vì replay có `run_id` mới.

### Transaction và lịch sử

- `IMP-012`: Một committed run MUST là atomic: hoặc toàn bộ business rows/counters/history được commit, hoặc không có partial current state.
- `IMP-013`: Mọi lần thử ghi MUST có attempt status; chỉ lần thành công mới có committed run.
- `IMP-014`: Observation không đổi business value vẫn MUST có presence trong run mới.
- `IMP-015`: Thay đổi business value tạo revision; thay đổi lineage-only không được giả thành business change.

## Kết quả import

API commit trả `ImportOutcome` với các trường:

| Trường | Ý nghĩa |
|---|---|
| `attempt_id` | Lần thử import |
| `status` | `committed`, `duplicate` hoặc trạng thái từ chối tương ứng |
| `message` | Thông báo vận hành nếu có |
| `run_id` | Run đã commit, có thể `null` |
| `duplicate_of_run_id` | Run nguồn khi duplicate |
| `inserted_count` | Observation mới |
| `updated_count` | Observation có revision business mới |
| `unchanged_count` | Observation giữ business value |
| `restored_count` | Observation được khôi phục |
| `deleted_count` | Observation tombstone |
| `lineage_changed_count` | Observation không đổi business value nhưng đổi lineage |

## Các nhánh thất bại

| Điều kiện | Kết quả |
|---|---|
| Không phải `.xlsx` | `422`, không ghi dữ liệu |
| File API lớn hơn 50 MB | `413`, không ghi dữ liệu |
| Không parse được | `422`, không ghi dữ liệu |
| Hash khác preview | `409`, không ghi dữ liệu |
| Quality gate có error | `422`, không commit |
| Mode không hợp lệ | `422`, không commit |
| Logical key trùng trong một dataset | attempt rejected, không commit |
| Transaction lỗi | rollback; attempt ghi nhận failed nếu đã được tạo |

## Vận hành

- UI: tab **Import Excel** → preview → xác nhận → xem **Lịch sử nhập**.
- CLI: `scripts/import_workbook.py`.
- Integrity: `scripts/verify_database.py`.
- Backup trước replay/phục hồi: `scripts/backup_database.py`.

Tiêu chí kiểm chứng nằm tại `ACC-IMP-*` trong [acceptance-criteria.md](../quality/acceptance-criteria.md).
