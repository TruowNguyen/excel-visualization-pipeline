# 11 — Kế hoạch tab Báo cáo: cấu trúc, luồng hành động và triển khai

Ngày: 05/10/2026. Sản phẩm: Automated CX Report.
Trạng thái ban đầu: **Proposed**. Đến 05/10/2026, người dùng đã yêu cầu triển khai và xác nhận **PDF + DOCX**, **chọn/bỏ điểm đề xuất**. Bản nháp v1 đã được cài đặt; xem [as-built](12-report-workspace-as-built.md) và [bằng chứng kiểm chứng](evidence/2026-10-05-reports-review.md).
Phần kế hoạch bên dưới giữ lịch sử thiết kế, không phải mọi mục đều đã hoàn thành. Formal approval, mẫu cuối của mentor, đa dự án/nhóm và retention vẫn chưa có.

## 1. Mục tiêu và nguyên tắc

Nhân sự CX tạo một bản báo cáo để người quản lý hiểu nhanh dữ liệu đã diễn biến thế nào, KPI nào cần chú ý và nhận định dựa trên số liệu nào. Tab Báo cáo phục vụ chuẩn bị, kiểm tra và xuất tài liệu; không thay tab Tổng quan/Thống kê dùng để khám phá dữ liệu.

Template chưa chốt không ngăn lập kế hoạch nền tảng. Tách ba lớp:

1. **Dữ liệu báo cáo:** phạm vi, snapshot, KPI, facts, chuỗi biểu đồ, giai đoạn, điểm đáng chú ý và nguồn.
2. **Nội dung:** diễn giải đã kiểm chứng, tóm tắt, lựa chọn của người dùng và ghi chú.
3. **Trình bày:** template có version, preview và renderer từng định dạng xuất.

Không ghép nguyên các khối AI Insight thành báo cáo. Composer chọn ý chính, nối diễn biến, tránh lặp và giữ đúng chủ thể. Template đổi không làm thay công thức; thay phép tính phải tạo lại dữ liệu phân tích và revision.

Đã có yêu cầu từ người dùng: một tab báo cáo, năm phần nội dung, đánh dấu điểm đáng chú ý trên biểu đồ và xuất định dạng phù hợp. Chưa được duyệt: template cuối, định dạng xuất, phạm vi đa nhóm/đa dự án, quyền sửa nội dung hoặc tự thêm điểm.

Bản kế hoạch kế thừa các cổng an toàn AI-RPT trong [đặc tả reporting](03-automated-reporting.md). Năm phần ở đây là đề xuất nội dung mới để duyệt, không tự xóa requirement về source/limitations, version hay approval của đặc tả cũ.

## 2. Phạm vi bản đầu đề xuất

| Hạng mục | Đề xuất cho bản đầu | Ranh giới |
|---|---|---|
| Dự án | Một dự án trong một báo cáo | Đa dự án là đợt sau |
| Nội dung theo dõi | Một nhóm: node, một/nhiều vấn đề được chọn hoặc tất cả con trực tiếp | Không tự cộng cha/con; đa nhóm cần duyệt riêng |
| Nguồn phân tích | Chọn Tổng quan hoặc Thống kê, có receipt rõ ràng | Không trộn hai cơ sở tính trong cùng chuỗi |
| Thời gian/cách tính | Tái sử dụng khả năng hiện có của từng nguồn | Thống kê không tự tạo error_rate; both giữ hai bộ facts riêng |
| Báo cáo | Năm phần người dùng đề xuất, kèm ghi chú dữ liệu và nguồn | Không thêm heading Follow-up/đề xuất kiểm tra làm nội dung chính |
| Đánh dấu | Engine đề xuất; người dùng chọn/bỏ điểm có căn cứ | Tự chọn thêm điểm/giai đoạn là decision needed |
| Chỉnh sửa | Đề xuất sửa tiêu đề và commentary; khóa số, ngày, đơn vị, nguồn | Mọi sửa lời diễn giải có trạng thái và lịch sử |
| Xuất | HTML preview bắt buộc; ưu tiên thử PDF trước | PDF/DOCX/PPTX chưa được người dùng chọn |
| Kiểm tra | “Đã kiểm tra bản nháp” do người dùng chủ động xác nhận | Không gọi APPROVED khi chưa có authenticated reviewer |
| Lưu | Đề xuất lưu bản nháp/revision trên backend để mở lại | Chính sách lưu/xóa/retention cần chốt ở Gate 0 |

