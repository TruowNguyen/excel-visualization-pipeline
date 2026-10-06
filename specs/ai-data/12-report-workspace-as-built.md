# 12 — Tab Báo cáo: phiên bản đã triển khai

Ngày triển khai: 05/10/2026; cập nhật UX/UI: 06/10/2026. Sản phẩm: Automated CX Report. Trạng thái: **As-built — bản nháp v1**, không phải báo cáo đã phê duyệt.

Thực hiện theo [kế hoạch 11](11-report-workspace-plan.md). Người dùng đã chọn **PDF và DOCX**, chỉ **chọn/bỏ điểm hệ thống đề xuất**. Báo cáo mới dùng template dự thảo `cx-period-report` phiên bản `1.3`, renderer `cx-report-renderer-v4`; không coi đây là mẫu báo cáo cuối của mentor. Báo cáo template `1.0`/`1.1`/`1.2` giữ bố cục tương thích, không tự chuyển template của snapshot cũ.

## 1. Cách sử dụng

1. Mở tab **Báo cáo** để xem danh sách bản nháp. Chủ động chọn một bản nháp để mở, hoặc chọn **Tạo báo cáo mới** để hiện thiết lập. Không tự mở bản gần nhất, kể cả sau reload hoặc khi quay lại tab. **Tạo báo cáo từ phạm vi này** ở Tổng quan/Thống kê mở thẳng thiết lập đã sao chép, chưa hiện nội dung báo cáo.
2. Sidebar chỉ giữ bộ chọn dự án khi tab Báo cáo đang mở. Trong **Thiết lập báo cáo mới**, chọn tên, nội dung theo dõi, vấn đề, thời gian và cách tính. Phạm vi báo cáo độc lập với bộ lọc dashboard; báo cáo đã lưu nằm trong disclosure riêng.
3. Chọn **Chuẩn bị bản nháp**. Backend chụp dữ liệu committed và lưu v1, chưa gọi LLM.
4. Kiểm tra phạm vi và số liệu; chọn **Tạo diễn giải AI** nếu cần. AI chỉ diễn giải facts từ bản dữ liệu đã lưu.
5. Chọn tối đa năm điểm đáng chú ý. **Xem trên biểu đồ** định vị điểm/giai đoạn; nhấp điểm đã chọn trên biểu đồ định vị nhận định tương ứng. Có thể định vị cả nhận định đã bỏ chọn: anchors hiện tạm với nhãn **Đang xem**, không tự chọn lại và không gọi API. **Xem nguồn** mở cơ chế điều tra hiện có.
6. Có thể sửa tiêu đề, lời diễn giải có căn cứ và ghi chú. **Lưu phiên bản mới** kiểm chứng lời sửa và tạo revision mới. Số, ngày, đơn vị, series và nguồn không được sửa.
7. Chọn **Đánh dấu đã kiểm tra** nếu đã kiểm tra bản nháp. Chọn PDF/DOCX rồi **Xuất phiên bản**. File luôn mang nhãn **BẢN NHÁP / DRAFT**; không bắt buộc xác nhận đã kiểm tra để xuất một bản nháp.

Các chỉnh sửa chưa lưu phải được lưu trước khi sinh lại AI, đánh dấu kiểm tra hoặc xuất. Reload trở về danh sách, không phục hồi nội dung chưa lưu. Bản cũ chỉ đọc/xuất; muốn sửa phải mở bản mới nhất. Nhập dữ liệu mới không âm thầm sửa báo cáo đã lưu.

**Xóa bản nháp** nằm ở mỗi dòng trong danh sách. Xác nhận nêu rõ tên bản nháp, xóa tất cả phiên bản khỏi danh sách và không xóa PDF/DOCX đã tải. Backend kiểm tra đúng dự án/nguồn và phiên bản mới nhất; nếu đã có cập nhật khác, trả 409 và giữ bản nháp. Khi lỗi, giao diện giữ nội dung và cho mở lại/thử lại. Xóa thành công không tự chọn bản tiếp theo. Đây là xóa mềm bằng migration `008_report_deletions.sql`: các snapshot/phiên bản/tệp xuất được giữ trong kho cho khả năng phục hồi quản trị, nhưng các API đọc, sửa, AI, kiểm tra và xuất đều chặn bản đã xóa. Chưa có chức năng khôi phục trên giao diện.

