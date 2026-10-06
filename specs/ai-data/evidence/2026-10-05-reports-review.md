# Kiểm thử và đánh giá tab Báo cáo — 05/10/2026

## Kết luận

Bản nháp v1 đáp ứng luồng đã chọn: **năm phần → dữ liệu đã chụp → diễn giải tùy chọn → chọn/bỏ điểm đề xuất → lưu revision → PDF/DOCX**. Không coi đây là template cuối hay official approval. [Hành vi và giới hạn](../12-report-workspace-as-built.md).

LLM được gọi thật qua provider đã cấu hình, không dùng fixture để kết luận chất lượng AI. Matrix cuối có **14 phạm vi**, **13 provider calls**: 12 kết quả `accepted`, một `partial`, một `insufficient_data` không gọi AI. Claim không đủ số kỳ được loại riêng; báo cáo vẫn có các đoạn AI hợp lệ và Engine fallback. `accepted` không có nghĩa tất cả đoạn đều do AI viết hoặc chất lượng narrative đã được nghiệm thu production.

## 1. Phương pháp và dữ liệu

- `scripts/evaluate_reports.py --live` dùng bản sao SQLite của dữ liệu committed hiện tại, không tạo test reports trong DB sử dụng hằng ngày.
- Mỗi case gọi create report thật → regenerate với LLM thật → kiểm tra snapshot/charts/facts không đổi → độc lập so chuỗi với Analytics Engine/prepare_period_statistics → gọi renderer PDF và DOCX thật → mở/parse file.
- Manifest: [14 phạm vi](2026-10-04-linked-insight-manifest.json). Output cuối: [verified JSON](2026-10-05-reports-verified.json). Các file live/final trước đó ghi lịch sử chỉnh composer và renderer, không thay bằng chứng cuối.
- Model được cấu hình `ag/gemini-3.7-flash-low`; response provider báo `gemini-3.7-flash-tiered`. Ghi đúng model response trong từng report, không đổi cấu hình hoặc tuyên bố hai tên là hai model độc lập.
- Prompt context-insight-v5, grounded-synthesis-v5 và semantic-grounding-v9 giữ nguyên. Chỉnh trong lượt này ở capture/composer/storage/renderers/UI, không nới validator để tăng tỷ lệ pass.

| Case | Phạm vi | Validation cuối | PDF / DOCX |
|---|---|---|---|
| 1 | VSO, nhóm đang chọn, Tổng quan ngày, 3 KPI | accepted | 5 trang / 3 chart |
| 2 | VSO, nhóm đang chọn, Thống kê tuần, both | accepted | 6 trang / 4 chart |
| 3 | VSO, nhóm đang chọn, Thống kê tháng, both | accepted | 4 trang / 4 chart |
| 4 | SmartParking, nhóm, Thống kê tuần, both | accepted | 6 trang / 4 chart |
| 5 | VSO, 2 vấn đề chọn, Thống kê ngày, both | accepted | 7 trang / 4 chart |
| 6 | VSO, 2 vấn đề chọn, Thống kê tuần, sum | partial: insufficient_trend_periods | 4 trang / 2 chart |
| 7 | VSO, 2 vấn đề chọn, Thống kê tháng, both | accepted | 5 trang / 4 chart |
| 8 | V-Pet, tất cả vấn đề, Thống kê tuần, avg | accepted | 7 trang / 5 chart |
| 9 | V-Pet, tất cả vấn đề, Thống kê tháng, both | accepted | 9 trang / 10 chart |
| 10 | VSO, 2 vấn đề chọn, Tổng quan ngày | accepted | 5 trang / 2 chart |
| 11 | VSO, tất cả vấn đề, Tổng quan ngày | accepted | 11 trang / 7 chart |
| 12 | VW Vũ Yên, tất cả vấn đề, Thống kê quý, both | not_run / insufficient_data | 7 trang / 10 chart |
| 13 | VSO, Số lỗi, Thống kê tuần, avg | accepted | 3 trang / 1 chart |
| 14 | VSO, Tổng số, Thống kê tuần, avg | accepted | 3 trang / 1 chart |

