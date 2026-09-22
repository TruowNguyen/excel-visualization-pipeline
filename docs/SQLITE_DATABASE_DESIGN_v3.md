# Thiết kế SQLite cho lịch sử dữ liệu và cập nhật workbook — v3

## 0. Trạng thái tài liệu

- Phiên bản: `3.0`
- Phạm vi: persistence local bằng SQLite cho pipeline Excel hiện tại.
- Thay thế về mặt thiết kế: `SQLITE_DATABASE_DESIGN_v2.md`.
- Mục tiêu triển khai: giữ toàn bộ lịch sử giá trị, cập nhật workbook an toàn, audit được từng lần upload và phục vụ dashboard từ current state.

### Các thay đổi chính so với v2

1. Tách `import_attempts` khỏi `import_runs` để ghi được cả upload trùng, rejected và failed mà không xung đột unique constraint.
2. Bổ sung `import_scopes` để định nghĩa chính xác phạm vi của `full_snapshot` trước khi cho phép tombstone.
3. Tách `semantic_hash` và `lineage_hash`; thay đổi vị trí ô Excel không còn bị tính nhầm thành thay đổi giá trị nghiệp vụ.
4. Bổ sung `import_observation_presence` để audit chính xác record nào xuất hiện trong mỗi workbook, kể cả record không đổi.
5. Dùng internal surrogate ID ổn định cho entity và quản lý parser key/path bằng `entity_aliases`.
6. Chuẩn hóa transaction lifecycle để không giữ SQLite write lock trong lúc đọc và parse Excel.
7. Định nghĩa invariant cho import counters và canonical serialization trước khi hash.
8. Chốt cơ chế current pointer có nullable foreign key để tránh vấn đề circular foreign key khi insert.

---

## 1. Mục tiêu

Thiết kế phải đáp ứng các yêu cầu sau:

- lưu toàn bộ chuỗi thời gian kể từ ngày dữ liệu hợp lệ của nguồn;
- tiếp nhận workbook mới nhiều lần mà không tạo duplicate;
- thêm ngày mới và sửa dữ liệu ngày cũ;
- không làm mất giá trị trước khi sửa;
- phân biệt thay đổi dữ liệu với thay đổi vị trí/metadata nguồn;
- giữ nguồn truy vết: workbook, hash, sheet, ô Excel, parser version và parser config;
- một lần import lỗi không làm thay đổi dữ liệu đang phục vụ dashboard;
- audit được mọi lần upload, bao gồm duplicate, rejected và failed;
- audit được record nào thực sự xuất hiện trong mỗi workbook;
- dashboard đọc nhanh current state mà không phải dựng lại lịch sử revision;
- chạy local bằng SQLite và thư viện `sqlite3` chuẩn của Python;
- có thể rebuild database từ migrations, raw workbook và parser/config tương ứng.

Không dùng `INSERT OR REPLACE` trên bảng current state vì thao tác này có thể xóa dấu vết, thay đổi surrogate key và phá foreign key.

## 2. Ngoài phạm vi giai đoạn đầu

- nhiều writer import đồng thời;
- đặt SQLite trên network share hoặc thư mục đồng bộ thời gian thực;
- tự động merge entity sau khi đổi tên/di chuyển hierarchy;
- materialized aggregate tuần/tháng/quý;
- tự động tombstone khi chưa có snapshot scope đầy đủ;
- đồng bộ hai chiều từ database trở lại Excel.

---

## 3. Thuật ngữ và nguyên tắc

### 3.1. Hai loại lịch sử

1. **Lịch sử nghiệp vụ**: observation theo entity, ngày và metric.
2. **Lịch sử chỉnh sửa**: các phiên bản giá trị của cùng logical key qua nhiều import.

`observations` giữ identity và current pointer. `observation_revisions` là append-only và giữ lịch sử giá trị.

### 3.2. Attempt, artifact và run

- `source_artifact`: một nội dung file duy nhất, nhận diện bằng SHA-256.
- `import_attempt`: một lần người dùng hoặc CLI gửi file vào hệ thống. Mọi attempt đều được lưu.
- `import_run`: một lần import đã commit thành công và đã làm thay đổi hoặc xác nhận current state.

Một artifact có thể có nhiều attempt nhưng cùng một bộ:

```text
source_id + source_hash + parser_config_hash + import_contract_hash
```

chỉ được tạo tối đa một committed run.

`import_contract_hash` được tính từ canonical JSON của `import_mode` và toàn bộ declared scopes/policies. Cùng file và parser nhưng chạy với mode/scope khác có thể tạo kết quả khác nên không phải exact duplicate; tuy nhiên importer mặc định phải từ chối áp dụng lại artifact đó để tránh replay ngoài ý muốn. Contract khác chỉ được commit qua thao tác replay tường minh.

Upload trùng tạo thêm `import_attempt` có status `duplicate`, tham chiếu run cũ và không tạo `import_run` mới.

### 3.3. Replay protection

Một artifact đã commit không được tự động áp dụng lại chỉ vì người dùng đổi mode/scope. Nếu artifact cũ được chạy sau một artifact mới hơn, current values có thể bị đưa lùi về dữ liệu cũ dù không có tombstone.

Quy tắc mặc định:

