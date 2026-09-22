CREATE TABLE data_sources (
    source_id INTEGER PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'excel',
    minimum_data_date TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE source_artifacts (
    artifact_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id),
    source_file TEXT NOT NULL,
    archived_file_path TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    file_size INTEGER NOT NULL CHECK(file_size >= 0),
    received_at TEXT NOT NULL,
    UNIQUE(source_id, source_hash)
);

CREATE TABLE import_attempts (
    attempt_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id),
    artifact_id INTEGER NOT NULL REFERENCES source_artifacts(artifact_id),
    submitted_file_name TEXT NOT NULL,
    requested_mode TEXT NOT NULL CHECK(requested_mode IN ('full_snapshot', 'incremental')),
    parser_config_hash TEXT NOT NULL,
    import_contract_hash TEXT NOT NULL,
    import_contract_json TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'received', 'processing', 'duplicate', 'rejected', 'failed', 'committed'
    )),
    duplicate_of_run_id INTEGER REFERENCES import_runs(run_id),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    failure_code TEXT,
    failure_message TEXT
);

CREATE TABLE import_runs (
    run_id INTEGER PRIMARY KEY,
    attempt_id INTEGER NOT NULL UNIQUE REFERENCES import_attempts(attempt_id),
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id),
    artifact_id INTEGER NOT NULL REFERENCES source_artifacts(artifact_id),
    source_hash TEXT NOT NULL,
    parser_config_hash TEXT NOT NULL,
    import_contract_hash TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    import_mode TEXT NOT NULL CHECK(import_mode IN ('full_snapshot', 'incremental')),
    status TEXT NOT NULL CHECK(status IN ('pending', 'committed')),
    started_at TEXT NOT NULL,
    committed_at TEXT,
    minimum_data_date TEXT,
    maximum_data_date TEXT,
    input_record_count INTEGER NOT NULL DEFAULT 0 CHECK(input_record_count >= 0),
    accepted_key_count INTEGER NOT NULL DEFAULT 0 CHECK(accepted_key_count >= 0),
    inserted_count INTEGER NOT NULL DEFAULT 0 CHECK(inserted_count >= 0),
    updated_count INTEGER NOT NULL DEFAULT 0 CHECK(updated_count >= 0),
    unchanged_count INTEGER NOT NULL DEFAULT 0 CHECK(unchanged_count >= 0),
    restored_count INTEGER NOT NULL DEFAULT 0 CHECK(restored_count >= 0),
    deleted_count INTEGER NOT NULL DEFAULT 0 CHECK(deleted_count >= 0),
    lineage_changed_count INTEGER NOT NULL DEFAULT 0 CHECK(lineage_changed_count >= 0),
    duplicate_key_count INTEGER NOT NULL DEFAULT 0 CHECK(duplicate_key_count >= 0),
    rejected_record_count INTEGER NOT NULL DEFAULT 0 CHECK(rejected_record_count >= 0),
    error_count INTEGER NOT NULL DEFAULT 0 CHECK(error_count >= 0),
    warning_count INTEGER NOT NULL DEFAULT 0 CHECK(warning_count >= 0),
    manifest_json TEXT NOT NULL,
    UNIQUE(source_id, source_hash, parser_config_hash, import_contract_hash)
);

CREATE TABLE import_scopes (
    scope_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    sheet_name TEXT,
    project_key TEXT,
    project_id INTEGER REFERENCES projects(project_id),
    root_external_entity_key TEXT,
    root_entity_id INTEGER REFERENCES entities(entity_id),
    metric_code TEXT REFERENCES metrics(metric_code),
    date_from TEXT NOT NULL,
    date_to TEXT NOT NULL,
    is_complete INTEGER NOT NULL CHECK(is_complete IN (0, 1)),
    missing_policy TEXT NOT NULL CHECK(missing_policy IN ('ignore', 'tombstone')),
    scope_hash TEXT NOT NULL,
    CHECK(date_from <= date_to),
    UNIQUE(run_id, scope_hash)
);

CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id),
    project_key TEXT NOT NULL,
    current_revision_id INTEGER REFERENCES project_revisions(project_revision_id),
    first_seen_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    last_seen_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    UNIQUE(source_id, project_key)
);

CREATE TABLE project_revisions (
    project_revision_id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(project_id),
    run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    semantic_hash TEXT NOT NULL,
    project_label TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    UNIQUE(project_id, run_id)
);

