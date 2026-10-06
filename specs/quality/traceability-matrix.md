# Requirement Traceability Matrix

- Audit date: 2026-09-25
- Status vocabulary: **Covered**, **Partial**, **Gap**, **Accepted, not built**, **Proposed**, **Decision needed**, **Out of scope**

## P0 — Import, storage và identity

Phần bổ sung 05/10/2026 — không thay trạng thái các gap storage bên dưới:

| Requirement ID | Specification ID | Implementation | Test evidence | Status |
|---|---|---|---|---|
| REQ-IMPORT-UI-01 Nhập ưu tiên, lịch sử tại chỗ, giữ phiên nhập và session history cũ | `ACC-IMP-017`, `ACC-IMP-018` | `frontend/src/main.ts`, `import-history.ts` | `frontend/e2e/unified-import-workspace.spec.ts` | Covered trên API mô phỏng |
| REQ-IMPORT-UI-02 Kết quả ghi/tải lại độc lập, một POST, không đoán kết quả chưa rõ hoặc version mới | `ACC-IMP-019`, `ACC-IMP-020` | `commitFile`, `refreshImportedWorkspace`, `refreshHistory` | cùng file và `workspace-freshness.spec.ts` | Covered trên API mô phỏng |
| REQ-IMPORT-UI-03 Quality gate, reload/rời tab, responsive và báo cáo giới hạn | `ACC-IMP-021`, `ACC-IMP-022` | `renderImport`, CSS nhập | cùng file, 4 viewport | Covered trên API mô phỏng |

Kết quả chạy thật, ảnh và giới hạn: [báo cáo Nhập Excel hợp nhất](unified-import-workspace-evidence.md).

| Requirement ID | Specification ID | Implementation | Test evidence | Status |
|---|---|---|---|---|
| REQ-FS-01 Incremental không xóa key vắng mặt | `IMP-008`, `DB-010` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): `_validate_mode_and_scopes`, `_apply_tombstones` | [`test_storage.py`](../../tests/test_storage.py): `test_incremental_updates_history_and_preserves_missing_dates` | Covered |
| REQ-FS-02 Full snapshot phải có scope | `IMP-009` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): `_auto_scopes`, `_validate_mode_and_scopes` | Không có assertion trực tiếp trên stored auto scope | Partial |
| REQ-FS-03 Default full snapshot giữ missing current rows | `IMP-009`, `ACC-IMP-009` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): auto scope `ignore` | Chưa có targeted test với missing rows | Gap |
| REQ-FS-04 Tombstone chỉ trong complete declared scope | `IMP-016`, `ACC-IMP-010` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): `_resolve_and_store_scopes`, `_apply_tombstones` | [`test_storage.py`](../../tests/test_storage.py): `test_full_snapshot_tombstones_only_declared_scope` | Partial: fixture chỉ date/sheet |
| REQ-FS-05 Full snapshot cần UI confirmation | `IMP-007`, `DASH-*`, `ACC-IMP-007` | [`frontend/src/main.ts`](../../frontend/src/main.ts): `commitDisabled`, confirm checkbox | [`chart-lineage.spec.ts`](../../frontend/e2e/chart-lineage.spec.ts): `full snapshot remains blocked...` | Covered |
| REQ-RPL-01 Replay là forward recovery với attempt/run mới | `IMP-017`, `DB-013` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): `_prepare_attempt`, `_commit_result` | [`test_storage.py`](../../tests/test_storage.py): explicit replay test chỉ assert committed/current | Partial |
| REQ-RPL-02 Replay contract chứa base hash/json/attempt ID | `IMP-018`, `DB-013` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): `_replay_contract` | Chưa assert persisted contract JSON/hash | Gap |
| REQ-RPL-03 Replay revision semantics | `IMP-019` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): `_upsert_observations` | Update case partial; unchanged/restore/insert replay chưa test | Partial |
| REQ-RPL-04 Replay tạo presence/lineage mới | `IMP-020` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): presence/snapshot inserts | Chưa có replay-specific count/ref assertion | Gap |
| REQ-RPL-05 Duplicate/stale/validation/commit order | `IMP-021` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): `_process_result`, `_commit_result` | Exact duplicate và artifact-applied có test; stale/concurrency chưa test | Partial |
| REQ-RPL-06 Replay bypass stale nhưng không validation/transaction | `IMP-022` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py) | Không có replay-invalid/concurrency test | Gap |
| REQ-RPL-07 Replay chỉ expose qua CLI | `IMP-022` | [`scripts/import_workbook.py`](../../scripts/import_workbook.py); [`app/api.py`](../../app/api.py) không có field | Không có CLI contract test | Partial |
| REQ-ID-01 Exact active alias giữ entity identity | `DATA-003`, `ACC-DATA-006` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py): `_upsert_entities` | Không assert trực tiếp alias row/lifecycle | Gap |
| REQ-ID-02 Rename/move/merge continuity | `DATA-009`, `DATA-010`, `SCP-203` | Parser key ở [`parser/hierarchy.py`](../../src/excel_visualization_pipeline/parser/hierarchy.py); workflow không tồn tại | Không có | Decision needed |
| REQ-OBS-01 Observation logical key không chứa unit | `DATA-004`, `DB-005` | Migration [`001_initial.sql`](../../src/excel_visualization_pipeline/storage/migrations/001_initial.sql) | Incremental test giữ observation refs; chưa có unit-change fixture riêng | Partial |
| REQ-HASH-01 Semantic và lineage hash tách biệt | `IMP-015`, `DATA-*` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py) | `test_lineage_only_change_does_not_create_business_revision` | Covered |
| REQ-PRES-01 Unchanged vẫn có run presence | `IMP-014` | [`storage/importer.py`](../../src/excel_visualization_pipeline/storage/importer.py) | Lineage-only test assert revisions=6, presence=12 | Covered |