Không bao gồm: lịch tạo/gửi tự động, email, publish, chữ ký, quy trình nhiều cấp duyệt, phân quyền mới, dự báo, correlation, anomaly hoặc nguyên nhân nghiệp vụ không có facts. Desktop-first; giữ hệ thống thiết kế hiện có, không thiết kế lại mobile.

## 3. Cấu trúc tính năng trong tab

### 3.1. Ba vùng chức năng

- **Thiết lập báo cáo:** tên, dự án, phạm vi, thời gian, nguồn phân tích, nhóm kỳ/cách tính; chọn template nếu có nhiều template được duyệt. Khởi đầu bằng một template dự thảo, không dựng template editor kéo-thả.
- **Bản nháp và kiểm tra:** preview năm phần, điều hướng tới từng phần, biểu đồ tương tác, danh sách điểm được đánh dấu, nguồn và cảnh báo. Các hành động chỉnh sửa nằm cạnh nội dung liên quan.
- **Lưu/xuất:** lưu revision, đánh dấu đã kiểm tra, chọn định dạng và xuất exact revision. Lịch sử bản nháp là vùng phụ, không cạnh tranh với việc tạo báo cáo mới.

Thao tác chính thay theo trạng thái: “Tạo bản nháp” → “Kiểm tra bản nháp” → “Xuất báo cáo”. Không đặt nhiều nút primary cùng lúc. “Sinh lại diễn giải” là thao tác phụ có cảnh báo phần nào sẽ thay thế.

### 3.2. Năm phần báo cáo

| Phần | Nội dung | Chủ sở hữu dữ liệu | Quy tắc |
|---|---|---|---|
| 1. Thông tin báo cáo | Tên, dự án, membership, khoảng thời gian, nhóm kỳ, cách tính, data-as-of, revision, thời điểm tạo | Composer deterministic | Phân biệt thời gian tạo với thời gian dữ liệu; không để AI sửa metadata |
| 2. Executive Summary / Tóm tắt điều hành | Đề xuất 3–5 câu: diễn biến chính, chỉ số/vấn đề cần chú ý, insight quan trọng và giới hạn làm thay đổi cách hiểu | AI từ findings đã kiểm chứng + fallback Engine | Khoảng 30 giây đọc; có 1–2 bằng chứng định lượng; không thêm kết luận ngoài phần dưới |
| 3. KPI Overview / Tổng quan KPI | Tên KPI, mức/số liệu phù hợp, đơn vị, coverage và nhịp thay đổi quan trọng | Deterministic | Tách entity/calculation/unit; không cộng mọi vấn đề thành tổng dự án hoặc lấy đầu–cuối làm trend |
| 4. Diễn biến trong kỳ | Biểu đồ và diễn giải theo các giai đoạn; mức trước/sau, chênh lệch, mốc đỉnh/đáy khi facts hỗ trợ | Analytics + AI đã kiểm chứng | Kể đầu/giữa/cuối, không chỉ đọc từng kỳ; đỉnh/đáy nằm trong giai đoạn, không tạo section thứ sáu |
| 5. Điểm đáng chú ý | Một số findings được chọn: biến động lớn, đổi chiều, nhịp liên tiếp, đỉnh/đáy, liên hệ KPI | Analytics + AI đã kiểm chứng | Mỗi finding gắn với chart anchor và facts; không lặp nguyên phần 4 |

Giới hạn dữ liệu quan trọng xuất hiện ngay gần kết luận liên quan. Chi tiết phương pháp/nguồn là phần hỗ trợ thu gọn trong preview, ghi chú hoặc phụ lục khi xuất; không thay năm section chính bằng một danh sách template dài.

KPI Overview phải xác định vai trò của số: mức tại kỳ, SUM trong kỳ, average_per_day, phần trăm hoặc điểm phần trăm. Không trung bình đơn giản các tỷ lệ hay các giá trị trung bình. Không tính tổng của chuỗi lũy kế rồi gọi là số phát sinh mới. Phần chưa có chính sách tổng hợp hợp lệ trình bày theo kỳ hoặc báo không đủ căn cứ, không đặt một “tổng” giả.

### 3.3. Trải nghiệm đọc

