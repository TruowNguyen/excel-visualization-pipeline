# Báo cáo: kiểm thử API LLM thật và đánh giá trải nghiệm — 06/10/2026

## Kết luận

Báo cáo giữ đúng số liệu trong mẫu kiểm thử, nhưng cách đọc và thao tác chưa đáp ứng mục tiêu báo cáo ngắn, tập trung. Biểu đồ Báo cáo dùng template riêng, không kế thừa biểu đồ Tổng quan/Thống kê. Cần ưu tiên cấu trúc giao diện và hợp đồng biểu đồ; không coi việc nới validator là giải pháp chính cho vấn đề UI.

Lượt này chỉ kiểm thử, chẩn đoán và lưu bằng chứng. Không sửa UI, prompt, validator, dữ liệu production hoặc báo cáo đã lưu của người dùng.

## Phạm vi và cách kiểm thử

- Dữ liệu hiện tại được sao lưu sang database đánh giá riêng bằng `backup_database`; gọi các endpoint tạo/sinh lại/xuất báo cáo bằng FastAPI TestClient.
- Người dùng xác nhận cho phép gửi tên dự án/vấn đề, thời gian và facts KPI tới API 9Router đã cấu hình. Không gửi workbook trong payload, không ghi API key vào bằng chứng.
- Model cấu hình `ag/gemini-3.7-flash-low`; model trả về `gemini-3.7-flash-tiered`; prompt `context-insight-v5`.
- Manifest: [8 trường hợp](2026-10-06-report-audit-manifest.json). Output raw/validated và đối chiếu nguồn: [kết quả API thật](2026-10-06-report-audit-verified.json).
- Lượt chạy trong sandbox trước khi có quyền mạng không nhận được output, trả `timeout`; [bằng chứng thất bại kết nối](2026-10-06-report-audit-live.json) không được tính là đánh giá narrative LLM thật. Không suy ra lỗi timeout production từ lượt bị hạn chế mạng này.
- Browser tích hợp không có kết nối. Dùng Playwright/Chrome của dự án sau khi được duyệt chạy cục bộ. Replay nguyên output endpoint thật trên UI hiện tại; phần khung dashboard/API bootstrap là fixture giả lập. Không chụp phiên dashboard đang dùng của người dùng.

## Kết quả API

| Case | Phạm vi | Kết quả validator | Sinh lại báo cáo | Số chart | PDF |
|---|---|---|---:|---:|---:|
| 1 | VSO, một node, Tổng quan ngày | partial, một claim bị loại | 7.19 s | 3 | 5 trang |
| 2 | VSO, riêng Camera, Tổng quan ngày | accepted | 4.75 s | 1 | 3 trang |
| 3 | VSO, Camera + Đèn pha, Tổng quan ngày | accepted | 6.23 s | 2 | 5 trang |
| 4 | VSO, một node, Thống kê tuần, tổng + trung bình | accepted | 6.57 s | 4 | 6 trang |
| 5 | VSO, Camera + Đèn pha, Thống kê tuần, tổng | accepted | 7.29 s | 2 | 4 trang |
| 6 | V-Pet, cả nhóm, Thống kê tháng, tổng + trung bình | accepted | 6.51 s | 10 | 9 trang |
| 7 | VSO, cả nhóm, Tổng quan ngày | accepted | 7.05 s | 7 | 11 trang |
| 8 | VW Vũ Yên, cả nhóm, Thống kê quý | insufficient_data, không gọi LLM | 0.17 s | 10 | 7 trang |

7 lượt có phản hồi từ provider: 6 accepted, 1 partial. Case 8 không đủ kỳ liền nhau, đúng hành vi không dựng xu hướng. Sinh lại endpoint bao gồm phần xử lý sau provider; không phải số đo riêng thời gian reasoning. Chuẩn bị case 7 mất 9.67 s, cho thấy độ trễ chuẩn bị nhiều vấn đề cũng cần xem xét riêng với LLM.