## P1 — API, dashboard và lineage

| Requirement ID | Specification ID | Implementation | Test evidence | Status |
|---|---|---|---|---|
| REQ-SRC-01 API source do server resolve | API Source resolution | [`app/api.py`](../../app/api.py): `EVP_SOURCE_KEY`/`SOURCE_KEY` | API tests monkeypatch `SOURCE_KEY`; không test environment wiring | Partial |
| REQ-DATE-01 Recent luôn lấy 10 ngày distinct | API workspace query, `DASH-*` | [`date_ranges.py`](../../src/excel_visualization_pipeline/date_ranges.py), [`app/api.py`](../../app/api.py): `_window` | [`test_date_ranges.py`](../../tests/test_date_ranges.py) | Partial: API bỏ qua `count` chưa assert trực tiếp |
| REQ-API-01 Endpoint/query/status contract | API v1 | [`app/api.py`](../../app/api.py) | [`test_api.py`](../../tests/test_api.py) | Partial: không snapshot toàn schema/casing |
| REQ-LIN-01 Exact refs resolve đúng revision/cell | API Lineage, `FLOW-007` | [`repository.py`](../../src/excel_visualization_pipeline/storage/repository.py) | API + Playwright lineage tests | Covered |
| REQ-LIN-02 Aggregate refs immutable và có contributors | API Lineage, `FLOW-008` | [`aggregates.py`](../../src/excel_visualization_pipeline/storage/aggregates.py), [`aggregate_lineage.py`](../../app/aggregate_lineage.py) | [`test_api.py`](../../tests/test_api.py) | Covered |
| REQ-CSV-01 Export toàn bộ current rows của project | API CSV export, `ACC-DASH-011` | [`app/api.py`](../../app/api.py): `export_csv` | API test chỉ assert `200` | Gap |
| REQ-CACHE-01 Server cache đổi key theo committed run | API Cache identity, `DASH-010` | [`app/api.py`](../../app/api.py): `_source`, workspace cache key | API test assert cache hit và lineage freshness; chưa test eviction | Partial |
| REQ-REFRESH-01 Committed import cập nhật dashboard không reload trang | `DASH-011`, `ACC-DASH-012` | [`frontend/src/main.ts`](../../frontend/src/main.ts): `commitFile`, `bootstrap`, forced `loadWorkspace` | [`workspace-freshness.spec.ts`](../../frontend/e2e/workspace-freshness.spec.ts): successful import scenario | Covered |
| REQ-REFRESH-02 Manual refresh fetch lại cùng filter | `DASH-009`, `ACC-DASH-013` | [`frontend/src/main.ts`](../../frontend/src/main.ts): refresh action → `bootstrap(true)` | [`workspace-freshness.spec.ts`](../../frontend/e2e/workspace-freshness.spec.ts): same-query refresh scenario | Covered |
| REQ-UI-01 Request superseded không ghi đè data mới | `DASH-012`, `ACC-DASH-010` | [`frontend/src/main.ts`](../../frontend/src/main.ts): active `AbortController`/request identity | [`workspace-freshness.spec.ts`](../../frontend/e2e/workspace-freshness.spec.ts): late-response scenario; [`workspace-performance.spec.ts`](../../frontend/e2e/workspace-performance.spec.ts) | Covered |
| REQ-CMP-01 Contextual same-parent eligibility | Contextual Comparison §2, `ACC-CMP-001`–`ACC-CMP-004` | [`entity_selection.py`](../../src/excel_visualization_pipeline/entity_selection.py), [`app/api.py`](../../app/api.py) | API/helper tests + [`contextual-comparison.spec.ts`](../../frontend/e2e/contextual-comparison.spec.ts) | Covered |
| REQ-CMP-02 Metric/time/unit alignment và quarter | Contextual Comparison §3/§8, `ACC-CMP-005`, `ACC-CMP-007` | [`charts.py`](../../src/excel_visualization_pipeline/visualization/charts.py), [`app/api.py`](../../app/api.py) | chart/API tests + contextual Playwright | Covered |
| REQ-CMP-03 DataVersion/stale-response protection | Contextual Comparison §4/§8, `ACC-CMP-005`–`ACC-CMP-006` | [`frontend/src/main.ts`](../../frontend/src/main.ts) | contextual late-response và committed-version scenarios | Covered |
| REQ-CMP-04 Large modal/focus/legacy parity guard | Contextual Comparison §8, `ACC-CMP-008`–`ACC-CMP-009` | [`frontend/src/main.ts`](../../frontend/src/main.ts), [`style.css`](../../frontend/src/style.css) | 1366×768, 1440×900, focus return, tab cũ bị ẩn và full regression | Covered; parity audit hoàn tất |
| REQ-CMP2-00 Parity missing/zero trước khi tái sử dụng Statistics | [Contextual Comparison Phase 2](../frontend/contextual-comparison-phase-2.md) §2.4/§11, `CMP2-ACC-000` | [`charts.py`](../../src/excel_visualization_pipeline/visualization/charts.py): semantic guard của `prepare_period_statistics` | `test_period_statistics_rejects_inferred_zero_when_positive_source_rate_has_no_error_count` | Covered |
| REQ-CMP2-01 Thống kê đa nội dung | [Contextual Comparison Phase 2](../frontend/contextual-comparison-phase-2.md) §4–§5, `CMP2-ACC-001`–`CMP2-ACC-006` | [`app/api.py`](../../app/api.py), [`charts.py`](../../src/excel_visualization_pipeline/visualization/charts.py), popup hiện tại | API/chart tests + contextual Playwright | Covered |
| REQ-CMP2-02 Bằng chứng đúng entity | Contextual Comparison Phase 2 §6, `CMP2-ACC-007`–`CMP2-ACC-009` | [`aggregate_lineage.py`](../../app/aggregate_lineage.py): `statistics_comparison` | API provenance/contributor + fail-closed test | Covered |
| REQ-CMP2-03 Điều tra và Audit round-trip | Contextual Comparison Phase 2 §7–§9, `CMP2-ACC-010`–`CMP2-ACC-013` | [`main.ts`](../../frontend/src/main.ts), [`style.css`](../../frontend/src/style.css) | contextual Playwright tại 1366×768 và 1440×900 | Covered |
| REQ-CMP2-04 Đối chiếu toàn dự án và tương đương | Contextual Comparison Phase 2 §11–§12, `CMP2-ACC-014`–`CMP2-ACC-017` | Builder dùng chung với `prepare_period_statistics`; tab So sánh cũ bị ẩn, contract API cũ được giữ | real-workbook matrix + full backend/frontend regression | Covered |

