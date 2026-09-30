# Bằng chứng kích hoạt AI và kiểm thử live — 2026-09-25

## Phạm vi xác nhận

- Owner đã xác nhận privacy gate cho môi trường hiện tại.
- `.env` runtime có `EVP_AI_ENABLED=true` và `EVP_AI_EXTERNAL_ALLOWED=true`.
- Provider: `9router`; configured model: `ag/gemini-3.7-flash-high`.
- API key được phát hiện là đã cấu hình nhưng không được đọc ra evidence, response hoặc log kiểm thử.
- Privacy mode runtime: `normalized_facts_only`.

## Kết quả kiểm thử

| Kiểm chứng | Lệnh | Kết quả |
|---|---|---|
| Safe runtime status | `GET /api/ai/status` qua `TestClient` | `enabled=true`, `configured=true`, `externalAllowed=true`, `privacyMode=normalized_facts_only` |
| Model + schema bằng synthetic facts | `python scripts/smoke_ai_9router.py` | **PASS**, exit `0`; response model `gemini-3.7-flash-tiered`; schema `ai-narrative-v1`; không đọc SQLite/workbook |
| Live vertical slice | `python scripts/smoke_ai_runtime.py` | **PASS**, exit `0`; committed normalized data → period facts/evidence → 9Router → validator; `status=ready`, `validation=accepted`, `narrativeMode=ai` |
| Python regression | `python -m pytest` | **72 passed**, 18 warning deprecation từ FastAPI/Python 3.14 |
| Production frontend build | `cd frontend; npm run build` | **PASS**; còn warning Plotly chunk >500 kB |
| Browser regression | `cd frontend; npm test -- --reporter=line` | **24 passed** trong 32,0 giây |

Safe output của live smoke:

```json
{
  "configuredModel": "ag/gemini-3.7-flash-high",
  "evidenceKinds": ["exact"],
  "featureEnabled": true,
  "groupBy": "day",
  "narrativeMode": "ai",
  "periodCount": 9,
  "privacyGate": true,
  "privacyMode": "normalized_facts_only",
  "promptVersion": "trend-summary-v2",
  "provider": "9router",
  "responseModel": "gemini-3.7-flash-tiered",
  "schemaVersion": "ai-trend-v2",
  "status": "ready",
  "validation": "accepted",
  "validationErrors": []
}
```

## Hardening phát hiện từ kiểm thử thật

Hai output ban đầu bị validator chặn an toàn, không được render như narrative current:

1. Ngày như `01/01/2026` từng bị hiểu nhầm thành numeric claim. Validator hiện chỉ bỏ qua temporal token đã tồn tại trong snapshot; ngày không thuộc snapshot vẫn bị `unsupported_date_mention`.
2. Count có dấu phân cách hàng nghìn như `18,900` từng bị hiểu thành `18.9`. Numeric parser hiện phân biệt grouped thousands và decimal comma; tolerance cho count cũng được siết để `18,901` không thể khớp fact `18,900`.

Các trường hợp trên đã có regression test trong `tests/test_ai.py`.

## Privacy evidence

Live smoke chỉ xuất metadata an toàn. Nó không in hoặc persist:

- API key;
- project/entity label hoặc ref thật;
- provider payload/narrative;
- workbook hash, sheet/cell, raw value;
- observation/lineage/aggregate/import reference;
- revision history.

Provider payload runtime vẫn chỉ gồm token giả danh, metric allowlist, boundary kỳ, deterministic facts/series, quality metadata và logical evidence ID. `.env.example` tiếp tục để hai gate ở `false` nhằm tránh tự bật external call cho môi trường mới.

## Giới hạn còn lại

- Chưa có token/cost telemetry hoặc daily budget.
- Snapshot AI vẫn in-memory, tối đa 100 item/process.
- API vẫn là trusted-internal, chưa có RBAC/rate limit theo user.
- Response model do gateway báo là `gemini-3.7-flash-tiered`, trong khi model được cấu hình là alias `ag/gemini-3.7-flash-high`; configured model đã tồn tại trong model catalog và adapter không tự chọn fallback khác.
- Approval này chỉ áp dụng cho môi trường hiện tại và Trend Summary; không tự mở rộng sang comparison, report draft hoặc scheduled delivery.
