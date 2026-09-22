CREATE VIEW v_current_projects AS
SELECT
    p.project_id AS db_project_id,
    p.source_id,
    p.project_key,
    pr.project_label,
    pr.sheet_name,
    p.first_seen_run_id,
    p.last_seen_run_id,
    p.is_active
FROM projects p
JOIN project_revisions pr ON pr.project_revision_id = p.current_revision_id
WHERE p.is_active = 1;

CREATE VIEW v_current_entities AS
SELECT
    e.entity_id AS db_entity_id,
    e.source_id,
    p.project_key AS project_id,
    pr.project_label,
    er.external_entity_key AS entity_id,
    per.external_entity_key AS parent_entity_id,
    er.entity_level,
    er.entity_depth,
    er.entity_label,
    er.entity_path,
    er.sheet_name,
    er.source_row,
    er.unit_raw,
    er.unit_original,
    er.unit_normalized,
    er.effective_unit,
    er.unit_source_level,
    uer.external_entity_key AS unit_source_entity_id,
    er.parser_rule,
    er.parser_confidence,
    e.first_seen_run_id,
    e.last_seen_run_id,
    e.is_active
FROM entities e
JOIN entity_revisions er ON er.entity_revision_id = e.current_revision_id
JOIN projects p ON p.project_id = e.project_id
JOIN project_revisions pr ON pr.project_revision_id = p.current_revision_id
LEFT JOIN entities pe ON pe.entity_id = e.parent_entity_id
LEFT JOIN entity_revisions per ON per.entity_revision_id = pe.current_revision_id
LEFT JOIN entities ue ON ue.entity_id = er.unit_source_entity_id
LEFT JOIN entity_revisions uer ON uer.entity_revision_id = ue.current_revision_id
WHERE e.is_active = 1 AND p.is_active = 1;

CREATE VIEW v_current_observations AS
SELECT
    o.observation_id,
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
JOIN v_current_entities e ON e.db_entity_id = o.entity_id
WHERE o.is_deleted = 0 AND r.is_deleted = 0;

CREATE VIEW v_import_history AS
SELECT
    a.attempt_id,
    a.source_id,
    a.submitted_file_name,
    sa.source_hash,
    a.requested_mode,
    a.parser_version,
    a.status AS attempt_status,
    a.started_at,
    a.finished_at,
    a.duplicate_of_run_id,
    a.failure_code,
    a.failure_message,
    r.run_id,
    r.committed_at,
    r.input_record_count,
    r.accepted_key_count,
    r.inserted_count,
    r.updated_count,
    r.unchanged_count,
    r.restored_count,
    r.deleted_count,
    r.lineage_changed_count,
    r.error_count,
    r.warning_count
FROM import_attempts a
JOIN source_artifacts sa ON sa.artifact_id = a.artifact_id
LEFT JOIN import_runs r ON r.attempt_id = a.attempt_id;
