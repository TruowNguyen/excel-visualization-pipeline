# Sửa phản hồi tổng quan ba metric — 01/10/2026

## Nguyên nhân

API `ai-overview-v1` chứa chuỗi kỳ tại `metrics[].series`, không có `series` ở root. Frontend gọi `.map()` trên trường root không tồn tại trong lần render sau response, khiến UI vẫn hiển thị trạng thái chờ. Fixture Playwright cũ có thêm `series: []`, che mất sự khác biệt contract.

Payload overview còn lặp facts tại root và trong từng metric, dùng prompt trend dài; bộ lọc fact đầu–cuối không xử lý prefix metric nên bỏ sót facts cần cho tổng quan.

## Thay đổi

- Frontend chấp nhận root series không có trong overview; fixture mô phỏng đúng response thật và kiểm tra không có page error.
- Prompt riêng `metric-overview-v1`, 2–3 câu tổng quan và tối đa một insight.
- Facts gửi một lần tại root. Tên fact đầu–cuối xử lý đúng namespace.
- Context overview tập trung peak/lowest/latest change và vị trí lịch sử. Analytics và bằng chứng chi tiết vẫn đầy đủ trong response local.
- JSON request được serialize gọn. Smoke ghi riêng thời gian provider và toàn API.

## Xác minh

Live smoke với ba metric, mỗi metric chín kỳ: `ready`, narrative `ai`, validation `accepted`, một attempt. Lần đo sau sửa: provider 6.127 ms; API 10.286 ms; prompt 2.045 ký tự. Đây là một phép đo, không phải SLA hay phân vị latency.

31 test AI và 9 test trình duyệt AI Insights đạt; production build đạt. Fixture overview không còn root series.
