# Documentation Drift Report

- Audit date: 2026-09-25
- Scope: `specs/`, `docs/`, README, implementation, migrations, config, tests và scripts
- Change boundary: audit ban đầu chỉ sửa documentation. Freshness follow-up ngày 2026-09-25 sửa frontend request orchestration và test; không đổi schema, migration, API contract hoặc data-processing semantics.

## Kết quả tổng quát

Audit đã đối chiếu contract với implementation thay vì coi tài liệu cũ là đúng mặc định. Các correction đã được áp dụng trực tiếp; hành vi chưa đủ test được đánh dấu **Partial/Gap** trong [acceptance-criteria.md](acceptance-criteria.md). Ma trận chi tiết nằm tại [traceability-matrix.md](traceability-matrix.md).

## Findings và resolution

### DRIFT-001 — Replay bị mô tả như rollback revision

- Severity: **P0**
- Affected: `README.md`, `docs/SYSTEM_SPECIFICATION.md`, `specs/core/import-process.md`, `specs/core/database-design.md`.
- Claim cũ: replay có thể đưa current pointer/current value “về revision cũ”, không nêu rõ run/revision mới.
- Implementation: `_replay_contract()` tạo contract chứa base contract và attempt ID; `_commit_result()` tạo run mới; `_upsert_observations()` tạo revision mới khi semantic state khác và luôn tạo presence/lineage cho record có mặt.
- Test: `test_explicit_replay_can_restore_values_from_an_older_artifact` chỉ assert committed/update/current value; chưa assert toàn bộ identity/history.
- Resolution: `IMP-017`–`IMP-022` trở thành canonical replay contract; wording rollback pointer đã bị loại bỏ.
- Remaining: `ACC-IMP-012`, `014`, `015` còn Partial/Gap.

### DRIFT-002 — Full snapshot thiếu ranh giới scope/tombstone

- Severity: **P0**
- Affected: `specs/core/import-process.md`, `specs/api/api-contract.md`, `specs/quality/acceptance-criteria.md`.
- Claim cũ: chỉ nói auto-tombstone tắt, chưa phân biệt auto scope và explicit programmatic scope.
- Implementation: `_auto_scopes()` tạo scope theo sheet/date với `missing_policy=ignore`; tombstone chỉ chạy cho full snapshot, complete scope, policy `tombstone` và selector match. Web API/CLI không expose declared scopes.
- Test: explicit scoped tombstone có fixture; default full snapshot với missing rows chưa có targeted test.
- Resolution: bổ sung `IMP-009`, `IMP-016` và `ACC-IMP-009`–`010`.
- Remaining: default missing-record preservation là coverage gap; selector project/entity/metric/incomplete/overlap chưa được assert đầy đủ.

### DRIFT-003 — Entity alias được mô tả như workflow đã hỗ trợ

- Severity: **P0**
- Affected: `specs/core/data-model.md`, `specs/core/database-design.md`, `README.md`, `docs/SYSTEM_SPECIFICATION.md`, `docs/SQLITE_DATABASE_DESIGN_v3.md`, PRD.
- Claim cũ: rename/move có thể được nối bằng “manual alias mapping”, dễ hiểu là đã có workflow hỗ trợ.
- Implementation: importer đọc exact active alias và chỉ tự insert `alias_reason='initial'`; parser key phụ thuộc sheet/path/occurrence. Không có API/CLI/UI quản trị rename/move/manual merge.
- Test: không có assertion trực tiếp cho alias lifecycle hoặc continuity qua rename/move.
- Resolution: ghi rõ hành vi exact-key hiện tại; thêm `DATA-009`, `DATA-010` và `SCP-203 Decision needed`.
- Remaining: mentor/product owner phải chốt matching, approval và quyền quản trị alias.

### DRIFT-004 — Source key của public API không rõ

