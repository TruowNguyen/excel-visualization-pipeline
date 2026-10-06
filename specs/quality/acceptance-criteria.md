# Acceptance criteria và bằng chứng kiểm thử

- Trạng thái: **Normative acceptance gate**
- Contract IDs: `ACC-*` excluding the separately owned AI/Data v2 namespace `AI-ACC-*`

## Quy tắc xác nhận

Một chức năng chỉ được đánh dấu hoàn thành khi đồng thời có:

1. scope đã được xác nhận;
2. spec mô tả input, output, edge case và failure behavior;
3. implementation có thể chạy trong môi trường bàn giao;
4. automated test hoặc acceptance evidence lặp lại được;
5. không có lỗi blocker trong quality gate liên quan.

“Có màn hình” hoặc “chạy được một lần” không đủ để xác nhận hoàn thành.

## Quality gate toàn hệ thống

Chạy từ repository root:

```powershell
python -m pytest
python scripts\smoke_test.py "..\test data for CX report dashboard.xlsx"
python scripts\smoke_test_storage.py "..\test data for CX report dashboard.xlsx"
cd frontend
npm run build
npm test
```

Kết quả bắt buộc:

- mọi command exit code `0`;
- Python tests không failed;
- smoke test workbook thật pass;
- database integrity là `ok` và không có foreign-key issue;
- frontend typecheck/build pass;
- Playwright E2E không failed.

Bundle-size warning hiện là non-blocking; lỗi build/typecheck là blocking.

## Mức bằng chứng

- **Covered**: test có assertion trực tiếp cho điều kiện được nêu.
- **Partial**: test chỉ xác nhận một phần; phần còn lại không được coi là pass.
- **Gap**: hành vi thấy trong implementation/spec nhưng chưa có acceptance evidence lặp lại được.
- **Not applicable**: ngoài gate do scope chưa được chốt hoặc chưa triển khai.

## Import acceptance

| ID | Given / When / Then | Bằng chứng chính | Mức bằng chứng |
|---|---|---|---|
| ACC-IMP-001 | Given workbook hợp lệ, when preview, then trả valid manifest và database chưa có project mới | `tests/test_api.py::test_workspace_api_reads_imported_sqlite_without_reparsing` | Covered |
| ACC-IMP-002 | Given hash khác preview, when commit, then `409` và current state không đổi | `tests/test_api.py::test_workspace_api_reads_imported_sqlite_without_reparsing` | Covered |
| ACC-IMP-003 | Given validation error, when import, then attempt bị audit và không có committed run/current-state change | `tests/test_storage.py::test_rejected_import_is_audited_without_changing_current_data` | Covered |
| ACC-IMP-004 | Given import hợp lệ, when commit, then counters và bootstrap phản ánh dữ liệu | `tests/test_api.py`, `tests/test_storage.py` | Partial: không assert mọi counter invariant |
| ACC-IMP-005 | Given cùng artifact/config/contract, when import lại, then duplicate không tạo run/revision/presence trùng | `tests/test_storage.py::test_commits_and_skips_duplicate_without_duplicating_data` | Covered |
| ACC-IMP-006 | Given incremental thiếu key cũ, when commit, then key cũ vẫn current và không tombstone | `tests/test_storage.py::test_incremental_updates_history_and_preserves_missing_dates` | Covered |
| ACC-IMP-007 | Given full snapshot UI, when chưa confirm, then nút commit bị chặn | `frontend/e2e/chart-lineage.spec.ts` | Covered |
| ACC-IMP-008 | Given commit thành công, when verify DB, then integrity/foreign keys hợp lệ | `scripts/smoke_test_storage.py` | Covered khi script thực sự được chạy |
| ACC-IMP-009 | Given full snapshot không truyền scope, when core tạo auto scopes, then mỗi sheet có date bounds và `missing_policy=ignore`; record vắng mặt không bị xóa | `_auto_scopes()` và `_apply_tombstones()` trong `storage/importer.py` | Gap: chưa có targeted test cho default full snapshot có missing rows |
| ACC-IMP-010 | Given complete full-snapshot scope với `missing_policy=tombstone`, when key trong scope vắng mặt, then chỉ key trong scope bị tombstone | `tests/test_storage.py::test_full_snapshot_tombstones_only_declared_scope` | Covered cho date/sheet fixture; project/entity/metric/incomplete/overlap selectors chưa được assert |
| ACC-IMP-011 | Given cùng artifact với contract khác và không explicit replay, when import, then rejected `ARTIFACT_ALREADY_APPLIED` và không tạo run | `tests/test_storage.py::test_same_artifact_cannot_be_silently_reapplied_with_another_mode` | Covered |
| ACC-IMP-012 | Given artifact cũ và `allow_replay=True`, when replay, then tạo committed run mới và current value phản ánh artifact cũ qua update mới | `tests/test_storage.py::test_explicit_replay_can_restore_values_from_an_older_artifact` | Partial: assert commit/update/current value, chưa assert contract/run/revision/presence identities |
| ACC-IMP-013 | Given artifact cũ và đã có artifact khác mới hơn, when import thường, then rejected `STALE_ARTIFACT_REPLAY` | `_process_result()` trong `storage/importer.py` | Gap: không có targeted automated test |
| ACC-IMP-014 | Given repeated explicit replay, when chạy nhiều lần, then mỗi lần có replay contract/run riêng nhưng không nhân bản artifact/logical observation | `_replay_contract()` và database constraints | Gap |
| ACC-IMP-015 | Given replayed value không đổi/đã deleted/mới, then lần lượt giữ revision current + presence mới/tạo restore/tạo insert | `_upsert_observations()` | Gap cho replay-specific cases |
| ACC-IMP-016 | Given concurrent exact imports, when đến commit boundary, then chỉ một run commit và lần còn lại duplicate | duplicate recheck trong `_commit_result()` | Gap: không có concurrency test |