- exact source/config/contract đã commit → `duplicate`;
- cùng artifact nhưng contract khác → rejected với `ARTIFACT_ALREADY_APPLIED`;
- artifact từng commit nhưng sau đó đã có artifact khác mới hơn → rejected với `STALE_ARTIFACT_REPLAY`;
- chỉ thao tác phục hồi/correction có xác nhận mới dùng `allow_replay`;
- explicit replay tạo `import_contract_hash` mới chứa replay attempt ID để vẫn audit/idempotent ở cấp run;
- phải backup trước replay.

Dashboard không tự import khi widget rerun. Chọn file chỉ parse/validate preview; database chỉ thay đổi sau khi người dùng bấm **Xác nhận import**.

### 3.4. Logical key của observation

```text
source_id + entity_id + observed_date + metric_code
```

Không đưa unit vào logical key. Sửa unit là revision của cùng observation.

### 3.5. Current state và append-only history

- `entities` và `observations` là current index.
- `entity_revisions` và `observation_revisions` chỉ append.
- current pointer được phép `NULL` khi vừa tạo row, sau đó được cập nhật trong cùng transaction.
- dashboard chỉ đọc các current view mặc định.

### 3.6. Ý nghĩa dữ liệu thiếu

Database giữ nguyên semantics do parser cung cấp:

- ô trống: không ghi nhận được dữ liệu trong ngày, ví dụ `value_kind=not_recorded`;
- dấu `-`: marker riêng của nguồn, không tự động đồng nhất với ô trống;
- số `0`: giá trị số hợp lệ;
- `NULL`: không có numeric value, không mặc định đồng nghĩa với `0`;
- phần trăm được lưu numeric theo canonical rule và hiển thị theo `display_value`/format.

Storage layer không tự diễn giải lại hoặc tự tính `% báo sai`; business rule thuộc parser/normalization layer.

---

## 4. Chế độ import và phạm vi snapshot

### 4.1. `incremental`

Workbook chỉ chứa phần dữ liệu cần thêm hoặc cập nhật.

- key mới: insert;
- key đã có nhưng semantic value thay đổi: update revision;
- key đã có và giống nhau: unchanged;
- key không xuất hiện: không làm gì;
- không tombstone observation;
- không deactivate entity vì vắng mặt.

### 4.2. `full_snapshot`

Workbook tuyên bố đại diện đầy đủ cho một hoặc nhiều phạm vi được khai báo trong `import_scopes`.

Một full snapshot có thể:

- vừa sửa dữ liệu cũ vừa thêm dữ liệu mới;
- chỉ thêm dữ liệu mới;
- chỉ sửa dữ liệu cũ;
- không thay đổi semantic value nhưng vẫn xác nhận record còn tồn tại.

Không được suy luận mode chỉ từ khoảng ngày hoặc nội dung file. `import_mode` phải do CLI/UI/config truyền tường minh.

### 4.3. Snapshot scope

Mỗi `full_snapshot` phải có ít nhất một scope. Một scope mô tả:

- source;
- sheet/project;
- root entity hoặc toàn bộ project;
- metric hoặc toàn bộ metric;
- khoảng ngày;
- phạm vi có đầy đủ hay không;
- policy đối với record vắng mặt.

Quy ước trường selector `NULL` nghĩa là “tất cả trong source/scope cha”. Ví dụ `metric_code=NULL` nghĩa là tất cả metric trong scope đó.

Chỉ được tombstone khi đồng thời thỏa mãn:

```text
import_mode = full_snapshot
AND scope.is_complete = 1
AND scope.missing_policy = tombstone
AND observation nằm trong scope
AND observation không xuất hiện trong import_observation_presence của run
```

MVP sử dụng:

```text
missing_policy = ignore
```

cho mọi scope. Chỉ bật `tombstone` sau khi scope contract và test đã ổn định.

### 4.4. Bốn kịch bản nghiệp vụ

| Case | Mode | Dữ liệu cũ | Dữ liệu mới | Kết quả |
|---|---|---|---|---|
| 1 | `full_snapshot` | Có thay đổi | Có | insert + update + unchanged |
| 2 | `full_snapshot` | Không đổi | Có | insert + unchanged |
| 3 | `full_snapshot` | Có thay đổi | Không | update + unchanged |
| 4 | `incremental` | Không bắt buộc chứa | Có/phần nối tiếp | chỉ xử lý key có trong file |

Upload lại file/config đã committed là technical duplicate, không phải import mode thứ ba.

---

## 5. Identity contract

### 5.1. Source

`source_key` là định danh cấu hình ổn định, không dùng tên file.

Ví dụ:

```text
cx_report_master
```

### 5.2. Project

Database dùng `project_id INTEGER` làm internal ID. Parser key hiện tại được lưu ở `project_key` và unique trong từng source:

```text
UNIQUE(source_id, project_key)
```

Current view có thể expose `project_key AS project_id` để giữ tương thích với DataFrame/dashboard hiện tại.

### 5.3. Entity

Database dùng `entity_id INTEGER` làm ID ổn định. ID do parser sinh từ path không còn là primary key; nó được lưu thành `external_entity_key` trong `entity_aliases`.

Luồng resolve:

1. Tìm alias hiện hành theo `source_id + external_entity_key`.
2. Nếu có, dùng lại internal `entity_id`.
3. Nếu không có, tạo entity mới và alias mới.
4. Nếu người quản trị xác nhận rename/move là cùng một entity, thêm alias mới trỏ vào entity cũ và đóng alias cũ nếu cần.

MVP không tự đoán rename/move. Nếu không có mapping thủ công, parser key mới tạo entity mới.

### 5.4. Metric

`metric_code` là canonical code. Mapping từ label Excel sang metric code nằm trong parser config và hash của mapping phải tham gia `parser_config_hash`.

Ba metric ban đầu:

| `metric_code` | Tên hiển thị | Kiểu |
|---|---|---|
| `total` | Tổng số/Cảnh báo | count |
| `error` | Báo sai/Lỗi | count |
| `error_rate` | % báo sai | percentage |

---

## 6. Vị trí database và raw artifact

```text
data/
├── local/
│   └── analytics.sqlite3
├── raw/
│   └── <artifact_id>__<source_hash>.xlsx
└── backups/
    └── analytics_YYYYMMDD_HHMMSS.sqlite3
```

`data/` phải nằm trong `.gitignore`. Không commit database, raw workbook hoặc backup.

Workbook được lưu ở filesystem; SQLite chỉ lưu path, SHA-256, size và metadata. Không lưu `.xlsx` dạng BLOB.

Nếu file có cùng hash đã tồn tại, tái sử dụng artifact thay vì copy thêm file.

---

## 7. Sơ đồ dữ liệu

```text
data_sources
  ├──< source_artifacts ──< import_attempts
  │                              │
  │                              └── 0..1 import_runs
  │                                      ├──< import_scopes
  │                                      ├──< validation_issues
  │                                      ├──< project_revisions >── projects
  │                                      ├──< entity_revisions >── entities
  │                                      ├──< observation_revisions >── observations
  │                                      └──< import_observation_presence >── observations
  └──< projects ──< entities ──< entities (parent-child)
                         │
                         ├──< entity_aliases
                         └──< observations >── metrics
```

---

## 8. Schema đề xuất

### 8.1. `schema_migrations`

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `version` | INTEGER | PK |
| `name` | TEXT | NOT NULL |
| `applied_at` | TEXT | NOT NULL, UTC ISO-8601 |

### 8.2. `data_sources`

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `source_id` | INTEGER | PK |
| `source_key` | TEXT | NOT NULL UNIQUE |
| `display_name` | TEXT | NOT NULL |
| `source_type` | TEXT | NOT NULL DEFAULT `excel` |
| `minimum_data_date` | TEXT | nullable, `YYYY-MM-DD` |
| `created_at` | TEXT | NOT NULL |

`minimum_data_date` là cấu hình theo source. Với nguồn hiện tại đặt `2026-08-01`; không hard-code ngày này thành global database constraint.

### 8.3. `source_artifacts`

Một row cho một nội dung file duy nhất trong một source.

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `artifact_id` | INTEGER | PK |
| `source_id` | INTEGER | FK, NOT NULL |
| `source_file` | TEXT | NOT NULL |
| `archived_file_path` | TEXT | NOT NULL |
| `source_hash` | TEXT | SHA-256, NOT NULL |
| `file_size` | INTEGER | NOT NULL |
| `received_at` | TEXT | NOT NULL |

```sql
UNIQUE(source_id, source_hash)
```

### 8.4. `import_attempts`

Ghi mọi lần upload hoặc chạy CLI, kể cả không tạo run.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `attempt_id` | INTEGER | PK |
| `source_id` | INTEGER | FK |
| `artifact_id` | INTEGER | FK |
| `submitted_file_name` | TEXT | tên file ở đúng attempt này |
| `requested_mode` | TEXT | `full_snapshot`/`incremental` |
| `parser_config_hash` | TEXT | hash canonical config |
| `import_contract_hash` | TEXT | hash mode + scopes/policies |
| `import_contract_json` | TEXT | canonical contract do caller khai báo |
| `parser_version` | TEXT | version code/schema |
| `status` | TEXT | `received`, `processing`, `duplicate`, `rejected`, `failed`, `committed` |
| `duplicate_of_run_id` | INTEGER | nullable FK |
| `started_at`, `finished_at` | TEXT | UTC ISO-8601 |
| `failure_code` | TEXT | nullable |
| `failure_message` | TEXT | nullable, không chứa secret |

Một attempt `duplicate` phải có `duplicate_of_run_id`. Attempt `committed` phải liên kết được đúng một run.

### 8.5. `import_runs`

