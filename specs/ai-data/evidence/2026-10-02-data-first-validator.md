# Validator ưu tiên độ đúng của dữ liệu — 02/10/2026

## Chính sách hiện tại

Narrative v4 dùng `semantic-grounding-v3`. Không đổi system prompt, Analytics Engine, UI, model, timeout hoặc số lần gọi provider trong đợt này.

- Bỏ danh sách từ vựng được phép. Các từ nối hoặc cách nói mới không còn khiến một nhận định bị loại chỉ vì extractor chưa biết từ đó.
- `relation_not_expressed`, `ambiguous_metric_subject` và `unquantified_magnitude` là cảnh báo chất lượng diễn giải. Cảnh báo không loại claim, không chuyển kết quả thành `partial`, không kích hoạt fallback.
- Cảnh báo được ghi ở `validation.warnings` và `validation.claimResults[].warnings`. Claim vẫn giữ nguyên câu của provider; `errors` chỉ chứa lỗi chặn. `partial` chỉ xảy ra khi có claim bị loại nhưng vẫn còn claim hợp lệ.
- Giữ kiểm tra JSON/identity, candidate/claim type, citation dependency closure, source evidence, KPI/phạm vi thời gian, số/đơn vị, cặp số–ngày, vai trò cao nhất/thấp nhất và các mâu thuẫn chiều biến động mà extractor nhận diện được.
- Câu có số trung gian và ngày rõ ràng được đối chiếu với điểm dữ liệu tương ứng, không bị ép số đó phải là giá trị cuối. Với “tăng lên / giảm xuống / giữ nguyên ở”, còn đối chiếu chiều với kỳ liền trước; đúng số nhưng sai chiều vẫn bị loại.
- Cho phép giải thích tác động mẫu số khi facts xác nhận số lỗi giữ nguyên, Tổng số thay đổi và tỷ lệ thay đổi ngược chiều. Ví dụ: “Tỷ lệ báo sai tăng do Tổng số giảm, trong khi Báo sai/Lỗi giữ nguyên.” Đây là quan hệ phép tính đã có fact, không phải suy đoán nguyên nhân nghiệp vụ.
- Vẫn chặn dự báo, khẳng định chất lượng và nguyên nhân nghiệp vụ không có căn cứ. Hai hoặc ba kỳ vẫn không đủ để gọi là xu hướng theo chính sách hiện tại. Nhận định chỉ có limitation hoặc không xác định được KPI không được coi là phân tích hợp lệ.

## Giới hạn

Đây là extractor có giới hạn, không phải bộ chứng minh ý nghĩa của mọi câu tiếng Việt. Bỏ whitelist làm giảm loại nhầm, nhưng không bảo đảm phát hiện mọi khẳng định sai diễn đạt bằng từ mới. Citation đúng và số đúng không tự chứng minh toàn bộ câu văn đúng. Prompt và deterministic facts vẫn giới hạn nội dung provider; kiểm thử đối kháng vẫn cần bổ sung theo các lỗi thực tế.

Kiểm tra số vẫn dùng giá trị fact chính xác, không tự cho phép LLM làm tròn hoặc tính số mới. Nới câu chữ không đồng nghĩa nới nguồn dữ liệu.

## Kiểm chứng

- Regression mới: cách diễn đạt tự nhiên, cảnh báo không gây fallback, giải thích mẫu số hợp lệ, sai chiều mẫu số, nguyên nhân/đánh giá chất lượng không có căn cứ, số đúng gán sai ngày, số trung gian đúng ngày nhưng sai chiều.
- Replay cả ba response trong [bằng chứng gọi provider trước đó](2026-10-02-live-semantic-evaluation.json), dựng lại snapshot từ normalized series, chỉ khớp analysis identity cho fixture. Không thay text/citation. Cả ba response đều giữ đủ hai claim và có trạng thái kiểm chứng `accepted`.
- Replay là kiểm thử offline; không có API LLM mới và không có phép đo latency mới trong đợt này. Các receipt lịch sử trong JSON gốc được giữ nguyên để đối chiếu.
- Toàn bộ Python regression suite: `python -m pytest -o addopts='' -q` → **249 passed**, 18 cảnh báo deprecation FastAPI/Python có sẵn. Không sửa frontend nên không chạy lại build/browser suite trong đợt này.
