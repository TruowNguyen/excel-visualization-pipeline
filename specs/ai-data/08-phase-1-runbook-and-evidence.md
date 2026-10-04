# 08 — Runbook và bằng chứng Phase 1 Trend Summary

- Phiên bản: **1.3.0**
- Ngày cập nhật giao diện: **2026-09-30**
- Phạm vi: Phase 1, một project + một entity + một hoặc toàn bộ ba metric + một window
- External-provider gate cho môi trường hiện tại: **ĐÃ ĐƯỢC OWNER XÁC NHẬN VÀ ĐÃ BẬT**. Cấu hình mẫu cho môi trường mới vẫn mặc định khóa.

## 1. Thành phần đã bàn giao

| Lớp vertical slice | As-built |
|---|---|
| Backend | `AnalyticsEngine`, `TrendStrategy`, committed read adapter, `EvidenceBuilder`, checksum/importRef, in-memory `AnalysisSnapshotRepository`, API status/create/get |
| AI | `LLMAdapter`, `NineRouterLLMAdapter`, `PromptRegistry trend-summary-v6`, trend từng metric và overview ba metric trong một provider call, model check, latency budget 12 giây, không retry request tương tác, output tối đa 700 token |
| Validation | `OutputValidator ai-narrative-v1`, fact/evidence ID, numeric mention, direction, unsupported cause, injection content và strict field check |
| Frontend | Phân tích xu hướng bằng AI nằm sau Overview; luồng đọc Tổng quan → Câu chuyện dữ liệu kết nối peak/lowest, largest change, consecutive run, ending plateau và historical context; bảng từng kỳ/evidence/metadata dùng progressive disclosure; giữ đầy đủ loading/error/fallback/stale/retry, live status và focus lifecycle |
| Testing | Unit, provider fake/error mapping, SQLite integration, API contract, Playwright success/failure/stale/retry/evidence/scope/focus/responsive CTA và regression core/frontend |

Shared component nằm trong `src/excel_visualization_pipeline/ai/`; Phase 2 phải thêm strategy/schema/prompt mới trên pipeline này, không tạo adapter/validator thứ hai.

## 2. Privacy boundary thực tế

Nguồn phân tích là `v_current_observations` sau committed import. Preview và workbook raw không đi vào AI service.

Payload có thể gửi tới 9Router khi cả hai gate bật:

- `projectToken`, `entityToken`: SHA-256 scoped token, không gửi label/ref thật;
- `metricCode`, allowlisted `metricDisplayName`;
- exact date window và comparison basis;
- deterministic facts cần cho narrative: đầu–cuối, pattern, peak/lowest, largest increase/decrease, consecutive run, ending plateau, historical range/position, fact ID và logical evidence ID; chuỗi raw không gửi tới provider vì trùng với kết quả deterministic;
- coverage/quality metadata;
- prompt/schema version cố định.

Không gửi: workbook/file hash, raw cell, sheet/cell address, project/entity label, observation/lineage/aggregate/import ref, revision history, issue text, API key. Evidence ref chỉ tồn tại trong local API response. Provider prompt/raw response không được persist.

`EVP_AI_ENABLED=false` tắt feature. `EVP_AI_EXTERNAL_ALLOWED=false` cho phép backend tạo facts/evidence nhưng adapter trả safe fallback mà không mở network call. Đây là cấu hình mặc định trong `.env.example`.

## 3. Vận hành

1. Cấu hình `GEMINI_API_KEY`, `GEMINI_API_BASE_URL`, `GEMINI_MODEL` phía server.
2. Đặt `EVP_AI_ENABLED=true` để panel gọi deterministic analysis.
3. Giữ `EVP_AI_EXTERNAL_ALLOWED=false` cho tới khi `AI-DEC-006` có approval record. Approval cho môi trường hiện tại đã được xác nhận ngày 2026-09-25.
4. Sau approval, operator gọi `POST /api/ai/provider/check`; thao tác này chỉ đọc model catalog.
5. Bật `EVP_AI_EXTERNAL_ALLOWED=true`, chạy synthetic smoke rồi live normalized-data smoke:

```powershell
python scripts/smoke_ai_9router.py
python scripts/smoke_ai_runtime.py
```