Đối chiếu **166 điểm numeric, 200 anchors**, không có mismatch; cả 8 snapshot/facts/charts giữ nguyên sau khi sinh AI. **16/16 lần xuất PDF/DOCX** trả HTTP 200, có năm phần, DRAFT và report identity. Đây là kiểm chứng số liệu/chart và cấu trúc file, không phải chứng minh mọi câu văn hay mọi trang Word đều hoàn hảo. Không kiểm tra phân trang trong Microsoft Word ở lượt này.

## Đánh giá nội dung

Điểm đạt:

- Case 1 diễn giải giảm ở đầu chuỗi, tăng lên đỉnh 43, sau đỉnh giảm và giữ nguyên ở cuối; không chỉ kể 16 → 22.
- Có căn cứ tăng/giảm: lỗi 19 → 43, +24 (+126.32%); 43 → 32, -11 (-25.58%).
- Case 4 giữ riêng tổng tuần và trung bình/ngày: 104 → 76 (-28), nhưng 17.33 → 25.33 (+8). Không dùng tổng kỳ làm đại diện cho mức mỗi ngày.
- Case 3 phân biệt đỉnh Camera ngày 13/09 và Đèn pha ngày 15/09, không gộp thành đỉnh chung hoặc tương quan/nhân quả.
- Một vấn đề có dữ liệu riêng được báo cáo độc lập; không buộc đưa cả dự án vào phân tích.

Điểm còn yếu:

- Tóm tắt nhóm chưa phải lựa chọn ưu tiên nghiệp vụ. Case 7 mở bằng Động vật và Bóng đổ; Camera/Đèn pha nằm ở nhận định khác và chi tiết phía dưới. `accepted` chỉ là kiểm chứng các claim trả về, không phải điểm chất lượng của executive summary.
- Nội dung vẫn trộn nhiều đoạn AI/Engine, lặp nguồn và giới hạn. Câu “Hai kỳ chỉ đủ so sánh”, “Đây không phải kết luận về tác động…” xuất hiện nhiều lần, nên gom hạn chế theo phần thay vì đặt lại trong từng đoạn.
- Chưa có chế độ tổng hợp nhóm ngắn và tùy chọn đưa chi tiết thành viên vào báo cáo/bản xuất. Chọn điểm nổi bật không giảm số biểu đồ hoặc số phần chi tiết.
- Case 1 có false rejection ở claim đúng số liệu: “cả Tổng số và Số lỗi cùng giảm, lần lượt từ 214 xuống 209 ... và từ 43 xuống 32 ...; tỷ lệ 20.09% xuống 15.31%”. Tất cả số liệu khớp operands và displayValue Engine. Kiểm tra `_subject_at` cho thấy parser gán 214/209 vào `error` vì đây là chủ ngữ gần nhất; từ “lần lượt” chưa được ánh xạ thành cặp chủ ngữ–giá trị. Vì vậy `unsupported_numeric_mention` ở case này là hạn chế liên kết chủ ngữ, không phải số liệu bịa. Nên bổ sung quy tắc phối hợp có phạm vi và regression test; không cho phép số bất kỳ chỉ vì xuất hiện đâu đó trong snapshot.

## Bằng chứng UI và template

Replay case 1/4/7 ở 1440 × 1000; 6 ảnh được mở kiểm tra (top và story cho từng case), không blank/loading. Các ảnh dưới `.impeccable/review/reports-audit-2026-10-06/`; số đo nằm trong `case-1.json`, `case-4.json`, `case-7.json`. Story case 7 là ảnh dài, thumbnail không dùng để khẳng định kiểm tra mọi dòng; số lượng/vị trí và template lấy từ DOM/Plotly thật.

| Replay | Độ dài trang | Bắt đầu diễn biến | Vị trí nút xuất | Phần thành viên |
|---|---:|---:|---:|---:|
| Case 1 | 6,233 px | 1,509 px | 6,111 px | 1 |
| Case 4 | 6,885 px | 1,550 px | 6,763 px | 2 cách tính |
| Case 7 | 12,563 px | 1,866 px | 12,442 px | 7 |

