CREATE INDEX idx_artifacts_source_hash
ON source_artifacts(source_id, source_hash);

CREATE INDEX idx_attempts_source_started
ON import_attempts(source_id, started_at DESC);

CREATE INDEX idx_runs_source_committed
ON import_runs(source_id, committed_at DESC);

CREATE INDEX idx_scopes_run
ON import_scopes(run_id);

CREATE INDEX idx_projects_source_active
ON projects(source_id, is_active);

CREATE INDEX idx_entities_project
ON entities(project_id, is_active);

CREATE INDEX idx_entities_parent
ON entities(parent_entity_id, is_active);

CREATE UNIQUE INDEX uq_active_entity_alias
ON entity_aliases(source_id, external_entity_key)
WHERE valid_to_run_id IS NULL;

CREATE INDEX idx_obs_entity_date
ON observations(entity_id, observed_date)
WHERE is_deleted = 0;

CREATE INDEX idx_obs_date_metric
ON observations(observed_date, metric_code)
WHERE is_deleted = 0;

CREATE INDEX idx_obs_source_current
ON observations(source_id, is_deleted, observed_date);

CREATE INDEX idx_revisions_observation
ON observation_revisions(observation_id, revision_id);

CREATE INDEX idx_presence_observation
ON import_observation_presence(observation_id, run_id);

CREATE INDEX idx_issues_attempt
ON validation_issues(attempt_id, severity);
