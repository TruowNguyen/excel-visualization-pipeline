# Báo cáo có AI hỗ trợ — Hồ sơ triển khai v2

- Phiên bản đặc tả: **2.2.0**
- Trạng thái runtime: **Phase 1 as-built, external call đã được duyệt và kiểm thử cho môi trường hiện tại** đối với trend summary; **Đề xuất** đối với comparison/reporting
- Contract canonical: [README.md](README.md)
- Product baseline: `SCP-102`, `PRD-F102`, `UC-10`
- Development provider: **9Router**, OpenAI-compatible API
- Development model mặc định: `ag/gemini-3.7-flash-low` (ưu tiên độ trễ cho luồng diễn giải facts)

Tài liệu này là hồ sơ triển khai của các module contract canonical. Nó không sở hữu namespace yêu cầu `AI-*` độc lập.

## Ranh giới runtime

AI chuyển deterministic fact có evidence thành narrative tiếng Việt ngắn gọn. AI không tính source-of-truth KPI, thay observation/revision/current pointer, import workbook, gửi notification, approve report hoặc chạy issue workflow.

Repository đã có vertical slice Trend Summary gồm adapter, endpoint, prompt runtime, validator, evidence và UI. Snapshot Phase 1 chỉ lưu in-memory; comparison/report persistence chưa tồn tại. Config example không tự bật external provider vì còn feature/privacy gate riêng.

## Hồ sơ provider

Development gateway được dự án chọn là 9Router. Server-side adapter dự kiến đọc:

- `GEMINI_API_KEY`;
- `GEMINI_API_BASE_URL`, mặc định `https://9router.com/v1`;
- `GEMINI_MODEL`, mặc định `ag/gemini-3.7-flash-low`.
- `EVP_AI_TIMEOUT_SECONDS=12`, `EVP_AI_MAX_RETRIES=0` cho request tương tác.
- `EVP_AI_MAX_OUTPUT_TOKENS=700` để giới hạn thời gian sinh narrative.

Credential phải chỉ nằm phía server. Model availability phải được kiểm tra theo account đang cấu hình; adapter không được âm thầm đổi sang model khác. Việc gửi CX data thật vẫn bị tắt cho tới khi `AI-DEC-006` duyệt allowed field, privacy, deployment region, retention và logging.

## Request runtime Phase 1

`POST /api/projects/{project}/ai/trend-summary` nhận một metric hoặc selection code `all` và một grain cho mỗi lần phân tích. `all` tạo overview của ba metric trong một provider call:

```json
{
  "entityRef": "root",
  "metricCode": "error_rate",
  "start": "2026-09-01",
  "end": "2026-09-30",
  "groupBy": "week",
  "scope": "node"
}
```

Backend resolve project, entity, metric, date và scope theo cùng rule với workspace hiện tại. Client không được gửi KPI value tùy ý để model coi là nguồn sự thật.

## Response runtime Phase 1 — rút gọn

```json
{
  "schemaVersion": "ai-trend-v3",
  "status": "ready",
  "window": {"start": "2026-09-01", "end": "2026-09-30", "groupBy": "week", "comparisonBasis": "period_over_period_and_first_last"},
  "series": [
    {"periodLabel": "01/09–06/09/2026", "value": 8.2, "change": null, "evidenceId": "ev-period-000"},
    {"periodLabel": "07/09–13/09/2026", "value": 6.7, "change": {"absolute": -1.5, "absoluteDisplay": "-1.5 pp", "relativePercent": -18.29, "direction": "decreasing"}, "evidenceId": "ev-period-001"}
  ],
  "facts": [{"factId": "fact-trend-pattern", "kind": "trend_pattern", "value": "consistently_decreasing"}],
  "provider": {"name": "9router", "model": "ag/gemini-3.7-flash-low", "promptVersion": "trend-summary-v6", "latencyMs": 5200, "attemptCount": 1},
  "dataAsOf": {"snapshotId": "analysis-snapshot-opaque", "committedImportRef": "import-ref-opaque"},
  "narrative": {"mode": "ai", "summary": {"text": "...", "factIds": ["fact-trend-pattern"]}}
}
```

Model trả reference tới deterministic fact ID, không trả numeric truth độc lập hoặc raw observation ID. Fact resolve qua typed evidence contract trong `AI-CON-*`:

```json
{"kind": "exact", "observationRef": "...", "lineageRef": "..."}
```

hoặc:

```json
{"kind": "aggregate", "aggregateRef": "..."}
```

## Hành vi bắt buộc

- Chỉ dựng context từ committed data đã khóa.
- Giữ nguyên phân biệt missing, zero, marker, invalid và numeric.
- Dùng canonical metric code `total`, `error`, `error_rate`; display label là metadata riêng.
- Tính SUM, AVG, weighted rate, comparison và direction bằng deterministic pipeline trước khi gọi model.
- Áp dụng core behavior hiện tại `0/0 -> 0%`; các invalid zero-denominator case khác trả unavailable.
- Validate output schema, fact ID, numeric mention, scope và evidence trước khi render.
- Coi workbook text là untrusted data, không phải instruction.
- Ghi provider/model/prompt/policy/snapshot metadata an toàn, không chứa secret hoặc raw internal database path.
- Đánh dấu response cũ stale khi có committed import mới; không mutate historical snapshot.
- Giữ dashboard, import và lineage hoạt động trong mọi provider failure.

## Trạng thái lỗi

| Điều kiện | Kết quả bắt buộc |
|---|---|
| Thiếu config | `provider_unavailable`; core vẫn hoạt động |
| 401/403 | Configuration error; không blind retry |
| Model unavailable | Reject request; không âm thầm đổi model |
| 429 | Bounded backoff hoặc explicit retry-later state |
| Timeout/5xx | Explicit provider failure và deterministic fallback |
| Invalid JSON/schema/fact reference | Reject generated narrative |
| Evidence không resolve | Loại claim bị ảnh hưởng hoặc reject output theo approved policy |
| Có committed import mới | Giữ snapshot và đặt `newerDataAvailable`/stale |

## Bảng chuyển đổi ID v1 đã ngừng sử dụng

| ID cũ | Owner canonical v2 |
|---|---|
| `AI-001`–`AI-005` | `AI-CON-030`–`AI-CON-035` cùng provider profile này |
| `AI-006`–`AI-013` | `AI-CON-001`–`AI-CON-013`, `AI-TR-001`–`AI-TR-013` |
| `AI-014`–`AI-018` | `AI-CON-020`–`AI-CON-024`, `AI-TR-050`–`AI-TR-052` |
| `AI-019`–`AI-028` | `AI-CON-020`–`AI-CON-035`, `AI-ACC-CON-*` |
| `ACC-AI-001`–`ACC-AI-010` | `AI-ACC-TR-*`, `AI-ACC-CON-*`, `AI-ACC-RPT-*` |

Yêu cầu mới không được viện dẫn ID cũ nếu không đồng thời viện dẫn ID canonical v2 thay thế.
