# KPI links clarification — 2026-10-02

User intent: explain the relationship between three KPIs, not statistical correlation.

- Removed Pearson first-difference computation, correlation facts, coefficient UI and six-period availability warning.
- Runtime: grounded-synthesis-v3, trend-summary-v10 / metric-overview-v6, shared grounded-insight-v3.md.
- Added nine grounded numerator/denominator/rate movement recipes. Each uses aligned eligible contiguous periods, all three metric operands, evidence and scope. Short partial two-period recipes have lower priority than meaningful longer-window structure.
- Two periods remain comparison, three a short sequence; trend language requires four contiguous periods. Dates and one shared short-window table remain.
- No business causality or quality judgement; prompt includes unchanged-error and falling-error/rising-share examples. Strict validation stays in place.
- Removed the synthetic correlation-only E2E JSON; weekly rendering now reuses the existing harness. No source data or database deleted.

Verification: all 164 Python tests and all 15 AI Playwright E2E tests passed; frontend build passed with existing Plotly chunk warning. Impeccable detector ran once and returned [].
Desktop captures are full-panel crops at 1440/1280 viewport widths, not full dashboards. Current-insight uses previously captured committed normalized VSO facts and deterministic fallback; source routes are mocked. Other fixtures are synthetic; weekly is label/rendering evidence, not actual aggregation. No live provider accuracy/latency claim, mobile optimization or production rollout.

Finish review: independent reviewer failed on service usage limit. Disclosed substituted in-thread Impeccable fallback returned disposition: ship for supplied desktop panel scope, with no material UI fixes. This is not independent approval. TYPE/MATERIAL/GROUND preserve the incumbent; all eleven required captures were inspected. One weekly fixture correction aligned selector, narrative and values, then confirmed. Missing DESIGN.md/design.json remain preexisting drift, not repaired.