Chỉ tồn tại lâu dài cho import đã commit thành công. Trạng thái `pending` chỉ tồn tại bên trong transaction và không quan sát được sau rollback.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `run_id` | INTEGER | PK, thứ tự commit |
| `attempt_id` | INTEGER | FK UNIQUE |
| `source_id` | INTEGER | FK |
| `artifact_id` | INTEGER | FK |
| `source_hash` | TEXT | denormalized để tra cứu/audit |
| `parser_config_hash` | TEXT | NOT NULL |
| `import_contract_hash` | TEXT | hash canonical mode + scopes/policies |
| `parser_version` | TEXT | NOT NULL |
| `import_mode` | TEXT | `full_snapshot`/`incremental` |
| `status` | TEXT | `pending`/`committed` |
| `started_at`, `committed_at` | TEXT | UTC ISO-8601 |
| `minimum_data_date`, `maximum_data_date` | TEXT | phạm vi thực tế trong input |
| `input_record_count` | INTEGER | số normalized row trước dedupe |
| `accepted_key_count` | INTEGER | số logical key hợp lệ duy nhất |
| `inserted_count` | INTEGER | observation mới |
| `updated_count` | INTEGER | semantic value đổi |
| `unchanged_count` | INTEGER | semantic value không đổi |
| `restored_count` | INTEGER | tombstone xuất hiện lại |
| `deleted_count` | INTEGER | tombstone do scope policy |
| `lineage_changed_count` | INTEGER | lineage đổi nhưng semantic không đổi |
| `duplicate_key_count` | INTEGER | key trùng trong input |
| `rejected_record_count` | INTEGER | normalized row bị loại |
| `error_count`, `warning_count` | INTEGER | quality report |
| `manifest_json` | TEXT | canonical manifest |

```sql
UNIQUE(source_id, source_hash, parser_config_hash, import_contract_hash)
CHECK(import_mode IN ('full_snapshot', 'incremental'))
CHECK(status IN ('pending', 'committed'))
```

Vì failed/rejected/duplicate chỉ nằm trong `import_attempts`, unique constraint không chặn retry hợp lệ.

### 8.6. `import_scopes`

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `scope_id` | INTEGER | PK |
| `run_id` | INTEGER | FK |
| `sheet_name` | TEXT | nullable selector |
| `project_key` | TEXT | nullable selector do caller khai báo |
| `project_id` | INTEGER | nullable resolved FK |
| `root_external_entity_key` | TEXT | nullable selector do caller khai báo |
| `root_entity_id` | INTEGER | nullable resolved FK, gồm cả descendants |
| `metric_code` | TEXT | nullable FK |
| `date_from`, `date_to` | TEXT | bắt buộc, inclusive |
| `is_complete` | INTEGER | 0/1 |
| `missing_policy` | TEXT | `ignore`/`tombstone` |
| `scope_hash` | TEXT | hash canonical selector |

```sql
CHECK(date_from <= date_to)
CHECK(is_complete IN (0, 1))
CHECK(missing_policy IN ('ignore', 'tombstone'))
UNIQUE(run_id, scope_hash)
```

`incremental` không được có `missing_policy='tombstone'`.

`scope_hash` được tính từ selector do caller khai báo (`sheet_name`, `project_key`, `root_external_entity_key`, metric và date range), không tính từ internal ID. Importer phải resolve mỗi selector sang đúng project/entity trước khi diff; selector không resolve được hoặc resolve mơ hồ phải làm quality gate fail.

### 8.7. `projects`

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `project_id` | INTEGER | PK |
| `source_id` | INTEGER | FK |
| `project_key` | TEXT | parser/business key |
| `current_revision_id` | INTEGER | nullable FK |
| `first_seen_run_id` | INTEGER | FK |
| `last_seen_run_id` | INTEGER | FK |
| `is_active` | INTEGER | 0/1 |

```sql
UNIQUE(source_id, project_key)
```

### 8.8. `project_revisions`

Append-only để thay đổi label hoặc source metadata của project không ghi đè lịch sử:

```text
project_revision_id INTEGER PK
project_id INTEGER FK
run_id INTEGER FK
semantic_hash TEXT
project_label TEXT
sheet_name TEXT
recorded_at TEXT
```

```sql
UNIQUE(project_id, run_id)
```

### 8.9. `entities`

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `entity_id` | INTEGER | PK, stable internal ID |
| `source_id` | INTEGER | FK |
| `project_id` | INTEGER | FK |
| `parent_entity_id` | INTEGER | nullable self FK |
| `current_revision_id` | INTEGER | nullable FK |
| `first_seen_run_id` | INTEGER | FK |
| `last_seen_run_id` | INTEGER | FK |
| `is_active` | INTEGER | 0/1 |

```sql
CREATE INDEX idx_entities_project ON entities(project_id, is_active);
CREATE INDEX idx_entities_parent ON entities(parent_entity_id, is_active);
```

Không tự deactivate entity trong MVP chỉ vì entity không xuất hiện trong một workbook.

### 8.10. `entity_aliases`

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `alias_id` | INTEGER | PK |
| `source_id` | INTEGER | FK |
| `external_entity_key` | TEXT | parser-generated key/path key |
| `entity_id` | INTEGER | FK tới stable entity |
| `valid_from_run_id` | INTEGER | FK |
| `valid_to_run_id` | INTEGER | nullable FK |
| `alias_reason` | TEXT | `initial`, `rename`, `move`, `manual_merge` |

Chỉ một active mapping cho mỗi `source_id + external_entity_key`. Dùng partial unique index:

```sql
CREATE UNIQUE INDEX uq_active_entity_alias
ON entity_aliases(source_id, external_entity_key)
WHERE valid_to_run_id IS NULL;
```

### 8.11. `entity_revisions`

Append-only khi semantic hierarchy thay đổi:

