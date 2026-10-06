# Đặc tả Automated CX Report

Thư mục này là nguồn đặc tả chuẩn cho hành vi có thể quan sát và điều kiện nghiệm thu của hệ thống. Khi mô tả trong `specs/` khác với tài liệu giải thích trong `docs/`, cần cập nhật một trong hai và chốt quyết định trước khi phát hành; không âm thầm chọn một phiên bản.

## Cách tổ chức tài liệu

```text
specs/
├── product/   # scope, PRD, use cases
├── core/      # import, flow, domain model, database
├── api/       # public/backend contracts
├── frontend/  # observable dashboard behavior
├── ai-data/   # AI context, model, output and safety contracts
└── quality/   # acceptance, traceability and drift audit
```

| Module | Tài liệu | Câu hỏi được trả lời |
|---|---|---|
| Product | [scope-and-status.md](product/scope-and-status.md) | Chức năng nào thuộc phạm vi, đã làm hay còn chờ quyết định? |
| Product | [product-requirements.md](product/product-requirements.md) | Sản phẩm giải quyết vấn đề gì, cho ai và có yêu cầu nào? |
| Product | [use-cases.md](product/use-cases.md) | Actors thực hiện các luồng nghiệp vụ và ngoại lệ nào? |
| Core | [import-process.md](core/import-process.md) | Workbook đi qua preview, quality gate và commit như thế nào? |
| Core | [data-flow.md](core/data-flow.md) | Dữ liệu đi từ Excel tới SQLite, API và dashboard ra sao? |
| Core | [data-model.md](core/data-model.md) | Các thực thể, khóa, revision và lineage có ý nghĩa gì? |
| Core | [database-design.md](core/database-design.md) | SQLite schema, ERD, khóa, revision và transaction được thiết kế ra sao? |
| API | [api-contract.md](api/api-contract.md) | Frontend và client được phép dựa vào endpoint, tham số và lỗi nào? |
| Frontend | [dashboard-behavior.md](frontend/dashboard-behavior.md) | Dashboard phải phản ứng thế nào với bộ lọc, dữ liệu thiếu và lỗi? |
| Frontend | [overview-summary-metrics.md](frontend/overview-summary-metrics.md) | Bốn thẻ Tổng quan/Thống kê dùng Tổng số ghi nhận; nguồn và cách đọc trong mục thu gọn. |
| Frontend | [overview-summary-metrics-plan.md](frontend/overview-summary-metrics-plan.md) | Lưu đề xuất cũ và các điểm dừng trước khi duyệt mapping nguồn. |
| Quality | [overview-summary-gate-0.md](quality/overview-summary-gate-0.md) | Inventory nguồn, quyết định đổi metric và lịch sử Gate 0. |
| Quality | [overview-summary-metrics-evidence.md](quality/overview-summary-metrics-evidence.md) | Bằng chứng implementation, backend/frontend regression và kiểm chứng cả sáu dự án. |
| Quality | [overview-statistics-summary-evidence.md](quality/overview-statistics-summary-evidence.md) | Bổ sung thẻ Thống kê theo calculation hiện có và bỏ khối thông tin Tổng quan mở sẵn. |
| Frontend | [unified-import-workspace.md](frontend/unified-import-workspace.md) | Nhập Excel hợp nhất: ưu tiên nhập mới, lịch sử phụ mở tại chỗ; đặc tả và giới hạn đã triển khai. |
| Frontend | [contextual-comparison.md](frontend/contextual-comparison.md) | Shape và contract nào đã khóa cho Contextual Comparison? |
| Frontend | [contextual-comparison-phase-2.md](frontend/contextual-comparison-phase-2.md) | Phase 2 Thống kê đa nội dung đang hoạt động thế nào và được triển khai theo lát dọc nào? |
| Quality | [contextual-comparison-vs1-evidence.md](quality/contextual-comparison-vs1-evidence.md) | Bằng chứng source/API/UI/test cho Vertical Slice 1? |
| Quality | [contextual-comparison-phase-2-evidence.md](quality/contextual-comparison-phase-2-evidence.md) | Bằng chứng hoàn thành Gate 2.0 và các lát Phase 2? |
| AI/Data | [README.md](ai-data/README.md) | AI trend, comparison, reporting, data/evidence contract và acceptance được quản trị thế nào? |
| AI/Data | [11-report-workspace-plan.md](ai-data/11-report-workspace-plan.md) | Kế hoạch gốc tab Báo cáo; v1 đã được triển khai, các mục ngoài v1 vẫn là proposal. |
| AI/Data | [12-report-workspace-as-built.md](ai-data/12-report-workspace-as-built.md) | Bản nháp năm phần, snapshot/revision, điểm đề xuất và xuất PDF/DOCX; không có official approval. |
| Quality | [acceptance-criteria.md](quality/acceptance-criteria.md) | Điều kiện nào chứng minh từng chức năng hoạt động? |
| Quality | [traceability-matrix.md](quality/traceability-matrix.md) | Requirement nào được nối tới contract, code và test nào? |
| Quality | [documentation-drift-report.md](quality/documentation-drift-report.md) | Những điểm drift nào đã được phát hiện, sửa hoặc còn mở? |
| Quality | [contextual-comparison-gate-0.md](quality/contextual-comparison-gate-0.md) | Gate 0 đã xác minh calculation, hierarchy, version và lineage ra sao? |

