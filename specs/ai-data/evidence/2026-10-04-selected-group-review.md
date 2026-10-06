# Đánh giá AI Insight của nhóm vấn đề đang chọn — 04/10/2026

## Phạm vi thực hiện

Sửa lỗi hiển thị tiền tố tên nhóm và chạy mới API LLM thật để đánh giá. Không chỉnh prompt, Analytics Engine hoặc validator trong lượt này; các đề xuất bên dưới chưa triển khai.

“Nhóm đang chọn” được kiểm tra bằng selection=node, không phải selected children: VSO / Chất lượng cảnh báo - ghi nhận trên hệ thống. Chạy thêm SmartParking để đối chiếu dữ liệu lớn và thiếu kỳ. Node phân tích dữ liệu trực tiếp của nhóm, không tự cộng các vấn đề con.

Provider thật: 9Router / gemini-3.7-flash-tiered. Bốn request `/ai/context-insight` gồm VSO Overview ngày, VSO Statistics tuần/both và tháng/both, SmartParking Statistics tuần/both. Chạy thêm `/ai/trend-summary` VSO ngày/all, là đường Overview node mà UI hiện sử dụng. Tổng cộng 5 request generation thật, không mock provider.

## Lỗi tiền tố “1.1.”

API cố ý giữ entityLabel nguồn. Context composer ghép nhãn đó vào overview; renderer trước đây chỉ format tên KPI, không format tên section như sidebar. Vì vậy tên nhóm raw lọt vào topic, detail summary và prose.

Đã thêm formatter dùng metadata entity_level=section và `getEntityDisplayName` sẵn có; chỉ thay tên nhóm đã biết, không regex xóa mọi số đầu câu. Áp dụng cho đoạn tổng quan/giai đoạn/liên hệ/giới hạn, tên khối chi tiết và excluded; Overview legacy cũng dùng formatter trong aiReadable. API entityLabel, IDs, facts, evidence và chữ số KPI không đổi. Ví dụ 1.1 là mức số liệu vẫn giữ nguyên; tên item bắt đầu bằng số không bị coi là section.

Impeccable được dùng để giữ nhất quán ngôn ngữ hiển thị với sidebar, không thay bố cục hoặc nội dung nhận định. Hai browser regression phát lại output tuần/tháng thật đã lưu, xác nhận tên nhóm không có số thứ tự, số bảng và evidenceId không đổi. Đã xem ảnh tháng `selected-group-label-month.png`; đây là replay output thật qua route fixture, không phải browser gọi provider trực tiếp.

## Kết quả kỹ thuật

| Đường API / phạm vi | Kết quả | Đoạn LLM được giữ | Request latency |
|---|---|---|---|
| Context VSO Overview ngày, node | accepted | 5/5 | 8.559 s |
| Context VSO Statistics tuần, node/both | accepted | 5/5 | 7.426 s |
| Context VSO Statistics tháng, node/both | accepted | 4/4 | 5.749 s |
| Context SmartParking Statistics tuần, node/both | accepted | 8/8 | 9.864 s |
| Legacy VSO Overview ngày, node/all | partial | 6/9 | 8.775 s |

Context có 97 điểm được đối chiếu canonical chart và 26 đối chiếu aggregate nguồn ở ranh giới chuỗi; không mismatch, không trùng factId, membership đầy đủ. Đây là lấy mẫu contributor nguồn, không audit mọi nguồn. Các số trong prose được validator hiện tại kiểm chứng; accepted không tự chứng minh nội dung đủ sâu hoặc mọi paraphrase đúng.

Frontend: 33 test context/terminology/reading pass, build pass; cảnh báo chunk Plotly đã có. Không thay production frontend sau build/test. Không chạy lại toàn bộ Python vì thay đổi chỉ ở presentation frontend; 342 pass của lượt trước không được coi là một lượt chạy mới. Không commit/push.

## Đánh giá nội dung

### Diễn biến: khá rõ

VSO ngày kể đúng cấu trúc số lỗi 16 → 8 → 10 → 8, thiếu một kỳ, tăng 19 → 43 rồi giảm 43 → 32 → 22 và giữ 22 ở cuối. Context overview có nhịp 19 → 43, chênh lệch 24 (126.32%), và 43 → 32, chênh lệch -11 (-25.58%). Đỉnh/đáy nằm trong giai đoạn, không heading riêng. Không dùng 16 → 22 làm đại diện cho toàn chuỗi.

### Cách tính: phân biệt được, nhưng giải thích chưa đủ

VSO tháng: tổng lỗi giảm 441 → 299, chênh lệch -142 (-32.2%), nhưng lỗi trung bình/ngày tăng 16.33 → 19.93, chênh lệch 3.6 (22.04%). Tổng số trung bình/ngày cũng tăng 147.11 → 255. Output giữ từng calculation riêng, nêu hai kỳ chỉ đủ so sánh và khác số ngày ghi nhận; không gán kết quả này thành xu hướng dài hạn.

