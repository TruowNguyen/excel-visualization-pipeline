# AI Insight — nhấn ý và sử dụng chiều rộng desktop

Yêu cầu: áp dụng nhấn mạnh có chọn lọc trên toàn tính năng AI Insight và không cắt thông tin/để vùng đọc quá hẹp trên desktop.

## Thực hiện

- `frontend/src/insight-text.ts` escape nguyên văn, chỉ tạo thẻ strong có class do ứng dụng kiểm soát; không render Markdown/HTML do LLM cung cấp. Hỗ trợ tên KPI, cụm diễn biến có giới hạn và hai chênh lệch tuyệt đối. Tối đa ba cụm body; tên vấn đề/cách tính ở đầu overview context tách thành dòng đậm riêng. Mọi số/ngày/% và thứ tự chữ giữ nguyên. Không thêm xanh/đỏ ngụ ý đánh giá chất lượng.
- Dùng chung trong legacy/node executive, insights, phases, relationships, takeaways, checks và context overview/phase/relationships/Engine fallback. Chronology/bảng nguồn giữ các nhấn số đã có, không thay phép tính hay nguồn.
- Bỏ giới hạn75ch ở các vùng insight, cho body dùng toàn chiều rộng nội dung; giữ lề26px desktop. Font body16px, executive17px/normal weight, line-height1.75. Issue picker dùng chiều rộng và chia cột theo không gian. Không đổi thứ tự đọc, disclosure, filter hay CTA.
- Bỏ overflow hidden của AI panel và ellipsis/max-width của ô bảng AI; nội dung dài xuống dòng. Bảng vẫn có vùng cuộn riêng khi cần. Không đổi dashboard ngoài AI hoặc thiết kế mobile.

## Kiểm tra

Batched inspection và một correction/confirmation round. Lượt đầu34/40 tests pass; fixture mới thất bại vì evidence compact thiếu relationshipDetails và metric đầu không có series, không phải lỗi số liệu ứng dụng. Đã chọn metric có series và bổ sung mảng bị artifact compact bỏ qua trong fixture; sửa dấu hai chấm của nhãn để không đứng đầu body. Không sửa provider/backend.

Full frontend suite cuối: **83 tests pass**; build/TypeScript pass, còn cảnh báo Plotly chunk đã có. `git diff --check` pass. Detector layout trước/sau `[]`; type chỉ cảnh báo Inter kế thừa, được giữ theo nhận diện hiện có.

10 regression mới: formatter giữ nguyên textContent/signed deltas, chỉ strong có kiểm soát, không tạo IMG thực thi, không tô đậm dates/%; node/children/Statistics ở1280/1440/1920 đo paragraph full-width, font>=16, không overflow hidden, mở detail/source table với tên rất dài, xác nhận không ellipsis hoặc tràn ngang cả page/panel. Existing narrow/source/freshness tests cũng nằm trong83, không tuyên bố nghiệm thu mobile mới.

Ảnh `.impeccable/review/insight-reading-{node,children,statistics}-{1280,1440,1920}.png`. Đã xem node1280, children1440 và Statistics1920. Ảnh children/Statistics dùng report từ lượt LLM thật đã lưu `context-quantified-verified.json` qua route mô phỏng, sửa tên/kỳ đầu thành chuỗi dài để stress wrapping. Đây là kiểm thử renderer của output có thật, **không gọi LLM mới**, không kiểm định lại accuracy/latency/nguồn. Screenshot không phải số liệu production; fixture tên dài và receipt được ghi rõ ở đây.

Self-review: luồng overview→liên hệ→chi tiết→nguồn còn nguyên; tiêu đề vấn đề phân biệt với body; chênh lệch nổi bật nhưng ngày/% không cạnh tranh; long text được wrap, không bị bỏ. Phần thân dùng toàn chiều rộng theo yêu cầu nên dòng dài hơn mức75ch trước đây; line-height được tăng để hỗ trợ đọc. Table stress cực dài vẫn có thể làm cột còn lại xuống dòng, không mất nội dung. Formatter nhận diện hữu hạn từ ngữ, không bảo đảm mọi paraphrase đều được highlight. Không có score usability hoặc independent SHIP mới. Skill Impeccable định hướng bảo toàn nhận diện, nhấn trọng tâm và kiểm chứng kích thước; drift DESIGN.md có sẵn không được sửa trong yêu cầu này. Không commit/push.