## AI/Data — report assistance

| Requirement ID | Specification ID | Implementation | Test evidence | Status |
|---|---|---|---|---|
| REQ-AI-01 Server-only 9Router configuration | `AI-CON-030`–`AI-CON-035`, `AI-PLAN-012`, `AI-PLAN-110`, `AI-ACC-CON-005`–`AI-ACC-CON-007` | [`ai/config.py`](../../src/excel_visualization_pipeline/ai/config.py), [`ai/llm.py`](../../src/excel_visualization_pipeline/ai/llm.py), [`.env.example`](../../.env.example); feature/privacy gate kép | [`test_ai.py`](../../tests/test_ai.py): HTTP mapping, model missing, secret/status và privacy gate | Covered cho implementation; production approval còn gate |
| REQ-AI-02 Context lấy từ committed data và khóa snapshot/opaque import ref | `AI-CON-001`–`AI-CON-013`, `AI-TR-001`–`AI-TR-013`, `AI-PLAN-010`–`AI-PLAN-011`, `AI-PLAN-016`, `AI-ACC-TR-*` | [`ai/analytics.py`](../../src/excel_visualization_pipeline/ai/analytics.py), [`ai/evidence.py`](../../src/excel_visualization_pipeline/ai/evidence.py), [`ai/repository.py`](../../src/excel_visualization_pipeline/ai/repository.py) | `test_trend_strategy_*`, `test_trend_api_full_slice_*` | Covered cho Phase 1 scope |
| REQ-AI-03 Structured output dùng fact IDs và typed evidence | `AI-CON-020`–`AI-CON-024`, `AI-PLAN-013`–`AI-PLAN-014`, `AI-ACC-CON-001`–`AI-ACC-CON-004` | [`ai/validation.py`](../../src/excel_visualization_pipeline/ai/validation.py), [`ai/service.py`](../../src/excel_visualization_pipeline/ai/service.py), AI API và panel | Validator/fabricated/invalid JSON tests + [`ai-insights.spec.ts`](../../frontend/e2e/ai-insights.spec.ts) | Covered cho Phase 1 scope |
| REQ-AI-04 Prompt safety và failure isolation | `AI-SCP-016`–`AI-SCP-017`, `AI-CON-021`–`AI-CON-035`, `AI-PLAN-003`–`AI-PLAN-005` | Payload allowlist/token giả danh, output escaping, deterministic fallback; core workspace không phụ thuộc AI | `test_output_validator_*`, provider failure tests, Playwright success/failure/stale/retry/evidence | Covered |
| REQ-AI-05 Privacy/retention/cost/evaluation/API approval | `AI-DEC-004`–`AI-DEC-008`, `AI-DEC-011`–`AI-DEC-013`, `AI-ACC-CON-007` | Safe baseline đã cài: no raw, in-memory, explicit user action, external gate off | CI không dùng secret; real smoke opt-in chưa chạy | Partial: production region/retention/cost/gold sign-off vẫn Decision needed |
| REQ-AI-06 Comparative analysis | `AI-SCP-002`, `AI-CMP-*`, `AI-PLAN-120`, `AI-ACC-CMP-*` | Chưa vào product scope đã duyệt | Không có | Proposed |
| REQ-AI-07 Template-driven report | `AI-SCP-003`–`AI-SCP-005`, `AI-RPT-*`, `AI-PLAN-130`, `AI-PLAN-140`, `AI-ACC-RPT-*` | `reporting/*`, migration 007, report API/workspace/chart; [as-built](../ai-data/12-report-workspace-as-built.md) | `tests/test_reporting.py`, `frontend/e2e/reports.spec.ts`, [LLM/exports](../ai-data/evidence/2026-10-05-reports-review.md) | Covered cho draft v1; authenticated approval/retention chưa có |

