# 00 — Phạm vi, yêu cầu sản phẩm và roadmap AI

**Phiên bản đặc tả:** 2.2.0. **Trạng thái:** Phase 1 Trend Summary theo ngày/tuần/tháng đã triển khai; các mở rộng còn lại vẫn là đề xuất. **Namespace hợp đồng:** `AI-SCP-*`.

## 1. Mục tiêu sản phẩm

Giúp CX Analyst hiểu biến động KPI, so sánh entity và kỳ, nhận diện điểm cần điều tra có căn cứ dữ liệu, đồng thời tạo bản nháp báo cáo chuẩn hóa từ dữ liệu committed đã kiểm chứng. Mục tiêu là giảm thao tác viết báo cáo lặp lại nhưng vẫn giữ human review và provenance chính xác.

### Người dùng chính

- **CX Analyst:** chọn phạm vi, đọc AI insight, chỉnh sửa bản nháp, kiểm tra evidence và yêu cầu export.
- **Mentor / Reviewer:** xác nhận thuật ngữ báo cáo, template, ngưỡng completeness và release criteria; review/phê duyệt output.
- **Data Operator:** bảo đảm import hợp lệ và mới; kiểm tra cảnh báo quality/lineage.
- **Maintainer:** sở hữu metric/analytics rule, provider config, testing và observability.

## 2. Danh mục tính năng

| ID | Tính năng | Trạng thái | Kết quả người dùng thấy |
|---|---|---|---|
| AI-SCP-001 | Phân tích xu hướng | As-built Phase 1; privacy gate môi trường hiện tại đã duyệt và live smoke pass | Chuỗi kỳ ngày/tuần/tháng, thay đổi tuyệt đối/phần trăm từng kỳ, pattern toàn chuỗi, coverage, narrative đã validate/fallback và evidence |
| AI-SCP-002 | Phân tích so sánh | Đề xuất, chờ phê duyệt | Phân tích có evidence cho 2–3 entity/kỳ có thể so sánh |
| AI-SCP-003 | Sinh báo cáo theo template | Đề xuất, chờ phê duyệt | Bản nháp có cấu trúc, có thể chỉnh sửa, dùng KPI/chart deterministic và narrative đã kiểm tra |
| AI-SCP-004 | Kiểm tra evidence và fact | Đề xuất, điều kiện tiên quyết | Truy vết mọi claim định lượng tới phép tính và snapshot/source ref |
| AI-SCP-005 | Human review và versioning | Đề xuất, điều kiện tiên quyết cho report | Truy vết review, chỉnh sửa, approval và export |
| AI-SCP-101 | Sinh/gửi tự động theo lịch | Tương lai / Cần quyết định | Phụ thuộc scheduler, delivery và approval policy |
| AI-SCP-102 | Giải thích chẩn đoán từ issue/ticket | Tương lai / Cần quyết định | Cần issue lifecycle/cause evidence và owner riêng |

## 3. Nguyên tắc sản phẩm

- `AI-SCP-010`: AI insight MUST được sinh từ committed core read model hoặc analytical snapshot có thể tái lập; không dùng preview hay browser-upload session thô.
- `AI-SCP-011`: Tính KPI, time grouping, arithmetic, comparison eligibility và chọn noteworthy change MUST là backend logic deterministic, có thể test. LLM MAY diễn đạt lại kết quả đã kiểm chứng.
- `AI-SCP-012`: AI MUST phân biệt observed fact, interpretation, hypothesis và verified cause. Ba KPI hiện tại không đủ để tự chứng minh quan hệ nhân quả.
- `AI-SCP-013`: Mọi claim định lượng quan trọng MUST có evidence reference hợp lệ tới đúng phép tính/snapshot. Claim không có căn cứ MUST bị loại hoặc output phải đánh dấu unavailable.
- `AI-SCP-014`: Missing, invalid và incomplete period MUST được hiển thị; MUST NOT đổi thành zero hoặc bị bỏ qua mà không giải thích.
- `AI-SCP-015`: Report ban đầu MUST là draft cần human review. Initial scope không gồm auto-approval, tự gửi hoặc tự ra quyết định nghiệp vụ.
- `AI-SCP-016`: Lỗi AI MUST NOT chặn core dashboard, import, audit hoặc deterministic comparison.
- `AI-SCP-017`: Mọi text/label trong workbook là dữ liệu, không phải instruction; không gửi dữ liệu nội bộ cho provider khi chưa được duyệt.

