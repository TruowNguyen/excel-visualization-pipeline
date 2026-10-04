# Semantic validator v2 và API thật — 02/10/2026

## Kết luận

Generation mới dùng provider/narrative v4, registry trend-summary-v12 / metric-overview-v8, resource grounded-insight-v4.md. Public envelope trend/overview, core KPI, weighted pair rule, EvidenceBuilder, privacy/freshness gates và provider timeout/retry không đổi.

Kết quả live chưa đạt chiều sâu insight mong muốn. Ba lần gọi thật trên cùng phạm vi VSO / 1.1. Chất lượng cảnh báo / 07–16/09/2026 / ba KPI đều nêu số/ngày đúng, nhưng ưu tiên đỉnh của số lỗi và Tổng số, không giải thích tỷ lệ báo sai. Lần cuối ready/partial: một claim được giữ. Không tuyên bố accepted toàn bộ. [Bằng chứng nguyên văn và latency](2026-10-02-live-semantic-evaluation.json).

## Audit và hợp đồng

- Engine xác lập điều đúng; câu fallback không còn là câu model bắt buộc sao chép. Legacy v1/v2/v3 giữ behavior cũ để tương thích; generation mới là v4, không full-match canonical expression.
- Structural layer strict: JSON, unknown/duplicate fields, identity/status, tối đa hai claim và 650 ký tự/claim, required fields, duplicate claim/fact IDs. Envelope sai không salvage.
- Grounding layer: candidate/claimType, fact trong snapshot, relation predicate/dependency closure, nguồn và metric/evidence scope. Một relation citation giải quyết các operand đã kiểm chứng; không bắt model chép mọi operand ID. ID giả không được tự sửa.
- Numerical/temporal layer riêng: Decimal so với giá trị fact; đúng metric, %, điểm phần trăm, vai trò đỉnh/đáy/giá trị kết thúc và cặp giá trị–ngày. Ngày dd/mm không được mơ hồ về năm. Không tự tính số mới hay làm tròn.
- Semantic layer riêng: trích xuất metric, chiều, chronology và quan hệ thay cho toàn câu. Câu giới hạn được phân biệt với khẳng định chất lượng/nguyên nhân/dự báo; câu giới hạn không che được khẳng định khác đi kèm.
- selectedCandidateIds là guidance, không ép selection/order. Provider nhận tối đa 12 candidate có semanticSpec, không có paragraph/regex/lineage targets. Mỗi request vẫn chỉ một generation call, không thêm LLM judge hoặc validation retry.
- Giữ claim hợp lệ, loại claim không qua kiểm chứng. validation.status=partial, claimResults có index/candidateId/errors/categories. Không còn claim hợp lệ thì deterministic fallback. Structural failure và provider failure vẫn khác semantic rejection.

## Giới hạn

Đây là semantic extractor tiếng Việt có phạm vi, KHÔNG phải bộ chứng minh entailment cho mọi câu tự nhiên. Nội dung chưa bao phủ fail closed với semantic_unverified. Không đánh đồng lỗi này với phát hiện dữ liệu sai. Các paraphrase đúng từ hai lần live đầu đã thành test hồi quy; không chỉnh model prose để làm nó pass. Lần live cuối vẫn còn false rejection do coverage; đây là giới hạn đang có, không phải kết quả semantic validation tổng quát đã hoàn tất.

LLMAdapter giữ JSON mode trên 9Router vì chưa xác minh gateway hỗ trợ strict JSON Schema. JSON/schema hợp lệ không tự chứng minh ngữ nghĩa đúng. [Official OpenAI Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

## Giao diện và kiểm tra

Impeccable clarify giữ giao diện desktop hiện có. Thông báo phân biệt lỗi định dạng, nguồn, số/ngày và ngữ nghĩa. Tổng quan/diễn biến engine vẫn có; narrative v4 đã kiểm chứng hiện trong “Điều cần chú ý”, có nhãn riêng, anchors theo IDs thực sự được chấp nhận. Một khối nguồn mặc định đóng. Không tối ưu thêm mobile.

236 Python tests, 20 AI Playwright tests và frontend build pass; build chỉ có cảnh báo Plotly chunk đã có. Các capture semantic-{structure,grounding,numerical_temporal,semantic,partial}-{1440,1280}.png là synthetic/mocked panel states, không phải ảnh provider live. Chúng không chứng minh live accuracy/latency. Builder review: trạng thái, nhãn nguồn, reading hierarchy và nguồn đóng đúng; không có yêu cầu sửa bố cục ngoài phạm vi.

## AI còn bỏ sót gì

Ngày 12–13/09, Tổng số giảm 515→214 nhưng Báo sai/Lỗi tăng 19→43: số lỗi và tỷ lệ cùng tăng, không thể giải thích bằng lượng ghi nhận tăng. Ngày 15–16/09, số lỗi giữ 22 nhưng Tổng số giảm 657→420: tỷ lệ tăng mà số lỗi không tăng. Đây là quan hệ đại số, không phải kết luận nguyên nhân nghiệp vụ hoặc chất lượng giảm.

Ưu tiên tiếp theo: tiêu chí chọn/giải thích quan hệ KPI và evals đa phạm vi, không bỏ safety gate để đạt pass rate.

## Tái lập có chủ đích

`python scripts/evaluate_ai_runtime.py --live --project VSO --entity 1-1-chat-luong-canh-bao-ghi-nhan-tren-he-thong-ba6898fb1d78 --start 2026-09-07 --end 2026-09-16`

Script yêu cầu --live và privacy/config gate bật. Dùng FastAPI TestClient đọc SQLite committed; provider là API thật. Repository snapshot thuộc process đánh giá riêng, không cập nhật kết quả trong browser/dev server. Output review có chuỗi chuẩn hóa và model prose, không có key/Excel/lineage targets. Ba calls trên một scope không xác lập accuracy, acceptance rate hoặc latency production.