Preview đọc dọc theo năm phần, tận dụng chiều rộng workspace; không bọc từng đoạn bằng card hoặc crop văn bản. Kế thừa DESIGN.md: Segoe UI/system, sidebar navy, nền trung tính, tím cho thao tác/focus. Nguồn mở trong cơ chế điều tra hiện có, không đưa người dùng rời bản nháp và mất vị trí.

Ở desktop, trình bày biểu đồ và đoạn giải thích trong cùng vùng nội dung. Dùng một mục lục gọn/điều hướng tại đầu báo cáo, không thêm sidebar vĩnh viễn làm hẹp chart. Vùng chọn điểm có thể mở/thu gọn cạnh biểu đồ. Số, nhãn nguồn và caption phải đọc được khi in/xuất.

Đây là định hướng bố cục để duyệt, chưa phải mockup, direction contract đã chốt hoặc nghiệm thu UI. Skill impeccable ảnh hưởng đến ưu tiên tác vụ, đọc theo trình tự và giảm tải nhận thức; không thay nhận diện đang có.

## 4. Luồng hành động

Luồng chính đề xuất:

**Mở Báo cáo → Chọn phạm vi → Kiểm tra dữ liệu đầu vào → Tạo bản nháp → Chọn điểm/chỉnh nội dung → Kiểm tra bản nháp → Xuất exact revision.**

### A. Mở và thiết lập

1. Người dùng mở tab Báo cáo, hoặc vào từ Tổng quan/Thống kê bằng hành động “Tạo báo cáo từ phạm vi này”.
2. Hệ thống sao chép filter vào cấu hình ban đầu, không tự gọi LLM.
3. Người dùng xem receipt đầy đủ: dự án, vấn đề được chọn, thời gian thực tế, nhóm kỳ, cách tính và metric.
4. Backend kiểm tra membership, dữ liệu, quyền theo access model thực tế, compatibility và budget; trả rõ vấn đề bị loại và lý do.
5. Các control của Báo cáo độc lập với bộ lọc dashboard sau khi bắt đầu. Thay sidebar không âm thầm thay bản nháp.

Không có dữ liệu hoặc chọn rỗng: không tạo prose giả; giữ form để sửa. Một kỳ: vẫn có bảng/biểu đồ dữ liệu, không tạo trend. Hai kỳ: chỉ so sánh, không tạo đoạn xu hướng hay đỉnh/đáy thừa.

### B. Tạo bản nháp

1. Capture một snapshot nhất quán cho toàn bộ report. Nếu import đổi giữa lúc capture, retry có giới hạn hoặc báo conflict; không trộn version.
2. Engine chuẩn bị KPI, phases, facts, evidence và chart series cho toàn phạm vi.
3. Finding selector loại trùng và đề xuất những điểm đủ căn cứ. Render phần deterministic trước.
4. Gọi LLM có giới hạn để diễn giải phần được chọn, kiểm chứng từng claim. Không gọi lại mỗi lần người dùng bật/tắt marker.
5. Tạo Executive Summary sau khi có findings/diễn biến đã kiểm chứng. Mỗi câu summary giữ dependency tới nhận định/fact nguồn; không dựa vào raw model output bị loại.
6. Lưu nội dung hợp lệ và phần fallback thành draft revision, ghi rõ nguồn AI/Engine.
7. Provider lỗi không làm mất facts hoặc chart. Hiển thị bản deterministic và nút thử lại có chủ đích.

### C. Chọn điểm và chỉnh nội dung

1. Nhấp một finding làm nổi bật đúng điểm/giai đoạn trên chart; nhấp marker chọn finding tương ứng.
2. Chọn/bỏ finding chỉ thay tập điểm đưa vào bản xuất, không xóa fact gốc.
3. Đổi thứ tự các findings nếu phạm vi chỉnh sửa được duyệt; numbering được tạo lại thống nhất giữa chart và chú thích.
4. Sửa commentary không làm đổi series hay số định lượng trong field khóa. Nội dung tự nhập ghi nguồn “Người dùng chỉnh sửa”; kiểm tra lại số/ngày/phạm vi trước khi dùng làm analytical claim.
5. Ghi chú nghiệp vụ không được kiểm chứng để ở field riêng có nhãn, không tự đưa vào AI Summary như fact.
6. Nếu edits thay đổi nhận định, nội dung hoặc lựa chọn mà summary phụ thuộc, đánh dấu summary cần kiểm tra/cập nhật. Đổi template chỉ ảnh hưởng layout, không mặc định gọi lại AI.
7. Regenerate cho section đã chọn giữ snapshot, tạo revision mới và cho xem thay đổi trước khi nhận; không ghi đè phần đã sửa mà không xác nhận.

