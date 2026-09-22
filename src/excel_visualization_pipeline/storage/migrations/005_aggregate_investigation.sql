CREATE TABLE aggregate_snapshots (
    aggregate_id INTEGER PRIMARY KEY,
    aggregate_ref TEXT NOT NULL UNIQUE,
    fingerprint TEXT NOT NULL UNIQUE,
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id),
    project_label TEXT NOT NULL,
    context_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    aggregation_json TEXT NOT NULL,
    source_run_id INTEGER REFERENCES import_runs(run_id),
    calculator_version INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE aggregate_snapshot_members (
    aggregate_id INTEGER NOT NULL REFERENCES aggregate_snapshots(aggregate_id),
    ordinal INTEGER NOT NULL,
    lineage_ref TEXT NOT NULL REFERENCES observation_lineage_snapshots(lineage_ref),
    role TEXT NOT NULL,
    included INTEGER NOT NULL CHECK(included IN (0, 1)),
    contribution_value REAL,
    note TEXT,
    PRIMARY KEY(aggregate_id, ordinal),
    UNIQUE(aggregate_id, role, lineage_ref)
);

CREATE INDEX idx_aggregate_members_lineage
    ON aggregate_snapshot_members(lineage_ref);

CREATE TABLE aggregate_cursor_secret (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    secret BLOB NOT NULL
);

INSERT INTO aggregate_cursor_secret(singleton, secret) VALUES (1, randomblob(32));

CREATE TABLE observation_revision_public_refs (
    revision_id INTEGER PRIMARY KEY REFERENCES observation_revisions(revision_id),
    revision_ref TEXT NOT NULL UNIQUE
);

INSERT INTO observation_revision_public_refs(revision_id, revision_ref)
SELECT revision_id, 'rev_' || lower(hex(randomblob(16)))
FROM observation_revisions;

CREATE TABLE import_attempt_public_refs (
    attempt_id INTEGER PRIMARY KEY REFERENCES import_attempts(attempt_id),
    attempt_ref TEXT NOT NULL UNIQUE
);

INSERT INTO import_attempt_public_refs(attempt_id, attempt_ref)
SELECT attempt_id, 'att_' || lower(hex(randomblob(16)))
FROM import_attempts;

CREATE TABLE import_run_public_refs (
    run_id INTEGER PRIMARY KEY REFERENCES import_runs(run_id),
    import_ref TEXT NOT NULL UNIQUE
);

INSERT INTO import_run_public_refs(run_id, import_ref)
SELECT run_id, 'imp_' || lower(hex(randomblob(16)))
FROM import_runs;

CREATE TABLE validation_issue_lineage_links (
    issue_id INTEGER PRIMARY KEY REFERENCES validation_issues(issue_id),
    presence_id INTEGER NOT NULL REFERENCES import_observation_presence(presence_id)
);

INSERT INTO validation_issue_lineage_links(issue_id, presence_id)
SELECT vi.issue_id, p.presence_id
FROM validation_issues vi
JOIN import_observation_presence p
  ON p.run_id = vi.run_id
 AND p.sheet_name = vi.sheet_name
 AND p.cell_address = vi.cell_address
WHERE vi.run_id IS NOT NULL
  AND vi.sheet_name IS NOT NULL
  AND vi.cell_address IS NOT NULL
  AND (
      SELECT COUNT(*)
      FROM import_observation_presence candidate
      WHERE candidate.run_id = vi.run_id
        AND candidate.sheet_name = vi.sheet_name
        AND candidate.cell_address = vi.cell_address
  ) = 1;