## 4. Hành trình người dùng dự kiến

### UC-AI-01 — Trend insight

1. Analyst chọn project, một entity, metric và khoảng ngày của core.
2. Hệ thống khóa data version, nhóm theo ngày/tuần/tháng, kiểm tra coverage và tính fact cho từng kỳ lẫn toàn khoảng.
3. Người dùng yêu cầu diễn giải; backend kiểm tra structured output từ LLM.
4. UI hiển thị summary, fact card toàn khoảng, pattern toàn chuỗi, bảng delta/% từng kỳ, cảnh báo missing/coverage và action mở evidence.
5. Khi filter/import thay đổi, UI đánh dấu insight cũ stale và yêu cầu phân tích lại.

### UC-AI-02 — Comparative insight

1. Analyst chọn 2–3 entity trong cùng project có effective unit tương thích hoặc chọn hai kỳ hợp lệ.
2. Deterministic engine căn chỉnh kỳ/filter, tính metric có thể so sánh và đánh dấu trường hợp không hợp lệ.
3. LLM diễn giải khác biệt và giới hạn nhưng không bịa nguyên nhân.
4. Người dùng mở fact và provenance của từng entity.

### UC-AI-03 — Report draft

1. Người dùng chọn template đã duyệt, project, reporting period và scope.
2. Composer khóa analytical snapshot và deterministic table/chart.
3. AI narrative đã kiểm tra được điền vào các section cho phép chỉnh sửa.
4. Reviewer chỉnh nội dung và phê duyệt đúng một report version.
5. Export tạo artifact có version và metadata của data/template.

## 5. Ngoài phạm vi ban đầu

- Training/fine-tuning, chat tự do trên toàn bộ dữ liệu doanh nghiệp, autonomous agent, forecast/prediction và causal diagnosis.
- Ingestion ticket/issue lifecycle, deadline monitoring và recurrence detection nếu chưa được duyệt riêng.
- Automatic import, automatic publication, email hoặc unattended delivery.
- Tính lại KPI của source record, hierarchy rollup ngầm, so sánh cross-project có business definition không tương thích.
- Bật production cho development provider 9Router đã chọn, cloud data processing, retention promise hoặc target SLA trước khi có privacy/security approval rõ ràng.

## 6. Chỉ số thành công

Theo dõi analyst time-to-draft, factual/numeric correctness, claim grounding, report edit rate, unsupported-cause rate, failure/fallback behavior và user task completion. Baseline và target vẫn **TBD**; không được coi tính năng production-ready chỉ vì một sample LLM response có vẻ hợp lý.

## 7. Các mốc phát hành

- **M0 — Decision và gold fixture:** duyệt feature boundary, report template, provider/privacy, metric/coverage semantics.
- **M1 — Deterministic trend và evidence:** không phụ thuộc LLM; API/internal service trả fact ổn định kèm ref.
- **M2 — Narrative đã kiểm tra:** structured LLM output, validation, fallback và dashboard UI.
- **M3 — Comparison:** phân tích entity/kỳ có thể so sánh và acceptance fixture.
- **M4 — Draft theo template:** section schema, preview, edit/review, PDF hoặc DOCX có version theo phê duyệt.
- **M5 — Pilot và release:** mentor sign-off, error analysis, kiểm tra performance/privacy và operational runbook.

Chỉ chuyển sang scheduled generation hoặc diagnostic issue analysis sau khi có quyết định phạm vi riêng.