CREATE TABLE entities (
    entity_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id),
    project_id INTEGER NOT NULL REFERENCES projects(project_id),
    parent_entity_id INTEGER REFERENCES entities(entity_id),
    current_revision_id INTEGER REFERENCES entity_revisions(entity_revision_id),
    first_seen_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    last_seen_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
);

CREATE TABLE entity_aliases (
    alias_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id),
    external_entity_key TEXT NOT NULL,
    entity_id INTEGER NOT NULL REFERENCES entities(entity_id),
    valid_from_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    valid_to_run_id INTEGER REFERENCES import_runs(run_id),
    alias_reason TEXT NOT NULL CHECK(alias_reason IN ('initial', 'rename', 'move', 'manual_merge'))
);

CREATE TABLE entity_revisions (
    entity_revision_id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(entity_id),
    run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    semantic_hash TEXT NOT NULL,
    external_entity_key TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    parent_entity_id INTEGER REFERENCES entities(entity_id),
    entity_level TEXT NOT NULL,
    entity_depth INTEGER NOT NULL CHECK(entity_depth >= 0),
    entity_label TEXT NOT NULL,
    entity_path TEXT NOT NULL,
    unit_raw TEXT,
    unit_original TEXT,
    unit_normalized TEXT,
    effective_unit TEXT,
    unit_source_level TEXT,
    unit_source_entity_id INTEGER REFERENCES entities(entity_id),
    parser_rule TEXT,
    parser_confidence TEXT,
    recorded_at TEXT NOT NULL,
    UNIQUE(entity_id, run_id)
);

CREATE TABLE metrics (
    metric_code TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    value_type TEXT NOT NULL,
    default_unit TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
);

CREATE TABLE observations (
    observation_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id),
    entity_id INTEGER NOT NULL REFERENCES entities(entity_id),
    metric_code TEXT NOT NULL REFERENCES metrics(metric_code),
    observed_date TEXT NOT NULL,
    current_revision_id INTEGER REFERENCES observation_revisions(revision_id),
    latest_presence_id INTEGER REFERENCES import_observation_presence(presence_id),
    first_seen_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    last_seen_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK(is_deleted IN (0, 1)),
    CHECK(length(observed_date) = 10),
    CHECK(observed_date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'),
    UNIQUE(source_id, entity_id, observed_date, metric_code)
);

CREATE TABLE observation_revisions (
    revision_id INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL REFERENCES observations(observation_id),
    run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    change_type TEXT NOT NULL CHECK(change_type IN ('insert', 'update', 'delete', 'restore')),
    semantic_hash TEXT NOT NULL,
    metric_original TEXT NOT NULL,
    metric_normalized TEXT NOT NULL,
    unit_normalized TEXT,
    effective_unit TEXT,
    raw_value_text TEXT,
    raw_value_type TEXT NOT NULL,
    value_numeric REAL,
    value_numeric_text TEXT,
    chart_value REAL,
    chart_value_text TEXT,
    display_value TEXT NOT NULL,
    number_format TEXT,
    value_kind TEXT NOT NULL,
    data_note TEXT,
    validation_status TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK(is_deleted IN (0, 1)),
    recorded_at TEXT NOT NULL,
    UNIQUE(observation_id, run_id)
);

CREATE TABLE import_observation_presence (
    presence_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
    observation_id INTEGER NOT NULL REFERENCES observations(observation_id),
    sheet_name TEXT NOT NULL,
    cell_address TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    lineage_hash TEXT NOT NULL,
    parser_rule TEXT,
    parser_confidence TEXT,
    presence_status TEXT NOT NULL CHECK(presence_status IN ('inserted', 'updated', 'unchanged', 'restored')),
    recorded_at TEXT NOT NULL,
    UNIQUE(run_id, observation_id)
);

CREATE TABLE validation_issues (
    issue_id INTEGER PRIMARY KEY,
    attempt_id INTEGER NOT NULL REFERENCES import_attempts(attempt_id),
    run_id INTEGER REFERENCES import_runs(run_id),
    severity TEXT NOT NULL CHECK(severity IN ('error', 'warning')),
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    sheet_name TEXT,
    cell_address TEXT,
    external_entity_key TEXT,
    observed_date TEXT,
    created_at TEXT NOT NULL
);

INSERT INTO metrics(metric_code, display_name, value_type, default_unit) VALUES
    ('total', 'Tổng số', 'count', NULL),
    ('error', 'Báo sai/Lỗi', 'count', NULL),
    ('error_rate', '% báo sai', 'percentage', '%');
