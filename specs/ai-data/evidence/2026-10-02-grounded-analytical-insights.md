# Grounded analytical insights — 02/10/2026

## Root cause và phạm vi

Audit runtime xác nhận ba lớp cùng gây fact dump: temporal engine tạo sẵn câu đầy đủ; prompt/validator v1/v2 ép exact canonical sentence và citations; UI mở chronology/extrema theo từng metric mặc định. Facts nhiều hơn không tự giải quyết synthesis. Task mới cho phép triển khai, nhưng không đổi core KPI, weighted-rate, missing/zero, committed-only, source evidence, snapshot/freshness, feature/privacy gates hoặc provider budget. Không gọi external provider trong lần xác minh này.

## Thay đổi

`ai/synthesis.py` bổ sung `grounded-synthesis-v1`: nhóm structured facts thành relation candidates, ưu tiên một diễn biến chính và một quan hệ KPI đủ căn cứ (tối đa hai). Peak-retreat, trough-recovery, endpoint-mask, sustained direction, descriptive abstention; cross-metric count/rate dùng các chuyển tiếp liền nhau đủ operands; peak-offset chỉ dùng peak duy nhất đã kiểm chứng. Không tạo significance threshold. Gap không được nối; partial block nói rõ phạm vi. Historical context và toàn bộ facts gốc giữ trong detail, chưa có historical-comparison narrative mới.

PromptRegistry `trend-summary-v8` / `metric-overview-v4` cùng dùng `prompts/grounded-insight-v3.md`. Prompt định nghĩa Fact/Diễn biến/Insight, ưu tiên contrast, tách số/ngày sang anchors backend, có fewshot A peak-retreat, B equal-endpoint reversal, C count/rate, D abstention, E missing.

Provider input `ai-insight-provider-input-v3` chỉ gửi selected candidate facts và anchors, không full series/canonical paragraph/validation expressions/raw provenance. Provider output `ai-narrative-v3` gồm claims candidateId/text/factIds. Validator v3 bỏ exact whole-paragraph equality, thay bằng grammar diễn đạt tương đương có giới hạn, kiểm tra relation operands, metric/direction/scope/schema/citations; bác số/ngày mới và unsupported cause/quality/anomaly/forecast. Legacy v1/v2 exact validators vẫn giữ cho snapshot không có synthesis. Backend normalize thành API narrative; API response versions v3/v2 không đổi, synthesis/checks được checksum-pin.

UI desktop: summary → anchors → grouped limitations → contextual investigation. Chronology/extrema/largest changes/turning points/history/endpoint và period tables vẫn đủ nhưng mặc định thu gọn. Chỉ insufficient_data đưa limitation trước answer. Không tối ưu mobile mới.

## Before/after trên committed dataset hiện tại

Read-only normalized data: VSO, entity 1.1 Chất lượng cảnh báo, 07–16/09/2026. Tổng số: `71,454,342,251,missing,515,214,209,657,420`; Báo sai/Lỗi: `16,8,10,8,missing,19,43,32,22,22`. Không sửa DB. Fixture `current-insight.json` dùng facts engine thực từ normalized slice; source targets giả lập để kiểm thử rendering, không chứng minh live investigation vào DB.

Before summary:

> Tổng số: Chuỗi có kỳ thiếu; chỉ mô tả các đoạn có dữ liệu liền nhau. Báo sai/Lỗi: Chuỗi có kỳ thiếu; chỉ mô tả các đoạn có dữ liệu liền nhau. % báo sai: Chuỗi có kỳ thiếu; chỉ mô tả các đoạn có dữ liệu liền nhau.

After — deterministic fallback đã kiểm chứng, **không phải live LLM output**:

> Trong đoạn có dữ liệu liền nhau, Báo sai/Lỗi: nhịp tăng lên đỉnh không được duy trì; sau đỉnh chỉ số giảm qua các kỳ; các kỳ cuối giữ nguyên. Trong đoạn có dữ liệu liền nhau, Tổng số đạt đỉnh muộn hơn Báo sai/Lỗi; hai chỉ số không đạt mức cao nhất cùng kỳ.

Anchors tối thiểu: Báo sai/Lỗi 19 ngày 12/09, 43 ngày 13/09, 22 ngày 16/09; Tổng số 657 ngày 15/09. Limitation gom một lần: có 1/10 kỳ thiếu, không nối khoảng trống/không coi missing là 0. Suggested checks: đối chiếu đoạn 12–16/09 quanh đỉnh 13/09; đối chiếu Tổng số 15/09 với Báo sai/Lỗi 13/09. Mỗi nút dùng captured evidence ID, không lookup bằng value/date.

Không dùng ví dụ cross-metric chưa đúng của task làm fact: weighted rate peak thực là 22.54% ngày 07/09 (16/71), không phải 20.09% ngày 13/09 (43/214). Tổng số sau 13/09 cũng không tăng liên tục (214→209→657→420). Vì vậy output chỉ nói lệch kỳ peak đủ căn cứ, không nói lỗi/rate cùng peak hoặc tất cả kỳ sau đều tăng.

## Files thay đổi của lượt synthesis

- Backend: `src/excel_visualization_pipeline/ai/synthesis.py` (mới), `service.py`, `validation.py`, `prompts/grounded-insight-v3.md` (mới).
- Frontend: `frontend/src/main.ts`, `style.css`; `frontend/e2e/fixtures.ts`, `ai-insights.spec.ts`; fixtures `current-insight.json`, `two-point-insight.json`, `whole-series.json`.
- Tests: `tests/test_ai.py`, `tests/test_ai_synthesis.py` (mới). Tests/analytics/overview/temporal từ lượt trước được giữ, không ghi đè unrelated dirty changes.
- Specs: AI README, 01/04/05, API contract, dashboard behavior, evidence này; direction/evidence surface brief `.impeccable/surfaces/frontend-src-main-ts.md`.

## Verification và giới hạn

`python -m pytest -q`: toàn bộ 149 tests pass (existing deprecation warnings). `npx playwright test e2e/ai-insights.spec.ts`: 13 pass. Sau sửa Unicode metadata của committed fixture, targeted dataset E2E 1 pass và recapture hai desktop widths. `npm run build`: pass, existing Plotly chunk-size warning. Detector Impeccable chạy một lần, exit 0/no findings. Golden suite mới 24 cases bao gồm đủ mười tình huống yêu cầu, paraphrase hợp lệ và adversarial grounding/schema mutations.

Captures: `.impeccable/review/desktop-current-insight{,-1280}.png`, `desktop-whole-series{,-1280}.png`, `desktop{,-1280}.png`, `desktop-limited.png`. 1440/1280 là viewport; ảnh là toàn panel từ đầu panel, không phải toàn dashboard. Review/documentation verdict lưu trong surface brief sau handoff.

Giới hạn: grammar v3 vẫn đóng/bounded, không phải arbitrary free-form semantic validator; lựa chọn ưu tiên là structural policy, chưa có calibrated business significance. Chưa có live-provider evaluation/latency measurement, production rollout hoặc nghiên cứu xác nhận đọc hiểu 10–15 giây (chỉ là mục tiêu thiết kế). Không có narrative lịch sử mới. Cross-metric abstain nếu partial natural period, contributors sai, zero denominator, tied peak hoặc không alignment. Root DESIGN.md/design.json thiếu từ trước; ordinary extension không tự sửa drift.
