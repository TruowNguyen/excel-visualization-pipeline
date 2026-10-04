# 04 — Hợp đồng dữ liệu, bằng chứng, đầu ra LLM và tích hợp AI

## Cập nhật generation v4 — 02/10/2026

Policy hiện tại: `semantic-grounding-v4`. Số được đối chiếu với `value` hoặc `displayValue` của chính fact/point đúng KPI và đơn vị, không dùng epsilon hoặc tự làm tròn. Range dates không được dùng để suy ra date–value binding; ngày điểm rõ ràng vẫn phải khớp. Chủ ngữ được giải quyết trong từng câu, gồm tên rút gọn tỷ lệ và chủ ngữ ghép. Provider schema không đổi; prompt `trend-summary-v13` / `metric-overview-v9`. [As-built v4 và đánh giá live](evidence/2026-10-02-validator-v4-and-prompt-evaluation.md). Đoạn về chính sách v3 sau đây là baseline trước nâng cấp.

Provider input `ai-insight-provider-input-v4`, narrative `ai-narrative-v4`; public trend/overview envelope không đổi. Claim bắt buộc đúng `{candidateId, claimType, text, factIds}`; tối đa hai claim/650 ký tự; selectedCandidateIds chỉ là guidance. Citation relation giải quyết dependency closure đã kiểm chứng, không repair ID giả. Validation tách structure, grounding, numerical_temporal, semantic/safety. Có survivors: ready/ai và validation=partial khi claim khác bị loại; không có survivors: rejected_output/deterministic. Additive validation.categories và claimResults phục vụ debug/eval. Chính sách hiện tại `semantic-grounding-v3` thêm `validation.warnings` và `claimResults[].warnings`: cảnh báo cách diễn giải không làm claim bị loại hoặc kích hoạt partial/fallback. Xem [chính sách ưu tiên độ đúng dữ liệu](evidence/2026-10-02-data-first-validator.md) và [bằng chứng v2 trước đó](evidence/2026-10-02-semantic-validator-and-live-evaluation.md); legacy contracts bên dưới vẫn phục vụ snapshots cũ.

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
- `AI-CON-005`: Metric item MUST dùng core canonical code `total`, `error` hoặc `error_rate`. Request có thể dùng selection code `all` để yêu cầu overview của cả ba; `all` không phải KPI. Label như `Báo sai/Lỗi` nằm trong trường `metricDisplayName` riêng.
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
  "schemaVersion": "ai-trend-v3",
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
  "periodAnalytics": {"policyVersion": "period-level-v1", "peak": {}, "lowest": {}, "largestIncrease": null, "largestDecrease": {}, "consecutiveIncrease": null, "consecutiveDecrease": {}, "endingPlateau": {}, "latestChange": {}},
  "historicalContext": {"status": "available", "policyVersion": "trailing-12-periods-v1", "lookbackPeriodLimit": 12, "observedPeriodCount": 4},
  "quality": {"status": "valid", "validPeriodCount": 2, "expectedPeriodCount": 2, "policyVersion": "period-series-v3"},
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

### 4.0. Analytical overview v2 — runtime 02/10/2026

Runtime có `synthesis` dùng `ai-narrative-v3` cho cả single và overview. Provider trả chính xác root `{schemaVersion, analysisId, status, claims}`; mỗi claim có `{candidateId, text, factIds}` và đúng thứ tự candidate đã chọn. Input `ai-insight-provider-input-v3` chỉ gồm selected candidates, typed facts, anchors và limitations; không gửi full series, canonical paragraph, validation expressions hoặc provenance nội bộ. Validator khóa schema, relation kind/operands, citations, metric, direction và scope qua grammar tương đương có giới hạn; bác số/ngày mới, nguyên nhân, significance, đánh giá chất lượng và dự báo. Không có exact full-paragraph equality trên path v3. Backend normalize thành summary/insights/limitations/suggestedChecks cho API; đây không phải cùng shape với provider JSON. Ví dụ v1 bên dưới và exact-copy validator v1/v2 chỉ còn phục vụ snapshot legacy không có synthesis.

`synthesis` chứa policyVersion `grounded-synthesis-v1`, candidates và selectedCandidateIds; relation facts tham chiếu operandFactIds/evidenceIds. Checksum bao gồm synthesis và inspectionChecks. Full chronology vẫn giữ trong snapshot; provider không nhận dump chronology. Phạm vi `contiguous_block` luôn được nói rõ và không biến thành kết luận toàn khoảng.

`periodAnalytics.temporalStructure` (policy `chronological-stages-v1`) chứa `stages[]`, `turningPoints[]`, `gaps[]`, `overviewText`, `summaryText`, `overviewFactIds`, `summaryFactIds`, dependencies và evidence IDs. Các giai đoạn có indices, boundaries/labels, direction, transitionCount và canonical text phục vụ detail/legacy. Fact `temporal_structure`/`temporal_narrative` dẫn về supportingFactIds và evidence của toàn chuỗi. Snapshot/UI giữ đầy đủ giai đoạn; provider v3 chỉ nhận selected relation candidates và facts phụ thuộc, không nhận canonical summary hoặc toàn bộ chronology. Không thêm provider call/retry hay tăng token budget.

- `AI-CON-036`: Overview mathematical relationship MUST dùng aligned complete endpoints, cùng contributors đủ điều kiện của rate, positive denominator và evidence của operands; count độc lập không khớp MUST giữ description với limitation.
- `AI-CON-037`: Overview candidate text/dependencies MUST được validate exact và không heuristic repair; unsupported business cause/quality judgement MUST không được thêm.
- `AI-CON-038`: Inspection checks MUST thuộc backend và mở logical evidence ID trong captured snapshot, không do LLM tạo target.

Provider v2 giữ boundary normalized facts only, chỉ gửi candidate text, selected facts, logical IDs; không truyền comparisonBasis toàn bộ ngày/contributors, entity label hoặc core provenance refs. Không phát sinh thêm provider call/retry hoặc tăng output budget. Approval môi trường hiện tại không suy ra permission cho raw data hay nguồn mới.

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

Synthesis v3 giữ shape claims v3 và `minimumTrendPeriods=4`; bỏ các fields correlation của thử nghiệm v2. Candidate liên hệ có `relationshipDescription` (observation, interpretation, comparisonContext); fact `insight_relation` tham chiếu đủ period operands của cả ba KPI trong cùng đoạn. Provider nhận quan hệ đã kiểm chứng, không tự tính KPI hoặc correlation. API/checksum/safety gates giữ nguyên.

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

Synthesis v4 thêm `reading` (`policyVersion=analytical-reading-v1`, `overview`, `phases[]`, `takeaways[]`). Overview/phases/takeaways giữ factIds; phases/takeaways giữ evidenceIds. Ranh giới giai đoạn theo Báo sai/Lỗi nếu khả dụng, nếu không theo metric có dữ liệu; metric khác được mô tả theo các kỳ bên trong cùng giai đoạn, không chỉ hai endpoint. Không nối gaps. Các nhịp đổi chiều ngắn liên tiếp được gộp; giai đoạn dài và giữ nguyên vẫn riêng. Phần liên hệ chỉ dùng candidate có operands đủ cùng giai đoạn. Reading được checksum-pin cùng synthesis, không thêm model arithmetic hoặc request. Canonical và validated narrative được chuẩn hóa thành câu ngắn; validator vẫn kiểm chứng trước khi chuẩn hóa.
