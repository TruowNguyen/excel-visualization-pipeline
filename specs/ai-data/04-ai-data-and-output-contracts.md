# 04 — Hợp đồng dữ liệu, bằng chứng, đầu ra LLM và tích hợp AI

**Phiên bản đặc tả:** 2.2.0. **Trạng thái:** Contract Phase 1 as-built; contract cho comparison/report vẫn là đề xuất. **IDs:** `AI-CON-*`.

## 1. Ranh giới module

```text
Core: Excel -> validation -> SQLite committed current state/revisions/lineage
                                 |
                        read-only analytics adapter
                                 |
AI/Data: select/pin snapshot -> deterministic metrics/time comparisons
        -> coverage + evidence bundle -> LLM adapter (optional)
        -> strict output validation -> insight records
        -> report composer/template -> human review -> export
```

- `AI-CON-001`: AI/Data MUST chỉ đọc committed core data qua authorized read path. MUST NOT ghi vào core observation/revision/source artifact table.
- `AI-CON-002`: Core giữ quyền canonical đối với logical key, unit/value-kind interpretation, aggregate rule, exact/aggregate provenance và API compatibility.
- `AI-CON-003`: Không LLM response nào được tin như nguồn sự thật số liệu. Deterministic fact MUST được tạo trước khi gọi model.
- `AI-CON-004`: Mọi analysis MUST lưu data version và source/aggregate snapshot để việc regenerate ngôn ngữ không âm thầm trôi sang data mới.
- `AI-CON-005`: Trường service/API tên `metricCode` MUST dùng core canonical code `total`, `error` hoặc `error_rate`. Label như `Báo sai/Lỗi` nằm trong trường `metricDisplayName` riêng.
- `AI-CON-006`: Public/UI freshness metadata MUST dùng `importRef`/`committedImportRef` opaque và snapshot ID. Backend MAY dùng số nguyên `run_id` nội bộ nhưng MUST NOT expose nó làm public watermark.

## 2. Snapshot phân tích tất định

Phase 1 dùng `AnalysisSnapshotRepository` in-memory có giới hạn 100 snapshot/process và không persist prompt/raw response. Vì chưa chốt retention dài hạn nên không thêm migration hoặc sửa core table. Các record dài hạn dưới đây vẫn là đề xuất:

| Khái niệm | Mục đích |
|---|---|
| `analysis_request` | User scope, time, metric và policy version đã validate |
| `analysis_snapshot` | Fact bundle ổn định cùng data-as-of/version |
| `analysis_evidence` | Claim operand, calculation rule, exact/aggregate ref và coverage |
| `insight_generation` | Provider/prompt/schema version, generation status và validation outcome |
| `report_template` | Section/field schema ổn định |
| `report_version` | Draft/approved content khóa vào analysis snapshot |
| `report_review_event` | Audit của edit/approval/export |

Latest committed import có thể dùng để xác định freshness nhưng không thay thế việc lưu exact value, calculation, contributor và ref đã được report sử dụng. Core `aggregateRef` khóa aggregate snapshot; exact point cần cặp `observationRef + lineageRef`. Public contract nhận diện committed import bằng `importRef` opaque; không expose raw `run_id` hoặc tạo ref từ value/date similarity.

- `AI-CON-010`: Snapshot MUST chứa request, core data version, fact array, metric/unit/rule metadata, coverage, evidence và checksum/content version.
- `AI-CON-011`: Mọi material claim MUST trỏ tới evidence ID resolve được về captured fact và valid core reference; nếu safe provenance không có thì phải nêu rõ.
- `AI-CON-012`: Nếu expected evidence ref không resolve được hoặc thuộc project/snapshot khác, output MUST bị reject/đánh dấu unavailable; không heuristic repair.
- `AI-CON-013`: Core data mới MUST làm analysis/report cũ bị đánh dấu stale nhưng không rewrite historical snapshot.

## 3. Ví dụ gói đầu vào phân tích — dữ liệu giả lập

```json
{
  "schemaVersion": "ai-trend-v2",
  "analysisId": "demo-analysis-001",
  "kind": "trend",
  "scope": {
    "projectKey": "VSO",
    "entityIds": ["demo-entity"],
    "metricCode": "error",
    "metricDisplayName": "Báo sai/Lỗi",
    "mode": "node"
  },
  "window": {"start": "2026-09-01", "end": "2026-09-14", "groupBy": "week", "comparisonBasis": "period_over_period_and_first_last"},
  "dataAsOf": {"committedImportRef": "example-only", "snapshotId": "demo-snapshot-001"},
  "metric": {"unit": "lượt", "aggregationRule": "period_week_sum"},
  "series": [
    {"periodIndex": 0, "periodLabel": "Tuần 36/2026", "value": 120, "evidenceId": "ev-period-000", "change": null},
    {"periodIndex": 1, "periodLabel": "Tuần 37/2026", "value": 87, "evidenceId": "ev-period-001", "change": {"absolute": -33, "relativePercent": -27.5, "direction": "decreasing"}}
  ],
  "facts": [
    {"factId": "fact-change-001", "kind": "period_change", "value": -33, "evidenceIds": ["ev-period-000", "ev-period-001"]},
    {"factId": "fact-relative-change-001", "kind": "period_relative_change", "value": -27.5, "unit": "percent", "evidenceIds": ["ev-period-000", "ev-period-001"]},
    {"factId": "fact-trend-pattern", "kind": "trend_pattern", "value": "consistently_decreasing", "evidenceIds": ["ev-period-000", "ev-period-001"]}
  ],
  "quality": {"status": "valid", "validPeriodCount": 2, "expectedPeriodCount": 2, "policyVersion": "period-series-v2"},
  "evidence": [
    {"evidenceId": "ev-period-000", "periodStart": "2026-08-31", "periodEnd": "2026-09-06", "target": {"kind": "aggregate", "aggregateRef": "example-only"}},
    {"evidenceId": "ev-period-001", "periodStart": "2026-09-07", "periodEnd": "2026-09-13", "target": {"kind": "aggregate", "aggregateRef": "example-only"}}
  ]
}
```