- Severity: **P1**
- Affected: `specs/api/api-contract.md`, `docs/FRONTEND_BACKEND.md`.
- Claim cũ: mô tả `source_key` ổn định nhưng không nói client web có được truyền hay không.
- Implementation: API lấy `EVP_SOURCE_KEY`, mặc định `cx_report_master`; multipart preview/commit không có field `source_key`. CLI có `--source-key`.
- Resolution: thêm mục Source resolution; giữ nguyên API.
- Remaining: API vẫn chỉ phục vụ một configured source tại một thời điểm.

### DRIFT-005 — Quy ước casing API bị khái quát quá mức

- Severity: **P1**
- Affected: `specs/api/api-contract.md`.
- Claim cũ: read model dùng camelCase, import/history dùng snake_case.
- Implementation: top-level workspace/lineage chủ yếu camelCase; entity rows, audit rows, manifest, outcome và history có snake_case.
- Resolution: contract yêu cầu client theo schema từng endpoint, không tự đổi casing toàn cục.
- Remaining: chưa có generated OpenAPI/client schema snapshot test.

### DRIFT-006 — CSV export được mô tả rộng hơn test evidence

- Severity: **P1**
- Affected: `specs/api/api-contract.md`, `specs/quality/acceptance-criteria.md`.
- Claim cũ: export normalized project data nhưng không nêu filter semantics; acceptance dễ hiểu là đã được test.
- Implementation: endpoint xuất toàn bộ current rows của project bằng `to_csv(index=False)`, không nhận workspace filters.
- Test: chỉ assert status `200`.
- Resolution: bổ sung CSV contract và `ACC-DASH-011` Gap.
- Remaining: thiếu test content, header, media type, filename và filter-independence.

### DRIFT-007 — Refresh/post-commit workspace bị overclaim

- Severity: **P1**
- Affected: `specs/frontend/dashboard-behavior.md`, `specs/product/use-cases.md`.
- Claim cũ: sau commit UI tải lại bootstrap/workspace/history và nút refresh đọc lại API.
- Implementation tại thời điểm audit: UI gọi `bootstrap()`/history, nhưng `loadWorkspace()` short-circuit nếu request key/view/project không đổi; manual refresh cũng không reset key.
- Follow-up implementation: `loadWorkspace(debounceMs, force)` giữ optimization mặc định nhưng cho explicit refresh bypass; manual refresh gọi `bootstrap(true)` và committed import cũng force-fetch. Active-request identity tiếp tục chặn response superseded.
- Test: `frontend/e2e/workspace-freshness.spec.ts` kiểm chứng độc lập post-commit không reload trang, manual same-filter refresh và late superseded response.
- Resolution: thay `DASH-GAP-001` bằng contract as-built `DASH-009`, `DASH-011`, `DASH-012` và acceptance `ACC-DASH-010`, `012`, `013`.
- Remaining: Playwright dùng deterministic API harness; chưa có browser E2E ghi vào mutable production-like database.

### DRIFT-008 — Acceptance evidence không phân biệt covered và inferred

- Severity: **P1**
- Affected: `specs/quality/acceptance-criteria.md`.
- Claim cũ: bảng chỉ liệt kê file test, có thể ngụ ý toàn bộ điều kiện đã pass.
- Implementation/test review: nhiều file chỉ assert một phần, ví dụ CSV chỉ status; replay chỉ current value; entity alias không có test.
- Resolution: thêm mức **Covered/Partial/Gap/Not applicable**, dùng test/function cụ thể và bổ sung criteria còn thiếu.
- Remaining: các Gap được liệt kê trong traceability matrix.

### DRIFT-009 — Test inventory và SQLite status bị cũ

