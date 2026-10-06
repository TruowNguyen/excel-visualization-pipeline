# API contract v1

Latest additive AI contract (04/10/2026): `POST /api/projects/{project}/ai/context-insight`, ai-context-request-v1 → ai-context-v1; node/selected/all direct-child membership, canonical Statistics periods/calculations, typed evidence and stale receipts. Semantic policy is v7; legacy trend-summary envelopes remain compatible. [Request/response and limits](../ai-data/10-context-insight-as-built.md). Validator/version statements in earlier dated updates below are historical.

Current validator policy is `semantic-grounding-v4` (prompt registry trend-summary-v13 / metric-overview-v9). Numeric validation accepts only engine-authored value/displayValue representations with existing KPI/unit/date/source binding. Sentence-local subjects and range-versus-point dates replace cross-sentence nearest-token guesses. Warnings remain additive and non-blocking. [Current implementation and live evaluation](../ai-data/evidence/2026-10-02-validator-v4-and-prompt-evaluation.md); the v3 note below is historical.

AI generation v4 update: public ai-trend-v3/ai-overview-v2 envelopes unchanged. Narrative v4 adds verified claims and validationPolicy; validation may be `partial` with additive categories/claimResults. Partial narratives remain status=ready and contain only surviving claims. Structural/provider/no-survivor failures retain existing fallback statuses. Current `semantic-grounding-v3` adds `validation.warnings` and `claimResults[].warnings` (arrays of diagnostic codes). Warnings alone do not reject a claim or change accepted to partial. See [current data-first validation policy](../ai-data/evidence/2026-10-02-data-first-validator.md) and [previous v2 evidence](../ai-data/evidence/2026-10-02-semantic-validator-and-live-evaluation.md).

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
  "metricCode": "all",
  "start": "2026-09-01",
  "end": "2026-09-14",
  "groupBy": "week",
  "scope": "node"
}
```

`metricCode` nhận `all`, `total`, `error`, `error_rate`; `groupBy` nhận `day`, `week`, `month` và mặc định `day`; Phase 1 chỉ nhận `scope=node`. `all` là mặc định trên UI và tạo một provider call cho bản tổng quan ba metric. Response dùng `ai-overview-v2`, có `metrics` chứa ba kết quả trend đã namespace fact/evidence; từng metric riêng vẫn dùng `ai-trend-v3`. `periodAnalytics` dùng policy `period-level-v1`; `historicalContext` dùng tối đa 12 kỳ hợp lệ hoàn tất ngay trước window theo policy `trailing-12-periods-v1`.

Overview v2 thêm `comparisonBasis`, `insightCandidates`, `inspectionChecks`; root không có `series`. `comparisonBasis` policy `aligned-overview-v1` chứa các kỳ/tử số/mẫu số/ngày đủ điều kiện từ chính phép tính rate, baseline/current và status `comparable|limited|unavailable` với lý do. Relational candidate chỉ được tạo khi cả ba metric có cùng endpoint boundaries, đủ ngày/cả kỳ lịch, count khớp operands và denominator dương. Numerator bằng zero không tạo relative-growth fact; `0/0` không tạo relational claim. Comparison endpoint không đồng nghĩa tổng toàn window. Cross-metric facts có `operandFactIds`, policy version và evidence IDs của các operands.

`insightCandidates[]` gồm `candidateId`, `layer` (`whole_series|relational|descriptive|temporal`), `text`, `factIds`, `evidenceIds`. `whole-window` đứng đầu và là summary duy nhất khi có. Các metric thêm `periodAnalytics.temporalStructure` (`chronological-stages-v1`): giai đoạn tăng/giảm/giữ nguyên theo thứ tự, đảo chiều quan sát được giữa hai đoạn kề nhau, gaps và canonical summary/fact IDs. Kỳ thiếu ngắt liên tục; không gọi anomaly/significance. Temporal candidate cũ vẫn cung cấp một biến động lớn với evidence; UI chronology hiển thị cả largestIncrease/largestDecrease đã có. `inspectionChecks[]` là backend-owned text/fact IDs/logical evidence IDs; UI map tới captured exact/aggregate target. Không đổi schema API: trường mới tương thích bổ sung vào `ai-trend-v3`/`ai-overview-v2`.

Runtime mới giữ API `ai-trend-v3` / `ai-overview-v2`, thêm `synthesis` policy `grounded-synthesis-v1` (candidates/selectedCandidateIds/anchors). Checksum bao gồm synthesis và inspectionChecks. Provider input `ai-insight-provider-input-v3` chỉ gửi selected candidates, typed facts, anchors và limitations, không full series, canonical paragraph, validation grammar hoặc raw core provenance. Model output `ai-narrative-v3` có `{schemaVersion,analysisId,status,claims}`; claim có `{candidateId,text,factIds}`. Validator chấp nhận diễn đạt tương đương có giới hạn, khóa meaning/scope/direction/citations và bác số/ngày mới, nguyên nhân, chất lượng, anomaly, forecast. Backend normalize thành API narrative summary/insights/limitations/suggestedChecks; numerical/date anchors và checks thuộc backend. V1/v2 exact-copy chỉ phục vụ snapshot legacy không có synthesis. Không phải unrestricted generative analysis.

`series` chứa tối đa 60 kỳ theo thứ tự thời gian; request tạo nhiều hơn 60 kỳ trả `422 AI_REQUEST_INVALID` để người dùng chọn grain lớn hơn hoặc thu hẹp khoảng, không âm thầm cắt dữ liệu. Mỗi kỳ có boundary/label, value, số ngày quan sát/kỳ vọng, `evidenceId` và `change` so với kỳ hợp lệ ngay trước đó. `change` gồm absolute delta, relative percent hoặc `null` khi baseline bằng zero, direction và fact ID. Count được cộng theo kỳ; `error_rate` là ratio of sums trên các cặp tử số/mẫu số hợp lệ theo từng ngày, không lấy trung bình daily percentage và không ghép tử số của ngày thiếu mẫu số với ngày khác. Kỳ không có dữ liệu không được tự điền zero và phải xuất hiện trong limitation/coverage. `facts` vẫn giữ fact đầu–cuối để tương thích trình bày tổng quan, đồng thời thêm fact từng kỳ và `trend_pattern` của toàn chuỗi.

Status cuối gồm `ready`, `insufficient_data`, `provider_unavailable`, `rejected_output`, `stale`. `pending` chỉ là trạng thái UI local vì API Phase 1 non-streaming. Exact evidence chứa đúng `observationRef + lineageRef`; derived/aggregate evidence chứa `aggregateRef`. `dataAsOf.committedImportRef` là opaque; raw `run_id` không được expose.

`GET /ai/status` chỉ trả boolean/config metadata và model name. `POST /ai/provider/check` là explicit operator action gọi `/models`, không chạy tự động từ dashboard. `GET /ai/analyses/{analysisId}` chỉ đọc được snapshot còn trong cùng server process; import mới đổi status thành `stale` nhưng không rewrite fact cũ.

Error bổ sung: `409 AI_FEATURE_DISABLED`, `422 AI_REQUEST_INVALID`, `404 AI_ANALYSIS_NOT_FOUND`. API không log hoặc trả API key, raw prompt/provider response. Contract chi tiết và privacy boundary nằm tại [AI/Data v2.1](../ai-data/README.md).

## Thay đổi contract

Synthesis policy v3 giữ `minimumTrendPeriods=4`, không đổi response/narrative v3. Không phát sinh `minimumCorrelationPeriods`, `correlations[]`, `correlationNote` hay `pearson_change_correlation` facts. Các candidate liên hệ dùng `relationshipDescription` và `insight_relation` với period operands của ba KPI cùng đoạn đủ điều kiện; giải thích số lượng/mẫu số/tỷ trọng, không thống kê correlation. Short-window candidates không được claim trend/extrema. Feature/privacy/committed-only/freshness giữ nguyên.

Thêm field tương thích ngược được phép trong v1. Xóa/đổi nghĩa field, đổi status code hoặc đổi quy tắc filter MUST cập nhật spec, frontend, test API và tăng contract version khi client cũ không còn an toàn.

AI synthesis policy v4 adds `reading` with version `analytical-reading-v1`, nullable overview, shared phases and distinct takeaways. Every item retains its period/relation fact IDs; phase/takeaway source IDs use existing captured evidence. The additive field is pinned within synthesis checksum. Existing response/narrative schemas, one-call provider budget, KPI rules and safety gates remain unchanged. Clients without reading support may continue rendering the validated narrative; new clients use its deterministic reading structure and identify that copy as “Tổng hợp từ số liệu”.

# Bổ sung API — Tổng quan theo nguồn (05/10/2026)

GET workspace nhận optional `overview_source` trên overview/statistics/all; trả `overviewSummary` trên overview/all và `statisticsSummary` trên statistics/all (field ngoài view trả null). Statistics dùng danh sách kỳ/cách tính hiện có; summary thêm `calculation`/`requestedMode`, window null khi không có kỳ phù hợp. Khóa ba metric gốc và các response chart/Comparison hiện có không đổi. Summary dùng chung public `workspace.dataVersion`, không tạo run hoặc historical query mới. Source không hợp lệ trả 422, đọc version bị thay đổi liên tiếp tối đa ba lần trả 503 có thể thử lại.

Contract đầy đủ về sourceChoices, status, period coverage, extrema/change và cache identity: [Overview summary](../frontend/overview-summary-metrics.md#3-api-và-version). Đây là field additive; frontend không fallback metadata khi thiếu field.

## Tab Báo cáo — as-built 05/10/2026

Các route dưới dùng prefix `/api/projects/{project}/reports`; không thay API Insight cũ. Project/source ownership được kiểm tra, nhưng chưa có authentication.

| Method / suffix | Request | Response / tác dụng |
|---|---|---|
| `POST /preview` | `context`, `title`, `requestId` | Document deterministic, không lưu và không gọi AI |
| `POST /` | Như preview | Lưu captured v1; idempotent cùng requestId/payload |
| `GET /` | — | `{items}`: 100 bản cập nhật gần nhất của project/source |
| `GET /{reportId}` | — | Latest document + versions/local review/freshness |
| `GET /{reportId}/revisions/{revision}` | — | Exact immutable document |
| `POST /{reportId}/revisions` | `baseRevision`, `requestId`, optional `title`, `userNotes`, `selectedFindingIds`, `narrativeEdits` | Kiểm chứng lời sửa rồi lưu revision mới; không đổi số liệu |
| `POST /{reportId}/regenerate` | `baseRevision`, `requestId` | Diễn giải snapshot đã lưu bằng existing LLM/validator; revision mới, giữ manual edits |
| `POST /{reportId}/revisions/{revision}/check` | — | Local check chỉ cho latest; publicationStatus luôn draft |
| `POST /{reportId}/revisions/{revision}/exports` | `{format:"pdf"}` hoặc `{format:"docx"}` | Actual bytes, attachment; ghi exact revision và content hash |

`context` dùng `ai-context-request-v1`: `view`, `parentEntityRef`, `selection`, `entityRefs`, `metricCode`, grain/window/calculation/range/partial fields như context Insight. Tổng quan không nhận quarter; Thống kê không nhận error_rate. `expectedImportRef` tùy chọn phải khớp committed snapshot; không có thì backend tự chụp đúng version.

`requestId` 8–100 ký tự `[a-zA-Z0-9_-]`, create/title 1–200 ký tự không được chỉ là whitespace. Notes tối đa 5.000 ký tự. Selection tối đa 5 finding IDs thuộc báo cáo; tối đa 24 narrative edit entries, mỗi entry 1–5.000 ký tự. Root request từ chối field ngoài allowlist; không nhận đường dẫn xuất, facts/chart/source overrides hay arbitrary anchors.

Public document `cx-report-v1` có template `cx-period-report` 1.0; context/window/dataAsOf; kpis/charts/blocks/executiveSummary/findings/selectedFindingIds; limitations/evidence/facts; manualEdits/userNotes; generation/review/freshness/versions. `_bundle` nội bộ không expose. Summary có dependencies và có thể source mixed khi ghép AI với Engine.

Lỗi: `409 REPORT_CONFLICT` cho stale revision/idempotency payload mismatch/import thay đổi trong capture; `404 REPORT_NOT_FOUND` cho report/revision không thuộc project/source; `422 REPORT_INVALID` cho lựa chọn/lời sửa chưa đối chiếu được hoặc export/font invalid. Context preparation còn dùng `422 AI_CONTEXT_INVALID`. AI disabled trả `409 AI_FEATURE_DISABLED` khi regenerate, nhưng deterministic capture/export vẫn hoạt động.

Export trả `application/pdf` hoặc DOCX MIME; `Content-Disposition`, `X-Report-Revision`, `X-Content-SHA256`, `Cache-Control: no-store`. File đầu tiên của revision/format được lưu; lần sau trả nguyên byte, không render theo filters/review mới. Chỉnh sau đó tạo revision mới. File luôn DRAFT; không có approved/send/publish/delete endpoint.