Điểm còn thiếu: người đọc vẫn phải tự ghép thông tin “tổng giảm nhưng mức mỗi ngày tăng”. Tổng quan chủ yếu nói average, sum ở phần dưới. Nhận định hữu ích cần nhấn rằng tổng giảm chưa cho thấy mức lỗi ghi nhận mỗi ngày giảm, rồi đưa hai anchor đúng calculation. Không so trực tiếp mức sum với average hoặc tự tính một delta chung.

VSO tuần cuối: tổng lỗi 104 → 76 nhưng average lỗi 17.33 → 25.33, chênh lệch 8 (46.15%). Đây là minh chứng rõ để ưu tiên giải thích cách đọc hơn là chỉ liệt kê hai chiều. Nhãn/coverage nguồn cần được trình bày cùng nhận định; không suy ra nguyên nhân nghiệp vụ.

### Liên hệ KPI: chưa đạt kỳ vọng insight tổng hợp

Trong bốn payload context mới, candidate chỉ có overview và phases; không có candidate relationships. Issue report.relationships đều rỗng. Vì vậy node group context chủ yếu kể các chỉ số cạnh nhau, chưa có slot diễn giải quan hệ của chúng. Đây là hạn chế facts/candidate/composer, không thể giải quyết chỉ bằng nới validator hoặc thêm câu yêu cầu vào prompt.

Legacy Overview có relationships và đưa ra nội dung hữu ích: ngày 15–16/09, lỗi giữ 22 trong khi Total 657 → 420, tỷ lệ 3.35% → 5.24%; tỷ lệ tăng không đồng nghĩa có thêm lỗi. Tuy nhiên đoạn LLM này bị loại vì `unsupported_meaning`, report thay bằng nhận định Engine đúng nhưng thiếu anchor đầy đủ. Đoạn lỗi và Total cùng giảm ngày 13–14/09 cũng bị loại khi dùng “do” để giải thích quan hệ toán học; ba claim bị loại gồm một `numeric_period_mismatch` và hai `unsupported_meaning`. Đã đọc raw: các mức 43 → 22 và 20.09% → 3.35% thuộc đúng hai ngày biên nhưng cách gắn số/ngày vẫn làm gate loại. Đây là dấu hiệu false rejection cần hồi quy riêng, không là lý do bỏ các gate số/ngày/nhân quả.

Statistics chỉ cung cấp Total/Error, không có tỷ lệ. Không được tự tạo % báo sai hoặc kết luận chất lượng tốt/xấu trong review hay prompt. Có thể giải thích các chỉ số cùng/trái chiều khi Engine cấp facts tương ứng, không correlation hoặc nhân quả.

### Độ dễ đọc: đã đồng nhất nhãn, vẫn có lặp

Tên nhóm không còn số thứ tự trên UI. Cấu trúc một nhóm/hai calculation và phase labels nhất quán. Nhưng tháng chỉ có hai kỳ nên overview và phase gần như nhắc cùng nội dung; câu hạn chế số ngày còn lặp ở tổng quan, calculation và quality note. SmartParking có nhiều đoạn quan sát một kỳ vì thiếu kỳ, làm phần chi tiết dài. Không nên coi tất cả accepted là đã hết các vấn đề này.

## Hướng cải thiện đề xuất, chưa triển khai

1. Bổ sung deterministic relationship candidates cho node group: diễn biến Total/Error trong cùng cặp kỳ; với Overview có thêm quan hệ tỷ lệ khi numerator/denominator đủ điều kiện. Giữ unit/calculation/period/source rõ ràng.
2. Thêm tổng hợp cả hai cách tính bằng các anchor độc lập và coverage: “tổng lỗi giảm, nhưng lỗi ghi nhận trung bình mỗi ngày tăng”; không tạo phép trừ sum–average, không nhân quả.
3. Với hai kỳ, tránh lặp nguyên câu overview và phase; gom lời hạn chế trùng nhau ở đúng nơi ảnh hưởng cách hiểu.
4. Hồi quy validator các câu toán học đúng nhưng bị gắn nhãn nhân quả hoặc numeric_period_mismatch. Chỉ cho phép khi facts và vai trò số xác nhận được, không nới chung.

Kết luận: đủ tốt để đọc diễn biến có số minh chứng, nhưng chưa đạt mức phân tích tổng hợp KPI nhất quán ở nhóm đang chọn. Ưu tiên bổ sung relationship facts/candidates và composer; validator là vấn đề bổ sung riêng ở đường legacy.

## Artifacts

- [Manifest nhóm đang chọn](2026-10-04-selected-group-manifest.json).
- [Context API thật mới](2026-10-04-selected-group-live.json): rawNarrative, provider input, report, series, facts/evidence, source checks.
- [Legacy Overview thật mới](2026-10-04-selected-group-legacy-live.json): raw/output/validation.
