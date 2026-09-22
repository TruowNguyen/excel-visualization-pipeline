# Chart-to-lineage Phase 2

Phase 2 extends the existing exact-observation contract. It does not change chart calculations or the preview/commit import flow.

## Chart contract

- Daily exact points retain `ids[pointIndex] = observationRef` and `meta.lineage.lineageRefs[pointIndex]` (`kind: exact-observation`, contract version 1).
- Weekly/monthly and statistics points with evidence use `meta.lineage = {contractVersion: 2, kind: "aggregate", selectable, aggregateRefs}`. Each array position matches the rendered trace point. `null` means the point has no safe aggregate evidence. No aggregate is presented as one Excel cell.
- An `aggregateRef` identifies an immutable server-side snapshot of chart context, rendered value, calculation rule, source-run watermark, and exact revision-locked member `lineageRef`s. The frontend only displays this evidence; it never reconstructs contributors.

## API

- `GET /api/projects/{project}/aggregates/{aggregateRef}/provenance` returns the saved context, chart result, rule, observation counts, and freshness. `newerDataAvailable` means a newer committed source run exists, not necessarily that this particular point changed.
- `GET /api/projects/{project}/aggregates/{aggregateRef}/contributors?limit=50&cursor=…` returns ordered members, their roles/inclusion flags, exact `observationRef` and `lineageRef`, and an HMAC-signed opaque `nextCursor`. Limit: 1–100. The cursor is bound to one aggregate. Invalid cursors return 422.
- `GET /api/projects/{project}/observations/{observationRef}/revisions` returns revision summaries and opaque `revisionRef`, exact lineage where available, `importRef` and `attemptRef`.
- `GET /api/projects/{project}/imports/{importRef}` returns the committed workbook, hash, mode, date range, attempt reference and outcome counts for a run linked to the requested project.
- The Phase 1 exact provenance response gains `revision.revisionRef`, separate `revisionCurrent` and `sourcePresenceCurrent` flags, `import.importRef`/`attemptRef`, source freshness, and exact-linked validation issue references (`issueRef`). Existing fields are retained. Audit lookup still resolves the same `observationRef` + `lineageRef`.

Unknown/wrong-project refs return 404. Mismatched exact observation/lineage refs return 409. Legacy points without safe refs remain unselectable or show the existing no-provenance state; there is no date/metric/value heuristic join.

## Storage and compatibility

Migrations 005–006 add immutable aggregate snapshots/members, opaque public refs for revisions, attempts, runs and validation issues, explicit validation-to-presence links, and a cursor secret. Migration 006 also upgrades internal databases that applied an early 005 draft without the cursor-secret table. Previous Phase 1 refs and API consumers remain valid.

## Current boundaries

- Aggregate evidence is materialized on workspace requests with eligible chart points, so requests perform SQLite writes. The chart values are read from the already-rendered traces and are not recalculated by the lineage layer.
- The freshness flag is source-run level. It is a prompt to refresh/recheck, not proof that the selected point changed.
- Validation issues are linked only when their run + sheet + cell resolves to exactly one observation presence. Ambiguous or workbook-level issues are not attributed to a cell.
- Revision history is for one observation; it is not a full revision-history workspace or a comparison UI.
- A chart point with no complete lineage evidence has no aggregateRef. This is expected for legacy/incomplete data and for points without an actual numeric chart value.