### D. Kiểm tra và xuất

1. Hiển thị checklist: scope đúng, số/đơn vị đúng, missing rõ, marker đúng, summary không mâu thuẫn, nguồn còn đối chiếu được.
2. “Đã kiểm tra bản nháp” gắn exact revision. Đây là xác nhận cục bộ, không phải chữ ký hoặc phê duyệt có danh tính xác thực.
3. Người dùng chọn định dạng; export lấy reportId/revision/templateVersion cố định.
4. Render chart cùng marker/caption từ snapshot, không chụp dashboard theo filter hiện tại.
5. Tệp ghi **BẢN NHÁP / DRAFT**, data-as-of, ngày tạo và version. Không có APPROVED khi chưa đáp ứng AI-RPT-012.
6. Export lỗi giữ nguyên draft và cho thử lại; không regenerate nội dung hoặc gọi lại LLM.
7. Nội dung chỉnh sau “đã kiểm tra” tạo revision cần kiểm tra lại; artifact cũ giữ nguyên.

### E. Dữ liệu mới và mở lại

Import mới chỉ bật cờ “Dữ liệu nguồn đã có phiên bản mới”. Bản cũ vẫn đọc được theo snapshot đã capture. Người dùng chủ động chọn “Tạo bản mới từ dữ liệu mới”; không cập nhật chart mà giữ prose cũ.

Reload/restart server phải mở lại được draft nếu cơ chế lưu backend được duyệt. Snapshot AI hiện tại chỉ lưu in-memory, không được coi là kho báo cáo bền vững.

## 5. Đánh dấu điểm trên biểu đồ

### 5.1. Ba kiểu anchor

| Kiểu | Vị trí | Ví dụ |
|---|---|---|
| Point | Một KPI tại một kỳ | Mốc có số lỗi cao nhất đủ căn cứ |
| Interval | Hai kỳ hoặc một giai đoạn | Lỗi giảm liên tiếp sau đỉnh |
| Multi-metric | Các điểm cùng kỳ của nhiều KPI | Số lỗi giữ nguyên nhưng tỷ lệ tăng khi tổng giảm |

Mỗi annotation có định danh ổn định, findingId, chartId, entityRef, metricCode, calculation, periodStart/periodEnd, factIds/evidenceIds và caption. Với multi-metric, có danh sách anchors, không một cặp tọa độ dùng cho mọi metric.

Backend xác định điểm từ dữ liệu canonical. Frontend ánh xạ identity tới trace/điểm hiện tại; không lưu curveNumber/pointNumber hoặc pixel làm định danh lâu dài. Thay kích thước, thứ tự traces, nhãn tuần hoặc export không được làm marker lệch kỳ.

### 5.2. Selection và tính dễ đọc

- Dùng số đánh dấu ngắn (1, 2, 3...) trên chart, chú thích ở dưới/cạnh chart. Đề xuất tối đa 3–5 findings chính cho report đầu, cần kiểm tra trên dữ liệu thật trước khi chốt threshold.
- Giới hạn chú thích hiển thị cùng lúc theo chart, tránh nhãn chồng nhau; danh sách findings vẫn giữ đủ.
- Với giai đoạn dùng vùng nhẹ hoặc bracket phù hợp, không che đường/cột. Không dùng màu tăng/giảm để khẳng định tốt/xấu.
- Xếp ưu tiên theo từng KPI/đơn vị và ý nghĩa cấu trúc, không rank absolute delta giữa Lượt, Cảnh báo và phần trăm.
- Deduplicate finding cùng facts/kỳ; một đỉnh có thể là mốc đổi chiều nhưng không cần hai chú thích lặp.
- Missing không nối thành giai đoạn liên tục. Ngưỡng xu hướng/đỉnh–đáy theo policy đang có; dữ liệu ngắn không nâng thành trend.
- Danh sách findings dùng control có thể thao tác bằng bàn phím; không yêu cầu chỉ hover/click chart mới đọc được thông tin.
- Caption có KPI, kỳ, mức thay đổi và ý nghĩa ngắn. LLM không được tự sinh tọa độ, cấu hình Plotly, HTML hoặc URL.