## Nghiệm thu Nhập Excel hợp nhất — 05/10/2026

Các ca giao diện dùng API mô phỏng; không thay bằng chứng backend của `ACC-IMP-001..016`. Log chạy và giới hạn ở [báo cáo riêng](unified-import-workspace-evidence.md).

| ID | Điều kiện đạt | Test chính | Phạm vi |
|---|---|---|---|
| ACC-IMP-017 | Nhập ưu tiên, lịch sử mặc định đóng; mở/thu gọn/chi tiết không mất File, preview, xác nhận | `unified-import-workspace.spec.ts`: import first; legacy history | Giao diện mô phỏng |
| ACC-IMP-018 | Kho rỗng hoặc lỗi phân tích vẫn xem trước; history lỗi giữ list gần nhất; null không thành 0; escape dữ liệu nguồn | cùng file: can preview; history refresh failure; history detail | Giao diện mô phỏng |
| ACC-IMP-019 | Một POST đúng File/mode/hash; committed giữ khi GET lỗi; retry GET-only; duplicate không phiên mới; phiên chưa đổi không báo cập nhật | cùng file: single POST; duplicate; unchanged workspace version | Giao diện mô phỏng + `workspace-freshness.spec.ts` |
| ACC-IMP-020 | History response cũ không đè mới; POST mất phản hồi khóa ghi; 409 yêu cầu preview lại | cùng file: late old history; unknown POST; 409 invalidates | Giao diện mô phỏng |
| ACC-IMP-021 | Invalid không ghi; báo giới hạn 100 issue; rời/quay lại tab không ghi thêm; reload phải chọn lại File | cùng file: invalid preview; navigation during commit | Giao diện mô phỏng |
| ACC-IMP-022 | 1440/1366/1200/390: nút xác nhận trong luồng cuộn tự nhiên, không tràn ngang document, chi tiết tại chỗ | cùng file: responsive idle, preview and inline history | 4 viewport; ảnh trong báo cáo |

## Parsing và data acceptance

