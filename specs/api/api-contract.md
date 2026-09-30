# API contract v1

- Trạng thái: **As-built**
- Base path: `/api`
- Implementation: `app/api.py`

## Quy ước chung

- JSON không có một casing duy nhất: top-level workspace/bootstrap và lineage payload chủ yếu dùng camelCase; entity/audit rows, manifest, `ImportOutcome` và import history giữ snake_case từ dataframe/dataclass/storage. Client MUST dựa trên schema của từng endpoint, không tự đổi casing toàn cục.
- Date dùng ISO `YYYY-MM-DD`; timestamp lưu/trao đổi ở dạng ISO.
- Opaque refs MUST được xem như chuỗi không thể suy diễn.
- Response workspace có header `Server-Timing`; client không được coi timing là business contract.
- API hiện chưa có authentication/authorization và chỉ dành cho môi trường nội bộ tin cậy.

## Source resolution

- API phục vụ đúng một logical source tại một thời điểm qua server setting `EVP_SOURCE_KEY`, mặc định `cx_report_master`.
- `/api/bootstrap` trả source hiện hành trong `sourceKey`.
- Preview/commit không nhận `source_key` từ multipart form; commit luôn dùng source do server cấu hình.
- CLI import có `--source-key` riêng. Đây không phải field của public API v1.

## Endpoint catalog