Nếu duyệt thao tác tự thêm điểm: người dùng chỉ chọn điểm/kỳ thực sự tồn tại trong snapshot; giai đoạn phải qua kiểm tra boundary/gap. Annotation thủ công ghi rõ nguồn, không tự được gọi là phát hiện của Analytics.

## 6. Kiến trúc đề xuất và phần tái sử dụng

### 6.1. Luồng dữ liệu

**Report request → Resolve phạm vi + capture snapshot → Engine facts/series → Finding selector → Narrative kiểm chứng → Report composer → Lưu revision → Preview / Export renderer.**

Executive Summary là đầu ra tổng hợp từ bundle hợp lệ, không phải input để sinh ngược facts. Preview và export cùng đọc một ReportDocument, không tính lại KPI tại frontend/export.

### 6.2. Thành phần

| Thành phần | Đã có / có thể tái sử dụng | Cần bổ sung |
|---|---|---|
| Scope/period/calculation | Context Insight resolver, prepared statistics, dataVersion | Report context độc lập và capture nguyên tử |
| Analytics | Period/historical facts, phases, changes, extrema, KPI relations | Finding registry/selection, mapping annotation |
| AI | Adapter, privacy gate, budgets, validation, fallback | Composer/report slots, summary dependencies và đánh giá prompt báo cáo |
| Chart/source | Plotly, point selection, exact/aggregate lineage | Report chart identity, interval/multi-metric annotation, static rendering |
| Snapshot | Aggregate provenance được lưu; AI analysis repository in-memory | Durable ReportDocument + facts/evidence + series snapshot |
| UI | Tab shell, controls, disclosures, highlight và ngôn ngữ đã thống nhất | Tab Báo cáo, draft preview, review checklist, export action |
| Xuất | CSV dữ liệu hiện có | Bộ xuất tài liệu; CSV không thay report export |

Không tái sử dụng trực tiếp in-memory analysisId làm khóa report; không viết Engine mới với công thức khác. Legacy trend-summary và context-insight vẫn hoạt động như hiện có.

### 6.3. ReportDocument đề xuất

- Identity: reportId, revision, schemaVersion, templateId/templateVersion, locale.
- Context: project, mode overview/statistics, members và exclusions, requested/resolved window, grouping, calculation, metricCodes.
- Snapshot: source data version/checksum, capturedAt, calculation/policy versions, canonical series/facts/evidence, chart specs đã kiểm soát.
- Content: năm section, narrative blocks có fact/dependency refs, provenance AI/Engine/manual, limitations.
- Findings/annotations: định danh, anchors, selected, thứ tự, caption và validation result.
- Review: draft / needs_review / checked; chỉ trạng thái local. Generation, freshness và export receipt là các trường độc lập.
- Generation: prompt/model/policy version, timings, rejected claims/fallback reasons và coverage.
- Export receipts: report revision, format, renderer version, content hash, createdAt, outcome.

Không lưu raw Excel/credentials/provider prompt trong report mặc định. Tệp bằng chứng test gọi thật được quản trị riêng. Template chỉ cho phép section/field types đã khai báo, không chạy code hoặc HTML tùy ý.

### 6.4. Lưu và API — dự kiến, chưa là contract công bố

Đề xuất module reporting riêng dưới src/excel_visualization_pipeline, sử dụng analytics/storage chung. Frontend report-workspace và annotation renderer riêng; main.ts chỉ nối tab và lifecycle.

API ứng viên:

| Thao tác | API ứng viên |
|---|---|
| Xem phạm vi/số liệu đầu vào không gọi AI | POST /api/projects/{project}/reports/preview |
| Tạo bản nháp từ phạm vi đã chọn | POST /api/projects/{project}/reports |
| Mở exact revision | GET /api/projects/{project}/reports/{reportId}/revisions/{revision} |
| Lưu edits/selected findings thành revision mới | POST .../{reportId}/revisions |
| Sinh lại một phần trên snapshot cũ | POST .../{reportId}/regenerate |
| Ghi nhận đã kiểm tra exact revision | POST .../{reportId}/revisions/{revision}/check |
| Xuất exact revision | POST .../{reportId}/revisions/{revision}/exports |

Tên/status/schema cụ thể chỉ khóa sau Gate 0. Mutations có baseRevision để tránh ghi đè draft do response muộn; generate/export dùng requestId hoặc idempotency key để double-click không gọi trùng. Không tạo endpoint approved trước auth.