Không phát hiện tràn ngang ở các replay này. Các bài kiểm thử crop cũng đạt. Điều này không đồng nghĩa giao diện tiện dùng.

Vấn đề xác nhận:

1. Khung bộ lọc dashboard và số điểm dữ liệu vẫn hiển thị cùng phạm vi report độc lập. Người dùng dễ hiểu nhầm rằng đổi bộ lọc trái sẽ sửa report snapshot.
2. Metadata/thiết lập/lịch sử/notice chiếm phần lớn màn hình đầu; executive summary bắt đầu gần đáy viewport. Nút lưu/kiểm tra/xuất nằm sau toàn bộ chart và findings.
3. `report-chart.ts` dựng mỗi KPI thành một `scatter`, cùng màu `#315b83`, `showlegend=false`. Trong khi `charts.py` + `chart.ts` hiện có cột tổng và đường trung bình/tỷ lệ, màu theo KPI/cách tính và hover/legend chung. Case 4 có bốn chart rời thay vì template thống kê kết hợp đã quen thuộc.
4. Trục tuần của report chỉ hiển thị ngày bắt đầu như `01/08/2026`, `03/08/2026`, không hiển thị khoảng tuần như dashboard. Cách đọc kỳ không thống nhất giữa narrative, UI chart và export.
5. Case 1 nhãn tỷ lệ vẫn hiện `Tổng trong kỳ · percent`; dễ khiến người đọc hiểu tỷ lệ là số cộng dồn. Cần tên cách tính phù hợp từng metric, không thay giá trị.
6. Engine-proposed highlights có nhiều anchors; các số `1,4`, `3,5` lặp trên chart và vùng tô chồng nhau. Không sai anchor nhưng khó biết nhận định nào đang được nhấn mạnh.
7. PDF/DOCX dùng chart raster tự vẽ bằng Pillow trong `reporting/export.py`, cũng một đường xanh; chỉ sửa UI preview không đủ để đồng nhất template bản xuất.

## Hướng sửa đề xuất

Ưu tiên 1 — Dùng hợp đồng biểu đồ chung cho snapshot report: màu KPI, cột/đường, trục kỳ, đơn vị, legend, hover. Adapter phải lấy dữ liệu từ report snapshot, không fetch số liệu dashboard hiện tại. Khi tổng và trung bình cùng xuất hiện, giữ trục và đơn vị riêng. Đánh dấu dùng anchors canonical và giữ gap.

Ưu tiên 2 — Làm rõ phạm vi báo cáo ngay đầu: một vấn đề / các vấn đề chọn / cả nhóm, kèm danh sách dễ kiểm tra. Trong tab report, tránh các bộ lọc dashboard có vẻ điều khiển report nhưng thực tế không tác động tới snapshot. Giữ khả năng tạo báo cáo từ phạm vi dashboard bằng thao tác rõ ràng.

Ưu tiên 3 — Thanh thao tác dễ tiếp cận cho tạo AI/lưu/kiểm tra/xuất; metadata đầy đủ và lịch sử là thông tin phụ. Giữ năm section gốc nhưng summary và diễn biến cần lên trước các thông tin kỹ thuật.

Ưu tiên 4 — Tách phạm vi với mức độ chi tiết: báo cáo nhóm tóm tắt không bắt buộc chi tiết mỗi thành viên; cho chọn thành viên/biểu đồ để đưa vào bản xuất, hiển thị đúng những gì sẽ xuất. Không chỉ thu gọn UI trong khi PDF vẫn xuất tất cả.

Ưu tiên 5 — Tinh chỉnh nội dung tổng hợp, tránh lặp tên, cảnh báo và các chênh lệch vụn. Sửa parser phối hợp “lần lượt” theo evidence typed; không nới kiểm chứng số, kỳ, đơn vị và metric một cách toàn cục.