```text
entity_revision_id INTEGER PK
entity_id INTEGER FK
run_id INTEGER FK
semantic_hash TEXT
sheet_name TEXT
source_row INTEGER
parent_entity_id INTEGER NULL
entity_level TEXT
entity_depth INTEGER
entity_label TEXT
entity_path TEXT
unit_raw TEXT
unit_original TEXT
unit_normalized TEXT
effective_unit TEXT
unit_source_level TEXT
unit_source_entity_id INTEGER NULL
parser_rule TEXT
parser_confidence TEXT
recorded_at TEXT
```

```sql
UNIQUE(entity_id, run_id)
```

### 8.12. `metrics`

```text
metric_code TEXT PK
display_name TEXT NOT NULL
value_type TEXT NOT NULL
default_unit TEXT NULL
is_active INTEGER NOT NULL DEFAULT 1
```

### 8.13. `observations`

Một row cho một logical key.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `observation_id` | INTEGER | PK |
| `source_id` | INTEGER | FK |
| `entity_id` | INTEGER | FK |
| `metric_code` | TEXT | FK |
| `observed_date` | TEXT | `YYYY-MM-DD` |
| `current_revision_id` | INTEGER | nullable FK |
| `latest_presence_id` | INTEGER | nullable FK |
| `first_seen_run_id` | INTEGER | FK |
| `last_seen_run_id` | INTEGER | FK |
| `is_deleted` | INTEGER | 0/1 |

```sql
UNIQUE(source_id, entity_id, observed_date, metric_code)
CHECK(length(observed_date) = 10)
CHECK(observed_date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]')
CHECK(is_deleted IN (0, 1))

CREATE INDEX idx_obs_entity_date
ON observations(entity_id, observed_date)
WHERE is_deleted = 0;

CREATE INDEX idx_obs_date_metric
ON observations(observed_date, metric_code)
WHERE is_deleted = 0;
```

SQLite `CHECK` ở trên chỉ bảo vệ format cơ bản. Repository phải validate calendar date bằng `datetime.date.fromisoformat()` trước khi ghi; không dựa riêng vào `date()` của SQLite để từ chối mọi ngày lịch không hợp lệ.

### 8.14. `observation_revisions`

Append-only khi business/semantic value thay đổi hoặc lifecycle thay đổi.

| Nhóm | Cột |
|---|---|
| Identity | `revision_id`, `observation_id`, `run_id`, `change_type`, `semantic_hash` |
| Metric/value | `metric_original`, `metric_normalized`, `unit_normalized`, `effective_unit` |
| Raw/display | `raw_value_text`, `raw_value_type`, `value_numeric_text`, `chart_value_text`, `display_value`, `number_format` |
| Meaning | `value_kind`, `data_note`, `validation_status` |
| Lifecycle | `is_deleted`, `recorded_at` |

```sql
UNIQUE(observation_id, run_id)
CHECK(change_type IN ('insert', 'update', 'delete', 'restore'))
```

Numeric values dùng canonical decimal text trong hash để tránh sai khác binary float. Repository có thể cast sang numeric khi tạo DataFrame.

### 8.15. `import_observation_presence`

Ghi một row cho mỗi logical key hợp lệ xuất hiện trong run, kể cả unchanged.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `presence_id` | INTEGER | PK |
| `run_id` | INTEGER | FK |
| `observation_id` | INTEGER | FK |
| `sheet_name` | TEXT | nguồn hiện tại |
| `cell_address` | TEXT | nguồn hiện tại |
| `source_row` | INTEGER | nguồn hiện tại |
| `source_file` | TEXT | tên file nhận được |
| `lineage_hash` | TEXT | hash source/parser metadata |
| `parser_rule` | TEXT | rule dùng để parse |
| `parser_confidence` | TEXT | mức tin cậy |
| `presence_status` | TEXT | `inserted`, `updated`, `unchanged`, `restored` |

```sql
UNIQUE(run_id, observation_id)
```

Bảng này giải quyết hai nhu cầu:

- biết chính xác một workbook/run chứa observation nào;
- cập nhật lineage mới nhất mà không tạo business revision giả.

`observations.latest_presence_id` trỏ tới presence mới nhất.

### 8.16. `validation_issues`

```text
issue_id INTEGER PK
attempt_id INTEGER FK
run_id INTEGER NULL FK
severity TEXT
code TEXT
message TEXT
sheet_name TEXT NULL
cell_address TEXT NULL
external_entity_key TEXT NULL
observed_date TEXT NULL
created_at TEXT
```

Issue phát hiện trước commit vẫn audit được qua `attempt_id` dù không có run.

---

## 9. Canonical serialization và hashing

### 9.1. Quy tắc chung

Trước khi hash, payload được serialize thành canonical JSON:

- encoding UTF-8;
- Unicode chuẩn hóa NFC;
- object key sắp xếp cố định;
- không có whitespace không cần thiết;
- `null` khác chuỗi rỗng và khác `"-"`;
- boolean chỉ là `true`/`false`;
- ngày là `YYYY-MM-DD`;
- datetime là UTC ISO-8601 có hậu tố `Z`;
- số dùng canonical decimal string, không hash trực tiếp binary float;
- `-0`, `-0.0` chuẩn hóa thành `0` nếu cùng semantics;
- `NaN`/`Infinity` bị reject hoặc chuyển thành value kind tường minh trước hashing.