Lưu reports, immutable revisions và export receipts bằng migration additive nếu phương án lưu được duyệt. Capture đủ bundle để preview/export sau restart không phụ thuộc cache AI hoặc dữ liệu current đã đổi. Artifact path do backend quản trị, không nhận đường dẫn filesystem/URL tùy ý từ client. Retention/xóa lịch sử được thiết kế trước phát hành; không tự dọn evidence hiện có.

## 7. Export không phụ thuộc template cuối

- Định dạng dữ liệu report và template có version riêng; PDF/DOCX/PPTX là renderer khác nhau trên cùng document.
- Preview web tương tác; “Xem bản xuất” hiển thị layout/pagination của định dạng đã chọn trước tải.
- Biểu đồ static giữ đủ series, trục, đơn vị, marker, numbering và chú thích; không chỉ lấy viewport đang zoom hoặc chỉ lấy chart đang visible.
- Không cần pixel-identical giữa DOCX và PDF, nhưng nội dung, số liệu, annotations, source notes và version phải giống.
- PDF là ứng viên đầu để chia sẻ layout ổn định; DOCX để sửa tiếp; PPTX cần slide mapping riêng. XLSX/CSV là dữ liệu bổ trợ, không được coi là bản báo cáo đủ năm phần.
- Spike kiểm tra font tiếng Việt, biểu đồ, trang dài, bảng nhiều kỳ, print/page breaks, dung lượng và thời gian trên môi trường Windows thực tế. Chỉ chọn thư viện sau spike; chưa thêm dependency ở lượt kế hoạch.
- Không gửi chart hoặc nội dung nhạy cảm sang dịch vụ export ngoài nếu chưa có quyền rõ ràng.
- DOCX/PPTX sửa bên ngoài sẽ không còn được app đảm bảo grounding; metadata phải nêu bản xuất tương ứng revision nào. Không hứa tự đồng bộ edits ngoài ứng dụng.
- Failed export không đánh dấu exported hoặc phá bản đã lưu. Export lặp cùng revision có thể tái dùng artifact nếu checksum/config trùng và retention cho phép.

## 8. Triển khai theo lát dọc và điều kiện hoàn thành

Không đặt lịch hoặc cam kết ngày phát hành khi template và output format chưa chốt.

| Giai đoạn | Công việc | Điều kiện chuyển tiếp |
|---|---|---|
| 0. Chốt MVP + spike | Duyệt phạm vi, chỉnh sửa/annotation, export, lưu; sample report thực tế; kiểm tra snapshot và export kỹ thuật | Có decision record, contract draft, một sample năm phần được duyệt; không còn tự suy đoán format |
| 1. Document + tab deterministic | Capture snapshot, read model, persistence được duyệt; tab/form/preview thông tin, KPI, chart và fallback | Scope/calculation/series đúng; mở lại sau restart; missing rõ; không cần LLM để xem facts |
| 2. Findings + pointing | Selector, stable anchors, marker/vùng, mapping nguồn, chọn/bỏ và caption | Click hai chiều đúng entity/kỳ/metric; resize/export spike không lệch; không thêm điểm ngoài facts |
| 3. Narrative + Executive Summary | Tái sử dụng validator; report slots; budget; synthesize từ findings hợp lệ; fallback và provenance | LLM thật qua endpoint; không lặp section 4/5; summary hiểu nhanh, số đúng và phụ thuộc đúng |
| 4. Review/revision | Các edits đã duyệt, local checked, regenerate an toàn, concurrent edits/stale | Edit tạo revision và cần kiểm tra lại; không gọi checked là approved; dữ liệu mới không sửa draft cũ |
| 5. Export format ưu tiên | Static charts/annotations, layout và downloadable artifact, exact revision receipt | File mở được, chữ Việt đúng, đủ năm phần và source/version; không crop; error/retry không mất draft |
| 6. Format bổ sung + nghiệm thu | DOCX/PPTX chỉ nếu được chọn; kiểm tra ma trận dữ liệu, performance, accessibility, regression | Báo cáo đọc được và export đúng; bằng chứng kiểm thử rõ; cập nhật as-built và chỉ lúc đó mở public tab |