## Kiểm thử hồi quy

- Backend: `python -m pytest -o addopts='' -q tests/test_reporting.py tests/test_ai_report.py tests/test_charts.py` — **66 passed**.
- UI hiện có: `npm test -- reports.spec.ts` — **13 passed**, gồm snapshot, chọn phạm vi, đánh dấu, revision, đọc nguồn, reduced motion, crop 1366/1440/1920/390. 390 là regression, không thay đổi định hướng desktop-first.
- Replay output thật: `EVP_REPORT_AUDIT=1 npm test -- report-audit.spec.ts` — **3 passed**. PowerShell: `$env:EVP_REPORT_AUDIT='1'` trước khi chạy. Đây là replay output ghi ngày 06/10, không tự gọi LLM trong mỗi regression run.

Các test trên kiểm tra hành vi và an toàn số liệu; chưa có assertion buộc chart report thống nhất template dashboard. Vì thế test pass không phủ nhận phản hồi bất tiện từ người dùng.

## Bổ sung từ người dùng: thứ tự biểu đồ và diễn giải

Người dùng yêu cầu thiết kế lại phần Diễn biến để biết mỗi biểu đồ tương ứng với diễn giải nào. Cấu trúc đề xuất, chưa triển khai UI ở lượt đánh giá này:

- Mỗi cụm đọc: **tên vấn đề / nội dung phân tích → biểu đồ làm căn cứ → diễn giải tương ứng**. Không gom các đoạn của mọi KPI trước một danh sách biểu đồ rời phía dưới.
- Tổng quan của một nội dung có đủ 3 KPI: biểu đồ kết hợp theo template Tổng quan hiện có, rồi phần giải thích diễn biến và liên hệ của 3 KPI đó. Không chia một nhận định về lỗi/tổng/tỷ lệ thành ba bản sao.
- Một vấn đề chỉ có Số lỗi: một biểu đồ Số lỗi, ngay dưới là diễn giải của vấn đề đó. Không tạo chart KPI không có dữ liệu.
- Thống kê cùng một vấn đề: biểu đồ theo template Thống kê, giữ tổng và trung bình/ngày khác trục/đơn vị; phần diễn giải phải nói rõ đang đọc cách tính nào. Không mặc định bốn biểu đồ cùng màu cho bốn series.
- Báo cáo nhóm: mỗi vấn đề được đưa vào chi tiết là một cụm biểu đồ–diễn giải. Nhận định so sánh nhiều vấn đề thuộc một cụm riêng có biểu đồ đối chiếu cùng đơn vị hoặc liên kết rõ tới các cụm làm căn cứ; không gán nhận định chung vào riêng một thành viên. Không tự cộng thành tổng nhóm hoặc suy ra tác động nhân quả.
- Chọn liên kết biểu đồ dựa trên entity/calculation, candidate và fact/evidence dependencies, không đoán từ từ khóa trong văn bản LLM. Một đoạn chỉ hiển thị một lần tại cụm đủ biểu đồ hỗ trợ; chart anchors vẫn canonical.
- Giữ nguyên năm section cấp báo cáo đã thống nhất. Chỉ thay cấu trúc bên trong Diễn biến, không tạo heading đỉnh/đáy riêng. Mốc đỉnh/đáy và chênh lệch ở ngay trong diễn giải liên quan.
- Preview và PDF/DOCX phải dùng cùng một danh sách cụm đọc. Đổi template cần định danh version mới, không thay lặng lẽ bytes của export cũ đã lưu.

Việc triển khai tương ứng phải kiểm thử: single KPI, đủ 3 KPI, sum/avg/both, nhóm chọn/cả nhóm, thiếu dữ liệu, nhiều đơn vị, chỉnh diễn giải, chọn marker, snapshot/revision và export. Đây là hướng thiết kế tiếp theo, không được ghi nhận là năng lực đã triển khai.