- Severity: **P2**
- Affected: `README.md`, `docs/SYSTEM_SPECIFICATION.md`, `docs/SQLITE_DATABASE_DESIGN_v3.md`.
- Claim cũ: README 48 test, system spec 45 test; database design nói dashboard “sau”, aggregate persistence off và entity alias mapping thủ công.
- Verified: `pytest --collect-only` thu 50 test; FastAPI/dashboard import và aggregate migrations `005`–`006` đã có; alias workflow chưa có.
- Resolution: cập nhật inventory/status và dẫn về normative specs.
- Remaining: hard-coded test count có thể drift lại; ngày xác minh được ghi rõ.

### DRIFT-010 — Contract ownership và traceability phân tán

- Severity: **P2**
- Affected: toàn bộ `specs/`.
- Claim cũ: chưa có bảng tài liệu chuẩn theo prefix và chưa có end-to-end traceability matrix.
- Resolution: thêm owner table trong `specs/README.md`, report này và [traceability-matrix.md](traceability-matrix.md).
- Remaining: cần duy trì matrix trong cùng change khi thêm requirement/contract/test.

### DRIFT-011 — AI/Data draft xung đột namespace và core contract

- Severity: **P0**.
- Affected: toàn bộ `specs/ai-data/`, root spec index, PRD/use case, API/frontend/core cross-reference, acceptance và traceability.
- Claim cũ: `AI-DEC-001`–`AI-DEC-006` có hai bộ nghĩa; `AI-*`/`ACC-AI-*` và các namespace module cùng được coi là canonical; example dùng `error_count`, display label trong `metricCode`, evidence string đơn và integer source-run watermark; zero denominator được mô tả khác chart.
- Implementation/core contract: metric codes là `total`/`error`/`error_rate`; exact evidence cần `observationRef + lineageRef`; aggregate dùng `aggregateRef`; public run/import refs là opaque; chart hiện trả `0%` cho aggregate `0/0`.
- Resolution: phát hành AI/Data spec **v2.0.0** bằng tiếng Việt, chỉ định một owner cho từng prefix, retire ID v1, sửa metric/evidence/freshness/zero semantics, thống nhất 9Router là development provider nhưng production data vẫn chờ privacy/security approval.
- Resolution update 2026-09-25: Trend Summary Phase 1 đã as-built theo AI/Data v2.1; comparison/reporting vẫn Proposed. External provider production enablement vẫn chờ `AI-DEC-006`, `AI-DEC-007`, `AI-DEC-013`.

### DRIFT-012 — Kế hoạch AI dạng horizontal layer không bảo đảm feature hoàn chỉnh

- Severity: **P1**.
- Affected: `specs/ai-data/06-decisions-and-delivery-plan.md`, AI/Data index, root ownership và traceability.
- Claim cũ: delivery slice tách frozen fact layer, trend narrative, comparison và report drafting nhưng chưa bắt buộc mỗi feature đi hết backend → AI → validation → frontend → testing; extension/reuse boundary chưa đủ cụ thể.
- Resolution: thêm [07-vertical-slice-implementation-plan.md](../ai-data/07-vertical-slice-implementation-plan.md) làm owner của `AI-PLAN-*`; Phase 1 tạo shared component qua Trend Summary, Phase 2–4 chỉ mở rộng strategy/policy/composer và phải giữ regression gate của phase trước.
- Resolution update 2026-09-25: Phase 1 có implementation/test evidence tại `ai-data/08-phase-1-runbook-and-evidence.md`; Phase 2–5 vẫn chưa triển khai.

## Unresolved decisions

| Decision ID | Scope | Quyết định cần mentor/product owner chốt |
|---|---|---|
| DEC-001 | `SCP-201` | Due-date reminder thuộc sản phẩm này, chỉ tích hợp kết quả hay ngoài scope? |
| DEC-002 | `SCP-202` | Source-of-truth và identity/lifecycle cho recurrence là gì? |
| DEC-003 | `SCP-203` | Entity rename/move/merge match bằng gì, ai phê duyệt và quản trị alias ra sao? |
| DEC-004 | `SCP-101` | Nguồn file, timezone, retry và owner của scheduled import |
| DEC-005 | `SCP-102`, `AI-DEC-004`–`AI-DEC-008`, `AI-DEC-011`–`AI-DEC-013` | 9Router/model/output đã có development profile; còn privacy, retention, cost budget, persistence, API/UI, reviewer identity và ngưỡng evaluation |
| DEC-006 | Full snapshot | Có expose declared tombstone scopes ra operator/API hay giữ storage-core only? |