**Tạo báo cáo từ phạm vi này** kế thừa nhóm kỳ của dashboard: Tổng quan lấy bộ lọc tuần/tháng đang xem, không lấy `aiGroupBy` độc lập của Insight; Thống kê lấy `statisticsGroup` và cách tính. Khi thao tác này được chọn, setup mở lại và không bị cơ chế khôi phục báo cáo cũ che lên. Chỉ sao chép thiết lập, không tự tạo báo cáo/gọi AI và không sửa bản nháp đã lưu.

Thanh thao tác lưu/kiểm tra/xuất nằm ngay đầu tài liệu và bám khi cuộn; tên nút xuất ghi đúng revision đang xem. Thông tin báo cáo có dòng phạm vi/ngày ngắn gọn, metadata đầy đủ trong **Phạm vi và thông tin chi tiết**. Nội dung diễn giải dùng toàn chiều rộng vùng báo cáo, xuống dòng tự nhiên và không cắt nội dung.

## 2. Phạm vi hỗ trợ

| Lựa chọn | Hành vi hiện tại |
|---|---|
| Dự án | Một dự án trong mỗi báo cáo |
| Nội dung | Một node, các vấn đề chọn trong nhóm, hoặc tất cả con trực tiếp |
| Tổng quan | Ba KPI hiện có; ngày/tuần/tháng; khoảng ngày |
| Thống kê | `total`, `error`; ngày/tuần/tháng/quý; tổng, trung bình/ngày, hoặc cả hai |
| Khoảng thống kê | Các kỳ gần nhất, toàn bộ dữ liệu hoặc khoảng kỳ; tùy chọn kỳ chưa đầy đủ |
| Điểm đánh dấu | Tối đa 12 đề xuất, chọn tối đa 5; không tạo điểm/giai đoạn tùy ý |
| Lưu | Backend SQLite; danh sách 100 báo cáo cập nhật gần nhất của project/source; lịch sử revision |
| Xuất | PDF và DOCX của exact revision; file xuất lần đầu được lưu và trả lại nguyên byte khi xuất lại |

Không cộng các vấn đề thành tổng nhóm, không xếp hạng độ lớn giữa đơn vị khác nhau, không tính correlation, không suy ra nguyên nhân nghiệp vụ. Missing khác zero. Tổng và trung bình/ngày là hai cơ sở tính riêng; không tạo `error_rate` cho Thống kê.

## 3. Năm phần dùng chung preview và export

| Phần | Nguồn và quy tắc |
|---|---|
| Thông tin báo cáo | Deterministic: dự án, membership, window, calculation, snapshot, thời điểm tạo và version |
| Tóm tắt điều hành | Trích câu hoàn chỉnh từ diễn giải đã kiểm chứng; ưu tiên diễn biến và bằng chứng định lượng; tối đa hai vấn đề cùng một nhận định liên hệ chung khi có |
| Tổng quan KPI | Mức ở **kỳ có dữ liệu cuối**, đơn vị và coverage; không gọi đó là tổng toàn chuỗi. Preview bổ sung thay đổi ở kỳ cuối |
| Diễn biến trong kỳ | Mỗi vấn đề: biểu đồ tổng quát → diễn giải chung → từng biểu đồ metric → diễn giải riêng tương ứng. Chỉ một metric thì không lặp biểu đồ tổng quát. Liên hệ giữa các vấn đề đặt sau các cụm riêng |
| Điểm đáng chú ý | Số đánh dấu khớp biểu đồ; caption giữ các giá trị và mốc nội bộ quan trọng, không chỉ hai đầu; giới hạn, ghi chú và phụ lục nguồn |

Tóm tắt không có provider call riêng. Các đoạn thiếu định lượng có thể được ghép thêm một câu từ giai đoạn đã kiểm chứng cùng vấn đề/cách tính, có `dependencyBlockIds` và fact IDs đầy đủ. Khi nhiều vấn đề có câu tổng quan giống nhau, tên vấn đề/cách tính vẫn được giữ. Nhận định đối chiếu tổng với trung bình/ngày giữ con số của **cả hai**, không cắt còn một vế.