### 9.2. `semantic_hash`

Tối thiểu gồm:

```text
raw_value_type
raw_value_text canonical
value_numeric_text
chart_value_text
display_value
number_format
value_kind
data_note
unit_normalized
effective_unit
validation_status
```

Không gồm sheet/cell/parser metadata.

### 9.3. `lineage_hash`

Tối thiểu gồm:

```text
source_hash
sheet_name
cell_address
source_row
parser_version
parser_config_hash
parser_rule
parser_confidence
external_entity_key
```

### 9.4. Quy tắc revision

- semantic hash đổi: tạo `observation_revision`, tăng `updated_count`;
- chỉ lineage hash đổi: không tạo observation revision, tăng `lineage_changed_count` và tạo presence;
- cả hai không đổi: tạo presence, tăng `unchanged_count`;
- record mới: revision `insert`;
- tombstone xuất hiện lại: revision `restore` và tăng `restored_count`, không đồng thời tăng `updated_count`.

---

## 10. Counter invariants

Các trạng thái đối với accepted input key là loại trừ lẫn nhau:

```text
accepted_key_count
= inserted_count
 + updated_count
 + unchanged_count
 + restored_count
```

Trong đó:

- `inserted`: logical key chưa tồn tại;
- `updated`: tồn tại, chưa bị xóa và semantic hash đổi;
- `unchanged`: tồn tại, chưa bị xóa và semantic hash không đổi;
- `restored`: tồn tại nhưng đang tombstone và xuất hiện lại.

`deleted_count` đứng riêng vì được suy ra từ record vắng mặt trong complete snapshot scope:

```text
affected_count
= inserted_count
 + updated_count
 + restored_count
 + deleted_count
```

`lineage_changed_count` là diagnostic subset của các accepted key không đổi semantic; nó không cộng vào hai phương trình trên.

Nếu mỗi normalized input row chỉ được phân loại một lần thì:

```text
input_record_count
= accepted_key_count
 + duplicate_key_count
 + rejected_record_count
```

Nếu parser sinh nhiều logical record từ một ô/row thì đổi tên counter đầu vào thành `normalized_record_count` và vẫn giữ invariant tương đương ở cấp normalized record. Không để cùng một row vừa tính duplicate vừa tính rejected.

Khi nhiều row cùng tạo một logical key nhưng có giá trị xung đột, mặc định quality gate phải reject key đó thay vì âm thầm chọn row cuối cùng. Policy khác chỉ được dùng nếu được cấu hình và audit tường minh.

Entity counters, nếu cần, phải dùng tên riêng như `entity_inserted_count`, không gộp vào observation counters.

---

## 11. Transaction lifecycle

### Phase A — nhận file, không giữ write lock dài

1. Đọc bytes, tính SHA-256 và xác định/tạo `source_artifact` bằng transaction ngắn.
2. Tạo `import_attempt(status='received')`.
3. Tính canonical `parser_config_hash` và `import_contract_hash` từ mode/scopes/policies.
4. Kiểm tra committed run trùng key.
5. Nếu trùng: cập nhật attempt thành `duplicate`, gắn `duplicate_of_run_id`, kết thúc.
6. Cập nhật attempt thành `processing`.
7. Parse, normalize và validate workbook ngoài SQLite write transaction.
8. Nếu quality gate fail: lưu issues, cập nhật attempt thành `rejected`; current data không đổi.

### Phase B — commit dữ liệu

1. Mở connection và chạy `BEGIN IMMEDIATE`.
2. Kiểm tra duplicate key lần nữa để chống race.
3. Insert `import_runs(status='pending')` và các declared scopes.
4. Resolve/upsert project và entity identity.
5. Tạo project/entity revision khi semantic metadata hoặc hierarchy hash đổi.
6. Với mỗi accepted logical key:
   - resolve/create observation;
   - so sánh semantic hash;
   - append revision nếu cần;
   - insert presence cho mọi key;
   - cập nhật current pointer, latest presence và last seen;
   - cập nhật counter tương ứng.
7. Nếu full snapshot có complete tombstone scope, diff scope với presence và tạo revision `delete` theo policy.
8. Lưu counters/manifest và đổi run thành `committed`.
9. Cập nhật attempt thành `committed`.
10. `COMMIT`.

Nếu có lỗi ở Phase B:

- `ROLLBACK` toàn bộ run và domain changes;
- cập nhật attempt thành `failed` bằng transaction ngắn riêng;
- không có committed run dở dang;
- current state trước import giữ nguyên.

Nếu bước kiểm tra duplicate lần hai tìm thấy committed run do race, không tạo domain change: transaction hiện tại kết thúc, attempt được đánh dấu `duplicate` và trỏ tới run vừa tìm thấy.

Nếu process chết khi attempt đang `processing`, startup health check có thể đánh dấu attempt quá timeout thành `failed` với code `interrupted`.

---

## 12. Circular foreign key và thứ tự insert

`projects.current_revision_id`, `entities.current_revision_id`, `observations.current_revision_id` và `observations.latest_presence_id` phải nullable.

Thứ tự insert observation:

1. insert `observations` với pointer `NULL`;
2. insert `observation_revisions`;
3. insert `import_observation_presence`;
4. update current/latest pointer;
5. commit trong cùng transaction.

Không để project/entity/observation mới có pointer `NULL` thoát ra ngoài committed transaction.

Migration phải bật `PRAGMA foreign_keys=ON` và có integration test kiểm tra các pointer đều thuộc đúng parent observation/entity.

---

## 13. Current views cho dashboard

### 13.1. `v_current_entities`

Join `entities.current_revision_id` với `entity_revisions` và `projects.current_revision_id` với `project_revisions`, chỉ lấy các current row active. View expose parser-compatible key nếu dashboard hiện tại cần string ID.

### 13.2. `v_current_observations`

Join:

- `observations.current_revision_id` → semantic value hiện hành;
- `observations.latest_presence_id` → lineage hiện hành;
- current entity/project/metric.

View trả tên cột tương thích DataFrame hiện tại:

```text
project_id, project_label,
entity_id, parent_entity_id, entity_level, entity_depth,
entity_label, entity_path,
effective_unit,
date, metric_original, metric_normalized,
raw_value, value_numeric, chart_value, display_value,
value_kind, data_note,
sheet_name, cell_address, source_row,
number_format, parser_rule, parser_confidence,
validation_status, source_hash
```

Mặc định loại `observations.is_deleted=1`.

### 13.3. `v_import_history`

View bắt đầu từ `import_attempts`, left join `import_runs`, để hiển thị đủ:

- committed;
- duplicate và run được tham chiếu;
- rejected;
- failed;
- file/hash/parser version;
- counters và validation summary nếu có.

Không persist aggregate tuần/tháng/quý trong MVP. SUM/AVG theo kỳ được tính từ current observations; chỉ materialize khi benchmark chứng minh cần thiết.

---

## 14. Cấu hình SQLite

Mỗi connection:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
```

Nguyên tắc vận hành:

- nhiều reader, tối đa một writer;
- parameterized SQL, không nối chuỗi từ workbook;
- timestamp lưu UTC; business date lưu `YYYY-MM-DD`;
- không dùng SQLite file trực tiếp trên network share;
- transaction ghi ngắn, parse Excel bên ngoài write transaction;
- chỉ một importer process trong MVP; nếu cần nhiều importer, bổ sung application lock/queue.

Nên cân nhắc chuyển PostgreSQL khi có nhiều writer, nhiều máy truy cập trực tiếp hoặc database phải đặt trên storage mạng.

---

## 15. Backup, restore và rebuild

Không copy trực tiếp file `.sqlite3` khi WAL đang hoạt động. Dùng Online Backup API:

```python
with sqlite3.connect(source_path) as source:
    with sqlite3.connect(backup_path) as target:
        source.backup(target)
```

Quy định:

- backup trước schema migration;
- backup sau import production thành công nếu khối lượng cho phép;
- chạy `PRAGMA integrity_check` trên backup;
- lưu raw artifact theo content hash;
- manifest phải lưu parser version/config hash;
- restore smoke test phải kiểm tra schema version, foreign key và current views.

Rebuild deterministic chỉ được cam kết khi còn đủ:

```text
migrations + raw artifacts + parser code/version + parser config + import mode/scopes
```

---

## 16. Tích hợp codebase

```text
src/excel_visualization_pipeline/
└── storage/
    ├── __init__.py
    ├── connection.py
    ├── migrations.py
    ├── repository.py
    ├── importer.py
    ├── identity.py
    ├── canonical.py
    ├── hashing.py
    └── migrations/
        ├── 001_initial.sql
        ├── 002_indexes.sql
        └── 003_views.sql