| ID | Điều kiện pass | Bằng chứng chính | Mức bằng chứng |
|---|---|---|---|
| ACC-DATA-001 | Baseline nhận đúng 6 project, 36 entity, 4.182 record, 2.343 chartable record | `tests/test_smoke_real_workbook.py` | Covered |
| ACC-DATA-002 | Zero, blank, marker, text và percentage được phân biệt | `tests/test_parser.py`, `tests/test_validation.py` | Covered cho fixture hiện tại |
| ACC-DATA-003 | Mọi baseline record có cell address và cùng source hash | `tests/test_smoke_real_workbook.py` | Covered |
| ACC-DATA-004 | Duplicate logical key bị quality gate chặn | `tests/test_validation.py` | Covered ở validator; storage có check bổ sung chưa có test riêng |
| ACC-DATA-005 | Metric/unit/hierarchy parsing cho fixture cho kết quả kỳ vọng | `tests/test_parser.py`, `tests/test_hierarchy.py` | Covered cho fixture hiện tại |
| ACC-DATA-006 | Given cùng active external key, importer dùng lại entity identity; key chưa thấy tạo entity + alias `initial` | `_upsert_entities()` | Gap: chưa có assertion trực tiếp trên `entity_aliases` |
| ACC-DATA-007 | Rename/move/manual merge giữ historical continuity theo policy đã duyệt | Chưa có workflow/test | Not applicable: `SCP-203` Decision needed |

Nếu workbook baseline được thay có chủ đích, owner MUST lưu kết quả đối chiếu với báo cáo thủ công và cập nhật assertion trong cùng thay đổi. Không tự sửa expected count chỉ để test xanh.

## API và dashboard acceptance