Mỗi lát đi đủ backend → UI → tests/evidence, không chỉ dựng UI rỗng. Có thể để sau feature flag cho tới khi hoàn tất các lát MVP được duyệt. Không coi slice 1 là báo cáo AI hoàn chỉnh hoặc slice 5 là hỗ trợ mọi định dạng.

## 9. Trạng thái và ngoại lệ phải thiết kế

| Tình huống | Hành vi |
|---|---|
| Chưa chọn phạm vi/chọn rỗng | Hướng dẫn ngắn, không gọi model |
| Scope không có dữ liệu | Giữ lựa chọn, giải thích từng exclusion; không giả số 0 |
| Một/hai kỳ | Cho preview và so sánh có giới hạn; không bịa xu hướng |
| Đang chuẩn bị dữ liệu/AI | Báo từng công đoạn thật; không giả progress %, không khóa dashboard |
| AI timeout hoặc một claim bị loại | Giữ facts/chart và fallback có nhãn; thử lại theo section có chủ đích |
| Scope quá lớn | Nêu giới hạn và cách thu hẹp; không âm thầm bỏ vấn đề hoặc đoạn cuối |
| Dữ liệu nguồn mới | Gắn freshness flag, giữ snapshot cũ; tạo bản mới theo yêu cầu |
| Đổi cấu hình sau tạo draft | Form là cấu hình cho bản mới; draft cũ không đổi |
| Summary phụ thuộc content vừa sửa | Needs review/update; không giữ nhãn đã kiểm tra |
| Chuyển tab/đóng trang | Không mất revision đã lưu; cảnh báo edits chưa lưu khi cần |
| Response muộn/revision conflict | Không ghi đè bản mới; cho reload/so sánh thay đổi |
| Nguồn cũ chưa truy cập được | Nêu trạng thái, không mở current source thay historical source giả |
| Export lỗi/không hỗ trợ format | Giữ draft, báo nguyên nhân có căn cứ; không tải file giả rỗng |

## 10. Kiểm thử và nghiệm thu

### Kiểm thử xác định

- Report context đúng node/selected/all, project, ngày/tuần/tháng/quý và sum/average/both mà nguồn hỗ trợ; negative foreign IDs, parent/child overlap và unit mismatch.
- Raw values/rounding/percent-point roles bằng prepared chart và facts, không lấy narrative làm expected source.
- Missing/zero/inferred zero, sparse phases, constant/one/two periods, tied extrema, kỳ partial, đổi năm, lũy kế; không nối qua gap.
- Annotation identity không phụ thuộc trace order/pixels; markers đúng sau resize/zoom, chart cùng kỳ nhưng khác metric/cách tính không bị dùng nhầm anchor.
- Persist/restart/reopen; import giữa capture; import sau lưu; revision concurrency; regenerate giữ snapshot và edits đúng; sửa bất cứ phần đã kiểm tra đều invalidates receipt/dependencies cần thiết.
- Unsafe HTML/Markdown trong model hoặc manual text, prompt injection từ labels, arbitrary export path/remote URLs không được thực thi.
- PDF/DOCX/PPTX chỉ test format đã duyệt: file thật mở được, text Việt, bảng/charts/markers, nguồn/version, page breaks, long content, errors/retry.
- Keyboard, focus, source navigation, loading/failure, 1366/1440/1920 desktop, 200% zoom và baseline responsive không regress.
- Hồi quy import, Tổng quan, Thống kê, AI Insight, comparison và nguồn; không đổi các công thức đã có.

### Lần kiểm thử AI cuối phải chạy API thật

Sau sửa runtime/prompt/validator cuối của slice AI và nghiệm thu cuối, gọi qua endpoint báo cáo thật bằng provider đã cấu hình. Lưu riêng raw và validated output, Engine fallback, request/snapshot, annotations, latency/usage nếu có; không có secrets hoặc raw Excel.

Manifest đại diện: một và nhiều vấn đề, all, Tổng quan 3 KPI, Thống kê sum/average/both, các grouping có dữ liệu thật; ít dữ liệu/quý một kỳ phải báo đúng giới hạn. Dữ liệu multi-quarter synthetic được ghi rõ, không gọi là kiểm thử quarterly narrative thực tế.