Các tài liệu dài bao gồm biểu đồ, giới hạn và source appendix; số trang không tương đương số trang narrative AI.

## 2. Đối chiếu số liệu và mốc biểu đồ

**289 điểm numeric**, **328 anchors** khớp canonical series; không có point/anchor mismatch. Tất cả 14 `unchangedSnapshot=true`: sinh AI không sửa dataAsOf, charts hoặc facts. Không gán số tuần/tháng cho điểm ngày; Thống kê sum/avg được so với chính phép tính hiện có, không tự cộng lại ở renderer.

Ví dụ đã đọc và đối chiếu:

- VSO 12→13/09: số lỗi **19→43**, tăng **24**, **126.32%**. Sau đỉnh: 13→14/09 **43→32**, giảm **11**, **25.58%**. Phần sau kể giảm về 22 và giữ nguyên, không dùng 16→22 làm trend đại diện.
- VSO 07→08/09: Tổng số **71→454**, lỗi **16→8**, tỷ lệ **22.54%→1.76%**. Diễn giải nói cả số lỗi và tỷ lệ giảm; không biến quan hệ mẫu số thành nguyên nhân nghiệp vụ hay “chất lượng chắc chắn tốt hơn”.
- VSO thống kê tháng: lỗi tổng kỳ **441→299**, **-142**; trung bình/ngày **16.33→19.93**, **+3.6** theo precision Engine. Tóm tắt giữ cả hai cơ sở, không kết luận hoạt động giảm chỉ vì kỳ sau ngắn hơn.
- Camera và Đèn pha: đỉnh ở **13/09** và **15/09** khác nhau. Nhận định giữ tên vấn đề, không chọn một đỉnh đại diện cho cả nhóm. Khi hai vấn đề đổi chiều khác nhau, report không tổng hợp chúng thành một xu hướng chung giả.
- VW Vũ Yên quý: chưa có hai kỳ liên tiếp, giữ số đã ghi nhận và không gọi provider để bịa trend. Missing không được thay bằng zero.

Kiểm tra toàn bộ chart/anchor là tự động độc lập; các ví dụ prose phía trên được người triển khai đọc và đối chiếu. Đây không phải tuyên bố đã có một hội đồng nghiệp vụ đánh giá mọi câu hay formal sign-off.

## 3. Đánh giá nội dung và các sửa đã thực hiện

**Điểm đạt:** summary ưu tiên hình dạng diễn biến, có số trước/sau và chênh lệch; phases lồng đỉnh/đáy; ngày/tuần/tháng theo grain; quan hệ KPI giải thích volume/count/share trong phạm vi facts, không correlation. Selection không gọi thêm LLM. AI/Engine/manual không bị trộn nhãn.

**Điểm phát hiện và đã sửa trong composer:**

- Summary cũ có thể chọn hai đoạn cùng một vấn đề, bỏ qua vấn đề khác: ưu tiên một overview mỗi vấn đề trước đoạn thứ hai cùng chủ thể.
- Hai câu Engine giống nhau ở hai vấn đề bị mất tên: giữ entity/calculation trong summary nhiều vấn đề.
- Summary chỉ nói tăng/giảm mà không có số: ưu tiên overview định lượng; khi cần lấy thêm một câu phase cùng entity/calculation, giữ fact IDs và dependencies.
- Câu đối chiếu tổng/avg bị cắt sau tổng: giữ số và delta của cả tổng lẫn trung bình/ngày.
- Caption chỉ có hai đầu sẽ bỏ mất đỉnh nội bộ: giữ canonical first/last/local extrema anchors trong caption và chart.

**Điểm phát hiện và đã sửa khi xuất:** giữ nhãn kỳ thay vì đổi trục tuần/tháng thành ngày; metadata dùng tên cách tính dễ đọc; giữ nhãn nguồn AI/Engine/manual; PNG có origin/report/revision/chart/checksum metadata; không tô interval qua missing gap.

**Chưa hoàn hảo:** bản nhiều vấn đề vẫn có nhiều đoạn Engine và giới hạn lặp theo từng phép tính; summary không phải bộ xếp hạng KPI theo tầm quan trọng nghiệp vụ. Một số đơn vị nguồn như “Lượt (lũy kế)/ngày” dài vì giữ nguyên unit/công thức hiện có. Mẫu báo cáo cuối chưa được chốt; không tự sửa semantics để làm câu đẹp hơn.