Synthetic smoke không đọc SQLite/workbook. Live smoke đi qua FastAPI và committed normalized read model nhưng chỉ in safe metadata, không in key, project/entity label, narrative, fact value hoặc evidence ref. Exit `0` nghĩa đạt; exit `2` nghĩa gate/config chưa bật; exit `1` nghĩa provider/model/output lỗi.

Rollback/kill switch: đặt `EVP_AI_ENABLED=false` rồi restart server. Core import, dashboard, audit và lineage không phụ thuộc AI endpoint.

## 4. Bằng chứng lặp lại được

| Evidence | Lệnh | Kết quả gần nhất |
|---|---|---|
| Python unit/integration/regression | `python -m pytest` | **2026-09-30: 96 passed**; 18 deprecation warnings từ FastAPI/Python 3.14 |
| TypeScript static check | `cd frontend; npm run typecheck` | **2026-09-30: Pass** |
| Production frontend build | `cd frontend; npm run build` | **2026-09-30: Pass**, Vite tạo bundle; còn warning Plotly chunk >500 kB |
| Frontend AI + regression E2E | `cd frontend; npm test` | **2026-09-30: 50 passed**; gồm 9 flow AI và toàn bộ regression hiện có |
| Real 9Router synthetic | `python scripts/smoke_ai_9router.py` | **2026-09-25: Pass**; model response `gemini-3.7-flash-tiered`, schema `ai-narrative-v1`, synthetic-only |
| Live normalized-data slice | `python scripts/smoke_ai_runtime.py` | **2026-09-25: Pass**; `ready`, validation `accepted`, narrative `ai`, 9 kỳ ngày, evidence `exact`, `normalized_facts_only` |

Evidence record không chứa secret nằm tại [2026-09-25-live-ai-verification.md](evidence/2026-09-25-live-ai-verification.md).

Test mapping chính:

- `AI-ACC-TR-001`–`003`: `test_trend_strategy_weighted_rate_zero_and_missing_semantics`, `test_trend_strategy_one_point_is_insufficient_and_zero_baseline_has_no_relative_fact`;
- `AI-ACC-TR-008`–`010`: các test grouping/weighted-rate/pattern/60-period cùng `test_period_level_analytics_are_deterministic_and_grounded`, `test_period_level_analytics_find_consecutive_runs_and_ending_plateau`, historical-context tests và flow UI trong `frontend/e2e/ai-insights.spec.ts`;
- `AI-ACC-TR-004`, `007`: `test_trend_api_full_slice_uses_only_committed_normalized_facts_and_marks_stale`;
- `AI-ACC-CON-001`–`004`, `006`: validator/provider degradation tests trong `tests/test_ai.py`;
- Grounding live-provider: `test_output_validator_accepts_snapshot_dates_and_rejects_fabricated_dates`, `test_output_validator_distinguishes_thousands_and_decimal_commas`;
- `AI-ACC-CON-005`, `007`: provider payload assertions, prompt-injection test, feature/privacy gate và CI không secret;
- `AI-TR-050`–`052`: `frontend/e2e/ai-insights.spec.ts`.

## 5. Known limitations và exit gate

- Phase 1 phân tích tối đa 60 kỳ ngày/tuần/tháng, có period-level ranking deterministic và bối cảnh tối đa 12 kỳ liền trước. “Lớn nhất” chỉ là xếp hạng quan sát trong window; chưa claim threshold-based noteworthy change, relatively-stable hoặc statistical anomaly.
- `scope=children`, comparative insight và report draft chưa thuộc Phase 1 runtime.
- Snapshot mất khi server restart và giới hạn 100 item/process; đây là quyết định giảm retention tạm thời, chưa phù hợp report audit dài hạn.
- API vẫn là trusted-internal, chưa có auth/RBAC/rate limit theo user.
- Chưa có token/cost telemetry hoặc daily budget; đây vẫn là điều kiện hardening trước rollout rộng.
- Model name được kiểm tra explicit, không auto-fallback sang model khác.
- Privacy gate và real-provider smoke đã hoàn tất cho môi trường hiện tại; rollout rộng vẫn cần accuracy/cost threshold và operational monitoring.

Phase 1 được coi là **implementation complete, external enablement verified for the current environment**. Không bắt đầu Phase 2 nếu scope comparison chưa được mentor/PO duyệt hoặc full regression cuối không xanh.