## Quy ước trạng thái

- **As-built**: hành vi đang tồn tại trong code và có bằng chứng kiểm thử.
- **Accepted, not built**: phạm vi đã được xác nhận nhưng chưa triển khai.
- **Proposed**: thiết kế mở rộng đang chờ product owner/mentor chấp thuận, chưa phải cam kết phạm vi.
- **Decision needed**: chưa được đưa vào phạm vi cho tới khi có quyết định bằng văn bản.
- **Out of scope**: chủ động không thực hiện trong phiên bản được nêu.

Từ khóa **MUST**, **SHOULD**, **MAY** lần lượt biểu thị bắt buộc, khuyến nghị và tùy chọn. Mỗi thay đổi hành vi MUST cập nhật tài liệu liên quan và tiêu chí nghiệm thu tương ứng.

## Chủ sở hữu contract

Để tránh lặp quy tắc chi tiết, mỗi nhóm ID chỉ có một tài liệu chuẩn:

| Prefix | Tài liệu chuẩn |
|---|---|
| `SCP-*` | `product/scope-and-status.md` |
| `PRD-*` | `product/product-requirements.md` |
| `UC-*` | `product/use-cases.md` |
| `IMP-*` | `core/import-process.md` |
| `FLOW-*` | `core/data-flow.md` |
| `DATA-*` | `core/data-model.md` |
| `DB-*` | `core/database-design.md` |
| API v1 | `api/api-contract.md` |
| `DASH-*` | `frontend/dashboard-behavior.md` |
| `AI-SCP-*` | `ai-data/00-ai-scope-and-roadmap.md` |
| `AI-TR-*` | `ai-data/01-ai-trend-analysis.md` |
| `AI-CMP-*` | `ai-data/02-ai-comparative-analysis.md` |
| `AI-RPT-*` | `ai-data/03-automated-reporting.md` |
| `AI-CON-*` | `ai-data/04-ai-data-and-output-contracts.md` |
| `AI-ACC-*` | `ai-data/05-ai-evaluation-and-acceptance.md` |
| `AI-DEC-*` | `ai-data/06-decisions-and-delivery-plan.md` |
| `AI-PLAN-*` | `ai-data/07-vertical-slice-implementation-plan.md` |
| `ACC-*` ngoại trừ `AI-ACC-*` | `quality/acceptance-criteria.md` |

Các ID v1 `AI-001`–`AI-028` và `ACC-AI-001`–`ACC-AI-010` đã retired từ AI/Data v2.0.0; Phase 1 as-built được ghi nhận trong v2.1.0. Migration map nằm tại `ai-data/ai-reporting-model.md`. Tài liệu khác SHOULD tham chiếu ID canonical thay vì sao chép toàn bộ rule. Báo cáo drift và traceability là bằng chứng audit, không phải nơi định nghĩa hành vi mới.

## Quan hệ với các thư mục khác

- `specs/`: contract sản phẩm, quy tắc nghiệp vụ và acceptance criteria.
- `docs/`: giải thích kiến trúc, khảo sát và thiết kế triển khai chi tiết.
- `config/`: rule parser và visualization có thể cấu hình.
- `tests/`, `frontend/e2e/`: bằng chứng kiểm thử tự động.
- `scripts/`: thao tác vận hành, smoke test và quản trị database.

Các tài liệu nền vẫn được giữ tại:

- [`../docs/SYSTEM_SPECIFICATION.md`](../docs/SYSTEM_SPECIFICATION.md)
- [`../docs/SQLITE_DATABASE_DESIGN_v3.md`](../docs/SQLITE_DATABASE_DESIGN_v3.md)
- [`../docs/FRONTEND_BACKEND.md`](../docs/FRONTEND_BACKEND.md)
- [`../docs/CHART_LINEAGE_PHASE2.md`](../docs/CHART_LINEAGE_PHASE2.md)
- [`../excel_structure.md`](../excel_structure.md)

## Quy trình thay đổi spec

1. Gắn thay đổi với một ID trong spec, ví dụ `IMP-003` hoặc `ACC-DASH-004`.
2. Ghi rõ trạng thái và quyết định phạm vi nếu là chức năng mới.
3. Cập nhật contract/hành vi trước hoặc cùng pull request với code.
4. Thêm hoặc cập nhật test làm bằng chứng.
5. Chạy quality gate trong `quality/acceptance-criteria.md` trước khi xác nhận hoàn thành.