scripts/
├── init_database.py
├── import_workbook.py
├── backup_database.py
├── inspect_import_history.py
└── verify_database.py
```

API dự kiến:

```python
initialize_database(db_path)
register_import_attempt(db_path, source_key, workbook_path, mode, scopes)
import_pipeline_result(db_path, attempt_id, result)
load_current_data(db_path, project_id=None, start_date=None, end_date=None)
load_current_entities(db_path, project_id=None)
load_import_history(db_path)
load_observation_history(db_path, observation_id)
backup_database(db_path, backup_path)
verify_database(db_path)
```

Dashboard chuyển nguồn theo hai bước:

1. parse workbook, commit SQLite, vẫn render từ `PipelineResult` trong giai đoạn chuyển tiếp;
2. sau khi parity test ổn định, dashboard đọc current views; upload chỉ tạo attempt/run mới.

Cache dashboard key theo `latest_committed_run_id`, không chỉ theo workbook bytes.

---

## 17. Kế hoạch triển khai

### Phase 0 — chốt contract

- xác nhận source key;
- xác nhận import mode do ai cung cấp;
- định nghĩa snapshot scopes cho từng workbook type;
- chốt missing policy mặc định là `ignore`;
- chốt mapping metric;
- chốt rule/manual workflow khi entity rename/move;
- chốt canonical hashing fixture.

Deliverable: ADR về identity, mode, scope và missing policy.

### Phase 1 — storage foundation

- migrations, connection factory và PRAGMA;
- schema artifacts/attempts/runs/scopes;
- schema hierarchy/observations/revisions/presence;
- indexes và views;
- init, migrate, backup, verify scripts.

### Phase 2 — import/upsert

- artifact archive và duplicate attempt;
- canonical hash;
- entity resolution/aliases;
- observation revision và presence;
- counters/invariants;
- rollback và rejected/failed audit;
- tombstone code tồn tại nhưng feature flag off.

### Phase 3 — dashboard read path

- repository trả DataFrame tương thích;
- SQL filter theo project/entity/date;
- ancestor coverage cho statistics;
- cache theo committed run;
- import history tối giản.

### Phase 4 — tombstone và vận hành

- bật tombstone theo từng source/scope sau acceptance test;
- backup/restore drill;
- retention raw artifacts;
- logging và health check;
- benchmark và exit criteria khỏi SQLite.

---

## 18. Test bắt buộc

### 18.1. Migration và constraint

- migration chạy hai lần không lỗi;
- foreign key enforcement bật trên mọi connection;
- current pointer thuộc đúng project/entity/observation;
- project label thay đổi tạo project revision và giữ label cũ;
- partial unique active entity alias hoạt động;
- duplicate committed run key, bao gồm import contract hash, bị chặn;
- scope date và policy check hoạt động.

### 18.2. Duplicate/attempt lifecycle

- cùng workbook/config/import contract upload hai lần tạo hai attempts nhưng một committed run;
- attempt thứ hai là `duplicate` và trỏ đúng run;
- file giống nhau nhưng parser config khác có thể tạo run mới;
- file/parser giống nhau nhưng mode hoặc scope khác bị từ chối áp dụng lại nếu chưa có explicit replay;
- stale artifact replay không thay current data;
- explicit replay tạo run mới và được audit;
- rejected/failed có attempt nhưng không thay current data;
- retry sau failed/rejected được phép;
- interrupted attempt được recovery job đánh dấu.

### 18.3. Observation history

- ngày mới tạo observation + revision `insert`;
- sửa ngày cũ tạo revision `update` và giữ revision cũ;
- unchanged không tạo revision nhưng có presence;
- đổi cell address không tăng `updated_count`;
- lineage-only change tăng `lineage_changed_count`;
- blank, `0`, `-`, text và percentage giữ đúng semantics;
- restore tạo đúng một revision `restore` và không đếm trùng update.

### 18.4. Import modes/scopes

- incremental không tombstone record vắng mặt;
- full snapshot với missing policy `ignore` không tombstone;
- full snapshot chỉ tombstone trong complete scope có policy `tombstone`;
- không tombstone ngoài date/project/entity/metric scope;
- incomplete scope không được phép tombstone;
- record hiện diện ở run không bị tombstone;
- overlap scope cho kết quả deterministic.

### 18.5. Counter invariants

- mọi committed run thỏa phương trình `accepted_key_count`;
- deleted không cộng vào accepted input keys;
- restored không đồng thời được tính updated;
- lineage changed không làm thay đổi business affected count;
- duplicate input key có issue/counter rõ ràng.

### 18.6. Integration/smoke

1. Import workbook mẫu lần đầu.
2. Import workbook có ngày mới và một giá trị cũ được sửa.
3. Import workbook chỉ đổi layout/cell, không đổi semantic value.
4. Xác nhận current view đúng dữ liệu mới nhất.
5. Xác nhận revision và presence history đầy đủ.
6. Xác nhận chart/statistics parity với pipeline DataFrame.
7. Backup, restore và chạy smoke test lại.

Baseline workbook hiện tại:

```text
Project: 6
Entity: 36
Date hợp lệ từ: 01/08/2026
Normalized record: 4.182
Chartable record: 2.343
Quality-gate error: 0
```

Các số baseline phải được kiểm tra lại nếu workbook fixture thay đổi; không dùng chúng làm database constraint.

---

## 19. Tiêu chí hoàn thành

- mọi upload được audit bằng attempt;
- cùng file/config chỉ có một committed run;
- failed/rejected/duplicate không thay current state;
- dữ liệu ngày mới xuất hiện sau commit;
- sửa dữ liệu quá khứ không làm mất revision cũ;
- unchanged vẫn truy ra được là đã xuất hiện trong run nào;
- thay đổi vị trí ô không bị tính nhầm thành business update;
- full snapshot không xóa ngoài declared scope;
- tombstone bị tắt mặc định trong MVP;
- tất cả counter invariants pass;
- current views trả kết quả tương thích pipeline;
- backup có `integrity_check=ok` và restore được;
- database rebuild được từ artifacts/config/version còn lưu;
- unit, integration và smoke test đều pass.

---

## 20. Quyết định MVP

Các mặc định triển khai đầu tiên:

```text
Storage                  = SQLite local
Writer                   = một importer process
Default import mode      = full_snapshot do caller khai báo
Missing policy           = ignore
Auto tombstone           = off
Raw artifact archive     = on
Exact run presence audit = on
Entity rename/move       = manual alias mapping
Import entry point       = CLI trước, dashboard sau
Aggregate persistence    = off
```

Chỉ bật auto tombstone khi mỗi workbook type đã có scope contract, fixture test và người phụ trách dữ liệu xác nhận file thực sự là snapshot đầy đủ của scope đó.
