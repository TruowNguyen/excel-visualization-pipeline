# Whole-series AI Insights — 02/10/2026

## Mục tiêu và kết quả

Ưu tiên hiểu diễn biến trong toàn khoảng, thay thế cách đọc endpoint-led của analytical overview MVP cùng ngày. Engine cung cấp chronological stages, observed direct reversals và missing gaps trong periodAnalytics.temporalStructure. Chuỗi 16→8→10→8→19→43→32→22→22 tạo sáu đoạn: giảm, tăng, giảm, tăng liên tiếp tới đỉnh, giảm liên tiếp và giữ nguyên cuối. Plateau không bị gọi là ổn định thống kê; không suy ra chất lượng/nguyên nhân.

Prompt runtime: single `trend-summary-v7` (resource system-prompt-v2.md), overview `metric-overview-v3` (resource metric-overview-v2.md). API/narrative schema không đổi. Single summary phải khớp canonical temporal story; overview chỉ dùng whole-window candidate. Fallback cũng theo whole-series. Fact tổng hợp giữ nguồn/dependencies; compact single-provider payload không lặp toàn bộ giai đoạn. Không thay core KPI, privacy gate, retry hay output budget.

UI desktop-first trình bày stages, extrema và cả largestIncrease/largestDecrease có ngày trước endpoint supplemental disclosure. Historical context có sẵn được giữ lại. Quan hệ liên KPI hiện vẫn endpoint-only, ghi rõ và thu gọn; chưa tạo phase-specific causal/growth relationship. Missing biên/nội bộ không được gọi là full-window coverage; gaps ngắt consecutive và ending plateau.

## Verification

- `python -m pytest -q`: toàn bộ 125 tests pass; có 18 deprecation warnings FastAPI/Python hiện có.
- `npx playwright test e2e/ai-insights.spec.ts`: 12 tests pass, gồm engine-generated synthetic nine-period fixture, both largest changes, endpoint collapsed, captured scope/stale, fallback, source routing và desktop overflow. Hai regression mobile hiện có vẫn chạy; không mở rộng/mobile optimization.
- `npm run build`: pass; warning chunk Plotly >500kB không liên quan thay đổi này.
- Impeccable detector main.ts: exit 0, không findings. Independent desktop finish review: initial fix; verdict pass ship, ba findings resolved (largest fall, synthetic source-check count, stale documentation). Phạm vi approval là fix list trên năm panel captures, không renewed whole-surface audit.
- Captures: .impeccable/review/desktop-whole-series.png, desktop-whole-series-1280.png, desktop.png, desktop-1280.png, desktop-limited.png. Đây là synthetic panel captures; không phải live business/provider evidence.

Không gọi external provider trong verification này; chưa đo latency/accuracy với model thật. Không thêm persistence/report/export/scheduling hay hệ thống thiết kế toàn cục. DESIGN.md/design.json thiếu từ trước và không được sửa ngoài phạm vi.