## 4. Latency và phiên bị gián đoạn

Trong matrix verified, case 8 ghi ~60 phút ở generation và case 9 ghi ~47 phút ở prepare trong lúc phiên làm việc/quota bị gián đoạn. Đây là wall-clock measurements không hợp lệ để suy ra tốc độ dịch vụ; không có đủ telemetry để kết luận nguyên nhân provider. Giữ nguyên evidence, không xóa outlier.

Đã chạy lại hai phạm vi đó sau khi tiếp tục: [manifest](2026-10-05-reports-resume-manifest.json), [output LLM thật](2026-10-05-reports-resumed.json). Cả hai accepted, 54 điểm/66 anchors khớp, snapshot không đổi, bốn exports thành công. Prepare ~2.4–2.7 giây; generation endpoint ~7.0–8.6 giây, provider ~6.6–8.2 giây.

Ở 13 phạm vi gọi AI, thay case 8 bằng lần chạy lại, provider latency đo được **4.1–9.8 giây**. Đây là quan sát smoke, không phải SLA. Tổng thời gian còn gồm chuẩn bị Engine và render; phạm vi all issues cần nhiều công việc deterministic hơn. Không tự bật retry hoặc background gửi dữ liệu.

## 5. File xuất và UI

Matrix cuối có **28/28 actual exports** thành công; 5 section headings, DRAFT, report identity có trong cả PDF/DOCX. PDF parse được Unicode; DOCX mở bằng python-docx/ZIP, số chart images khớp documents. Hash/bytes được ghi trong JSON evidence; unit tests xác nhận re-export đúng revision trả nguyên byte sau khi có revision mới.

Đã raster và mở các trang PDF đại diện case 1,2,3,5: tiếng Việt, bảng, phase story, marker numbering, missing line breaks, weekly labels và sources đọc được. Artifact nằm trong `data/report-evaluation/6b0d7986fdd54a3e9beea6f6c7dd9c9c`; test artifacts không phải dữ liệu production. Chưa xác minh visual pagination trên Microsoft Word; không gọi DOCX “pixel-identical với PDF/preview”. Pagination dài và khoảng trắng vẫn cần chốt theo template cuối.

UI kiểm tra synthetic interaction fixture riêng trên 1366×768, 1440×900, 1920×1080 và 390×844. Không dùng screenshots này làm chứng cứ số liệu LLM. Impeccable finish reviewer xác nhận bố cục năm phần/full-width; chỉ ra ba lỗi read-only revision, pending provenance và reduced-motion. Đã sửa cả ba; verdict `ship` ở scope ba fixes, không phải whole-product approval. Detector chạy một lần, không có findings. DESIGN.md/sidecar được giữ nguyên; bước documenter bị quota nên primary hoàn tất ghi nhận trực tiếp.

## 6. Regression và cách chạy lại

- Backend: **425 passed**, gồm 24 report tests và parity 4 grain × 3 calculation; 28 FastAPI/Python deprecation warnings.
- Frontend: **175 passed**, gồm 13 Report tests. Một lượt trước có transient failure ở existing lineage loading-state assertion; kiểm tra riêng lặp 3 lần pass, full suite chạy lại 175/175 pass, không sửa test để bỏ assertion.
- Build: `npm run build` pass. Còn warning chunk Plotly >500KB; module vẫn lazy-loaded, không coi đó là build failure.
- `git diff --check` không có whitespace errors; Windows có thông báo LF/CRLF bình thường.

```powershell
python -m pytest -o addopts='' -q
cd frontend
npm run build
npx playwright test
```

Live opt-in (từ project root, cần feature/privacy/model/API key hợp lệ; có phát sinh usage):

```powershell
python scripts/evaluate_reports.py --live --manifest specs/ai-data/evidence/2026-10-04-linked-insight-manifest.json --output data/report-evaluation/recheck.json
```

Không thay production DB bằng evaluation copy; không dùng fallback hoặc fixture làm bằng chứng đã gọi LLM thật.