Dưới bốn kỳ liên tiếp không diễn giải thành xu hướng dài. Chuỗi quá ngắn không tạo đề xuất peak/trough dựa trên chỉ hai điểm. Một kỳ vẫn có số liệu/biểu đồ, nhưng không gọi LLM để tạo trend. Khoảng thiếu dữ liệu ngắt đường biểu đồ và phần tô giai đoạn.

Tổng quan có một biểu đồ chung với tổng/lỗi là cột, tỷ lệ là đường, rồi ba biểu đồ riêng. Thống kê chọn cả tổng và trung bình/ngày có một biểu đồ chung bốn traces, rồi mỗi metric có biểu đồ riêng gồm tổng và trung bình/ngày trên hai trục đơn vị. Khi hơn hai đơn vị thì tách nhóm theo cách tính/đơn vị, không ép ba đơn vị lên hai trục. Đây là lớp trình bày trên snapshot; không tạo tổng nhóm hoặc thay số/facts.

Các đoạn AI đã lưu nằm cạnh biểu đồ chung và chỉ được gán một lần. Diễn giải riêng lấy `temporal_narrative`/stages của Engine đúng entity, calculation và metric từ snapshot, ghi nhãn **Tổng hợp từ số liệu**, không giả thành lời AI và không suy ra metric từ từ khóa của câu văn. Hai/ba kỳ dùng so sánh kỳ có giá trị và chênh lệch đã tính; không thêm đỉnh/đáy hay kết luận xu hướng. Khoảng ngày viết `Kỳ 1 (07–13/09/2026) → Kỳ 2 (14–16/09/2026)`. Tỷ lệ dùng **điểm phần trăm** khi nêu chênh lệch tuyệt đối.

Template 1.3 làm rõ vai trò: biểu đồ chung ưu tiên liên hệ KPI và đối chiếu tổng với trung bình/ngày, không lặp toàn bộ giai đoạn dưới biểu đồ riêng. Metric prose chia tối đa hai giai đoạn mỗi đoạn, giữ đủ stages/gaps và các mốc đỉnh/đáy; chỉ thêm chênh lệch lấy từ fact đã có, không tự cộng các thay đổi để suy ra chênh lệch dài hạn. Nguồn chỉ nhắc khi thay nguồn/cách tính, hoặc có chỉnh sửa chưa lưu. Cảnh báo giống nhau gom theo entity và đúng tập metric/calculation bị ảnh hưởng.

Các đoạn giai đoạn đã lưu nhưng trùng vai trò với metric prose nằm trong **Diễn giải bổ sung đã lưu**, mặc định đóng ở cuối phần Diễn biến. Chúng vẫn đọc/sửa được, không lặp trong bản xuất. Đoạn người dùng đã sửa luôn được giữ trong phần chính. Không đổi prompt hoặc nới validator; snapshot/facts không đổi. Kết quả API thật và đánh giá nội dung: [review template 1.3](evidence/2026-10-06-report-clarity-review.md).

## 4. Snapshot, version và kiểm chứng

Luồng: `committed data → captured Engine bundle → saved v1 → optional validated AI → new revision → local check → exact-revision export`.

- Capture đọc version, observations và entities trong cùng transaction; kiểm tra lại committed version sau phân tích, conflict thì chưa lưu.
- Durable document giữ context, window, series, facts, evidence và `_bundle` nội bộ. Public API không trả `_bundle`.
- Sinh lại dùng `_bundle` đã lưu, không đọc số của bộ lọc hiện tại và không phụ thuộc TTL của AI analysis cache.
- Create/save/regenerate có `requestId` và payload hash để chống lặp. Base revision cũ trả conflict, không ghi đè revision mới.
- Mọi revision immutable. New import chỉ bật `freshness.newerDataAvailable`; user muốn cập nhật tạo báo cáo mới.
- Lời sửa của người dùng được validator kiểm chứng trước khi lưu; audit giữ trước/sau, thời gian, author `local_unverified_user`. Sinh lại AI không ghi đè đoạn manual đã lưu.
- Nội dung chưa lưu ghi rõ **chờ kiểm chứng**, không giữ nhãn AI đã kiểm chứng. Backend vẫn là cổng bảo vệ cuối cùng.
- `checked` là xác nhận local cho đúng revision, không phải `approved`. Không có authenticated reviewer.
- API report hoạt động với facts khi AI tắt. Gọi AI vẫn dùng feature/privacy/provider gate hiện có; lỗi provider hoặc claim bị loại không làm mất số liệu hay bản đã lưu.

