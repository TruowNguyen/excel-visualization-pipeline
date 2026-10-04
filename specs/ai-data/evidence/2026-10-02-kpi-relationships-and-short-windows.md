# KPI relationships and short windows — 02/10/2026

> Superseded: phần Pearson/correlation trong bản thử nghiệm này đã được bỏ theo clarification của người dùng; runtime hiện dùng grounded-synthesis-v3 và liên hệ số lượng/mẫu số/tỷ trọng. Các kết quả test bên dưới là bằng chứng lịch sử, không phải trạng thái runtime mới.

## Delivery

User correction: two points are comparison, not trend; two-point extrema and repeated metric templates are redundant; date chains unclear; prioritize relationships between three KPI rather than enumeration of daily values.

Backend `synthesis.py`: policy `grounded-synthesis-v2`, minimum four CONTIGUOUS periods for trend language, two-period `period_comparison`, three-period `short_sequence`. The latest contiguous block is counted, not all observed points across gaps. Cross-metric count/rate comparison says “giữa hai kỳ” for two periods. A useful cross-metric relation replaces weak/short per-metric narrative; meaningful reversal primary remains alongside it. Peak-offset requires at least four aligned periods.

Deterministic Pearson on FIRST DIFFERENCES for all three pairs: total/error, total/error_rate, error/error_rate. This measures linear association of period-to-period changes, not raw levels, not a test of trend or statistical significance. Use one longest aligned contiguous fully eligible natural-period block; latest block wins equal length. Require at least six periods = five paired changes. No gap interpolation or lag search, no invented strong/weak threshold. Constant changes give null/undefined, not r=0. Typed facts carry method, coefficient, sample/period counts, all operandFactIds/evidenceIds, and scoped boundaries in synthesis metadata. Rate is algebraically dependent on count and denominator, not an independent signal; not causal evidence.

Prompt registry `trend-summary-v9` / `metric-overview-v5`, resource remains `grounded-insight-v3.md`: short-window and correlation rules, fewshot F two-period comparison. Claims schema v3 unchanged. Validator still fail-closed candidate-specific grammar/citations/relations; no LLM arithmetic/numerical additions, no privacy/provider gating change. New language remains bounded, not arbitrary free prose. Historical comparison, p-values, confidence intervals, detrending beyond first differences and lagged relationships are not implemented.

Frontend uses neutral panel title “Phân tích KPI tự động”. Under four observed periods, one KPI-by-period comparison table replaces chronology, extrema, repeated per-metric disclosures and redundant endpoint supplement. Compact label `Kỳ 1 (07–13/09) → Kỳ 2 (14–16/09)`; full year/date scope retained in receipt, cross-year boundaries retain years. A joint-relationship section explains correlation availability, sample/method/scope and mathematical dependence; coefficients in one three-row collapsed table. Details and captured source investigations remain intact. No new mobile optimization.

## Before / after

Synthetic two-period values total100→200, error10→15, rate10%→7.5%: before summary claimed “đi lên qua các kỳ” plus separate metric chronology/extrema. After: “Báo sai/Lỗi tăng về số lượng nhưng tỷ lệ báo sai giảm giữa hai kỳ; Tổng số tăng nhanh hơn Báo sai/Lỗi trong phép tính tỷ lệ.” No trend inference; one common comparison table, no peak/lowest dump.

Synthetic six-period values total100,120,110,150,130,180; error10,12,11,15,13,18. Verified deterministic narrative: “Mức thay đổi của Tổng số và Báo sai/Lỗi có tương quan cùng chiều trong đoạn được đối chiếu; tỷ lệ báo sai phụ thuộc cả số lỗi và Tổng số, không phải một tín hiệu độc lập.” Count changes have r=1.000; rate stays10%, so the other two change correlations are undefined. Coefficients do not establish business quality/causality or significance.

Current committed normalized 07–16/09 slice still has one gap. Longest eligible contiguous block is12–16/09, FIVE periods, so no correlation coefficient is emitted. Peak-retreat and differing peak dates remain supported. Do not fabricate coefficients to satisfy UI. Current fixture keeps committed engine facts with mocked source targets; no DB write/live provider. Weekly label fixture is rendering-only synthetic, with old unrelated anchors cleared; it does not validate weekly aggregates or live provenance. All other new numerical fixtures computed through the actual engine.

## Verification and scope

157 Python tests pass; 15 AI Playwright E2E pass; frontend build pass (existing Plotly chunk-size warning). Eight additional unit cases cover short-period direction, three grounded pairs, positive/negative correlation, constant-change undefined, too few/disconnected samples, and short latest block. Two added E2E cases cover joint coefficients/readability and compact weekly comparison labels. Final AI subset also rerun after priority refinement. Detector ran once, exit0 `[]`.

Desktop panel evidence at1440/1280: `.impeccable/review/desktop{,-1280}.png`, `desktop-short-weekly{,-1280}.png`, `desktop-correlation{,-1280}.png`, `desktop-current-insight{,-1280}.png`, `desktop-whole-series{,-1280}.png`, `desktop-limited.png`. Panel crops start at panel top, not full dashboard captures. Two builder inspection rounds; final batch fixed correlation text truncation and cleared stale synthetic weekly anchors. Fresh independent reviewer/documenter outcomes recorded in surface brief. No external provider accuracy/latency, live source verification, production rollout or usability timing study claimed.

Changed: `ai/synthesis.py`, `ai/service.py`, active prompt; `frontend/src/main.ts`, `style.css`; `tests/test_ai.py`, `test_ai_synthesis.py`; E2E tests/harness and engine fixtures including new `correlation-insight.json`; AI README/spec01/04/05 and dashboard spec, this evidence and surface brief. Prior unrelated dirty worktree changes preserved. DESIGN.md/design.json remain missing preexisting drift, not repaired.