Người kiểm thử đọc output và bản xuất, không chỉ đếm accepted:
- Sau khoảng 30 giây có hiểu diễn biến và điểm đáng chú ý không?
- Có số trước/sau và chênh lệch đúng phạm vi không?
- Summary có mâu thuẫn với chart/diễn biến không?
- Finding có chỉ đúng vị trí, có giải thích ý nghĩa thay vì liệt kê số không?
- Đỉnh/đáy/gap/short-period được trình bày đúng không?
- Section 4/5 có bị trùng nội dung hoặc heading không?
- Fallback có còn giúp hiểu dữ liệu, được nhận diện đúng nguồn không?
- Export có giữ nguyên các nhận định và chú thích đã kiểm tra không?

Sai số, sai entity/calculation/kỳ, marker lệch vị trí, suy diễn nhân quả không căn cứ, mất snapshot hoặc bản xuất khác revision đã xem là lỗi chặn nghiệm thu. Partial không tự là fail, accepted không tự là chất lượng tốt. Performance budget sẽ chốt bằng số đo ở Gate 0/3; không hứa SLA chưa đo.

Formal approval AI-ACC-RPT-004 không được tự đánh dấu pass cho local checked. Cần ghi riêng phần deferred do chưa có auth, không thay requirement cũ ngầm.

## 11. Quyết định còn mở và bước tiếp theo

| Quyết định | Khuyến nghị để duyệt | Ảnh hưởng nếu chọn khác |
|---|---|---|
| D1. Định dạng bản đầu | Preview + PDF đầu tiên; DOCX là ứng viên kế tiếp | Chọn DOCX/PPTX ngay làm thay renderer/test/template export |
| D2. Quyền annotation/edit | Hệ thống đề xuất, người dùng chọn/bỏ và sửa commentary có kiểm chứng | Tự thêm điểm/giai đoạn cần picker, anchor validation và provenance thủ công |
| D3. Phạm vi | Một dự án, một nhóm/node với selected/all trong bản đầu | Nhiều nhóm cần scope resolver mới, tránh overlap và summary hierarchy; nhiều dự án cần đợt riêng |
| D4. Template | Năm section stable IDs, một template draft có version | Thay bố cục được; template editor tự do không nằm MVP |
| D5. Lưu/revision/retention | Lưu backend, revisions immutable, không auth/approval giả | Chỉ session không đáp ứng mở lại/restart; retention cần chính sách riêng |
| D6. Nhận định do người dùng sửa | Kiểm chứng analytical claims; ghi chú chủ quan có nhãn riêng | Không thể vừa sửa tùy ý vừa hứa toàn bộ text được Engine xác minh |

Các khuyến nghị trên **chưa phải quyết định của người dùng**. Có thể duyệt kế hoạch và điều chỉnh D1–D6 trước khi khóa contract/viết code. Câu hỏi về format và quyền annotation đã được gửi ở lượt trước; kế hoạch không coi các lựa chọn chưa trả lời là đã được chấp nhận.

Bước tiếp theo: duyệt MVP → chốt decision record + sample report năm phần → thực hiện Gate 0 → triển khai slice 1. Không cần đợi template trang trí hoàn hảo, nhưng phải chốt các ngữ nghĩa dữ liệu/edits/export trước khi phát hành.

## 12. Tài liệu và nguồn đối chiếu

- [Reporting canonical / AI-RPT](03-automated-reporting.md): an toàn số liệu, version, draft/export và auth approval.
- [Acceptance reporting](05-ai-evaluation-and-acceptance.md): AI-ACC-RPT.
- [Context Insight as-built](10-context-insight-as-built.md) và [đánh giá API thật](evidence/2026-10-04-linked-insight-review.md): phần tái sử dụng và giới hạn validator hiện tại.
- [KPI summary theo nguồn](../frontend/overview-summary-metrics.md): không sao chép phạm vi bốn thẻ vào Report KPI Overview mà không resolve report context.
- Code đối chiếu: ai/context.py, analytics.py, report.py, semantic.py, repository.py; visualization prepared data; storage/aggregates.py; frontend/src/chart.ts, context-insight.ts, main.ts.
- Product/design authority: PRODUCT.md, DESIGN.md; tab mới giữ thế giới giao diện, chưa chốt mockup bố cục.

Khi implementation được duyệt: cập nhật API/data/storage contract, product scope/use cases, reporting AI-RPT, acceptance và traceability tương ứng. Chỉ chuyển As-built sau tests, API LLM thật và kiểm tra export hoàn tất. Không commit/push/freeze ở lượt kế hoạch này.