Không thay prompt hay semantic policy hiện có: `context-insight-v5`, `grounded-synthesis-v5`, `semantic-grounding-v9`. `ai/context.py` tách bước diễn giải retained bundle nhưng giữ hành vi mặc định của AI Insight cũ.

## 5. Chart anchor và nguồn

Anchor gồm `chartId`, `entityRef`, `metricCode`, `calculation`, `periodStart/periodEnd`, `factId`, `evidenceId` và giá trị canonical. Các ID được tạo ổn định từ identity, không lưu pixel hay Plotly trace index. Khi nhiều nhận định cùng trỏ một điểm, marker hiển thị các số tương ứng.

Panel kết hợp mặc định chỉ có một badge cho mỗi kỳ, gộp số của các nhận định đã chọn. Khi focus một nhận định, hiển thị anchors/interval của nhận định đó; phần tô không bắc qua missing. Focus nhận định đã bỏ chọn chỉ phục vụ đọc tạm thời; export vẫn theo `selectedFindingIds` đã lưu.

Exact evidence mở `observationRef + lineageRef`; aggregate evidence mở `aggregateRef` của snapshot đã chụp. Render UI/renderer không dò nguồn theo text, value hoặc ngày do LLM viết.

## 6. API và lưu trữ

Route prefix `/api/projects/{project}/reports`; [API contract](../api/api-contract.md#tab-báo-cáo--as-built-05102026).

Migration `007_reports.sql` thêm `reports`, `report_revisions`, `report_operations`, `report_checks`, `report_exports`. Không thay observations, parser hay import semantics. Lưu snapshot và file xuất trong DB cần được tính vào dung lượng backup/retention; chưa có tự xóa hay nút xóa báo cáo.

Files chính: `reporting/composer.py`, `story.py`, `repository.py`, `export.py`, `frontend/src/report-workspace.ts`, `report-chart.ts`, `report-workspace.css`. Integration trong `main.ts` và `app/api.py`.

## 7. PDF/DOCX và vận hành

- PDF dùng ReportLab, font Unicode nhúng; DOCX dùng python-docx. Cả hai dùng cùng section document và PNG biểu đồ vẽ từ canonical points, không chụp dashboard.
- Template `1.1` xuất panel kết hợp → diễn giải tương ứng, cùng thứ tự đọc như preview; giữ nhãn cách tính và không lặp lại tên vấn đề ở heading ảnh. Template `1.0` vẫn xuất biểu đồ rời theo entity/calculation/metric dù preview hiện tại có thể dẫn xuất panel kết hợp. Không migration snapshot cũ; chưa có parity bố cục mới cho export legacy.
- File đã xuất/lưu trước đó trả lại nguyên byte, không dựng lại bằng renderer mới. Muốn có bố cục mới cần tạo báo cáo template `1.1`; revision của báo cáo cũ không tự đổi template.
- PNG có metadata về origin, report/revision/chart và source checksum. Marker/interval đúng lựa chọn đã lưu; missing ngắt đường và không tô liền qua khoảng trống.
- Axis giữ nhãn kỳ của Engine. Metadata dùng tên ngày/tuần/tháng/quý và cách tính dễ đọc; các mã/ref kỹ thuật được giữ để truy vết.
- Export ghi version, data-as-of, checksum, prompt/policy/model và local review status tại lần xuất đầu. Nhãn DRAFT không đổi khi đánh dấu đã kiểm tra.
- PDF/DOCX giữ nhãn nguồn AI/Engine/manual. Ghi chú người dùng nằm riêng, chưa kiểm chứng.
- Chỉnh file DOCX ngoài ứng dụng không còn được kiểm chứng như revision trong hệ thống. Không import ngược DOCX.
- Cài dependencies từ `pyproject.toml`. Trên Windows dùng Segoe UI; Linux có DejaVu Sans hoặc cấu hình `EVP_REPORT_FONT` trỏ font TrueType hỗ trợ tiếng Việt. Thiếu font báo lỗi, không âm thầm dùng font hỏng tiếng Việt.

## 8. Kiểm chứng và giới hạn còn lại

[Đánh giá output, đối chiếu nguồn và file xuất](evidence/2026-10-05-reports-review.md). Script `scripts/evaluate_reports.py` chạy opt-in `--live` trên bản sao SQLite để không tạo report test trong DB đang dùng.

[Bằng chứng UX/UI ngày 06/10](evidence/2026-10-06-report-ux-review.md): ma trận tám phạm vi có 7 provider calls đều `accepted`, một ca thiếu dữ liệu không gọi provider; 166 điểm và 200 anchors đúng nguồn, 16 lần xuất thành công. Hai ca xác nhận cuối (Tổng quan ngày; Thống kê tuần với cả hai cách tính) đều `accepted`, đối chiếu 27/32 điểm và 49/43 anchors, bốn lần xuất thành công. Snapshot giữ nguyên; không thay prompt/validator.

Production build đạt; lượt cuối 14 test báo cáo và 3 diagnostic replay đạt. Lượt đặt output test trong frontend gặp Vite watch EBUSY trên file download; chuyển artifacts ra ngoài root Vite rồi chạy lại đạt. Full frontend trước đó 174 đạt/3 skipped, một lỗi trace ENOENT khi dùng chung thư mục chạy đã đạt khi recheck độc lập. Backend trước đó 427 đạt, một lỗi setup do quyền thư mục temp đã đạt khi recheck; sau test bổ sung và chỉnh export có 28 test báo cáo/story đạt. Những kết quả này là bằng chứng lượt chạy, không phải một full-suite mới sau mọi sửa cuối.

Captures fixture 1366/1440/1920/390 ở `.impeccable/review/reports/`; replay ca 1/4/7 và `deselected-finding.png` ở `.impeccable/review/reports-ux-2026-10-06/` dùng prose/snapshot thật trên bootstrap dashboard synthetic. Recapture Tổng quan/Thống kê dùng hai response API cuối; ca nhiều vấn đề giữ response ma trận tám phạm vi. PDF có render trực quan `overview-pdf-final-2.png` và `statistics-pdf-final-2.png`; DOCX chỉ kiểm tra cấu trúc/nội dung/ảnh. Không có static raster shipping; PNG export local giữ metadata provenance.

Finish review độc lập ngày 06/10 yêu cầu sửa chiều rộng prose và navigation của nhận định bỏ chọn; các sửa đã triển khai và recapture. [Verdict cuối](../../.impeccable/review/reports-ux-2026-10-06/finish-verdict.md) ghi `ship`, cả hai sửa đổi `resolved`, không còn việc ở phạm vi hai điểm được chấm. Verdict này không chứng nhận toàn bộ surface/tính năng; review đầy đủ và verdict được parent ghi lại từ reviewer độc lập, không tự chấm inline.

Đã có tests cho idempotency, project isolation, snapshot/revision conflicts, manual numeric validation, import trong/sau capture, AI disabled, Unicode/escaping và actual PDF/DOCX bytes. Thống kê kiểm tra parity đủ 4 grain × 3 cách tính. UI dùng fixture synthetic riêng; không dùng nó làm bằng chứng LLM thật.

Giới hạn v1:

- Template cuối, đa dự án/đa nhóm, arbitrary annotations, official approval và retention policy chưa triển khai.
- Không schedule, send, publish hay triển khai production authentication.
- Provider chỉ được diễn giải số candidate bounded; báo cáo có thể trộn AI và Engine, không phải toàn bộ đoạn đều do AI viết.
- Phạm vi nhiều vấn đề vẫn tạo tài liệu dài; Summary chọn một số ý đại diện, không phải xếp hạng tầm quan trọng nghiệp vụ cho toàn dự án.
- DOCX được kiểm tra cấu trúc/nội dung/ảnh, chưa kiểm tra visual pagination trên Microsoft Word thực tế ở môi trường này.
- Desktop-first. Kiểm tra 390px là chống regression/overflow, không mở rộng cam kết tối ưu mobile.
