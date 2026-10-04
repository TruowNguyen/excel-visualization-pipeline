# Analytical overview MVP — 02/10/2026

## Delivered scope

- Desktop-first existing AI panel, no mobile optimization or new visual identity.
- `ai-overview-v2`, `ai-overview-provider-input-v2`, `ai-narrative-v2`, prompt `metric-overview-v2`.
- `aligned-overview-v1` comparison basis: same complete endpoint boundaries, positive denominator, nonnegative numerator and counts consistent with rate operands. Partial/incompatible endpoints retain descriptive facts and limitations.
- Relationship and optional growth enum facts with operand dependencies/evidence. Zero numerator has no relative growth fact; zero exposure has no relational claim.
- Bounded temporal candidate (largest absolute movement, priority rate/error/total), structured source checks, immutable result name, neutral direction styling, limitations before conclusion.
- Model selects/connects exact backend-approved candidate sentences; no free-form mathematical or business-cause claims. Invalid selection/text/citations returns the same deterministic summary and source checks.
- Existing single-metric analytics, weighted pair rule, core values, privacy gate, one overview call, 12-second default timeout and 700-token output cap preserved.

## Verification

- Full Python suite: `python -m pytest`: **112 passed** before two additional overview edge-case tests; no application code changed after that run.
- Final AI subset: `python -m pytest tests/test_ai.py tests/test_ai_overview.py`: **45 passed**, including complete-week excluded pairs, zero numerator, exact v2 citations, wrong text/cause rejection, SQLite service integration and logical exact/aggregate evidence checks.
- Frontend AI suite: `npm test -- ai-insights.spec.ts`: **11 passed**.
- Final desktop confirmation: `npm test -- ai-insights.spec.ts -g desktop`: **3 passed** after the coverage-note separation fix.
- `npm run build`: passed (existing Plotly chunk-size advisory remains).
- Detector on main.ts: `[]`; independent finish review: ship; one minor coverage-note spacing issue fixed and confirmed in refreshed captures.
- Desktop synthetic captures: `.impeccable/review/desktop.png`, `desktop-1280.png`, `desktop-limited.png`. These validate layout, not live model performance or real-user comprehension. Existing mobile regression tests were retained, not expanded into a mobile optimization scope.

## Boundaries / known limitations

- No live external provider call made during this implementation; no new latency/SLA claim. Synthetic/fake-provider tests do not prove actual model selection compliance or production clarity.
- Temporal/relational results are deterministic descriptive comparisons, not root cause, business-quality judgement, anomaly, turning point or peak alignment. No new report approval/export/persistence.
- Complete endpoints are a conservative MVP gate, not an approved general coverage threshold. Historical context remains available in full metric response; overview candidates do not exhaustively narrate it.
- Runtime rates remain computed from the approved weighted pair implementation. Daily source-percentage wording in `AI-TR-013` must be resolved before supporting different source-rate semantics.
- Source references stay server-side; provider sees only normalized candidate text, selected facts and logical IDs. This does not authorize additional data sources or raw provenance payloads.
- No global design-system files created: missing DESIGN.md/design.json is preexisting drift, local extension documented in the surface brief.
