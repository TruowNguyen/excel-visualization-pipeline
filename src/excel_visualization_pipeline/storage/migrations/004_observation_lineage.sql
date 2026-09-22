CREATE TABLE observation_public_refs (
    observation_id INTEGER PRIMARY KEY REFERENCES observations(observation_id),
    observation_ref TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE observation_lineage_snapshots (
    presence_id INTEGER PRIMARY KEY REFERENCES import_observation_presence(presence_id),
    lineage_ref TEXT NOT NULL UNIQUE,
    observation_id INTEGER NOT NULL REFERENCES observations(observation_id),
    revision_id INTEGER NOT NULL REFERENCES observation_revisions(revision_id),
    created_at TEXT NOT NULL,
    UNIQUE(observation_id, revision_id, presence_id)
);

INSERT INTO observation_public_refs(observation_id, observation_ref, created_at)
SELECT
    o.observation_id,
    'obs_' || lower(hex(randomblob(16))),
    COALESCE(r.recorded_at, CURRENT_TIMESTAMP)
FROM observations o
LEFT JOIN observation_revisions r ON r.revision_id = o.current_revision_id;

INSERT INTO observation_lineage_snapshots(
    presence_id, lineage_ref, observation_id, revision_id, created_at
)
SELECT
    p.presence_id,
    'lin_' || lower(hex(randomblob(16))),
    p.observation_id,
    (
        SELECT r.revision_id
        FROM observation_revisions r
        WHERE r.observation_id = p.observation_id
          AND r.run_id <= p.run_id
        ORDER BY r.run_id DESC, r.revision_id DESC
        LIMIT 1
    ),
    p.recorded_at
FROM import_observation_presence p
WHERE EXISTS (
    SELECT 1
    FROM observation_revisions r
    WHERE r.observation_id = p.observation_id
      AND r.run_id <= p.run_id
);

CREATE INDEX idx_lineage_snapshots_observation
    ON observation_lineage_snapshots(observation_id, revision_id);

DROP VIEW v_current_observations;

CREATE VIEW v_current_observations AS
SELECT
    o.observation_id,
    opr.observation_ref,
    ols.lineage_ref,
    r.revision_id,
    p.presence_id,
    p.run_id AS lineage_run_id,
    o.source_id,
    e.project_id,
    e.project_label,
    e.entity_id,
    e.parent_entity_id,
    e.entity_level,
    e.entity_depth,
    e.entity_label,
    e.entity_path,
    e.unit_raw,
    e.unit_original,
    e.unit_normalized,
    e.effective_unit,
    e.unit_source_level,
    e.unit_source_entity_id,
    o.observed_date AS date,
    r.metric_original,
    r.metric_normalized,
    o.metric_code,
    r.raw_value_text AS raw_value,
    r.raw_value_type,
    r.value_numeric,
    r.chart_value,
    r.display_value,
    r.number_format,
    r.value_kind,
    r.data_note,
    p.sheet_name,
    p.cell_address,
    p.source_row,
    p.source_file,
    p.source_hash,
    p.parser_rule,
    p.parser_confidence,
    r.validation_status,
    o.first_seen_run_id,
    o.last_seen_run_id
FROM observations o
JOIN observation_revisions r ON r.revision_id = o.current_revision_id
JOIN import_observation_presence p ON p.presence_id = o.latest_presence_id
LEFT JOIN observation_public_refs opr ON opr.observation_id = o.observation_id
LEFT JOIN observation_lineage_snapshots ols ON ols.presence_id = p.presence_id
JOIN v_current_entities e ON e.db_entity_id = o.entity_id
WHERE o.is_deleted = 0 AND r.is_deleted = 0;