Các quyết định này không được tự động coi là failed acceptance. Freshness gap trước đây đã được xử lý và không phải product decision.

## Files reviewed

- Tất cả Markdown trong `specs/` và `docs/`.
- `README.md`, `PRODUCT.md`, `config/*.yaml`.
- `app/api.py`, `app/dashboard.py`, `app/aggregate_lineage.py`.
- `src/excel_visualization_pipeline/`, đặc biệt parser, date ranges, charts và storage.
- Migrations `001`–`006`.
- `tests/`, `frontend/e2e/`, frontend types/main/chart.
- Scripts import, smoke, backup, history và integrity.

## Verification record

Các lệnh dưới đây được chạy trên working tree ngày 2026-09-25 sau khi cập nhật tài liệu:

| Kiểm tra | Kết quả |
|---|---|
| Internal Markdown links trong `README.md`, `PRODUCT.md`, `docs/`, `specs/` | **PASS** — 29 file, 0 target bị thiếu sau khi thêm vertical-slice plan |
| AI/Data v2 definition uniqueness | **PASS** — 140 canonical AI definition ID, 0 duplicate, 0 retired v1 definition |
| AI/Data v2 owner check | **PASS** — 0 definition nằm ngoài owner file của prefix tương ứng |
| Markdown trailing whitespace + `git diff --check` | **PASS** — không có whitespace error; Git chỉ cảnh báo LF/CRLF của working copy |
| `python -m pytest` | **PASS** — 50 passed, 14 FastAPI deprecation warnings, 10.62s |
| `python scripts/smoke_test.py "D:\task\test data for CX report dashboard.xlsx"` | **PASS** — 6 project, 4.182 record, 2.343 chartable record |
| `python scripts/smoke_test_storage.py ... --database <temporary.sqlite3>` | **PASS** — committed run 1, 4.182 record, 36 entity, integrity hợp lệ |
| `npm test -- e2e/workspace-freshness.spec.ts` trong `frontend/` | **PASS** — 3 freshness scenarios passed, 6.7s |
| `npm test` trong `frontend/` | **PASS** — 19 Playwright tests passed, 26.3s |
| `npm run build` trong `frontend/` | **PASS** — TypeScript/Vite build thành công; còn warning chunk Plotly lớn hơn 500 kB |

Việc toàn bộ suite hiện tại pass không biến các mục **Partial/Gap** thành **Covered**: các suite đó chưa có assertion cho chính điều kiện còn thiếu được liệt kê trong traceability matrix.

## Change summary

- Thiết lập `specs/` làm contract chuẩn và chỉ định owner theo prefix.
- Chốt semantics full snapshot, explicit replay, revision/presence và thứ tự duplicate/stale validation theo implementation hiện tại.
- Sửa overclaim về entity rename/move, source resolution, response casing, CSV và refresh/cache.
- Phân loại acceptance evidence thành Covered/Partial/Gap/Not applicable thay vì suy luận từ tên file test.
- Giữ nguyên các trạng thái sản phẩm đã yêu cầu và tách sáu quyết định chưa chốt.
- Tổ chức `specs/` theo module; phát hành AI/Data v2.0.0 với namespace `AI-SCP`/`AI-TR`/`AI-CMP`/`AI-RPT`/`AI-CON`/`AI-ACC`/`AI-DEC` cho AI-assisted reporting qua 9Router.
- Audit ban đầu không thay đổi application code. Freshness follow-up chỉ đổi frontend request orchestration và test harness; không đổi database schema/migration, API contract hoặc data-processing semantics.