| Method | Path | Mục đích |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/bootstrap` | Danh sách project, counters và date bounds |
| GET | `/projects/{project}/entities` | Hierarchy của project |
| GET | `/projects/{project}/workspace` | Read model cho các tab phân tích |
| GET | `/projects/{project}/export.csv` | Export normalized rows |
| POST | `/imports/preview` | Parse/validate, không ghi database |
| POST | `/imports` | Commit workbook đã preview |
| GET | `/imports` | Tối đa 100 import attempt gần nhất |
| GET | `/projects/{project}/observations/{observationRef}/provenance` | Nguồn exact observation |
| GET | `/projects/{project}/observations/{observationRef}/revisions` | Lịch sử revision |
| GET | `/projects/{project}/audit/lookup` | Mở đúng audit row theo refs |
| GET | `/projects/{project}/aggregates/{aggregateRef}/provenance` | Contract của aggregate point |
| GET | `/projects/{project}/aggregates/{aggregateRef}/contributors` | Contributor có phân trang |
| GET | `/projects/{project}/imports/{importRef}` | Chi tiết committed import |
| GET | `/ai/status` | Trạng thái AI/config/privacy, không chứa secret |
| POST | `/ai/provider/check` | Explicit model discovery; không gửi business data |
| POST | `/projects/{project}/ai/trend-summary` | Tạo Trend Summary cho một entity/window |
| GET | `/ai/analyses/{analysisId}` | Đọc snapshot in-memory và kiểm tra stale |

## Workspace query

`GET /projects/{project}/workspace`

| Tham số | Giá trị/default | Quy tắc |
|---|---|---|
| `view` | `all` | `all`, `overview`, `statistics`, `comparison`, `audit` |
| `mode` | `recent` | `recent`, `week`, `month`, `custom` |
| `count` | `8` | 1–60; `recent` vẫn chọn 10 ngày dữ liệu gần nhất |
| `start`, `end` | null | Bắt buộc hợp lệ với `custom` và nằm trong biên dữ liệu |
| `entity` | auto | Phải thuộc project; bỏ trống chọn entity nông nhất có data |
| `scope` | `node` | `node` hoặc `children` |
| `statistics_group` | `week` | `day`, `week`, `month`, `quarter` |
| `statistics_mode` | `both` | `both`, `sum`, `average` |
| `include_incomplete` | `true` | Có/không gồm kỳ biên chưa đầy đủ |
| `statistics_count` | `8` | 1–3660 |
| `statistics_from`, `statistics_to` | null | Lọc kỳ thống kê |
| `comparison_metric` | `Báo sai/Lỗi` | Một trong ba metric ở lens `metric`; được giữ nhưng bỏ qua ở lens `statistics` |
| `comparison_entities` | rỗng | Danh sách ID ngăn bởi dấu phẩy, tối đa 3 |
| `comparison_anchor` | null | Bật Contextual Comparison; anchor phải thuộc direct-child scope hiện tại |
| `comparison_lens` | `metric` | `metric` hoặc `statistics`; mặc định giữ hành vi Phase 1 |
| `comparison_calculation` | `sum` | `sum` hoặc `average_per_day`; chỉ áp dụng khi lens là `statistics` |
| `audit_offset` | `0` | Không âm |
| `audit_limit` | `100` | 1–500 |

Response MUST có `dataVersion`, `window`, `selectedEntity`, `scopeIds`, `overview`, `statistics`, `statisticsPeriods`, `comparisonCandidates`, `comparison`, `comparisonTable`, `capabilities` và `audit`. Khi request một `view` riêng, các section không được yêu cầu trả collection rỗng/null phù hợp thay vì âm thầm tính toàn bộ.

`dataVersion` là additive contract dùng để nhận diện current committed data đã dựng workspace:

```json
{
  "dataVersion": {
    "committedImportRef": "imp_opaque",
    "committedAt": "2026-09-28T10:00:00+00:00"
  }
}
```

- `committedImportRef` là public identity opaque; client MUST không dùng hoặc suy diễn `run_id` nội bộ.
- Hai workspace có cùng `committedImportRef` được dựng từ cùng current committed revision của source, dù filter khác nhau.
- `dataVersion` mới chỉ nhận diện current read model. Workspace API không nhận revision/import ref lịch sử và không thể tính lại chart tùy ý trên revision cũ.
- Exact lineage và aggregate snapshot đã đăng ký vẫn có thể resolve bất biến theo ref cũ; khả năng này không đồng nghĩa với historical workspace query.

### Contextual Comparison (additive)

Khi có `comparison_anchor`, server áp dụng contract khác với luồng So sánh cũ. Luồng cũ không còn là tab điều hướng nhưng contract backend vẫn được giữ để tương thích:

- candidate chỉ là true sibling cùng project và cùng non-null `parent_entity_id`;
- anchor luôn đứng đầu `comparisonSelection.accepted` và không thể bỏ;
- tối đa ba entity tính cả anchor;
- eligibility được tính lại theo `comparison_metric` ở lens Chỉ số gốc; ở lens Thống kê, backend dùng các cặp `(metric, kỳ)` của cả hai chỉ số đếm, cùng period range, grain, calculation và effective unit;
- numeric zero là giá trị hợp lệ; missing không tạo comparable point;
- chế độ `metric`: ngày dùng exact daily point; tuần/tháng/quý dùng period sum hoặc weighted rate hiện có;
- chế độ `statistics`: không có lựa chọn metric; backend trả đồng thời `Tổng số` và `Báo sai/Lỗi` hiện có, cùng dùng `period_sum` hoặc `average_per_day` cho ngày/tuần/tháng/quý;
- response cũ vẫn tương thích: `comparisonCandidates` và `comparison` được giữ, đồng thời thêm `comparisonContext`, `comparisonSelection` và `comparisonTable`;
- `comparisonTable` chỉ có dữ liệu ở chế độ Thống kê, có cột `metric`, dùng cùng prepared frame với biểu đồ và có `aggregateRef` khi bằng chứng đủ điều kiện.

Mã lý do hiện có: `UNIT_UNKNOWN`, `UNIT_MISMATCH`, `ANCHOR_NO_VALUE`, `NO_METRIC_VALUE`, `RATE_NUMERATOR_MISSING`, `STATISTIC_VALUE_MISSING`, `NO_ELIGIBLE_DAYS`, `DIRECT_TOTAL_REQUIRED`, `NO_OVERLAPPING_PERIOD`, `NOT_SIBLING`, `LIMIT_REACHED`. `RATE_NUMERATOR_MISSING` nghĩa là có tỷ lệ nguồn dương nhưng thiếu `Báo sai/Lỗi`, nên backend không suy ngược tử số đã làm tròn để tạo tỷ lệ theo kỳ. Lens Thống kê bỏ qua `comparison_metric` để tương thích ngược và không trả `STATISTIC_METRIC_UNSUPPORTED`. Yêu cầu có anchor ngoài phạm vi node con trực tiếp trả `422` với mã `CONTEXTUAL_ANCHOR_OUT_OF_SCOPE`.

Nếu không có `comparison_anchor`, endpoint giữ nguyên logic/casing của Comparison tab cũ và các field contextual trả `null`.

## Import contract

### Preview

`POST /imports/preview`, multipart field `file`.

Response `200`:

```json
{
  "manifest": { "source_hash": "...", "record_count": 0, "projects": [] },
  "valid": true,
  "issues": [],
  "errorCount": 0,
  "warningCount": 0
}
```

### Commit

`POST /imports`, multipart fields:

- `file`: workbook;
- `mode`: `incremental` hoặc `full_snapshot`;
- `expected_hash`: `manifest.source_hash` từ preview.

API không nhận declared scopes, `missing_policy`, `source_key` hoặc `allow_replay`. Với `full_snapshot`, storage core tự tạo scope theo sheet/date và dùng `missing_policy=ignore`; xem `IMP-009` và `IMP-016`.

Response thành công là `ImportOutcome` mô tả trong [import-process.md](../core/import-process.md). Client MUST xử lý cả `committed` và `duplicate` như kết quả xác định, không tự retry mù khi không rõ server đã commit hay chưa.

## CSV export

`GET /projects/{project}/export.csv` trả toàn bộ current normalized rows của project từ SQLite, không áp dụng entity/time/audit-page filter của workspace. Response dùng `text/csv; charset=utf-8`, không ghi index và đặt filename `normalized-data.csv`. Test hiện chỉ xác nhận endpoint trả `200`; nội dung, header và filter-independence còn là acceptance coverage gap.

## Cache identity

Source cache và workspace cache phía server đều đưa latest committed `run_id` vào cache key. Committed run mới vì vậy tạo key mới mà không cần xóa cache cũ ngay lập tức. Hành vi nút refresh và client-side request deduplication thuộc `DASH-*`.

`run_id` chỉ là cache/revision identity nội bộ. Public client đối chiếu freshness bằng `dataVersion.committedImportRef`.

## Lineage contract

- Exact point mang `observationRef` và `lineageRef` contract version 1.
- Aggregate point mang `aggregateRef`; contributor pagination dùng cursor opaque gắn với aggregate.
- Cursor bị sửa hoặc dùng sai contract trả `422`.
- Snapshot cũ vẫn resolve đúng revision cũ và báo freshness nếu có data mới hơn.

## Error semantics

| HTTP | Ý nghĩa điển hình |
|---:|---|
| `404` | Project/ref không tồn tại hoặc không thuộc project |
| `409` | Hash thay đổi hoặc observation/lineage ref mismatch |
| `413` | Workbook vượt 50 MB |
| `422` | File/mode/filter/cursor/quality gate không hợp lệ |

Lineage error có object `detail` chứa `code`, `message` và có thể có `retryable`. Client MUST hiển thị thông báo an toàn và không suy đoán một lineage khác.

## AI Trend Summary API

AI endpoint chỉ hoạt động khi `EVP_AI_ENABLED=true`. Việc gọi external model còn yêu cầu `EVP_AI_EXTERNAL_ALLOWED=true` và cấu hình `GEMINI_*` hợp lệ. Khi privacy gate đóng, endpoint vẫn có thể trả deterministic facts với `provider_unavailable`; không có request business data nào rời server.

`POST /projects/{project}/ai/trend-summary` nhận JSON:

```json
{
  "entityRef": "opaque-core-entity-id",
  "metricCode": "error",
  "start": "2026-09-01",
  "end": "2026-09-14",
  "groupBy": "week",
  "scope": "node"
}
```

`metricCode` chỉ nhận `total`, `error`, `error_rate`; `groupBy` nhận `day`, `week`, `month` và mặc định `day`; Phase 1 chỉ nhận `scope=node`. Start/end inclusive và phải tạo được context từ committed current view của project. Response `ai-trend-v2` gồm `analysisId`, `status`, `scope`, `window`, `dataAsOf`, `metric`, `series`, `facts`, `quality`, `evidence`, `narrative`, `provider`, `validation`.

`series` chứa tối đa 60 kỳ theo thứ tự thời gian; request tạo nhiều hơn 60 kỳ trả `422 AI_REQUEST_INVALID` để người dùng chọn grain lớn hơn hoặc thu hẹp khoảng, không âm thầm cắt dữ liệu. Mỗi kỳ có boundary/label, value, số ngày quan sát/kỳ vọng, `evidenceId` và `change` so với kỳ hợp lệ ngay trước đó. `change` gồm absolute delta, relative percent hoặc `null` khi baseline bằng zero, direction và fact ID. Count được cộng theo kỳ; `error_rate` là ratio of sums trên các cặp tử số/mẫu số hợp lệ theo từng ngày, không lấy trung bình daily percentage và không ghép tử số của ngày thiếu mẫu số với ngày khác. Kỳ không có dữ liệu không được tự điền zero và phải xuất hiện trong limitation/coverage. `facts` vẫn giữ fact đầu–cuối để tương thích trình bày tổng quan, đồng thời thêm fact từng kỳ và `trend_pattern` của toàn chuỗi.

Status cuối gồm `ready`, `insufficient_data`, `provider_unavailable`, `rejected_output`, `stale`. `pending` chỉ là trạng thái UI local vì API Phase 1 non-streaming. Exact evidence chứa đúng `observationRef + lineageRef`; derived/aggregate evidence chứa `aggregateRef`. `dataAsOf.committedImportRef` là opaque; raw `run_id` không được expose.

`GET /ai/status` chỉ trả boolean/config metadata và model name. `POST /ai/provider/check` là explicit operator action gọi `/models`, không chạy tự động từ dashboard. `GET /ai/analyses/{analysisId}` chỉ đọc được snapshot còn trong cùng server process; import mới đổi status thành `stale` nhưng không rewrite fact cũ.

Error bổ sung: `409 AI_FEATURE_DISABLED`, `422 AI_REQUEST_INVALID`, `404 AI_ANALYSIS_NOT_FOUND`. API không log hoặc trả API key, raw prompt/provider response. Contract chi tiết và privacy boundary nằm tại [AI/Data v2.1](../ai-data/README.md).

## Thay đổi contract

Thêm field tương thích ngược được phép trong v1. Xóa/đổi nghĩa field, đổi status code hoặc đổi quy tắc filter MUST cập nhật spec, frontend, test API và tăng contract version khi client cũ không còn an toàn.