Sample trên chỉ minh họa schema. Placeholder ref MUST NOT được xem là core reference hợp lệ hoặc được live validator chấp nhận.

Mỗi evidence target dùng đúng một trong hai cấu trúc loại trừ lẫn nhau:

```json
{"kind": "exact", "observationRef": "opaque", "lineageRef": "opaque"}
```

```json
{"kind": "aggregate", "aggregateRef": "opaque"}
```

Exact target thiếu bất kỳ thành phần nào đều invalid. Aggregate target MUST NOT giả làm một Excel cell.

## 4. Hợp đồng đầu ra LLM

Structured output dưới đây là logical schema được đề xuất, không phải API response đã tồn tại. Model trả ngôn ngữ và reference tới **fact ID đã có sẵn**; MUST NOT tự thêm numeric source-of-truth field.

```json
{
  "schemaVersion": "ai-narrative-v1",
  "analysisId": "demo-analysis-001",
  "status": "ready",
  "summary": {
    "text": "Số báo sai/lỗi giảm 33 lượt (27,5%) so với kỳ tham chiếu.",
    "factIds": ["fact-change-001", "fact-relative-change-001"],
    "claimType": "descriptive"
  },
  "insights": [
    {
      "type": "series_trend",
      "text": "Chuỗi giảm liên tục qua các kỳ hợp lệ.",
      "factIds": ["fact-trend-pattern", "fact-change-001"],
      "claimType": "descriptive"
    }
  ],
  "limitations": [],
  "suggestedChecks": ["Đối chiếu các ngày thay đổi mạnh với sổ theo dõi nghiệp vụ."]
}
```

- `AI-CON-020`: Validate JSON/schema/enum, scope, allowed claim type, fact ID, evidence availability và numeric mention với deterministic bundle.
- `AI-CON-021`: Reject numerical statement không được hỗ trợ và verified-cause language không có căn cứ. MAY regenerate theo bounded retry policy vẫn TBD; nếu không đạt, trả deterministic-only fallback.
- `AI-CON-022`: Giữ localization và unit presentation, bao gồm percentage point so với relative percent; rounding policy vẫn TBD.
- `AI-CON-023`: Output MUST phân tách `facts`, `interpretation`, `hypothesis`, `limitations` và suggested human check khi phù hợp. Hypothesis không bao giờ được trình bày như evidence-backed root cause.
- `AI-CON-024`: Coi label, note và workbook text là untrusted prompt data; chúng không được override system instruction hoặc cấp quyền access/send/tool action.

## 5. Giao diện dịch vụ và API Phase 1

Ưu tiên internal service contract:

- `build_analysis_snapshot(request) -> AnalysisSnapshot | ValidationError`
- `compute_trend(snapshot, policy) -> TrendFacts`
- `compute_comparison(snapshot, policy) -> ComparisonFacts | NotComparable`
- `generate_narrative(facts, policy) -> StructuredNarrative | Fallback`
- `compose_report(template, snapshots, narrative) -> ReportDraft`
- `validate_report(draft) -> ValidationResult`

Endpoint Phase 1 đã triển khai:

- `GET /api/ai/status`: trạng thái feature/config/privacy an toàn, không trả secret;
- `POST /api/ai/provider/check`: explicit operator check `/models`, không gửi business data;
- `POST /api/projects/{project}/ai/trend-summary`: tạo snapshot/facts/evidence/narrative;
- `GET /api/ai/analyses/{analysisId}`: đọc snapshot trong cùng process và cập nhật `stale` nếu có committed import mới.

Chi tiết request/response và error nằm tại [API contract](../api/api-contract.md). API report/approval/export vẫn **TBD**.

## 6. Ranh giới provider, quyền riêng tư và lỗi

- `AI-CON-030`: Provider/model, deployment location, allowable field, PII/security review, retention và logging MUST được duyệt trước khi gửi dữ liệu nội bộ tới external service.
- `AI-CON-031`: Giảm LLM payload xuống computed fact và label cần thiết; mặc định không gửi raw workbook, password, hidden sheet, issue text không liên quan hoặc full revision history.
- `AI-CON-032`: Redact hoặc loại secret/identifier theo approved privacy policy. Ghi model/prompt/schema/policy version và safe telemetry; tránh log raw sensitive prompt nếu chưa được phép rõ ràng.
- `AI-CON-033`: Timeout, provider error, invalid schema, missing evidence, budget/rate-limit problem MUST trả state rõ ràng; deterministic analytics vẫn dùng được.
- `AI-CON-034`: MVP không cần action-capable autonomous agent. LLM không được ghi SQLite business table, đổi config, gửi report hoặc approve report.
- `AI-CON-035`: Renderer phải sanitize/escape model/source text để chống HTML/script hoặc template injection.

## 7. Mục tiêu phi chức năng cần owner duyệt

Latency/error budget và token/cost limit vẫn TBD sau representative workbook/performance test. Repeated identical request chỉ MAY tái sử dụng validated analysis snapshot khi scope, data version, metric policy, prompt/model/schema version và privacy contract đều khớp. Việc này không làm yếu explicit replay hoặc core import idempotency.