| ID | Điều kiện pass | Bằng chứng chính | Mức bằng chứng |
|---|---|---|---|
| ACC-DASH-001 | Empty database trả trạng thái rỗng và không tự import | `tests/test_api.py` | Covered ở API; UI empty copy chưa có assertion riêng |
| ACC-DASH-002 | Project, entity, overview, statistics, comparison và audit trả các phần contract chính | `tests/test_api.py` | Partial: không snapshot toàn bộ response schema |
| ACC-DASH-003 | Recent/week/month/date range và weighted rate đúng rule | `tests/test_date_ranges.py`, `tests/test_charts.py` | Covered cho calculation fixtures; API recent ignores `count` được xác nhận bằng code, chưa assert riêng |
| ACC-DASH-004 | Comparison chỉ cho entity cùng unit | `app/api.py`, `tests/test_api.py`, `tests/test_charts.py` | Partial: test API chỉ đi happy path khi có candidates |
| ACC-DASH-005 | Exact chart point resolve đúng workbook cell và audit row | `tests/test_api.py`, `frontend/e2e/chart-lineage.spec.ts` | Covered |
| ACC-DASH-006 | Aggregate resolve đúng result/contributors và cursor chống sửa | `tests/test_api.py` | Covered |
| ACC-DASH-007 | Revision cũ vẫn resolve sau import mới và báo stale/freshness | `tests/test_api.py` | Covered |
| ACC-DASH-008 | Không render giao diện Điều tra bằng bàn phím; nhấn điểm Plotly vẫn mở đúng nguồn và trạng thái unavailable vẫn an toàn | `frontend/e2e/chart-lineage.spec.ts` | Covered |
| ACC-DASH-009 | Critical desktop text đạt AA ở viewport đã quy định | `frontend/e2e/contrast.spec.ts` | Covered khi Playwright suite được chạy |
| ACC-DASH-010 | Given request cũ còn pending và request mới hoàn thành trước, when request cũ hoàn thành muộn, then nó không ghi đè workspace mới | `frontend/e2e/workspace-freshness.spec.ts::a superseded request that finishes late...`; `workspace-performance.spec.ts` | Covered |
| ACC-DASH-011 | CSV export trả toàn bộ current project rows, không phụ thuộc workspace filters, với media type/filename đúng | `app/api.py`; `tests/test_api.py` chỉ assert status `200` | Gap |
| ACC-DASH-012 | Given import trả outcome `committed`, when UI hoàn tất post-commit refresh, then workspace được fetch lại và hiển thị payload mới mà không reload toàn trang | `frontend/e2e/workspace-freshness.spec.ts::successful import refreshes dashboard data...` | Covered |
| ACC-DASH-013 | Given cùng project/view/filter, when người dùng bấm **Làm mới dữ liệu**, then workspace endpoint được gọi lại với cùng query và payload mới được render | `frontend/e2e/workspace-freshness.spec.ts::manual refresh fetches workspace again...` | Covered |
| ACC-CMP-001 | Given Statistics đang xem direct children, when render child chart, then có CTA So sánh gọn; node/root không có contextual CTA | `frontend/e2e/contextual-comparison.spec.ts::vertical slice 1 opens...` | Covered |
| ACC-CMP-002 | Khi chart có nhiều chỉ số/chuỗi, lúc mở popup thì chọn sẵn chỉ số dùng gần nhất hoặc `Báo sai/Lỗi`, không hỏi lại mức thời gian/phạm vi/đơn vị đã rõ | `frontend/e2e/contextual-comparison.spec.ts::vertical slice 1 opens...` | Đã bao phủ |
| ACC-CMP-003 | Candidate chỉ hợp lệ khi cùng project, cùng non-null parent, cùng unit và có kỳ metric trùng anchor | `tests/test_entity_selection.py`; `tests/test_api.py::test_contextual_comparison_contract_filters_siblings_and_keeps_legacy_api` | Covered |
| ACC-CMP-004 | Anchor khóa và selection tối đa ba entity; backend loại ID sai kèm reason | `tests/test_api.py::test_contextual_comparison_contract_filters_siblings_and_keeps_legacy_api` | Covered |
| ACC-CMP-005 | Đổi chỉ số tính lại điều kiện hợp lệ, giữ sibling còn hợp lệ; phản hồi cũ hoàn thành muộn không ghi đè phản hồi mới | `frontend/e2e/contextual-comparison.spec.ts::metric change recomputes eligibility...`; `percentage metric remains available...` | Đã bao phủ |
| ACC-CMP-006 | Data version khác snapshot nguồn khóa mixed-revision calculation cho tới khi cập nhật current workspace | `frontend/e2e/contextual-comparison.spec.ts::new committed data version blocks...` | Covered |
| ACC-CMP-007 | So sánh chỉ số gốc hỗ trợ ngày/tuần/tháng/quý; tỷ lệ theo kỳ là tỷ lệ có trọng số trên tổng. Node con được dùng `Tổng số` của tổ tiên gần nhất cùng đơn vị nhưng không bị gán giả `Tổng số` trực tiếp | `tests/test_charts.py::test_grouped_error_rate_inherits_nearest_parent_total_without_filling_child_total`; `tests/test_api.py::test_contextual_comparison_contract_filters_siblings_and_keeps_legacy_api` | Đã bao phủ |
| ACC-CMP-008 | Modal giữ chart tối thiểu 640×340 tại 1366×768 và 1440×900, đóng modal trả focus về CTA nguồn | `frontend/e2e/contextual-comparison.spec.ts` | Covered |
| ACC-CMP-009 | Không có anchor thì API So sánh cũ giữ tương thích ngược; tab cũ không còn là lối vào giao diện | API contextual test; `frontend/e2e/contextual-comparison.spec.ts::hidden legacy workspaces are not restored as top-level tabs` | Đã bao phủ |
| ACC-CMP-010 | Có tỷ lệ nguồn dương nhưng thiếu `Báo sai/Lỗi`, khi tổng hợp theo tuần/tháng/quý thì không suy thành `0%` hoặc suy ngược tử số; backend trả `RATE_NUMERATOR_MISSING` | `tests/test_charts.py::test_grouped_rate_does_not_infer_zero_when_positive_source_rate_has_no_error_count`; `tests/test_api.py::test_contextual_period_status_explains_missing_rate_numerator`; kiểm thử Playwright thông báo thiếu tử số | Đã bao phủ |

## Acceptance theo phase và tính năng mở rộng

### Contextual Comparison Phase 2 — Thống kê đa nội dung

Nguồn đặc tả: [contextual-comparison-phase-2.md](../frontend/contextual-comparison-phase-2.md). Các tiêu chí dưới đây đã được khóa bằng source và kiểm thử ngày 2026-09-30:

| ID | Tiêu chí | Bằng chứng bắt buộc | Trạng thái |
|---|---|---|---|
| CMP2-ACC-000 | Thống kê và Chỉ số gốc không cho kết quả missing/zero mâu thuẫn khi có tỷ lệ nguồn dương nhưng thiếu tử số | Regression calculation + báo cáo tác động | Đạt |
| CMP2-ACC-001 | Chuyển sang Thống kê giữ anchor và sibling còn hợp lệ | API + Playwright | Đạt |
| CMP2-ACC-002 | Tổng trong kỳ đa nội dung khớp `prepare_period_statistics.period_sum` | Chart/API unit test | Đạt |
| CMP2-ACC-002A | Lens Thống kê chỉ cho chọn cách tính và tự hiển thị cả `Tổng số` lẫn `Báo sai/Lỗi` hiện có; metric đã chọn ở lens gốc được giữ khi quay lại | API + Playwright | Đạt |
| CMP2-ACC-002B | Popup Thống kê không hiển thị bảng số liệu hoặc danh sách điểm bàn phím; Trung bình mỗi ngày dùng toàn bộ đường nét liền và nhấn điểm biểu đồ vẫn mở Điều tra | Chart test + Playwright | Đạt |
| CMP2-ACC-002C | Chỉ số gốc và Thống kê dùng chung màu theo entity, cột nhóm cho count/sum và line nét liền rộng 3 px, marker 8 px cho rate/average | Chart test + Playwright | Đạt |
| CMP2-ACC-003 | Backend loại khác cha, dự án, đơn vị hoặc không có kỳ giao nhau | API test | Đạt |
| CMP2-ACC-004 | Trung bình mỗi ngày bằng tổng chia số ngày đủ điều kiện | Calculation regression | Đạt |
| CMP2-ACC-005 | Missing, zero, ký hiệu nguồn và kỳ chưa đầy đủ giữ đúng contract hiện tại | Fixture matrix | Đạt |
| CMP2-ACC-006 | Coverage kế thừa đúng ancestor nhưng không tạo Tổng số giả | Calculation/API test | Đạt |
| CMP2-ACC-007 | Mỗi điểm tổng hợp ánh xạ đúng entity, metric, phép tính và kỳ | Aggregate lineage test | Đạt |
| CMP2-ACC-008 | Thành phần của Trung bình mỗi ngày tách value và coverage | Provenance/contributor test | Đạt |
| CMP2-ACC-009 | Thiếu lineage thì Điều tra fail closed, không đoán ref | API + Playwright | Đạt |
| CMP2-ACC-010 | Điều tra không che biểu đồ tại 1366×768 và 1440×900 | Playwright viewport | Đạt |
| CMP2-ACC-011 | Đóng Điều tra giữ popup và biểu đồ ổn định; vòng đi-về Đối chiếu giữ đúng điểm và viewport | Playwright | Đạt |
| CMP2-ACC-012 | Audit round-trip khôi phục popup khi cùng phiên bản dữ liệu | Playwright navigation | Đạt |
| CMP2-ACC-013 | Import mới và phản hồi cũ không làm trộn snapshot | API + Playwright stale response | Đạt |
| CMP2-ACC-014 | Ma trận 6 dự án không có trường hợp hợp lệ nhưng chart rỗng | Kiểm tra dữ liệu thật | Đạt |
| CMP2-ACC-015 | Giá trị đa nội dung khớp Thống kê đơn nội dung | Cross-surface parity test | Đạt |
| CMP2-ACC-016 | Phase 1, AI, Audit và import freshness không regression | Full regression | Đạt |
| CMP2-ACC-017 | Tab So sánh cũ và nút mở mục cũ được ẩn sau kiểm tra tương đương; API cũ vẫn tương thích | API + Playwright | Đạt |

### Scheduled daily import (`SCP-101`)

Chưa được đánh dấu pass cho tới khi có test chứng minh:

- scheduler phát hiện đúng một input mới theo lịch/timezone đã chốt;
- duplicate không tạo run business trùng;
- lỗi có retry/backoff và phát tín hiệu vận hành;
- lần chạy có audit và có thể xác định workbook nào đã xử lý;
- restart không làm mất lịch hoặc xử lý lặp ngoài contract.