## Product scope/status

| Requirement ID | Specification ID | Implementation | Test evidence | Status |
|---|---|---|---|---|
| REQ-SCHED-01 Scheduled daily import | `SCP-101`, `PRD-F101`, `UC-09` | Không có scheduler/watcher | Không có | Accepted, not built |
| REQ-SCOPE-AI-01 AI trend summary | `SCP-102`, `PRD-F102`, `UC-10`, `AI-SCP-001`, `AI-TR-*`, `AI-CON-*` | AI service/adapter/validator, context API và UI | `test_ai*`, context e2e và [live evidence](../ai-data/README.md) | As-built trong phạm vi nội bộ; không phải production sign-off |
| REQ-DUE-01 Due-date reminder | `SCP-201`, `PRD-F201`, `UC-11` | Không có issue model | Không có | Decision needed |
| REQ-REC-01 Recurrence detection | `SCP-202`, `PRD-F202`, `UC-11` | Không có issue lifecycle | Không có | Decision needed |
| REQ-ID-03 Alias administration policy | `SCP-203`, `DATA-010` | Schema capability only | Không có | Decision needed |

## Orphan/gap summary

Các requirement đã xác nhận về hành vi nhưng chưa đủ acceptance coverage:

- default full snapshot `missing_policy=ignore` với input thiếu rows;
- replay contract identity, repeated replay và presence/lineage counts;
- replay unchanged/restore/insert cases;
- stale artifact rejection và duplicate race tại commit boundary;
- entity alias creation/resolution và unit-change continuity;
- CSV payload/header/filter semantics;

Không test nào được ghi **Covered** chỉ vì nằm trong cùng file; status dựa trên assertion thực tế đã đọc.

# Bổ sung traceability — Overview summary

`UC-OV-KPI` → `DASH-OV-KPI` / `ACC-OV-KPI` → `overview_summary.py` (Overview/Statistics), API workspace/read snapshot, `overview-summary.ts`/main.ts → `test_overview_summary.py`, `test_overview_summary_api.py`, `overview-summary.spec.ts`. Bằng chứng ban đầu: [overview-summary-metrics-evidence.md](overview-summary-metrics-evidence.md); mở rộng Thống kê/thu gọn: [overview-statistics-summary-evidence.md](overview-statistics-summary-evidence.md).