### AI trend summary (`SCP-102`)

Acceptance canonical của AI/Data v2 nằm tại [05-ai-evaluation-and-acceptance.md](../ai-data/05-ai-evaluation-and-acceptance.md):

| Nhóm | Phạm vi | Mức bằng chứng hiện tại |
|---|---|---|
| `AI-ACC-TR-*` | Deterministic trend, zero/missing, weighted rate, coverage, freshness | Gap |
| `AI-ACC-CMP-*` | Eligibility và evidence hai phía cho comparison | Gap; feature Proposed |
| `AI-ACC-CON-*` | Schema/fact/evidence validation, prompt safety, provider fallback và privacy | Gap / Decision needed |
| `AI-ACC-RPT-*` | Template, version, review, approval và export | Gap; feature Proposed |

Các ID v1 `ACC-AI-001`–`ACC-AI-010` đã retired và chỉ còn trong migration map. Không tiêu chí AI nào được xem là pass vì repository chưa có adapter/API/UI/test AI.

### Due date, recurrence và entity identity (`SCP-201`, `SCP-202`, `SCP-203`)

Các mục này hiện là **Decision needed**, không nằm trong acceptance gate. Nếu mentor đưa issue workflow vào scope, MUST bổ sung spec và fixture trước khi code, bao gồm timezone boundary, trạng thái fixed/reopened, định danh issue, chống cảnh báo trùng và quyền sở hữu notification. Nếu duyệt entity continuity, MUST chốt matching/approval/alias lifecycle và fixture rename/move/merge trước khi đánh dấu pass.

## Biên bản nghiệm thu tối thiểu

Mỗi lần bàn giao nên ghi:

- commit/tag được kiểm tra;
- phiên bản workbook/config;
- command và kết quả test;
- manifest baseline;
- danh sách known limitations;
- các mục `Decision needed` và người chịu trách nhiệm chốt;
- chữ ký/xác nhận của người nghiệm thu hoặc link tới ticket phê duyệt.

# Bổ sung AI-RPT — Báo cáo bản nháp v1 (05/10/2026)

Nghiệm thu phần draft của `AI-RPT-001`–`AI-RPT-006`, `AI-RPT-010`–`AI-RPT-011`, `AI-RPT-013`–`AI-RPT-015`: năm section/template version, dữ liệu committed bất biến, lời AI/manual có kiểm chứng, nguồn chính xác, revision/history/idempotency, import mới không ghi đè và file PDF/DOCX DRAFT theo exact revision. Bằng chứng: `tests/test_reporting.py`, `frontend/e2e/reports.spec.ts` và [live/output/export review](../ai-data/evidence/2026-10-05-reports-review.md). Thống kê kiểm tra parity 4 grain × 3 cách tính.

Không nghiệm thu authenticated approval (`AI-RPT-012`), retention policy, schedule/send/publish hoặc pagination trong Microsoft Word thực tế. Local checked không tương đương approved. [Phạm vi đã triển khai](../ai-data/12-report-workspace-as-built.md).

# Bổ sung ACC-OV-KPI — Bốn thẻ Tổng quan theo nguồn

Nghiệm thu theo các lát count/contract, extrema, adjacent change, freshness/responsive tại [contract](../frontend/overview-summary-metrics.md#5-acceptance-theo-lát-dọc). Áp dụng hướng hybrid đã duyệt, không áp dụng yêu cầu nguồn project-only của đề xuất cũ. Thống kê phải khớp SUM/AVG/ngày, danh sách kỳ và bộ lọc hiện có; không mượn số Tổng quan khi đổi tab/cách tính hoặc không có kỳ. Khối thông tin phía trên thẻ không mở sẵn; nguồn vẫn xem/chọn được trong mục thu gọn. Kết quả test/inventory ban đầu: [evidence](overview-summary-metrics-evidence.md); bổ sung hiện tại: [Thống kê và thu gọn](overview-statistics-summary-evidence.md). Không coi missing là 0, source riêng là tổng project hoặc metadata bootstrap là count trong window.
